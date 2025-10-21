from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np, os

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

# ---------- PARSER ----------
def baca_data_berita(file_path="data_berita.txt"):
    with open(file_path, "r", encoding="utf-8") as f:
        teks = f.read().strip()

    blok = [b.strip() for b in teks.split("\n\n") if b.strip()]
    data = {"Judul": "", "Subjudul": "", "Isi": []}
    current_key = None

    for b in blok:
        lower = b.lower()
        if lower.startswith("judul:"):
            current_key = "Judul"
            data["Judul"] = b.split(":", 1)[1].strip()
        elif lower.startswith("subjudul:"):
            current_key = "Subjudul"
            data["Subjudul"] = b.split(":", 1)[1].strip()
        else:
            # kalau baris tambahan dari judul/subjudul panjang
            if current_key == "Judul" and not data["Subjudul"]:
                data["Judul"] += " " + b.strip()
            elif current_key == "Subjudul" and (not lower.startswith("judul:")):
                data["Subjudul"] += " " + b.strip()
            else:
                data["Isi"].append(b.strip())
    return data

# ---------- BLOK: JUDUL + SUBJUDUL ----------
def render_opening(judul_txt, subjudul_txt, fonts):
    dur = durasi_judul(judul_txt, subjudul_txt)
    total_frames = int(FPS * dur)
    fade_frames = int(FPS * 0.7)
    margin_x = 70

    font_judul = ImageFont.truetype(fonts["judul"], 54)
    font_sub = ImageFont.truetype(fonts["subjudul"], 28)
    wrapped_judul = smart_wrap(judul_txt, font_judul, VIDEO_SIZE[0])
    wrapped_sub = smart_wrap(subjudul_txt, font_sub, VIDEO_SIZE[0]) if subjudul_txt else None

    # posisi tetap (tidak dinaikkan)
    y_judul = int(VIDEO_SIZE[1] * 0.60)
    judul_h = sum(font_judul.getbbox(line)[3] for line in wrapped_judul.split("\n"))
    jarak_vertikal = 16
    y_sub = y_judul + judul_h + jarak_vertikal if wrapped_sub else None

    frames = []
    for i in range(total_frames):
        t = min(1.0, i / float(fade_frames))
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
def render_text_block(text, font_path, font_size, dur):
    total_frames = int(FPS * dur)
    fade_frames = min(18, total_frames)
    margin_x = 70
    font = ImageFont.truetype(font_path, font_size)
    wrapped = smart_wrap(text, font, VIDEO_SIZE[0])
    lines = wrapped.split("\n")

    line_heights = [font.getbbox(line)[3] for line in lines if line.strip()]
    text_height = sum(line_heights)
    base_y = int(VIDEO_SIZE[1] * 0.60)
    bottom_limit = VIDEO_SIZE[1] - 140
    y_pos = base_y if base_y + text_height <= bottom_limit else bottom_limit - text_height

    frames = []
    for i in range(total_frames):
        t = min(1.0, i / float(fade_frames))
        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
        make_text_frame(layer, wrapped, font, (margin_x, y_pos))
        visible = render_wipe_layer(layer, t)
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))
    return frames_to_clip(frames)

def render_penutup(dur=3.0):
    frames = [np.array(Image.new("RGB", VIDEO_SIZE, BG_COLOR)) for _ in range(int(FPS * dur))]
    return frames_to_clip(frames)

def add_overlay(base_clip):
    if not os.path.exists(OVERLAY_FILE): return base_clip
    overlay = ImageClip(OVERLAY_FILE, duration=base_clip.duration)
    return CompositeVideoClip([base_clip, overlay], size=VIDEO_SIZE)

# ---------- UTAMA ----------
def buat_video(data):
    clips = [render_opening(data.get("Judul", ""), data.get("Subjudul", ""), FONTS)]
    for isi in data.get("Isi", []):
        clips.append(render_text_block(isi, FONTS["isi"], 34, durasi_otomatis(isi)))
    clips.append(render_penutup(3.0))
    final = concatenate_videoclips(clips, method="compose")
    result = add_overlay(final)
    result.write_videofile("video_01.mp4", fps=FPS, codec="libx264", audio=False)

if __name__ == "__main__":
    data = baca_data_berita("data_berita.txt")
    buat_video(data)
