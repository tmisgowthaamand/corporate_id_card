import os
import re

APP_PY = r"c:\Users\Admin\OneDrive\Desktop\New folder\corporate_id_card\id-card-generator\backend\app.py"

with open(APP_PY, 'r', encoding='utf-8') as f:
    content = f.read()

new_generation_code = """# ── Exact mapping from HTML: 240px x 370px ──
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
    \"\"\"Convert O+, A-, B+ etc. to O +ve, A -ve, B +ve format.\"\"\"
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
"""

# Replace between '# ── CR80 standard: 54mm × 85.6mm (portrait) ──' and 'def _draw_wrapped_text'
start_marker = "# ── CR80 standard: 54mm × 85.6mm (portrait) ──"
end_marker = "def _draw_wrapped_text"

if start_marker in content and end_marker in content:
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    new_app = content[:start_idx] + new_generation_code + "\n" + content[end_idx:]
    with open(APP_PY, 'w', encoding='utf-8') as f:
        f.write(new_app)
    print("Updated app.py successfully")
else:
    print("Markers not found")
