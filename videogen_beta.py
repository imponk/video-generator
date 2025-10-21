import os
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont

# ==============================
# KONFIGURASI DASAR
# ==============================
VIDEO_SIZE = (1080, 1080)
DURASI_PER_SCENE = 7
BACKGROUND_COLOR = (0, 0, 0)
LOGO_PATH = "semangat.png"

FONTS = {
    "judul": "DMSerifDisplay-Regular.ttf",
    "subjudul": "Poppins-Bold.ttf",
    "isi": "ProximaNova-Regular.ttf"
}

# ==============================
# PARSER DATA_BERITA.TXT
# ==============================
def baca_data_berita(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    berita_list = []
    data = {"Judul": "", "Subjudul": "", "Isi": ""}
    mode = None

    for line in lines:
        line = line.strip()

        if not line:
            continue  # lewati baris kosong

        # Pembatas antarberita
        if line.startswith("---"):
            if data["Judul"]:
                berita_list.append(data)
                data = {"Judul": "", "Subjudul": "", "Isi": ""}
            continue

        if line.startswith("Judul:"):
            data["Judul"] = line.replace("Judul:", "").strip()
            mode = "judul"
            continue

        if line.startswith("Subjudul:"):
            data["Subjudul"] = line.replace("Subjudul:", "").strip()
            mode = "subjudul"
            continue

        # Kelanjutan dari judul/subjudul/isi
        if mode == "judul" and not data["Subjudul"] and not data["Isi"]:
            data["Judul"] += " " + line.strip()
        elif mode == "subjudul" and not data["Isi"]:
            data["Subjudul"] += " " + line.strip()
        else:
            data["Isi"] += (" " if data["Isi"] else "") + line.strip()
            mode = "isi"

    if data["Judul"]:
        berita_list.append(data)

    return berita_list


# ==============================
# RENDER TEKS & VIDEO
# ==============================
def render_opening(judul, subjudul, fonts):
    # buat kanvas hitam
    img = Image.new("RGB", VIDEO_SIZE, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    font_judul = ImageFont.truetype(fonts["judul"], 54)
    font_subjudul = ImageFont.truetype(fonts["subjudul"], 40)

    # posisi awal teks
    x_center = VIDEO_SIZE[0] // 2

    # tulis judul
    judul_lines = textwrap(judul, font_judul, 900)
    y_text = 220
    for line in judul_lines:
        w, h = draw.textsize(line, font=font_judul)
        draw.text(((VIDEO_SIZE[0] - w) / 2, y_text), line, fill="white", font=font_judul)
        y_text += h + 8

    # tulis subjudul
    if subjudul:
        sub_lines = textwrap(subjudul, font_subjudul, 900)
        y_text += 20
        for line in sub_lines:
            w, h = draw.textsize(line, font=font_subjudul)
            draw.text(((VIDEO_SIZE[0] - w) / 2, y_text), line, fill="white", font=font_subjudul)
            y_text += h + 6

    # convert jadi clip
    np_img = np.array(img)
    clip = ImageClip(np_img).set_duration(0.2)

    return clip


def render_isi(isi_text, fonts):
    font_isi = ImageFont.truetype(fonts["isi"], 36)

    img = Image.new("RGB", VIDEO_SIZE, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    lines = textwrap(isi_text, font_isi, 960)
    y_start = 380  # sejajar dengan posisi subjudul

    for line in lines:
        w, h = draw.textsize(line, font=font_isi)
        draw.text(((VIDEO_SIZE[0] - w) / 2, y_start), line, fill="white", font=font_isi)
        y_start += h + 6

    # jika teks terlalu panjang dan mendekati logo, naikkan semua sedikit
    if y_start > 880:
        shift = y_start - 880
        new_img = Image.new("RGB", VIDEO_SIZE, BACKGROUND_COLOR)
        new_img.paste(img, (0, -shift // 2))
        img = new_img

    np_img = np.array(img)
    clip = ImageClip(np_img).set_duration(DURASI_PER_SCENE)

    # tambahkan logo
    if os.path.exists(LOGO_PATH):
        logo = ImageClip(LOGO_PATH).set_duration(DURASI_PER_SCENE).resize(width=150)
        logo = logo.set_position(("left", "bottom"))
        clip = CompositeVideoClip([clip, logo])

    return clip


def textwrap(text, font, max_width):
    words = text.split(" ")
    lines, current = [], ""

    for word in words:
        test_line = f"{current} {word}".strip()
        if font.getlength(test_line) <= max_width:
            current = test_line
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    return lines


def buat_video(data):
    opening = render_opening(data["Judul"], data["Subjudul"], FONTS)
    isi = render_isi(data["Isi"], FONTS)
    final = concatenate_videoclips([opening, isi])
    final.write_videofile("output_video.mp4", fps=24, codec="libx264", audio=False)


# ==============================
# MAIN EXECUTION
# ==============================
if __name__ == "__main__":
    berita_list = baca_data_berita("data_berita.txt")
    for i, data in enumerate(berita_list, start=1):
        buat_video(data)
        os.rename("output_video.mp4", f"video_{i:02d}.mp4")
