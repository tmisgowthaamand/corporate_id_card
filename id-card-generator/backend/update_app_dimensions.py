import os

APP_PY = r"c:\Users\Admin\OneDrive\Desktop\New folder\corporate_id_card\id-card-generator\backend\app.py"

with open(APP_PY, 'r', encoding='utf-8') as f:
    content = f.read()

new_code = """# ── Exact mapping from HTML: 204px x 323px (CR80) ──
CARD_W = 638
CARD_H = 1011
S = CARD_W / 204.0  # Scale factor from 204px to 638px (~3.127)

# ── Standardized color tokens ──
GOLD = '#E6A817'
GOLD_RGB = (230, 168, 23)
CARD_BG = (255, 255, 255)  # #FFFFFF
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

    # ── Gold header — max 30% (~97px in HTML) ──
    header_h = int(97 * S)
    draw.rectangle([0, 0, CARD_W, header_h], fill=GOLD)

    # ── Wave separator (32px viewBox height) ──
    wave_h = int(32 * S)
    wave_img = Image.new('RGBA', (CARD_W, wave_h), (0, 0, 0, 0))
    # M0 28 L0 8 Q60 -8 120 12 Q180 32 240 8 L240 28 Z
    # We map x from 0..240 to 0..CARD_W
    for x in range(CARD_W):
        t = x / CARD_W * 240.0
        if t <= 120:
            tt = t / 120.0
            y_norm = (1 - tt)**2 * 8 + 2 * (1 - tt) * tt * -8 + tt**2 * 12
        else:
            tt = (t - 120) / 120.0
            y_norm = (1 - tt)**2 * 12 + 2 * (1 - tt) * tt * 32 + tt**2 * 8
            
        y_px = int(y_norm / 32.0 * wave_h)
        y_px = max(0, min(wave_h - 1, y_px))
        for y in range(y_px, wave_h):
            wave_img.putpixel((x, y), CARD_BG + (255,))
        for y in range(0, y_px):
            wave_img.putpixel((x, y), GOLD_RGB + (255,))
    img.paste(wave_img, (0, header_h - wave_h), wave_img)
    draw = ImageDraw.Draw(img)

    # ── Lanyard hole: 26x13 ──
    hole_w = int(26 * S)
    hole_h = int(13 * S)
    hole_x = (CARD_W - hole_w) // 2
    draw.rounded_rectangle([hole_x, -int(1 * S), hole_x + hole_w, hole_h],
                           radius=hole_h // 2, fill='#1a1a1a')

    # ── Header paddings ──
    pad_top = int(18 * S)
    pad_x = int(16 * S)

    # ── Company logo circle — 32x32 ──
    company = emp.get('company', 'Acme Corp International')
    initials = get_initials(company)

    logo_r = int(16 * S)
    logo_cx = pad_x + logo_r
    logo_cy = pad_top + logo_r + int(2 * S)

    draw_circle_outline_aa(img, logo_cx, logo_cy, logo_r, int(2 * S),
                           (255, 255, 255, int(255*0.8)))
    overlay_logo = Image.new('RGBA', (logo_r * 2, logo_r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(overlay_logo).ellipse([0, 0, logo_r * 2, logo_r * 2],
                                          fill=(255, 255, 255, int(255*0.15)))
    img.paste(overlay_logo, (logo_cx - logo_r, logo_cy - logo_r), overlay_logo)

    draw = ImageDraw.Draw(img)
    font_logo = get_font('playfair', int(13 * S))
    bbox = draw.textbbox((0, 0), initials, font=font_logo)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((logo_cx - tw // 2, logo_cy - th // 2 - int(2 * S)), initials,
              fill='white', font=font_logo)

    # ── Company name (next to logo) — 9px, 600, max-width 110px ──
    font_org = get_font('dmsans-semibold', int(9 * S))
    max_org_w = int(110 * S)
    org_x = logo_cx + logo_r + int(6 * S)
    org_lines = _wrap_text(draw, company, font_org, max_org_w)
    org_y = logo_cy - int(8 * S)
    for ol in org_lines:
        draw.text((org_x, org_y), ol, fill='white', font=font_org)
        org_y += int(draw.textbbox((0, 0), ol, font=font_org)[3] * 1.2)

    # ── EMPLOYEE badge — 8px, letter-spacing 1.5px, padding 3px 8px ──
    card_type = emp.get('card_type', 'EMPLOYEE').upper()
    font_badge = get_font('dmsans-semibold', int(8 * S))
    bb = draw.textbbox((0, 0), card_type, font=font_badge)
    badge_tw = bb[2] - bb[0]
    badge_pad_x = int(8 * S)
    badge_pad_y = int(3 * S)
    badge_h = int(bb[3] + badge_pad_y * 2)
    badge_w = badge_tw + badge_pad_x * 2 + int(6 * S)  # space for letter spacing
    badge_x = CARD_W - pad_x - badge_w
    badge_y = pad_top + int(4 * S)
    badge_overlay = Image.new('RGBA', (badge_w, badge_h), (0, 0, 0, 0))
    ImageDraw.Draw(badge_overlay).rounded_rectangle(
        [0, 0, badge_w, badge_h], radius=int(10 * S), fill=(255, 255, 255, int(255*0.2)))
    img.paste(badge_overlay, (badge_x, badge_y), badge_overlay)
    draw = ImageDraw.Draw(img)
    draw.text((badge_x + badge_pad_x, badge_y + badge_pad_y - int(1*S)), card_type,
              fill='white', font=font_badge)

    # ── FRONT BODY ──
    # body padding 10px 16px 14px
    body_pad_top = int(10 * S)
    body_pad_x = int(16 * S)
    body_y = header_h - wave_h + body_pad_top + int(24 * S) # Adjust below wave

    font_name = get_font('playfair-bold', int(14 * S))
    font_role = get_font('dmsans-semibold', int(9 * S))
    font_dept = get_font('dmsans', int(9 * S))

    name = emp.get('name', 'Praveen Kumar')
    designation = emp.get('designation', 'FULL STACK DEVELOPER')
    department = emp.get('department', 'IT')

    # ── Photo box — 80x95, border-radius 12px, 3px solid #E6A817 ──
    photo_w = int(80 * S)
    photo_h = int(95 * S)
    photo_x = CARD_W - body_pad_x - photo_w
    photo_y = body_y - int(10*S)

    border = int(3 * S)
    # Box shadow glow (simulation)
    glow_img = Image.new('RGBA', (CARD_W, CARD_H), (0, 0, 0, 0))
    glow_r = int(12 * S)
    ImageDraw.Draw(glow_img).rounded_rectangle(
        [photo_x - border - glow_r, photo_y - border - glow_r,
         photo_x + photo_w + border + glow_r, photo_y + photo_h + border + glow_r],
        radius=glow_r*2, fill=(230, 168, 23, 30))
    img.paste(glow_img, (0, 0), glow_img)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([photo_x - border, photo_y - border,
                            photo_x + photo_w + border, photo_y + photo_h + border],
                           radius=int(12 * S), fill=GOLD)
    inner_r = int(12 * S) - border
    inner_img = Image.new('RGBA', (photo_w, photo_h), (0, 0, 0, 0))
    # background: linear-gradient(135deg, #fdf6e3, #f0e0b0)
    for py_off in range(photo_h):
        frac = py_off / max(1, photo_h - 1)
        r = int(253 + (240 - 253) * frac)
        g = int(246 + (224 - 246) * frac)
        b = int(227 + (176 - 227) * frac)
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
                [0, 0, photo_w, photo_h], radius=inner_r, fill=255)
            img.paste(emp_photo, (photo_x, photo_y), mask)
            draw = ImageDraw.Draw(img)
        except:
            pass # keep placeholder

    # ── Text to left of photo ──
    max_text_w = photo_x - body_pad_x - int(8 * S)
    name_lines = _wrap_text(draw, name, font_name, max_text_w)
    
    cur_y = photo_y + photo_h - int(38 * S) - (len(name_lines)-1)*int(14*S*1.2)
    for line in name_lines:
        draw.text((body_pad_x, cur_y), line, fill=TEXT_PRIMARY, font=font_name)
        cur_y += int(draw.textbbox((0, 0), line, font=font_name)[3] * 1.2)

    cur_y += int(2 * S)
    role_text = designation.upper()
    role_lines = _wrap_text(draw, role_text, font_role, max_text_w)
    for line in role_lines:
        draw.text((body_pad_x, cur_y), line, fill=GOLD, font=font_role)
        cur_y += int(draw.textbbox((0, 0), line, font=font_role)[3] * 1.3)

    cur_y += int(1 * S)
    draw.text((body_pad_x, cur_y), department, fill=TEXT_MUTED, font=font_dept)

    # ── Divider ──
    div_y = photo_y + photo_h + int(12 * S)
    for x in range(body_pad_x, CARD_W - body_pad_x):
        frac = (x - body_pad_x) / max(1, (CARD_W - 2 * body_pad_x))
        alpha = int(255 * (1 - frac * 0.9))
        draw.point((x, div_y), fill=GOLD_RGB + (alpha,))

    # ── Details grid — 8px 12px gap ──
    grid_y = div_y + int(8 * S)
    font_label = get_font('dmsans-semibold', int(7 * S))
    font_value = get_font('dmsans-medium', int(11 * S))
    col2_x = CARD_W // 2 + int(6 * S)
    row_gap = int(24 * S)

    blood = format_blood_group(emp.get('blood_group', 'O -ve'))
    mobile = emp.get('mobile', emp.get('contact', '+91 XXXXX XXXXX'))
    
    details = [
        (body_pad_x, grid_y, "EMPLOYEE ID", emp.get('employee_id', 'EMP-0000')),
        (col2_x, grid_y, "VALID UNTIL", emp.get('valid_till', 'Dec 2027')),
        (body_pad_x, grid_y + row_gap, "BLOOD GROUP", blood),
        (col2_x, grid_y + row_gap, "CONTACT", mobile),
    ]
    label_val_gap = int(2 * S)
    for dx, dy, label, value in details:
        draw.text((dx, dy), label, fill=TEXT_LABEL, font=font_label)
        lh = draw.textbbox((0, 0), label, font=font_label)[3]
        draw.text((dx, dy + lh + label_val_gap), value, fill=TEXT_VALUE, font=font_value)

    # ── Bottom section ──
    bottom_y = CARD_H - int(14 * S) - int(64 * S) - int(12 * S)
    
    # Divider above bottom section
    div_y2 = bottom_y - int(8 * S)
    for x in range(body_pad_x, CARD_W - body_pad_x):
        frac = (x - body_pad_x) / max(1, (CARD_W - 2 * body_pad_x))
        alpha = int(255 * (1 - frac * 0.9))
        draw.point((x, div_y2), fill=GOLD_RGB + (alpha,))

    qr_container_size = int(64 * S)
    qr_pad = int(4 * S)

    # QR box — 64x64
    draw.rounded_rectangle([body_pad_x, bottom_y,
                            body_pad_x + qr_container_size, bottom_y + qr_container_size],
                           radius=int(6 * S), fill='white', outline=GOLD,
                           width=max(1, int(1 * S)))

    emp_id = emp.get('employee_id', 'EMP-0000')
    qr_img = generate_qr_code(emp_id, qr_container_size - qr_pad*2)
    img.paste(qr_img, (body_pad_x + qr_pad, bottom_y + qr_pad))
    draw = ImageDraw.Draw(img)

    # Employee ID right-aligned
    id_x = CARD_W - body_pad_x
    font_id_label = get_font('dmsans-semibold', int(7 * S))
    font_id_value = get_font('dmsans-bold', int(11 * S))

    id_label_y = bottom_y + int(36 * S)
    bb_label = draw.textbbox((0, 0), "EMPLOYEE ID", font=font_id_label)
    draw.text((id_x - (bb_label[2] - bb_label[0]), id_label_y),
              "EMPLOYEE ID", fill=TEXT_LABEL, font=font_id_label)
              
    id_val = emp_id
    bb_val = draw.textbbox((0, 0), id_val, font=font_id_value)
    draw.text((id_x - (bb_val[2] - bb_val[0]), id_label_y + bb_label[3] + label_val_gap),
              id_val, fill=TEXT_PRIMARY, font=font_id_value)

    # ── Website ──
    font_web = get_font('dmsans-semibold', int(8 * S))
    website = emp.get('website', 'www.acmecorp.com')
    web_x = text_center_x(draw, website, font_web, CARD_W)
    draw.text((web_x, CARD_H - int(14 * S)), website, fill=GOLD, font=font_web)

    corner_r = int(20 * S)
    final = _apply_rounded_corners(img, corner_r)

    emp_id_safe = emp_id.replace(' ', '_')
    output_path = os.path.join(OUTPUT_FOLDER, f'{emp_id_safe}_front.png')
    final.convert('RGB').save(output_path, 'PNG', dpi=(300, 300))
    return output_path

def generate_back_card(emp):
    img = Image.new('RGBA', (CARD_W, CARD_H), GOLD_RGB + (255,))
    draw = ImageDraw.Draw(img)
    pad = int(16 * S)

    # ── Decorative pattern — opacity 0.18 ──
    pat_alpha = int(255 * 0.18)
    draw_circle_outline_aa(img, int(160 * S), int(80 * S), int(90 * S),
                           int(24 * S), (255, 255, 255, pat_alpha))
    draw_circle_outline_aa(img, int(40 * S), int(280 * S), int(70 * S),
                           int(18 * S), (255, 255, 255, pat_alpha))
    draw = ImageDraw.Draw(img)
    draw.arc([-int(20*S), int(80*S), int(260*S), int(340*S)], 180, 90, fill=(255,255,255,pat_alpha), width=int(12*S))

    # ── Logo circle ──
    company = emp.get('company', 'Acme Corp International')
    initials = get_initials(company)
    logo_r = int(21 * S)
    logo_cx = CARD_W // 2
    logo_cy = int(20 * S) + logo_r

    draw_circle_outline_aa(img, logo_cx, logo_cy, logo_r, int(2 * S),
                           (255, 255, 255, int(255*0.6)))
    overlay_bg = Image.new('RGBA', (logo_r * 2, logo_r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(overlay_bg).ellipse([0, 0, logo_r * 2, logo_r * 2],
                                        fill=(255, 255, 255, int(255*0.1)))
    img.paste(overlay_bg, (logo_cx - logo_r, logo_cy - logo_r), overlay_bg)
    draw = ImageDraw.Draw(img)

    font_logo = get_font('playfair', int(15 * S))
    bb = draw.textbbox((0, 0), initials, font=font_logo)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((logo_cx - tw // 2, logo_cy - th // 2 - int(2 * S)),
              initials, fill='white', font=font_logo)

    # ── Terms & Conditions ──
    y = logo_cy + logo_r + int(24 * S)
    font_section = get_font('dmsans-bold', int(8 * S))
    font_terms = get_font('dmsans', int(8.5 * S))
    line_h = int(8.5 * S * 1.65)

    draw.text((pad, y), "TERMS & CONDITIONS",
              fill=(255, 255, 255, int(255*0.7)), font=font_section)
    y += int(14 * S)

    terms_1 = (
        "This card is the property of the issuing organization. "
        "If found, please return it to the address below. "
        "Unauthorized use of this card is strictly prohibited."
    )
    y = _draw_wrapped_text(draw, terms_1, pad, y, CARD_W - 2 * pad,
                           font_terms, (255, 255, 255, int(255*0.88)), line_h)
    y += int(8 * S)

    terms_2 = (
        "The cardholder must report loss or damage immediately. "
        "This card grants access only to authorized areas as per "
        "the holder's designation."
    )
    y = _draw_wrapped_text(draw, terms_2, pad, y, CARD_W - 2 * pad,
                           font_terms, (255, 255, 255, int(255*0.88)), line_h)

    # ── Divider ──
    y += int(10 * S)
    draw.line([pad, y, CARD_W - pad, y],
              fill=(255, 255, 255, int(255*0.25)), width=max(1, int(1 * S)))
    y += int(10 * S)

    terms_3 = (
        "This ID is valid for the period shown on the front. "
        "Management reserves the right to revoke access at any time "
        "without prior notice."
    )
    y = _draw_wrapped_text(draw, terms_3, pad, y, CARD_W - 2 * pad,
                           font_terms, (255, 255, 255, int(255*0.88)), line_h)

    # ── Signature line ──
    y += int(12 * S)
    sig_w = int(90 * S)
    draw.line([pad, y, pad + sig_w, y],
              fill=(255, 255, 255, int(255*0.45)), width=max(1, int(1 * S)))
    y += int(4 * S)
    font_sig = get_font('playfair', int(9 * S)) # Note: using playfair fallback since we don't have Dancing Script in python backend easily
    draw.text((pad, y), emp.get('name', 'Praveen Kumar'),
              fill=(255, 255, 255, int(255*0.85)), font=font_sig)

    # ── Footer ──
    footer_y = CARD_H - int(16 * S) - int(38 * S)
    draw.line([pad, footer_y, CARD_W - pad, footer_y],
              fill=(255, 255, 255, int(255*0.25)), width=max(1, int(1 * S)))
    footer_y += int(10 * S)

    font_footer_title = get_font('dmsans-bold', int(9 * S))
    font_footer_text = get_font('dmsans', int(8 * S))
    footer_line_h = int(8 * S * 1.65)

    draw.text((pad, footer_y), company.upper(), fill='white', font=font_footer_title)
    footer_y += int(10 * S)

    address = emp.get('address', 'Street, Area')
    city = emp.get('city', 'City — PIN')
    email = emp.get('email', 'contact@org.com')
    footer_lines = [
        "42 Business Park, Sector 5",
        "Chennai — 560 001",
        f"praveen@acmecorp.com | {emp.get('website', 'www.acmecorp.com')}",
    ]
    for line in footer_lines:
        draw.text((pad, footer_y), line,
                  fill=(255, 255, 255, int(255*0.82)), font=font_footer_text)
        footer_y += footer_line_h

    # INNER shadow overlay for back card
    shadow_img = Image.new('RGBA', (CARD_W, CARD_H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow_img).rounded_rectangle([0, 0, CARD_W, CARD_H], radius=int(20*S), outline=(255,255,255,int(255*0.08)), width=int(1*S))
    img.paste(shadow_img, (0, 0), shadow_img)

    corner_r = int(20 * S)
    final = _apply_rounded_corners(img, corner_r)

    emp_id_safe = emp.get('employee_id', 'EMP-0000').replace(' ', '_')
    output_path = os.path.join(OUTPUT_FOLDER, f'{emp_id_safe}_back.png')
    final.convert('RGB').save(output_path, 'PNG', dpi=(300, 300))
    return output_path
"""

# Replace between '# ── Exact mapping from HTML' and 'def _wrap_text'
start_marker = "# ── Exact mapping from HTML"
end_marker = "def _wrap_text"

if start_marker in content and end_marker in content:
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    new_app = content[:start_idx] + new_code + "\n" + content[end_idx:]
    with open(APP_PY, 'w', encoding='utf-8') as f:
        f.write(new_app)
    print("Updated app.py dimensions and styling successfully")
else:
    print("Markers not found")
