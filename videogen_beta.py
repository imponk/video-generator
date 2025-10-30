from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips, VideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np, os, math, re

# ========================
# KONFIGURASI DASAR
# ========================
VIDEO_SIZE = (720, 1280)
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255, 255)
HIGHLIGHT_COLOR = (0, 124, 188, 200)  # #007CBC
FPS = 24

FONTS = {
    "upper": "ProximaNova-Bold.ttf",
    "judul": "DMSerifDisplay-Regular.ttf",
    "subjudul": "ProximaNova-Regular.ttf",
    "isi": "Poppins-Bold.ttf",
}

OVERLAY_FILE = "semangat.png"


# ========================
# DURASI OTOMATIS
# ========================
def durasi_otomatis(teks, min_dur=3.5):
    if not teks:
        return min_dur
    kata = len(teks.split())
    if kata <= 15:
        durasi = 4
    elif kata <= 30:
        durasi = 5.5
    elif kata <= 50:
        durasi = 7
    else:
        durasi = 8
    return max(min_dur, round(durasi, 1))


def durasi_judul(judul, subjudul):
    panjang = len((judul or "").split()) + len((subjudul or "").split())
    if panjang <= 8: return 2.5
    elif panjang <= 14: return 3.0
    elif panjang <= 22: return 3.5
    return 4.0


# ========================
# PEMBUNGKUS TEKS CERDAS
# ========================
def smart_wrap(text, font, max_width, margin_left=70, margin_right=90):
    if not text:
        return ""
    paragraphs = text.split("\n")
    raw_lines = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            raw_lines.append("")
            continue
        words = para.split()
        line = ""
        for word in words:
            test_line = line + word + " "
            test_width = font.getbbox(test_line)[2]
            if test_width + margin_left + margin_right > max_width:
                raw_lines.append(line.strip())
                line = word + " "
            else:
                line = test_line
        if line:
            raw_lines.append(line.strip())
    return "\n".join(raw_lines)


# ========================
# FUNGSI TEKS & FRAME
# ========================
def make_text_frame(base_img, text, font, pos, alpha=255):
    draw = ImageDraw.Draw(base_img)
    fill = (TEXT_COLOR[0], TEXT_COLOR[1], TEXT_COLOR[2], alpha)
    draw.multiline_text(pos, text, font=font, fill=fill, align="left", spacing=4)


def frames_to_clip(frames_np):
    parts = [ImageClip(f, duration=1.0 / FPS) for f in frames_np]
    return concatenate_videoclips(parts, method="compose")


def ease_out(t):
    return 1 - pow(1 - t, 3)


def render_wipe_layer(layer, t):
    if t <= 0:
        return Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    t_eased = ease_out(t)
    width = int(VIDEO_SIZE[0] * t_eased)
    mask = Image.new("L", VIDEO_SIZE, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle([0, 0, width, VIDEO_SIZE[1]], fill=255)
    return Image.composite(layer, Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0)), mask)


# ========================
# HIGHLIGHT TEKS
# ========================
def draw_highlighted_text(draw, text, font, pos, highlight_words, fade_alpha=1.0):
    lines = text.split("\n")
    x, y = pos
    spacing = 6
    for line in lines:
        cursor_x = x
        for word in line.split(" "):
            clean_word = word.strip(".,!?;:()[]{}\"'")
            bbox = font.getbbox(word + " ")
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if clean_word in highlight_words:
                rect_y = y + h * 0.15
                rect_h = h * 0.8
                color = (
                    HIGHLIGHT_COLOR[0],
                    HIGHLIGHT_COLOR[1],
                    HIGHLIGHT_COLOR[2],
                    int(HIGHLIGHT_COLOR[3] * fade_alpha),
                )
                draw.rectangle(
                    [cursor_x - 2, rect_y, cursor_x + w + 2, rect_y + rect_h],
                    fill=color,
                )
            draw.text((cursor_x, y), word + " ", font=font, fill=TEXT_COLOR)
            cursor_x += w
        y += h + spacing


