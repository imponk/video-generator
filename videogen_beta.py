from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np, os, math, re

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

    if kata <= 15:
        durasi = 3.5
    elif kata <= 30:
        durasi = 4.5
    elif kata <= 50:
        durasi = 5.5
    else:
        durasi = 7.0

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

    cleaned_lines = []
    for i in range(len(raw_lines)):

        if i == len(raw_lines) - 1:
            cleaned_lines.append(raw_lines[i])
            break

        current_line = raw_lines[i]
        words = current_line.split()

        if not words:
            cleaned_lines.append(current_line)
            continue

        last_word = words[-1]

        if last_word.lower() in ['rp', 'ke', 'di']:
            line_without_last_word = " ".join(words[:-1])
            cleaned_lines.append(line_without_last_word)
            if i + 1 < len(raw_lines):
                 raw_lines[i+1] = last_word + " " + raw_lines[i+1]
        else:
            cleaned_lines.append(current_line)

    return "\n".join(cleaned_lines)

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

def render_opening(judul_txt, subjudul_txt, fonts):
    dur = durasi_judul(judul_txt, subjudul_txt)
    total_frames = int(FPS * dur)
    static_frames = int(FPS * 0.2)
    fade_frames = int(FPS * 0.8)
    margin_x = 70

    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    font_judul = ImageFont.truetype(fonts["judul"], 54)
    font_sub = ImageFont.truetype(fonts["subjudul"], 28)

    wrapped_judul = smart_wrap(judul_txt, font_judul, VIDEO_SIZE[0])
    wrapped_sub = smart_wrap(subjudul_txt, font_sub, VIDEO_SIZE[0]) if subjudul_txt else None

    y_judul = int(VIDEO_SIZE[1] * 0.60)

    judul_bbox = draw.multiline_textbbox((margin_x, y_judul), wrapped_judul, font=font_judul, spacing=4)

    if wrapped_sub:
        sub_bbox = draw.multiline_textbbox((0, 0), wrapped_sub, font=font_sub, spacing=4)
        tinggi_sub = sub_bbox[3] - sub_bbox[1]

        jarak_vertikal = max(18, int(tinggi_sub * 0.35))
        y_sub = judul_bbox[3] + jarak_vertikal
    else:
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
    margin_bawah_logo = 170 # Jarak aman dari bawah (termasuk overlay full screen)
    batas_bawah_aman = VIDEO_SIZE[1] - margin_bawah_logo

    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    font = ImageFont.truetype(font_path, font_size)
    wrapped = smart_wrap(text, font, VIDEO_SIZE[0])

    text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6)
    text_height = text_bbox[3] - text_bbox[1]
    bottom_y = base_y + text_height

    if bottom_y > batas_bawah_aman:
        font_size_new = max(30, int(font_size * 0.94))
        font = ImageFont.truetype(font_path, font_size_new)

        wrapped = smart_wrap(text, font, VIDEO_SIZE[0])
        text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6)
        text_height = text_bbox[3] - text_bbox[1]
        bottom_y = base_y + text_height

    if bottom_y > batas_bawah_aman:
        kelebihan = bottom_y - batas_bawah_aman
        offset = min(kelebihan + 10, 220)
        y_pos = base_y - offset
    else:
        y_pos = base_y

    frames = []
    for i in range(total_frames):
        t = 1.0 if not anim else min(1.0, i / float(fade_frames))
        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))

        draw_real = ImageDraw.Draw(layer)
        draw_real.multiline_text((margin_x, y_pos), wrapped, font=font, fill=TEXT_COLOR, align="left", spacing=6)

        visible = render_wipe_layer(layer, t)
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))

    return frames_to_clip(frames)

def render_penutup(dur=3.0):
    total_frames = int(FPS * dur)
    frames = [np.array(Image.new("RGB", VIDEO_SIZE, BG_COLOR)) for _ in range(total_frames)]
    return frames_to_clip(frames)

