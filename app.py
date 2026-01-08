import json
import random
import os
import requests
import textwrap
from datetime import datetime
from flask import Flask, render_template, send_file
from PIL import Image, ImageDraw, ImageFont

# ======================
# Flask
# ======================
app = Flask(__name__)

# ======================
# 설정
# ======================
BOOK_NAME_MAP = {
    "시": "시편",
    "잠": "잠언",
    "전": "전도서",
    "아": "아가",
    "마": "마태복음",
    "막": "마가복음",
    "눅": "누가복음",
    "요": "요한복음",
    "롬": "로마서"
}

JSON_PATH = "bible_meditation_structured.json"
BACKGROUND_IMAGE = "5423dc65-db92-440e-abf6-cab473e7bae6.png"

OUTPUT_DIR = "generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_PATH = "NanumGothic-Bold.ttf"
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"

STORY_SIZE = (1080, 1920)
FONT_SIZE = 52
LINE_WIDTH = 18
LINE_SPACING = int(FONT_SIZE * 0.6)

BASE_Y_RATIO = 0.62

BOX_PADDING_X = 60
BOX_PADDING_Y = 50
BOX_COLOR = (0, 0, 0, 140)

# ======================
# 폰트 다운로드
# ======================
def ensure_font():
    if os.path.exists(FONT_PATH):
        return

    r = requests.get(FONT_URL, timeout=10)
    if r.headers.get("Content-Type", "").startswith("text/html"):
        raise RuntimeError("폰트 다운로드 실패")

    with open(FONT_PATH, "wb") as f:
        f.write(r.content)

# ======================
# 랜덤 말씀
# ======================
def get_random_verse():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    book = random.choice(list(data.keys()))
    chapter = random.choice(data[book])
    verse = random.choice(chapter["verses"])

    return {
        "book": book,
        "chapter": chapter["chapter"],
        "verse": verse["verse"],
        "text": verse["text"]
    }

# ======================
# 유틸
# ======================
def wrap_text(text):
    return "\n".join(textwrap.wrap(text, LINE_WIDTH))


def format_reference(book, chapter, verse):
    full_book = BOOK_NAME_MAP.get(book, book)
    return f"{full_book} {chapter} {verse}"

# ======================
# 이미지 생성
# ======================
def create_story_image():
    ensure_font()

    verse = get_random_verse()
    verse_text = wrap_text(verse["text"])
    reference = format_reference(
        verse["book"],
        verse["chapter"],
        verse["verse"]
    )

    bg = Image.open(BACKGROUND_IMAGE).convert("RGBA")
    bg = bg.resize(STORY_SIZE)

    overlay = Image.new("RGBA", STORY_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    ref_font = ImageFont.truetype(FONT_PATH, FONT_SIZE - 12)

    text_bbox = draw.multiline_textbbox(
        (0, 0), verse_text, font=font, spacing=LINE_SPACING, align="center"
    )
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    base_y = int(STORY_SIZE[1] * BASE_Y_RATIO)
    text_x = (STORY_SIZE[0] - text_w) // 2
    text_y = base_y - text_h

    ref_bbox = draw.textbbox((0, 0), reference, font=ref_font)
    ref_w = ref_bbox[2] - ref_bbox[0]
    ref_h = ref_bbox[3] - ref_bbox[1]

    ref_x = (STORY_SIZE[0] - ref_w) // 2
    ref_y = base_y + 30

    # 반투명 박스
    box_left = min(text_x, ref_x) - BOX_PADDING_X
    box_top = text_y - BOX_PADDING_Y
    box_right = max(text_x + text_w, ref_x + ref_w) + BOX_PADDING_X
    box_bottom = ref_y + ref_h + BOX_PADDING_Y

    draw.rounded_rectangle(
        [box_left, box_top, box_right, box_bottom],
        radius=40,
        fill=BOX_COLOR
    )

    shadow = 2

    draw.multiline_text(
        (text_x + shadow, text_y + shadow),
        verse_text,
        font=font,
        fill=(0, 0, 0, 255),
        spacing=LINE_SPACING,
        align="center"
    )
    draw.multiline_text(
        (text_x, text_y),
        verse_text,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=LINE_SPACING,
        align="center"
    )

    draw.text(
        (ref_x + shadow, ref_y + shadow),
        reference,
        font=ref_font,
        fill=(0, 0, 0, 255)
    )
    draw.text(
        (ref_x, ref_y),
        reference,
        font=ref_font,
        fill=(230, 230, 230, 255)
    )

    final = Image.alpha_composite(bg, overlay)

    filename = f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    output_path = os.path.join(OUTPUT_DIR, filename)
    final.convert("RGB").save(output_path)

    return output_path

# ======================
# Flask Routes
# ======================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate")
def generate():
    path = create_story_image()
    return send_file(path, as_attachment=True)

# ======================
# 실행
# ======================
if __name__ == "__main__":
    app.run(debug=True)