# ========================
# BLOK TEKS (ISI BERITA)
# ========================
def render_text_block(text, font_path, font_size, dur, anim=True):
    total_frames = int(FPS * dur)
    fade_frames = min(18, total_frames)
    margin_x = 70
    base_y = int(VIDEO_SIZE[1] * 0.60)
    batas_bawah_aman = VIDEO_SIZE[1] - 170

    # Parsing highlight [[...]]
    highlight_words = re.findall(r"\[\[(.*?)\]\]", text)
    clean_text = re.sub(r"\[\[(.*?)\]\]", r"\1", text)

    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    font = ImageFont.truetype(font_path, font_size)
    wrapped = smart_wrap(clean_text, font, VIDEO_SIZE[0])
    text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6)
    text_height = text_bbox[3] - text_bbox[1]
    bottom_y = base_y + text_height

    if bottom_y > batas_bawah_aman:
        font_size_new = max(30, int(font_size * 0.94))
        font = ImageFont.truetype(font_path, font_size_new)
        wrapped = smart_wrap(clean_text, font, VIDEO_SIZE[0])

    y_pos = base_y if bottom_y <= batas_bawah_aman else base_y - 100

    frames = []
    for i in range(total_frames):
        t = 1.0 if not anim else min(1.0, i / float(fade_frames))

        # Delay highlight muncul setelah fade teks selesai
        highlight_delay = fade_frames + int(FPS * 0.8)
        t_highlight = 0.0
        if i > highlight_delay:
            t_highlight = min(1.0, (i - highlight_delay) / float(fade_frames))

        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
        draw_real = ImageDraw.Draw(layer)

        draw_highlighted_text(
            draw_real, wrapped, font, (margin_x, y_pos),
            highlight_words, fade_alpha=t_highlight
        )
        visible = render_wipe_layer(layer, t)
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))

    return frames_to_clip(frames)

# ========================
# OPENING (JUDUL & SUBJUDUL)
# ========================
def render_opening(judul_txt, subjudul_txt, fonts, upper_txt=None):
    dur = durasi_judul(judul_txt, subjudul_txt)
    total_frames = int(FPS * dur)
    static_frames = int(FPS * 0.2)
    fade_frames = int(FPS * 0.8)

    margin_x = 70
    margin_bawah_logo = 170
    batas_bawah_aman = VIDEO_SIZE[1] - margin_bawah_logo

    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    upper_font_size = 28
    judul_font_size = 60
    sub_font_size = 28
    spacing_upper_judul = 12
    spacing_judul_sub = 19  # sedikit diperlebar agar tidak mepet

    def calculate_layout(current_judul_font_size):
        font_upper = ImageFont.truetype(fonts["upper"], upper_font_size) if upper_txt else None
        font_judul = ImageFont.truetype(fonts["judul"], current_judul_font_size)
        font_sub = ImageFont.truetype(fonts["subjudul"], sub_font_size) if subjudul_txt else None

        wrapped_upper = smart_wrap(upper_txt, font_upper, VIDEO_SIZE[0]) if font_upper and upper_txt else None
        wrapped_judul = smart_wrap(judul_txt, font_judul, VIDEO_SIZE[0])
        wrapped_sub = smart_wrap(subjudul_txt, font_sub, VIDEO_SIZE[0]) if font_sub and subjudul_txt else None

        total_h = 0
        upper_h = judul_h = sub_h = 0

        if wrapped_upper:
            upper_bbox = draw.multiline_textbbox((0, 0), wrapped_upper, font=font_upper, spacing=4)
            upper_h = upper_bbox[3] - upper_bbox[1]
        if wrapped_judul:
            judul_bbox = draw.multiline_textbbox((0, 0), wrapped_judul, font=font_judul, spacing=4)
            judul_h = judul_bbox[3] - judul_bbox[1]
        if wrapped_sub:
            sub_bbox = draw.multiline_textbbox((0, 0), wrapped_sub, font=font_sub, spacing=4)
            sub_h = sub_bbox[3] - sub_bbox[1]

        total_h = upper_h + judul_h + sub_h
        if upper_h > 0 and (judul_h > 0 or wrapped_judul):
            total_h += spacing_upper_judul
        if (judul_h > 0 or wrapped_judul) and sub_h > 0:
            total_h += spacing_judul_sub

        y_start = int(VIDEO_SIZE[1] * 0.60)
        _y_upper = y_start
        _y_judul = _y_upper + (upper_h + spacing_upper_judul if wrapped_upper else 0)
        _y_sub = _y_judul + (judul_h + spacing_judul_sub if wrapped_judul else 0)

        return dict(
            font_upper=font_upper, font_judul=font_judul, font_sub=font_sub,
            wrapped_upper=wrapped_upper, wrapped_judul=wrapped_judul, wrapped_sub=wrapped_sub,
            y_upper=_y_upper, y_judul=_y_judul, y_sub=_y_sub
        )

    layout = calculate_layout(judul_font_size)
    frames = []

    for i in range(total_frames):
        if i < static_frames:
            t = 1.0
            anim = False
        elif i < static_frames + fade_frames:
            t = (i - static_frames) / float(fade_frames)
            anim = True
        else:
            t = 1.0
            anim = False

        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))

        if layout["wrapped_upper"]:
            make_text_frame(layer, layout["wrapped_upper"], layout["font_upper"], (margin_x, layout["y_upper"]))
        if layout["wrapped_judul"]:
            make_text_frame(layer, layout["wrapped_judul"], layout["font_judul"], (margin_x, layout["y_judul"]))
        if layout["wrapped_sub"]:
            make_text_frame(layer, layout["wrapped_sub"], layout["font_sub"], (margin_x, layout["y_sub"]))

        visible = render_wipe_layer(layer, t) if anim else layer
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))

    return frames_to_clip(frames)


