"""Generate a 5:3 submission thumbnail (1200x720) for AutoBrief."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 720
INK = (16, 36, 62)
BG_TOP = (11, 19, 32)
ACCENT = (37, 99, 235)
GOOD = (34, 197, 94)
WHITE = (245, 248, 252)
MUTED = (159, 176, 195)

img = Image.new("RGB", (W, H), BG_TOP)
d = ImageDraw.Draw(img)

# subtle vertical gradient
for y in range(H):
    t = y / H
    r = int(11 + (18 - 11) * t)
    g = int(19 + (30 - 19) * t)
    b = int(32 + (54 - 32) * t)
    d.line([(0, y), (W, y)], fill=(r, g, b))

F = "C:/Windows/Fonts/segoeuib.ttf"
FR = "C:/Windows/Fonts/segoeui.ttf"
def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", size)

f_tag = font(F, 30)
f_title = font(F, 132)
f_sub = font(FR, 40)
f_chip = font(F, 30)
f_foot = font(FR, 30)

# top tag
d.text((70, 70), "GOOGLE FOR STARTUPS · AI AGENTS CHALLENGE", font=f_tag, fill=MUTED)

# title
d.text((68, 150), "AutoBrief", font=f_title, fill=WHITE)

# subtitle (two lines)
d.text((72, 320), "Autonomous client-intake & proposal agent", font=f_sub, fill=ACCENT)
d.text((72, 372), "for a solo AI MVP studio", font=f_sub, fill=ACCENT)

# metric chips (outline-only on dark bg so text stays readable)
chips = [
    ("8/8 eval  ·  100% routing / scope / price", GOOD),
    ("3-5 hrs   ->   ~1 min per proposal", WHITE),
    ("Deterministic pricing  ·  human-approval gated", WHITE),
]
y = 452
for text, col in chips:
    bbox = d.textbbox((0, 0), text, font=f_chip)
    tw = bbox[2] - bbox[0]
    pad = 24
    box_w = tw + pad * 2
    d.rounded_rectangle([70, y, 70 + box_w, y + 54], radius=14,
                        outline=(90, 112, 145), width=2)
    d.text((70 + pad, y + 11), text, font=f_chip, fill=col)
    y += 70

# footer
d.text((70, H - 48), "Google ADK + Gemini (Vertex AI)  ·  MCP  ·  Cloud Run", font=f_foot, fill=MUTED)

out = "C:/Users/rnd/autobrief/docs/thumbnail.png"
img.save(out, "PNG")
print("saved", out, img.size)
