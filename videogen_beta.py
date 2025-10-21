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
    """Membungkus teks tapi tetap menghormati enter manual."""
    if not text:
        return ""
    paragraphs = text.split("\n")
    lines = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            lines.append("")
            continue
        words = para.split()
        line = ""
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

def render_opening(judul_txt, subjudul_txt, fonts):
    dur = durasi_judul(judul_txt, subjudul_txt)
    total_frames = int(FPS * dur)
    static_frames = int(FPS * 0.2)
    fade_frames = int(FPS * 0.8)
    margin_x = 70

    font_judul = ImageFont.truetype(fonts["judul"], 54)
    font_sub = ImageFont.truetype(fonts["subjudul"], 28)

    wrapped_judul = smart_wrap(judul_txt, font_judul, VIDEO_SIZE[0])
    wrapped_sub = smart_wrap(subjudul_txt, font_sub, VIDEO_SIZE[0]) if subjudul_txt else None

    judul_h = sum(font_judul.getbbox(line)[3] for line in wrapped_judul.split("\n"))

    if wrapped_sub:
        sub_lines = wrapped_sub.split("\n")
        tinggi_sub = sum(font_sub.getbbox(line)[3] for line in sub_lines)
        jarak_vertikal = max(18, int(tinggi_sub * 0.35))  # spacing lebih seimbang
        y_judul = int(VIDEO_SIZE[1] * 0.60)
        y_sub = y_judul + judul_h + jarak_vertikal
    else:
        y_judul = int(VIDEO_SIZE[1] * 0.60)
        y_sub = None

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
        make_text_frame(layer, wrapped_judul, font_judul, (margin_x, y_judul))
        if wrapped_sub:
            make_text_frame(layer, wrapped_sub, font_sub, (margin_x, y_sub))
        visible = render_wipe_layer(layer, t) if anim else layer
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))
    return frames_to_clip(frames)

def render_text_block(text, font_path, font_size, dur, anim=True):
    total_frames = int(FPS * dur)
    fade_frames = min(18, total_frames)
    margin_x = 70

    base_y = int(VIDEO_SIZE[1] * 0.60)
    margin_bawah_logo = 140

    font = ImageFont.truetype(font_path, font_size)
    wrapped = smart_wrap(text, font, VIDEO_SIZE[0])
    lines = [l for l in wrapped.split("\n") if l.strip()]

    line_heights = [font.getbbox(line)[3] for line in lines]
    text_height = sum(line_heights) + (len(lines) - 1) * 8

    bottom_y = base_y + text_height
    batas_bawah_aman = VIDEO_SIZE[1] - margin_bawah_logo

    if bottom_y > batas_bawah_aman:
        kelebihan = bottom_y - batas_bawah_aman
        offset = min(int(kelebihan * 0.6), 120)
        y_pos = base_y - offset
    else:
        y_pos = base_y

    frames = []
    for i in range(total_frames):
        t = 1.0 if not anim else min(1.0, i / float(fade_frames))
        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
        make_text_frame(layer, wrapped, font, (margin_x, y_pos))
        visible = render_wipe_layer(layer, t)
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))
    return frames_to_clip(frames)

# ---------- PENUTUP & OVERLAY ----------
def render_penutup(dur=3.0):
    total_frames = int(FPS * dur)
    frames = [np.array(Image.new("RGB", VIDEO_SIZE, BG_COLOR)) for _ in range(total_frames)]
    return frames_to_clip(frames)

def add_overlay(base_clip):
    if not os.path.exists(OVERLAY_FILE):
        return base_clip
    overlay = ImageClip(OVERLAY_FILE, duration=base_clip.duration)
    return CompositeVideoClip([base_clip, overlay], size=VIDEO_SIZE)

# ---------- PEMBACA FILE BERITA ----------
def baca_semua_berita(file_path):
    """Parser fleksibel untuk file berita:
    - Mendukung multiline Judul & Subjudul tanpa baris kosong
    - Tidak sensitif huruf besar-kecil
    - Paragraf isi otomatis dipisah 2x Enter
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blok_berita = content.strip().split("---")
    semua_data = []

    for blok in blok_berita:
        lines = blok.strip().splitlines()
        data, isi_raw = {}, []
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            lower_line = line.lower()

            if lower_line.startswith("judul:"):
                judul_lines = [line.split(":", 1)[1].strip()]
                i += 1
                while i < len(lines) and not lines[i].strip().lower().startswith("subjudul:"):
                    if lines[i].strip():
                        judul_lines.append(lines[i].strip())
                    i += 1
                data["Judul"] = "\n".join(judul_lines)
                continue

            elif lower_line.startswith("subjudul:"):
                sub_lines = [line.split(":", 1)[1].strip()]
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line or next_line.lower().startswith("judul:") or next_line.lower().startswith("subjudul:"):
                        break
                    sub_lines.append(next_line)
                    i += 1
                data["Subjudul"] = "\n".join(sub_lines)
                continue

            else:
                if line or isi_raw:
                    isi_raw.append(line)
                i += 1

        if isi_raw:
            isi_text = "\n".join(isi_raw).strip()
            paragraf_list = [p.strip() for p in isi_text.split("\n\n") if p.strip()]
            for idx, p in enumerate(paragraf_list, start=1):
                data[f"Isi_{idx}"] = p

        if data:
            semua_data.append(data)

    return semua_data

# ---------- PEMBUATAN VIDEO ----------
def buat_video(data, index=None):
    judul = data.get("Judul", "")
    print(f"▶ Membuat video: {judul}")
    opening = render_opening(judul, data.get("Subjudul", ""), FONTS)

    isi_clips = []
    for i in range(1, 30):
        key = f"Isi_{i}"
        if key in data and data[key].strip():
            teks = data[key]
            dur = durasi_otomatis(teks)
            clip = render_text_block(teks, FONTS["isi"], 34, dur)
            isi_clips.append(clip)

    penutup = render_penutup(3.0)
    final = concatenate_videoclips([opening] + isi_clips + [penutup], method="compose")
    result = add_overlay(final)

    filename = f"output_video_{index+1 if index is not None else '1'}.mp4"
    result.write_videofile(filename, fps=FPS, codec="libx264", audio=False)
    print(f"✅ Video selesai: {filename}\n")

# ---------- MAIN ----------
if __name__ == "__main__":
    FILE_INPUT = "data_berita.txt"
    if not os.path.exists(FILE_INPUT):
        print("❌ File data_berita.txt tidak ditemukan!")
        exit(1)

    semua = baca_semua_berita(FILE_INPUT)
    for i, data in enumerate(semua):
        buat_video(data, i)

    print("🎬 Semua video selesai dibuat.")
