from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np, os, math

VIDEO_SIZE = (720, 1280)
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255, 255)
FPS = 24

FONTS = {
    "judul": "DMSerifDisplay-Regular.ttf",
    "subjudul": "ProximaNova-Regular.ttf",
    "isi": "Poppins-Bold.ttf",
}

OVERLAY_FILE = "semangat.png"


# ---------- UTILITAS ----------
def durasi_otomatis(teks, min_dur=3, max_dur=6):
    if not teks:
        return min_dur
    kata = len(teks.split())
    durasi = max(min_dur, min((kata / 3.5), max_dur))
    return round(durasi, 1)


def durasi_judul(judul, subjudul):
    panjang = len((judul or "").split()) + len((subjudul or "").split())
    if panjang <= 8:
        return 2.5
    elif panjang <= 14:
        return 3.0
    elif panjang <= 22:
        return 3.5
    return 4.0


def smart_wrap(text, font, max_width, margin_left=70, margin_right=90):
    if not text:
        return ""
    words = text.split()
    lines, line = [], ""
    for word in words:
        test_line = line + word + " "
        if font.getlength(test_line) + margin_left + margin_right > max_width:
            lines.append(line.strip())
            line = word + " "
        else:
            line = test_line
    if line:
        lines.append(line.strip())
    return "\n".join(lines)


def make_text_frame(base_img, text, font, pos, alpha=255):
    draw = ImageDraw.Draw(base_img)
    fill = (TEXT_COLOR[0], TEXT_COLOR[1], TEXT_COLOR[2], alpha)
    draw.multiline_text(pos, text, font=font, fill=fill, align="left")


def frames_to_clip(frames_np):
    parts = [ImageClip(f, duration=1.0 / FPS) for f in frames_np]
    return concatenate_videoclips(parts, method="compose")


# ---------- EASING ----------
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


# ---------- BLOK: JUDUL + SUBJUDUL ----------
def render_opening(judul_txt, subjudul_txt, fonts):
    dur = durasi_judul(judul_txt, subjudul_txt)
    total_frames = int(FPS * dur)
    static_frames = int(FPS * 0.1)
    fade_frames = int(FPS * 0.7)
    margin_x = 70

    try:
        font_judul = ImageFont.truetype(fonts["judul"], 54)
        font_sub = ImageFont.truetype(fonts["subjudul"], 28)
    except:
        font_judul = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    wrapped_judul = smart_wrap(judul_txt, font_judul, VIDEO_SIZE[0])
    wrapped_sub = smart_wrap(subjudul_txt, font_sub, VIDEO_SIZE[0]) if subjudul_txt else None

    judul_h = sum(font_judul.getbbox(line)[3] for line in wrapped_judul.split("\n"))
    if wrapped_sub:
        sub_lines = wrapped_sub.split("\n")
        jarak_vertikal = 16  # sedikit lebih renggang agar seimbang
        y_judul = int(VIDEO_SIZE[1] * 0.60)
        y_sub = y_judul + judul_h + jarak_vertikal
    else:
        y_judul = int(VIDEO_SIZE[1] * 0.60)
        y_sub = None

    frames = []
    for i in range(total_frames):
        if i < static_frames:
            t = 0.0
        elif i < static_frames + fade_frames:
            t = (i - static_frames) / float(fade_frames)
        else:
            t = 1.0

        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
        make_text_frame(layer, wrapped_judul, font_judul, (margin_x, y_judul))
        if wrapped_sub:
            make_text_frame(layer, wrapped_sub, font_sub, (margin_x, y_sub))

        visible = render_wipe_layer(layer, t)
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))

    return frames_to_clip(frames)


# ---------- BLOK: ISI ----------
def render_text_block(text, font_path, font_size, dur, anim=True):
    total_frames = int(FPS * dur)
    fade_frames = min(18, total_frames)
    margin_x = 70

    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    wrapped = smart_wrap(text, font, VIDEO_SIZE[0])
    lines = wrapped.split("\n")

    line_heights = [font.getbbox(line)[3] for line in lines if line.strip()]
    text_height = sum(line_heights)
    base_y = int(VIDEO_SIZE[1] * 0.60)

    margin_bawah_logo = 140
    bottom_y = base_y + text_height
    if bottom_y > VIDEO_SIZE[1] - margin_bawah_logo:
        offset = (bottom_y - (VIDEO_SIZE[1] - margin_bawah_logo))
        y_pos = base_y - offset
    else:
        y_pos = base_y

    frames = []
    for i in range(total_frames):
        if not anim:
            t = 1.0
        else:
            t = min(1.0, i / float(fade_frames))
        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
        make_text_frame(layer, wrapped, font, (margin_x, y_pos))
        visible = render_wipe_layer(layer, t)
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))
    return frames_to_clip(frames)


# ---------- BLOK: PENUTUP ----------
def render_penutup(dur=3.0):
    total_frames = int(FPS * dur)
    frames = [np.array(Image.new("RGB", VIDEO_SIZE, BG_COLOR)) for _ in range(total_frames)]
    return frames_to_clip(frames)


# ---------- OVERLAY ----------
def add_overlay(base_clip):
    if not os.path.exists(OVERLAY_FILE):
        return base_clip
    overlay = ImageClip(OVERLAY_FILE, duration=base_clip.duration)
    return CompositeVideoClip([base_clip, overlay], size=VIDEO_SIZE)


# ---------- PARSER ----------
def baca_data_berita(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")

    data_list = []
    data = {"Judul": "", "Subjudul": "", "Isi": ""}
    mode = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("---"):
            if data["Judul"]:
                data_list.append(data)
                data = {"Judul": "", "Subjudul": "", "Isi": ""}
                mode = None
            continue
        if line.startswith("Judul:"):
            data["Judul"] = line.replace("Judul:", "").strip()
            mode = "judul"
        elif line.startswith("Subjudul:"):
            data["Subjudul"] = line.replace("Subjudul:", "").strip()
            mode = "subjudul"
        else:
            if mode == "judul" and not data["Subjudul"] and not data["Isi"]:
                data["Judul"] += " " + line.strip()
            elif mode == "subjudul" and not data["Isi"]:
                data["Subjudul"] += " " + line.strip()
            else:
                if data["Isi"]:
                    data["Isi"] += " " + line.strip()
                else:
                    data["Isi"] = line.strip()
            mode = "isi"

    if data["Judul"]:
        data_list.append(data)
    return data_list


# ---------- UTAMA ----------
def buat_video(data, output_name="video_01.mp4"):
    opening = render_opening(data.get("Judul", ""), data.get("Subjudul", ""), FONTS)
    isi_clip = render_text_block(data.get("Isi", ""), FONTS["isi"], 34, durasi_otomatis(data.get("Isi", "")))
    penutup = render_penutup(2.5)

    final = concatenate_videoclips([opening, isi_clip, penutup], method="compose")
    result = add_overlay(final)
    result.write_videofile(output_name, fps=FPS, codec="libx264", audio=False)


# ---------- EKSEKUSI ----------
if __name__ == "__main__":
    berita_list = baca_data_berita("data_berita.txt")
    for i, data in enumerate(berita_list, start=1):
        output_file = f"video_{i:02d}.mp4"
        print(f"🎬 Membuat {output_file} ...")
        buat_video(data, output_file)
    print("✅ Semua video selesai dibuat.")
