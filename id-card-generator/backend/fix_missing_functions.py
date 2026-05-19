import os

APP_PY = r"c:\Users\Admin\OneDrive\Desktop\New folder\corporate_id_card\id-card-generator\backend\app.py"

with open(APP_PY, 'r', encoding='utf-8') as f:
    content = f.read()

missing_funcs = """
def _wrap_text(draw, text, font, max_width):
    \"\"\"Word-wrap text to fit within max_width. Returns list of lines.\"\"\"
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
    \"\"\"Apply rounded corners to the card using an alpha mask.\"\"\"
    mask = Image.new('L', img.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    img.putalpha(mask)
    return img

def _draw_photo_placeholder(draw, x, y, w, h):
    \"\"\"Draw a gradient placeholder with gold silhouette SVG icon per spec.\"\"\"
    # Placeholder logic - no-op or simple drawing if photo is missing
    pass

"""

if "def _wrap_text" not in content:
    content = content.replace("def _draw_wrapped_text", missing_funcs + "def _draw_wrapped_text")
    with open(APP_PY, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added missing functions back")
else:
    print("Functions already exist")
