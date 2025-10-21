from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np, os, re, math

# ---------- KONFIGURASI DASAR ----------
VIDEO_SIZE = (720, 1280)
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255, 255)
FPS = 24

# Cari path folder assets (agar kompatibel di GitHub Actions)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

FONTS = {
    "judul": os.path.join(ASSETS_DIR, "DMSerifDisplay-Regular.ttf"),
    "subjudul": os.path.join(ASSETS_DIR, "ProximaNova-Regular.ttf"),
    "isi": os.path.join(ASSETS_DIR, "Poppins-Bold.ttf"),
}

OVERLAY_FILE = os.path.join(ASSETS_DIR, "semangat.png")

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

# ---------- FADE KIRI → KANAN ----------
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

    font_judul = ImageFont.truetype(fonts["judul"], 54)
    font_sub = ImageFont.truetype(fonts["subjudul"], 28)

    wrapped_judul = smart_wrap(judul_txt, font_judul, VIDEO_SIZE[0])
    wrapped_sub = smart_wrap(subjudul_txt, font_sub, VIDEO_SIZE[0]) if subjudul_txt else None

    judul_h = sum(font_judul.getbbox(line)[3] for line in wrapped_judul.split("\n"))
    if wrapped_sub:
        jarak_vertikal = 16
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

    font = ImageFont.truetype(font_path, font_size)
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
        t = min(1.0, i / float(fade_frames)) if anim else 1.0
        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
        make_text_frame(layer, wrapped, font, (margin_x, y_pos))
        visible = render_wipe_layer(layer, t)
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))
    return frames_to_clip(frames)

# ---------- BLOK: PENUTUP ----------
def render_penutup(dur=2.0):
    total_frames = int(FPS * dur)
    frames = [np.array(Image.new("RGB", VIDEO_SIZE, BG_COLOR)) for _ in range(total_frames)]
    return frames_to_clip(frames)

# ---------- OVERLAY ----------
def add_overlay(base_clip):
    if not os.path.exists(OVERLAY_FILE):
        return base_clip
    overlay = ImageClip(OVERLAY_FILE, duration=base_clip.duration)
    return CompositeVideoClip([base_clip, overlay], size=VIDEO_SIZE)

# ---------- PEMBACA DATA ----------
def parse_data_berita(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"---+", content.strip())
    hasil = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        judul, subjudul, isi = "", "", []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.lower().startswith("judul:"):
                judul = line.split(":", 1)[1].strip()
                i += 1
                while i < len(lines) and not lines[i].lower().startswith("subjudul:") and not lines[i-1].lower().startswith("subjudul:"):
                    if not lines[i].lower().startswith("judul:"):
                        judul += " " + lines[i].strip()
                    i += 1
            elif line.lower().startswith("subjudul:"):
                subjudul = line.split(":", 1)[1].strip()
                i += 1
                while i < len(lines) and not re.match(r"^(judul|subjudul):", lines[i], re.I):
                    subjudul += " " + lines[i].strip()
                    i += 1
            else:
                isi.append(line)
                i += 1

        hasil.append({
            "Judul": judul.strip(),
            "Subjudul": subjudul.strip(),
            "Isi": "\n\n".join(isi).strip(),
        })
    return hasil

# ---------- PEMBUAT VIDEO ----------
def buat_video(data, idx):
    opening = render_opening(data.get("Judul", ""), data.get("Subjudul", ""), FONTS)
    isi_block = render_text_block(data.get("Isi", ""), FONTS["isi"], 34, durasi_otomatis(data.get("Isi", "")))
    penutup = render_penutup(2.0)

    final = concatenate_videoclips([opening, isi_block, penutup], method="compose")
    result = add_overlay(final)
    output_file = f"video_{idx:02d}.mp4"
    result.write_videofile(output_file, fps=FPS, codec="libx264", audio=False)
    print(f"✅ Video disimpan: {output_file}")

# ---------- MAIN ----------
if __name__ == "__main__":
    data_file = os.path.join(BASE_DIR, "data_berita.txt")
    if not os.path.exists(data_file):
        print("❌ File data_berita.txt tidak ditemukan.")
        exit(1)

    daftar_berita = parse_data_berita(data_file)
    print(f"📄 Ditemukan {len(daftar_berita)} berita.")
    for i, berita in enumerate(daftar_berita, start=1):
        print(f"🎬 Membuat video ke-{i} ...")
        buat_video(berita, i)

    print("🎉 Semua video selesai dibuat.")