def add_overlay(base_clip):
    # --- FUNGSI INI SUDAH DIPERBARUI ---
    if not os.path.exists(OVERLAY_FILE):
        print(f"⚠️ File Overlay '{OVERLAY_FILE}' tidak ditemukan, video akan dibuat tanpa overlay.")
        return base_clip

    try:
        # Muat overlay (resolusi tinggi asli)
        overlay_pil = Image.open(OVERLAY_FILE).convert("RGBA")
    except Exception as e:
        print(f"❌ Error loading overlay '{OVERLAY_FILE}': {e}")
        return base_clip

    # Sesuaikan ukuran overlay agar sesuai dengan VIDEO_SIZE (720x1280)
    target_width = VIDEO_SIZE[0]
    target_height = VIDEO_SIZE[1]

    try:
        # Resize dengan anti-aliasing berkualitas tinggi
        overlay_pil_resized = overlay_pil.resize((target_width, target_height), Image.LANCZOS)
    except Exception as e:
        print(f"❌ Error resizing overlay to full screen: {e}")
        return base_clip

    # Ubah kembali ke ImageClip moviepy
    overlay_clip = ImageClip(np.array(overlay_pil_resized), duration=base_clip.duration)

    # Posisikan di (0,0) agar memenuhi layar
    pos_x = 0
    pos_y = 0

    try:
        # Gabungkan klip (overlay di atas video dasar)
        final_clip = CompositeVideoClip([base_clip, overlay_clip.set_pos((pos_x, pos_y))], size=VIDEO_SIZE)
        return final_clip
    except Exception as e:
        print(f"❌ Error compositing full-screen overlay: {e}")
        return base_clip # Kembalikan klip dasar jika gagal

def baca_semua_berita(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ File '{file_path}' tidak ditemukan!")
        exit(1)
    except Exception as e:
         print(f"❌ Error reading file '{file_path}': {e}")
         exit(1)

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

def buat_video(data, index=None):
    judul = data.get("Judul", "")
    print(f"▶ Membuat video: {judul}")
    try:
        opening = render_opening(judul, data.get("Subjudul", ""), FONTS)

        isi_clips = []
        isi_data = [f"Isi_{i}" for i in range(1, 30) if f"Isi_{i}" in data and data[f"Isi_{i}"].strip()]
        jeda = render_penutup(0.7)

        for idx, key in enumerate(isi_data):
            teks = data[key]
            dur = durasi_otomatis(teks)
            clip = render_text_block(teks, FONTS["isi"], 34, dur)
            isi_clips.append(clip)

            if idx < len(isi_data) - 1:
                isi_clips.append(jeda)

        penutup = render_penutup(3.0)
        final = concatenate_videoclips([opening] + isi_clips + [penutup], method="compose")
        result = add_overlay(final) # Panggil fungsi overlay yang sudah diperbarui

        filename = f"output_video_{index+1 if index is not None else '1'}.mp4"
        result.write_videofile(filename, fps=FPS, codec="libx264", audio=False)
        print(f"✅ Video selesai: {filename}\n")

    except Exception as e:
        print(f"❌ Gagal membuat video untuk '{judul}': {e}")
        # import traceback
        # print(traceback.format_exc())

if __name__ == "__main__":
    FILE_INPUT = "data_berita.txt"

    font_files_ok = True
    for font_file in FONTS.values():
        if not os.path.exists(font_file):
            print(f"❌ File Font '{font_file}' tidak ditemukan!")
            font_files_ok = False
    if not font_files_ok:
        exit(1)

    # Cek overlay di awal, tapi biarkan add_overlay() menangani jika tidak ada saat runtime
    if not os.path.exists(OVERLAY_FILE):
         print(f"⚠️ File Overlay '{OVERLAY_FILE}' tidak ditemukan (akan dilewati saat pembuatan video).")

    semua = baca_semua_berita(FILE_INPUT)
    if not semua:
        print(f"❌ Tidak ada data berita yang valid di '{FILE_INPUT}'.")
        exit(1)

    print(f"Total {len(semua)} video akan dibuat...")
    for i, data in enumerate(semua):
        buat_video(data, i)

    print("🎬 Semua video selesai dibuat (atau dilewati jika gagal).")
