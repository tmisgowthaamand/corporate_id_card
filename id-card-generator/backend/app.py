import os
import io
import json
import zipfile
import base64
import math
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import qrcode
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson import ObjectId

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

app = Flask(__name__, 
            template_folder=os.path.join(FRONTEND_DIR, 'templates'),
            static_folder=os.path.join(FRONTEND_DIR, 'static'))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://corporate-id-card.vercel.app')
CORS(app, resources={r"/*": {"origins": FRONTEND_URL}})

# On Vercel, the filesystem is read-only except for /tmp
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp/uploads'
    OUTPUT_FOLDER = '/tmp/output'
    STATIC_GENERATED = '/tmp/generated'
else:
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
    STATIC_GENERATED = os.path.join(FRONTEND_DIR, 'static', 'generated')

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, STATIC_GENERATED]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# ── MongoDB Connection ──
ENV_PATH = os.path.join(BASE_DIR, '.env')
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

MONGO_URI = os.environ.get('MONGO_URI', '')
MONGO_DB = os.environ.get('MONGO_DB', 'id_card_generator')

db = None
try:
    if MONGO_URI:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGO_DB]
        print(f'[MongoDB] Connected to database: {MONGO_DB}')
    else:
        print('[MongoDB] No MONGO_URI found, running without database')
except Exception as e:
    print(f'[MongoDB] Connection failed: {e}')
    db = None


def mongo_serialize(doc):
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None
    doc = dict(doc)
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc


