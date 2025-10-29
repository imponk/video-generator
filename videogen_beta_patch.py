"""
Patch untuk videogen_beta.py — optimalisasi RAM.
Tidak mengubah logika tampilan, parsing, atau layout.
Hanya mengganti metode rendering frame menjadi streaming.
"""

from moviepy.video.VideoClip import VideoClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# pastikan variabel global (VIDEO_SIZE, BG_COLOR, TEXT_COLOR, FPS, smart_wrap, render_wipe_layer, make_text_frame)
# sudah tersedia di script utama (videogen_beta.py)

def make_clip_from_generator(frame_generator, duration):
    """
    Membuat clip dari generator frame -> jauh lebih hemat RAM.
    """
    def make_frame(t):
        i = int(t * FPS)
        return frame_generator(i)
    return VideoClip(make_frame, duration=duration)


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
    spacing_judul_sub = 16

    def calculate_layout(current_judul_font_size):
        font_upper = ImageFont.truetype(fonts["upper"], upper_font_size) if upper_txt else None
        font_judul = ImageFont.truetype(fonts["judul"], current_judul_font_size) if judul_txt else None
        font_sub = ImageFont.truetype(fonts["subjudul"], sub_font_size) if subjudul_txt else None
        if not font_judul:
            font_judul = ImageFont.truetype(fonts["judul"], current_judul_font_size)

        wrapped_upper = smart_wrap(upper_txt, font_upper, VIDEO_SIZE[0]) if font_upper and upper_txt else None
        wrapped_judul = smart_wrap(judul_txt, font_judul, VIDEO_SIZE[0]) if font_judul and judul_txt else ""
        wrapped_sub = smart_wrap(subjudul_txt, font_sub, VIDEO_SIZE[0]) if font_sub and subjudul_txt else None

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
        current_y = y_start
        y_upper = y_judul = y_sub = None
        bottom_y = y_start

        if wrapped_upper:
            y_upper = current_y
            upper_bbox = draw.multiline_textbbox((margin_x, y_upper), wrapped_upper, font=font_upper, spacing=4)
            current_y = upper_bbox[3] + spacing_upper_judul
            bottom_y = upper_bbox[3]

        y_judul = current_y
        if wrapped_judul:
            judul_bbox = draw.multiline_textbbox((margin_x, y_judul), wrapped_judul, font=font_judul, spacing=4)
            bottom_y = judul_bbox[3]
            current_y = judul_bbox[3] + spacing_judul_sub

        if wrapped_sub:
            y_sub = current_y
            sub_bbox = draw.multiline_textbbox((margin_x, y_sub), wrapped_sub, font=font_sub, spacing=4)
            bottom_y = sub_bbox[3]

        return {
            "font_upper": font_upper, "font_judul": font_judul, "font_sub": font_sub,
            "wrapped_upper": wrapped_upper, "wrapped_judul": wrapped_judul, "wrapped_sub": wrapped_sub,
            "y_upper": y_upper, "y_judul": y_judul, "y_sub": y_sub, "bottom_y": bottom_y
        }

    layout = calculate_layout(judul_font_size)
    if layout["bottom_y"] > batas_bawah_aman:
        layout = calculate_layout(int(judul_font_size * 0.94))

    def frame_generator(i):
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
        if layout["wrapped_upper"] and layout["y_upper"] is not None:
            make_text_frame(layer, layout["wrapped_upper"], layout["font_upper"], (margin_x, layout["y_upper"]))
        if layout["wrapped_judul"] and layout["y_judul"] is not None:
            make_text_frame(layer, layout["wrapped_judul"], layout["font_judul"], (margin_x, layout["y_judul"]))
        if layout["wrapped_sub"] and layout["y_sub"] is not None:
            make_text_frame(layer, layout["wrapped_sub"], layout["font_sub"], (margin_x, layout["y_sub"]))
        visible = render_wipe_layer(layer, t) if anim else layer
        return np.array(Image.alpha_composite(frame, visible).convert("RGB"))

    return make_clip_from_generator(frame_generator, dur)


def render_text_block(text, font_path, font_size, dur, anim=True):
    total_frames = int(FPS * dur)
    fade_frames = min(18, total_frames)
    margin_x = 70
    base_y = int(VIDEO_SIZE[1] * 0.60)
    margin_bawah_logo = 170
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
    y_pos = base_y if bottom_y <= batas_bawah_aman else base_y - min(bottom_y - batas_bawah_aman + 10, 220)

    def frame_generator(i):
        t = 1.0 if not anim else min(1.0, i / float(fade_frames))
        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
        draw_real = ImageDraw.Draw(layer)
        draw_real.multiline_text((margin_x, y_pos), wrapped, font=font, fill=TEXT_COLOR, align="left", spacing=6)
        visible = render_wipe_layer(layer, t)
        return np.array(Image.alpha_composite(frame, visible).convert("RGB"))

    return make_clip_from_generator(frame_generator, dur)


def render_penutup(dur=3.0):
    def frame_generator(i):
        return np.array(Image.new("RGB", VIDEO_SIZE, BG_COLOR))
    return make_clip_from_generator(frame_generator, dur)