# ========================
# PENUTUP & OVERLAY
# ========================
def render_penutup(dur=3.0):
    total_frames = int(FPS * dur)
    frames = [np.array(Image.new("RGB", VIDEO_SIZE, BG_COLOR)) for _ in range(total_frames)]
    return frames_to_clip(frames)


def add_overlay(base_clip):
    if not os.path.exists(OVERLAY_FILE):
        return base_clip
    try:
        overlay_pil = Image.open(OVERLAY_FILE).convert("RGBA")
    except Exception as e:
        print(f"❌ Error loading overlay '{OVERLAY_FILE}': {e}")
        return base_clip
    overlay_pil_resized = overlay_pil.resize(VIDEO_SIZE, Image.LANCZOS)
    overlay_clip = ImageClip(np.array(overlay_pil_resized), duration=base_clip.duration)
    return CompositeVideoClip([base_clip, overlay_clip.set_pos((0, 0))], size=VIDEO_SIZE)


# ========================
# BACA DATA & GENERASI VIDEO
# ========================
def baca_semua_berita(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ File '{file_path}' tidak ditemukan!")
        exit(1)

    blok_berita = content.strip().split("---")
    semua_data = []
    for blok in blok_berita:
        lines = blok.strip().splitlines()
        data = {}
        key = None
        isi = []
        for line in lines:
            if line.lower().startswith("upper:"):
                key = "Upper"
                data[key] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("judul:"):
                key = "Judul"
                data[key] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("subjudul:"):
                key = "Subjudul"
                data[key] = line.split(":", 1)[1].strip()
            elif line.strip():
                isi.append(line.strip())
        if isi:
            for i, p in enumerate(isi, start=1):
                data[f"Isi_{i}"] = p
        if data:
            semua_data.append(data)
    return semua_data

def buat_video(data, index=None):
    judul = data.get("Judul", "")
    print(f"▶ Membuat video: {judul}")
    try:
        opening = render_opening(judul, data.get("Subjudul", None), FONTS, upper_txt=data.get("Upper", None))

        isi_clips = []
        isi_data = [f"Isi_{i}" for i in range(1, 30) if f"Isi_{i}" in data]
        jeda_awal = render_penutup(0.8)

        for idx, key in enumerate(isi_data):
            teks = data[key]
            dur = durasi_otomatis(teks)
            clip = render_text_block(teks, FONTS["isi"], 36, dur)
            isi_clips.append(clip)
            if idx < len(isi_data) - 1:
                isi_clips.append(jeda_awal)

        penutup = render_penutup(4.0)
        final = concatenate_videoclips([opening] + isi_clips + [penutup], method="compose")
        result = add_overlay(final)
        filename = f"output_video_{index+1 if index is not None else 1}.mp4"
        result.write_videofile(filename, fps=FPS, codec="libx264", audio=False, threads=4)
        print(f"✅ Video selesai: {filename}\n")

    except Exception as e:
        print(f"❌ Gagal membuat video untuk '{judul}': {e}")

# ========================
# MAIN
# ========================
if __name__ == "__main__":
    FILE_INPUT = "data_berita.txt"

    font_files_ok = True
    for key, font_file in FONTS.items():
        if not os.path.exists(font_file):
            print(f"❌ File Font '{font_file}' untuk '{key}' tidak ditemukan!")
            font_files_ok = False
    if not font_files_ok:
        exit(1)

    semua = baca_semua_berita(FILE_INPUT)
    if not semua:
        print(f"❌ Tidak ada data berita yang valid di '{FILE_INPUT}'.")
        exit(1)

    print(f"Total {len(semua)} video akan dibuat...")
    for i, data in enumerate(semua):
        buat_video(data, i)
    print("🎬 Semua video selesai dibuat (atau dilewati jika gagal).")