def allowed_file(filename, extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions


@app.route('/')
def index():
    return render_template('index.html')




@app.route('/upload-excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
        return jsonify({'error': 'Invalid file type. Please upload .xlsx file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        df = pd.read_excel(filepath)
        df = df.fillna('')
        employees = df.to_dict('records')
        for emp in employees:
            for key, value in emp.items():
                if not isinstance(value, str):
                    emp[key] = str(value)

        # Save to MongoDB
        if db is not None:
            collection = db['employees']
            for emp in employees:
                emp['uploaded_at'] = datetime.utcnow().isoformat()
                collection.update_one(
                    {'employee_id': emp.get('employee_id')},
                    {'$set': emp},
                    upsert=True
                )
            print(f'[MongoDB] Saved {len(employees)} employees to database')

        return jsonify({'success': True, 'employees': employees, 'count': len(employees)})
    except Exception as e:
        return jsonify({'error': f'Error reading Excel: {str(e)}'}), 400


@app.route('/upload-photos', methods=['POST'])
def upload_photos():
    if 'photos' not in request.files:
        return jsonify({'error': 'No photos uploaded'}), 400

    files = request.files.getlist('photos')
    uploaded = []

    for file in files:
        if file and allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            uploaded.append(filename)

    return jsonify({'success': True, 'uploaded': uploaded, 'count': len(uploaded)})


@app.route('/generate', methods=['POST'])
def generate_cards():
    data = request.get_json()
    employees = data.get('employees', [])

    if not employees:
        return jsonify({'error': 'No employee data provided'}), 400

    generated = []
    for i, emp in enumerate(employees):
        try:
            front_path = generate_front_card(emp)
            back_path = generate_back_card(emp)
            card_info = {
                'employee_id': emp.get('employee_id', f'EMP-{i+1}'),
                'name': emp.get('name', ''),
                'front': os.path.basename(front_path),
                'back': os.path.basename(back_path)
            }
            generated.append(card_info)

            # Log generation in MongoDB
            if db is not None:
                db['generated_cards'].update_one(
                    {'employee_id': card_info['employee_id']},
                    {'$set': {
                        **card_info,
                        'generated_at': datetime.utcnow().isoformat(),
                        'dpi': 300,
                        'format': 'PNG'
                    }},
                    upsert=True
                )
        except Exception as e:
            print(f"Error generating card for {emp.get('name', 'unknown')}: {e}")
            continue

    return jsonify({'success': True, 'generated': generated, 'count': len(generated)})


@app.route('/generate-single', methods=['POST'])
def generate_single():
    try:
        emp = {
            'name': request.form.get('name', ''),
            'employee_id': request.form.get('employee_id', ''),
            'designation': request.form.get('designation', ''),
            'department': request.form.get('department', ''),
            'valid_till': request.form.get('valid_till', 'Dec 2027'),
            'blood_group': request.form.get('blood_group', 'O+'),
            'mobile': request.form.get('mobile', ''),
            'email': request.form.get('email', ''),
            'company': request.form.get('company', 'Acme Corp International'),
            'website': request.form.get('website', 'www.acmecorp.com'),
            'address': request.form.get('address', ''),
            'photo': '',
        }

        # Handle photo upload
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename:
                filename = secure_filename(f"{emp['employee_id']}_{photo.filename}")
                photo_path = os.path.join(UPLOAD_FOLDER, filename)
                photo.save(photo_path)
                emp['photo'] = filename

        front_path = generate_front_card(emp)
        back_path = generate_back_card(emp)

        front_file = os.path.basename(front_path)
        back_file = os.path.basename(back_path)

        # Save to MongoDB
        if db is not None:
            db['employees'].update_one(
                {'employee_id': emp['employee_id']},
                {'$set': {**emp, 'uploaded_at': datetime.utcnow().isoformat()}},
                upsert=True
            )
            db['generated_cards'].update_one(
                {'employee_id': emp['employee_id']},
                {'$set': {
                    'employee_id': emp['employee_id'],
                    'name': emp['name'],
                    'front': front_file,
                    'back': back_file,
                    'generated_at': datetime.utcnow().isoformat(),
                    'dpi': 300,
                    'format': 'PNG'
                }},
                upsert=True
            )

        return jsonify({'success': True, 'front': front_file, 'back': back_file})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000')


@app.route('/card/<emp_id>')
def verify_card(emp_id):
    """Public verification page shown when QR code is scanned."""
    # Try to get employee data from MongoDB
    emp_data = None
    if db is not None:
        emp_data = db['employees'].find_one({'employee_id': emp_id})
        if emp_data:
            emp_data = mongo_serialize(emp_data)

    # Check if card images exist
    emp_id_safe = emp_id.replace(' ', '_')
    front_file = f'{emp_id_safe}_front.png'
    back_file = f'{emp_id_safe}_back.png'
    has_front = os.path.exists(os.path.join(OUTPUT_FOLDER, front_file))
    has_back = os.path.exists(os.path.join(OUTPUT_FOLDER, back_file))

    return render_template('verify.html',
                           emp_id=emp_id,
                           emp=emp_data,
                           front_file=front_file if has_front else None,
                           back_file=back_file if has_back else None,
                           has_card=has_front or has_back)


@app.route('/api/employee/<emp_id>')
def get_employee(emp_id):
    """Fetch a single employee by ID for loading into the form."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503

    emp = db['employees'].find_one({'employee_id': emp_id})
    if emp:
        return jsonify(mongo_serialize(emp))
    return jsonify({'error': 'Employee not found'}), 404


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


@app.route('/preview/<filename>')
def preview_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)


@app.route('/download-combined', methods=['POST'])
def download_combined():
    data = request.get_json()
    front = data.get('front', '')
    back = data.get('back', '')

    front_path = os.path.join(OUTPUT_FOLDER, front)
    back_path = os.path.join(OUTPUT_FOLDER, back)

    if not os.path.exists(front_path) or not os.path.exists(back_path):
        return jsonify({'error': 'Card files not found'}), 404

    front_img = Image.open(front_path)
    back_img = Image.open(back_path)

    # Side by side with a small gap
    gap = 40
    combined_w = front_img.width + gap + back_img.width
    combined_h = max(front_img.height, back_img.height)
    combined = Image.new('RGB', (combined_w, combined_h), (255, 255, 255))
    combined.paste(front_img.convert('RGB'), (0, 0))
    combined.paste(back_img.convert('RGB'), (front_img.width + gap, 0))

    buf = io.BytesIO()
    combined.save(buf, 'PNG', dpi=(300, 300))
    buf.seek(0)

    emp_id = front.replace('_front.png', '')
    return send_file(buf, mimetype='image/png', as_attachment=True,
                     download_name=f'{emp_id}_id_card.png')


@app.route('/download-zip', methods=['POST'])
def download_zip():
    data = request.get_json()
    files = data.get('files', [])

    if not files:
        all_files = os.listdir(OUTPUT_FOLDER)
        files = [f for f in all_files if f.endswith('.png')]

    if not files:
        return jsonify({'error': 'No files to download'}), 400

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename in files:
            filepath = os.path.join(OUTPUT_FOLDER, filename)
            if os.path.exists(filepath):
                zip_file.write(filepath, filename)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='id_cards.zip'
    )


@app.route('/get-generated')
def get_generated():
    files = []
    if os.path.exists(OUTPUT_FOLDER):
        for f in sorted(os.listdir(OUTPUT_FOLDER)):
            if f.endswith('.png'):
                files.append(f)
    return jsonify({'files': files})



def generate_qr_code(data, size=200):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1a1a1a", back_color="white").convert('RGB')
    qr_img = qr_img.resize((size, size), Image.LANCZOS)
    return qr_img


def get_font(name, size):
    font_map = {
        'playfair': 'PlayfairDisplay',
        'playfair-bold': 'PlayfairDisplay-Bold',
        'dmsans': 'DMSans',
        'dmsans-medium': 'DMSans-Medium',
        'dmsans-semibold': 'DMSans-SemiBold',
        'dmsans-bold': 'DMSans-Bold',
        'montserrat': 'Montserrat',
        'poppins': 'Poppins',
    }
    try:
        font_dir = os.path.join(FRONTEND_DIR, 'static', 'fonts')
        font_file = os.path.join(font_dir, f'{font_map.get(name, "DMSans")}-Regular.ttf')
        if os.path.exists(font_file):
            return ImageFont.truetype(font_file, size)
    except:
        pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()


def text_center_x(draw, text, font, card_w):
    bbox = draw.textbbox((0, 0), text, font=font)
    return (card_w - (bbox[2] - bbox[0])) // 2


def get_initials(company):
    words = company.split()
    return (words[0][0] + words[1][0]).upper() if len(words) >= 2 else words[0][:2].upper()


def draw_circle_outline_aa(base_img, cx, cy, r, stroke_w, color_rgba):
    """Draw anti-aliased circle outline using RGBA overlay at 2x then downscale."""
    s = 2
    sz = (r + stroke_w) * 2 * s + 4 * s
    overlay = Image.new('RGBA', (sz, sz), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    c = sz // 2
    od.ellipse([c - r * s, c - r * s, c + r * s, c + r * s],
               outline=color_rgba, width=stroke_w * s)
    overlay = overlay.resize((sz // s, sz // s), Image.LANCZOS)
    px = cx - overlay.width // 2
    py = cy - overlay.height // 2
    base_img.paste(overlay, (px, py), overlay)


# ── Exact mapping from HTML: 240px x 370px ──
# To get high quality, we multiply by 3
# 240 * 3 = 720
# 370 * 3 = 1110
CARD_W = 720
CARD_H = 1110
S = CARD_W / 240.0  # exactly 3.0

# ── Standardized color tokens ──
GOLD = '#E8A820'
GOLD_RGB = (232, 168, 32)
CARD_BG = (248, 246, 240)  # #f8f6f0
TEXT_PRIMARY = '#1a1a1a'
TEXT_MUTED = '#888888'
TEXT_LABEL = '#aaaaaa'
TEXT_VALUE = '#222222'

def format_blood_group(bg):
    """Convert O+, A-, B+ etc. to O +ve, A -ve, B +ve format."""
    bg = bg.strip()
    if not bg:
        return bg
    if bg.endswith('+ve') or bg.endswith('-ve'):
        return bg
    if bg.endswith('+'):
        return bg[:-1] + ' +ve'
    if bg.endswith('-'):
        return bg[:-1] + ' -ve'
    return bg

def generate_front_card(emp):
    img = Image.new('RGBA', (CARD_W, CARD_H), CARD_BG + (255,))
    draw = ImageDraw.Draw(img)

    # ── Gold header — height 110px in HTML ──
    header_h = int(110 * S)
    draw.rectangle([0, 0, CARD_W, header_h], fill=GOLD)

    # ── Wave separator (28px viewBox height) ──
    wave_h = int(28 * S)
    wave_img = Image.new('RGBA', (CARD_W, wave_h), (0, 0, 0, 0))
    # M0 28 L0 14 Q60 0 120 14 Q180 28 240 14 L240 28 Z
    for x in range(CARD_W):
        t = x / CARD_W * 240.0
        if t <= 120:
            tt = t / 120.0
            y_norm = (1 - tt) * (1 - tt) * 14 + 2 * (1 - tt) * tt * 0 + tt * tt * 14
        else:
            tt = (t - 120) / 120.0
            y_norm = (1 - tt) * (1 - tt) * 14 + 2 * (1 - tt) * tt * 28 + tt * tt * 14
            
        y_px = int(y_norm / 28.0 * wave_h)
        y_px = max(0, min(wave_h - 1, y_px))
        for y in range(y_px, wave_h):
            wave_img.putpixel((x, y), CARD_BG + (255,))
        for y in range(0, y_px):
            wave_img.putpixel((x, y), GOLD_RGB + (255,))
    img.paste(wave_img, (0, header_h - wave_h), wave_img)
    draw = ImageDraw.Draw(img)

    # ── Lanyard hole: width 28px, height 14px ──
    hole_w = int(28 * S)
    hole_h = int(14 * S)
    hole_x = (CARD_W - hole_w) // 2
    draw.rounded_rectangle([hole_x, -int(1 * S), hole_x + hole_w, hole_h],
                           radius=hole_h // 2, fill='#2a2a2a')

    # ── padding: 18px 18px 0 (top header) ──
    pad = int(18 * S)

    # ── Company logo circle — 34x34 ──
    company = emp.get('company', 'Acme Corp')
    initials = get_initials(company)

    logo_r = int(17 * S)
    logo_cx = pad + logo_r
    logo_cy = pad + logo_r

    draw_circle_outline_aa(img, logo_cx, logo_cy, logo_r, int(2 * S),
                           (255, 255, 255, 230))
    overlay_logo = Image.new('RGBA', (logo_r * 2, logo_r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(overlay_logo).ellipse([0, 0, logo_r * 2, logo_r * 2],
                                          fill=(255, 255, 255, 38))
    img.paste(overlay_logo, (logo_cx - logo_r, logo_cy - logo_r), overlay_logo)

    draw = ImageDraw.Draw(img)
    font_logo = get_font('playfair', int(14 * S))
    bbox = draw.textbbox((0, 0), initials, font=font_logo)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((logo_cx - tw // 2, logo_cy - th // 2 - int(2 * S)), initials,
              fill='white', font=font_logo)

    # ── Company name (next to logo) — 10px, 600, max-width 120px ──
    font_org = get_font('dmsans-semibold', int(10 * S))
    max_org_w = int(120 * S)
    org_x = logo_cx + logo_r + int(6 * S)
    org_lines = _wrap_text(draw, company, font_org, max_org_w)
    org_y = logo_cy - int(8 * S)
    for ol in org_lines:
        draw.text((org_x, org_y), ol, fill=(255, 255, 255, 230), font=font_org)
        org_y += int(draw.textbbox((0, 0), ol, font=font_org)[3] * 1.3)

    # ── EMPLOYEE badge — 9px, letter-spacing 1.5px, padding 3px 8px ──
    card_type = emp.get('card_type', 'EMPLOYEE').upper()
    font_badge = get_font('dmsans-semibold', int(9 * S))
    bb = draw.textbbox((0, 0), card_type, font=font_badge)
    badge_tw = bb[2] - bb[0]
    badge_pad_x = int(8 * S)
    badge_pad_y = int(3 * S)
    badge_h = int(bb[3] + badge_pad_y * 2)
    badge_w = badge_tw + badge_pad_x * 2
    badge_x = CARD_W - pad - badge_w
    badge_y = pad + int(4 * S)
    badge_overlay = Image.new('RGBA', (badge_w, badge_h), (0, 0, 0, 0))
    ImageDraw.Draw(badge_overlay).rounded_rectangle(
        [0, 0, badge_w, badge_h], radius=int(10 * S), fill=(255, 255, 255, 51))
    img.paste(badge_overlay, (badge_x, badge_y), badge_overlay)
    draw = ImageDraw.Draw(img)
    draw.text((badge_x + badge_pad_x, badge_y + badge_pad_y - int(1*S)), card_type,
              fill=(255, 255, 255, 217), font=font_badge)

    # ── FRONT BODY ──
    # body padding 14px 18px 18px
    body_pad_top = int(14 * S)
    body_pad = int(18 * S)
    body_y = header_h + body_pad_top - int(14 * S) # adjusted to match HTML where wave doesn't add height

    font_name = get_font('playfair-bold', int(17 * S))
    font_role = get_font('dmsans-semibold', int(10 * S))
    font_dept = get_font('dmsans', int(10 * S))

    name = emp.get('name', 'Employee Name')
    designation = emp.get('designation', 'Designation')
    department = emp.get('department', 'Department')

    # ── Photo box — 76x90, border-radius 10px, 2.5px solid #E8A820 ──
    photo_w = int(76 * S)
    photo_h = int(90 * S)
    photo_x = CARD_W - body_pad - photo_w
    photo_y = body_y + int(5*S)

    border = int(2.5 * S)
    draw.rounded_rectangle([photo_x - border, photo_y - border,
                            photo_x + photo_w + border, photo_y + photo_h + border],
                           radius=int(10 * S), fill=GOLD)
    inner_r = int(10 * S) - border
    inner_img = Image.new('RGBA', (photo_w, photo_h), (0, 0, 0, 0))
    # background: linear-gradient(135deg, #e0d5c0, #c8bda0)
    for py_off in range(photo_h):
        frac = py_off / max(1, photo_h - 1)
        r = int(224 + (200 - 224) * frac)
        g = int(213 + (189 - 213) * frac)
        b = int(192 + (160 - 192) * frac)
        for px_off in range(photo_w):
            inner_img.putpixel((px_off, py_off), (r, g, b, 255))
    inner_mask = Image.new('L', (photo_w, photo_h), 0)
    ImageDraw.Draw(inner_mask).rounded_rectangle([0, 0, photo_w, photo_h],
                                                   radius=inner_r, fill=255)
    inner_img.putalpha(inner_mask)
    img.paste(inner_img, (photo_x, photo_y), inner_img)
    draw = ImageDraw.Draw(img)

    photo_file = emp.get('photo', '')
    photo_path = os.path.join(UPLOAD_FOLDER, photo_file)
    if photo_file and os.path.exists(photo_path):
        try:
            emp_photo = Image.open(photo_path).convert('RGBA')
            src_w, src_h = emp_photo.size
            target_ratio = photo_w / photo_h
            src_ratio = src_w / src_h
            if src_ratio > target_ratio:
                new_w = int(src_h * target_ratio)
                left = (src_w - new_w) // 2
                emp_photo = emp_photo.crop((left, 0, left + new_w, src_h))
            elif src_ratio < target_ratio:
                new_h = int(src_w / target_ratio)
                emp_photo = emp_photo.crop((0, 0, src_w, new_h))
            emp_photo = emp_photo.resize((photo_w, photo_h), Image.LANCZOS)
            mask = Image.new('L', (photo_w, photo_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [0, 0, photo_w, photo_h], radius=int(10 * S) - border, fill=255)
            img.paste(emp_photo, (photo_x, photo_y), mask)
            draw = ImageDraw.Draw(img)
        except:
            pass # keep placeholder

    # ── Text to left of photo ──
    max_text_w = photo_x - body_pad - int(12 * S)
    name_lines = _wrap_text(draw, name, font_name, max_text_w)
    
    # Align bottom of text with photo, but in HTML they are align-items flex-end
    cur_y = photo_y + photo_h - int(38 * S) - (len(name_lines)-1)*int(17*S*1.2)
    for line in name_lines:
        draw.text((body_pad, cur_y), line, fill=TEXT_PRIMARY, font=font_name)
        cur_y += int(draw.textbbox((0, 0), line, font=font_name)[3] * 1.2)

    cur_y += int(3 * S)
    role_text = designation.upper()
    role_lines = _wrap_text(draw, role_text, font_role, max_text_w)
    for line in role_lines:
        draw.text((body_pad, cur_y), line, fill=GOLD, font=font_role)
        cur_y += int(draw.textbbox((0, 0), line, font=font_role)[3] * 1.3)

    cur_y += int(1 * S)
    draw.text((body_pad, cur_y), department, fill=TEXT_MUTED, font=font_dept)

    # ── Divider ──
    div_y = photo_y + photo_h + int(12 * S)
    for x in range(body_pad, CARD_W - body_pad):
        frac = (x - body_pad) / max(1, (CARD_W - 2 * body_pad))
        alpha = int(255 * (1 - frac * 0.9))
        draw.point((x, div_y), fill=GOLD_RGB + (alpha,))

    # ── Details grid — 8px 12px gap ──
    grid_y = div_y + int(12 * S)
    font_label = get_font('dmsans-semibold', int(8 * S))
    font_value = get_font('dmsans-medium', int(10 * S))
    col2_x = CARD_W // 2 + int(6 * S)
    row_gap = int(24 * S)

    blood = format_blood_group(emp.get('blood_group', 'O+'))
    mobile = emp.get('mobile', '')
    if len(mobile) == 10:
        mobile_fmt = f"+91 {mobile[:5]} {mobile[5:]}"
    else:
        mobile_fmt = f"+91 {mobile}"

    details = [
        (body_pad, grid_y, "EMPLOYEE ID", emp.get('employee_id', 'EMP-0000')),
        (col2_x, grid_y, "VALID UNTIL", emp.get('valid_till', 'Dec 2025')),
        (body_pad, grid_y + row_gap, "BLOOD GROUP", blood),
        (col2_x, grid_y + row_gap, "CONTACT", mobile_fmt),
    ]
    label_val_gap = int(1 * S)
    for dx, dy, label, value in details:
        draw.text((dx, dy), label, fill=TEXT_LABEL, font=font_label)
        lh = draw.textbbox((0, 0), label, font=font_label)[3]
        draw.text((dx, dy + lh + label_val_gap), value, fill=TEXT_VALUE, font=font_value)

    # ── Bottom section ──
    bottom_y = CARD_H - int(18 * S) - int(56 * S) - int(12 * S)
    qr_size = int(56 * S)

    # QR box — 56x56
    qr_pad = int(4 * S)
    draw.rounded_rectangle([body_pad, bottom_y,
                            body_pad + qr_size, bottom_y + qr_size],
                           radius=int(6 * S), fill='white', outline='#e8e0cc',
                           width=max(1, int(1 * S)))

    emp_id = emp.get('employee_id', 'EMP-0000')
    qr_url = f"{BASE_URL}/card/{emp_id}"
    qr_img = generate_qr_code(qr_url, qr_size - qr_pad*2)
    img.paste(qr_img, (body_pad + qr_pad, bottom_y + qr_pad))
    draw = ImageDraw.Draw(img)

    # Employee ID right-aligned
    id_x = CARD_W - body_pad
    font_id_label = get_font('dmsans-semibold', int(8 * S))
    font_id_value = get_font('dmsans-bold', int(11 * S))

    id_label_y = bottom_y + int(32 * S)
    bb_label = draw.textbbox((0, 0), "EMPLOYEE ID", font=font_id_label)
    draw.text((id_x - (bb_label[2] - bb_label[0]), id_label_y),
              "EMPLOYEE ID", fill=TEXT_LABEL, font=font_id_label)
              
    id_val = emp_id.split('-')[-1] if '-' in emp_id else emp_id
    id_val = f"EMP-{id_val}" if id_val.isdigit() else emp_id
    bb_val = draw.textbbox((0, 0), id_val, font=font_id_value)
    draw.text((id_x - (bb_val[2] - bb_val[0]), id_label_y + bb_label[3] + label_val_gap),
              id_val, fill=TEXT_PRIMARY, font=font_id_value)

    # ── Website ──
    font_web = get_font('dmsans-semibold', int(8 * S))
    website = emp.get('website', 'www.acmecorp.com')
    web_x = text_center_x(draw, website, font_web, CARD_W)
    draw.text((web_x, CARD_H - int(18 * S)), website, fill=GOLD, font=font_web)

    corner_r = int(18 * S)
    final = _apply_rounded_corners(img, corner_r)

    emp_id_safe = emp_id.replace(' ', '_')
    output_path = os.path.join(OUTPUT_FOLDER, f'{emp_id_safe}_front.png')
    final.convert('RGB').save(output_path, 'PNG', dpi=(300, 300))
    return output_path

def generate_back_card(emp):
    img = Image.new('RGBA', (CARD_W, CARD_H), GOLD_RGB + (255,))
    draw = ImageDraw.Draw(img)
    pad = int(18 * S)

    # ── Decorative pattern — opacity 0.12 ──
    pat_alpha = int(255 * 0.12)
    draw_circle_outline_aa(img, int(180 * S), int(80 * S), int(100 * S),
                           int(40 * S), (255, 255, 255, pat_alpha))
    draw_circle_outline_aa(img, int(60 * S), int(300 * S), int(80 * S),
                           int(30 * S), (255, 255, 255, pat_alpha))
    draw = ImageDraw.Draw(img)
    # The path: M40 180 Q120 120 200 180 Q280 240 200 300
    # Let's approximate it with an arc
    draw.arc([int(40*S), int(120*S), int(280*S), int(300*S)], 180, 90, fill=(255,255,255,pat_alpha), width=int(20*S))

    # ── Logo circle ──
    company = emp.get('company', 'Acme Corp')
    initials = get_initials(company)
    logo_r = int(22 * S)
    logo_cx = CARD_W // 2
    logo_cy = int(24 * S) + logo_r

    draw_circle_outline_aa(img, logo_cx, logo_cy, logo_r, int(2 * S),
                           (255, 255, 255, 153))
    overlay_bg = Image.new('RGBA', (logo_r * 2, logo_r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(overlay_bg).ellipse([0, 0, logo_r * 2, logo_r * 2],
                                        fill=(255, 255, 255, 38))
    img.paste(overlay_bg, (logo_cx - logo_r, logo_cy - logo_r), overlay_bg)
    draw = ImageDraw.Draw(img)

    font_logo = get_font('playfair', int(16 * S))
    bb = draw.textbbox((0, 0), initials, font=font_logo)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((logo_cx - tw // 2, logo_cy - th // 2 - int(2 * S)),
              initials, fill='white', font=font_logo)

    # ── Terms & Conditions ──
    y = logo_cy + logo_r + int(16 * S)
    font_section = get_font('dmsans-bold', int(9 * S))
    font_terms = get_font('dmsans', int(9 * S))
    line_h = int(9 * S * 1.6)

    draw.text((pad, y), "TERMS & CONDITIONS",
              fill=(255, 255, 255, 178), font=font_section)
    y += int(16 * S)

    terms_1 = (
        "This card is the property of the issuing organization. "
        "If found, please return it to the address below. "
        "Unauthorized use of this card is strictly prohibited."
    )
    y = _draw_wrapped_text(draw, terms_1, pad, y, CARD_W - 2 * pad,
                           font_terms, (255, 255, 255, 217), line_h)
    y += int(8 * S)

    terms_2 = (
        "The cardholder must report loss or damage immediately. "
        "This card grants access only to authorized areas as per "
        "the holder's designation."
    )
    y = _draw_wrapped_text(draw, terms_2, pad, y, CARD_W - 2 * pad,
                           font_terms, (255, 255, 255, 217), line_h)

    # ── Divider ──
    y += int(10 * S)
    draw.line([pad, y, CARD_W - pad, y],
              fill=(255, 255, 255, 64), width=max(1, int(1 * S)))
    y += int(10 * S)

    terms_3 = (
        "This ID is valid for the period shown on the front. "
        "Management reserves the right to revoke access at any time "
        "without prior notice."
    )
    y = _draw_wrapped_text(draw, terms_3, pad, y, CARD_W - 2 * pad,
                           font_terms, (255, 255, 255, 217), line_h)

    # ── Signature line ──
    y += int(18 * S)
    sig_w = int(100 * S)
    draw.line([pad, y, pad + sig_w, y],
              fill=(255, 255, 255, 102), width=max(1, int(1 * S)))
    y += int(4 * S)
    font_sig = get_font('dmsans', int(8 * S))
    draw.text((pad, y), emp.get('name', 'Employee'),
              fill=(255, 255, 255, 178), font=font_sig)

    # ── Footer ──
    footer_y = CARD_H - int(20 * S) - int(32 * S)
    draw.line([pad, footer_y, CARD_W - pad, footer_y],
              fill=(255, 255, 255, 64), width=max(1, int(1 * S)))
    footer_y += int(12 * S)

    font_footer_title = get_font('dmsans-bold', int(9 * S))
    font_footer_text = get_font('dmsans', int(8 * S))
    footer_line_h = int(8 * S * 1.6)

    draw.text((pad, footer_y), company.upper(), fill='white', font=font_footer_title)
    footer_y += int(12 * S)

    address = emp.get('address', 'Bengaluru')
    email = emp.get('email', 'hr@acmecorp.com')
    website = emp.get('website', 'www.acmecorp.com')
    footer_lines = [
        "42 Business Park, Sector 5",
        f"{address} — 560 001",
        f"{email} | {website}",
    ]
    for line in footer_lines:
        draw.text((pad, footer_y), line,
                  fill=(255, 255, 255, 204), font=font_footer_text)
        footer_y += footer_line_h

    corner_r = int(18 * S)
    final = _apply_rounded_corners(img, corner_r)

    emp_id_safe = emp.get('employee_id', 'EMP-0000').replace(' ', '_')
    output_path = os.path.join(OUTPUT_FOLDER, f'{emp_id_safe}_back.png')
    final.convert('RGB').save(output_path, 'PNG', dpi=(300, 300))
    return output_path


def _wrap_text(draw, text, font, max_width):
    """Word-wrap text to fit within max_width. Returns list of lines."""
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = words[0]
    for word in words[1:]:
        test = current + ' ' + word
        tw = draw.textbbox((0, 0), test, font=font)[2]
        if tw <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines

def _apply_rounded_corners(img, radius):
    """Apply rounded corners to the card using an alpha mask."""
    mask = Image.new('L', img.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    img.putalpha(mask)
    return img

def _draw_photo_placeholder(draw, x, y, w, h):
    """Draw a gradient placeholder with gold silhouette SVG icon per spec."""
    # Placeholder logic - no-op or simple drawing if photo is missing
    pass

def _draw_wrapped_text(draw, text, x, y, max_width, font, fill, line_height):
    """Draw text with word wrapping. Returns y position after last line."""
    words = text.split()
    lines = []
    current = ''
    for word in words:
        test = f'{current} {word}'.strip()
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        y += line_height
    return y


@app.route('/clear-output', methods=['POST'])
def clear_output():
    for f in os.listdir(OUTPUT_FOLDER):
        filepath = os.path.join(OUTPUT_FOLDER, f)
        if os.path.isfile(filepath):
            os.remove(filepath)
    if db is not None:
        db['generated_cards'].delete_many({})
    return jsonify({'success': True})


# ── MongoDB API Routes ──

@app.route('/api/employees', methods=['GET'])
def api_get_employees():
    """Get all employees from MongoDB."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503
    employees = list(db['employees'].find({}))
    return jsonify({'employees': [mongo_serialize(e) for e in employees], 'count': len(employees)})


@app.route('/api/employees/<employee_id>', methods=['GET'])
def api_get_employee(employee_id):
    """Get single employee by employee_id."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503
    emp = db['employees'].find_one({'employee_id': employee_id})
    if not emp:
        return jsonify({'error': 'Employee not found'}), 404
    return jsonify({'employee': mongo_serialize(emp)})


@app.route('/api/employees', methods=['POST'])
def api_add_employee():
    """Add or update a single employee."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503
    data = request.get_json()
    if not data or not data.get('employee_id'):
        return jsonify({'error': 'employee_id is required'}), 400
    data['uploaded_at'] = datetime.utcnow().isoformat()
    db['employees'].update_one(
        {'employee_id': data['employee_id']},
        {'$set': data},
        upsert=True
    )
    return jsonify({'success': True, 'employee_id': data['employee_id']})


@app.route('/api/employees/<employee_id>', methods=['DELETE'])
def api_delete_employee(employee_id):
    """Delete an employee by employee_id."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503
    result = db['employees'].delete_one({'employee_id': employee_id})
    if result.deleted_count == 0:
        return jsonify({'error': 'Employee not found'}), 404
    return jsonify({'success': True, 'deleted': employee_id})


@app.route('/api/employees/search', methods=['GET'])
def api_search_employees():
    """Search employees by name, department, or designation."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503
    q = request.args.get('q', '')
    dept = request.args.get('department', '')

    query = {}
    if q:
        query['$or'] = [
            {'name': {'$regex': q, '$options': 'i'}},
            {'employee_id': {'$regex': q, '$options': 'i'}},
            {'designation': {'$regex': q, '$options': 'i'}},
        ]
    if dept:
        query['department'] = dept

    employees = list(db['employees'].find(query))
    return jsonify({'employees': [mongo_serialize(e) for e in employees], 'count': len(employees)})


@app.route('/api/departments', methods=['GET'])
def api_get_departments():
    """Get distinct departments."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503
    departments = db['employees'].distinct('department')
    return jsonify({'departments': departments})


@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    """Get dashboard statistics."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503
    total_employees = db['employees'].count_documents({})
    total_generated = db['generated_cards'].count_documents({})
    departments = db['employees'].distinct('department')
    return jsonify({
        'total_employees': total_employees,
        'total_generated': total_generated,
        'departments': len(departments),
        'department_list': departments
    })


@app.route('/api/load-from-db', methods=['GET'])
def api_load_from_db():
    """Load all employees from MongoDB for card generation (used by frontend)."""
    if db is None:
        return jsonify({'error': 'Database not connected'}), 503
    employees = list(db['employees'].find({}))
    clean = []
    for emp in employees:
        e = mongo_serialize(emp)
        e.pop('_id', None)
        e.pop('uploaded_at', None)
        clean.append(e)
    return jsonify({'success': True, 'employees': clean, 'count': len(clean)})


@app.route('/db-status')
def db_status():
    """Check MongoDB connection status."""
    if db is None:
        return jsonify({'connected': False, 'message': 'Not connected to MongoDB'})
    try:
        client.admin.command('ping')
        emp_count = db['employees'].count_documents({})
        card_count = db['generated_cards'].count_documents({})
        return jsonify({
            'connected': True,
            'database': MONGO_DB,
            'employees': emp_count,
            'generated_cards': card_count
        })
    except Exception as e:
        return jsonify({'connected': False, 'message': str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
