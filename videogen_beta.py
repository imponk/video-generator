def render_opening(judul_txt, subjudul_txt, fonts, upper_txt=None):
    dur = durasi_judul(judul_txt, subjudul_txt)
    total_frames = int(FPS * dur)
    static_frames = int(FPS * 0.2)
    fade_frames = int(FPS * 0.8)
    margin_x = 70

    dummy_img = Image.new("RGBA", (1, 1)); draw = ImageDraw.Draw(dummy_img)
    font_upper = ImageFont.truetype(fonts["upper"], 24) if upper_txt else None
    font_judul = ImageFont.truetype(fonts["judul"], 54)
    font_sub = ImageFont.truetype(fonts["subjudul"], 28) if subjudul_txt else None

    wrapped_upper = smart_wrap(upper_txt, font_upper, VIDEO_SIZE[0]) if font_upper else None
    wrapped_judul = smart_wrap(judul_txt, font_judul, VIDEO_SIZE[0])
    wrapped_sub = smart_wrap(subjudul_txt, font_sub, VIDEO_SIZE[0]) if font_sub else None

    spacing_upper_judul = 15
    spacing_judul_sub = 18

    # --- Tentukan Posisi Y Berdasarkan Elemen Teratas ---
    # 1. Tentukan Y awal untuk elemen paling atas (di 60%)
    y_start = int(VIDEO_SIZE[1] * 0.60)
    
    y_upper = None
    y_judul = None
    y_sub = None

    current_y = y_start # Mulai dari posisi 60%

    # 2. Render Upper jika ada
    if wrapped_upper:
        y_upper = current_y
        # Ukur posisi bawah Upper untuk elemen berikutnya
        upper_bbox = draw.multiline_textbbox((margin_x, y_upper), wrapped_upper, font=font_upper, spacing=4)
        current_y = upper_bbox[3] + spacing_upper_judul # Update Y untuk Judul
    
    # 3. Render Judul (selalu ada)
    # Jika Upper tidak ada, Judul mulai di y_start (60%)
    # Jika Upper ada, Judul mulai di current_y (di bawah Upper)
    y_judul = current_y 
    # Ukur posisi bawah Judul untuk elemen berikutnya
    judul_bbox = draw.multiline_textbbox((margin_x, y_judul), wrapped_judul, font=font_judul, spacing=4)
    current_y = judul_bbox[3] + spacing_judul_sub # Update Y untuk Subjudul

    # 4. Render Subjudul jika ada
    if wrapped_sub:
        # Subjudul mulai di current_y (di bawah Judul)
        y_sub = current_y
        # (Tidak perlu update current_y lagi setelah ini)

    # --- Render Frame (Sama seperti sebelumnya) ---
    frames = []
    for i in range(total_frames):
        if i < static_frames: t = 1.0; anim = False
        elif i < static_frames + fade_frames: t = (i - static_frames) / float(fade_frames); anim = True
        else: t = 1.0; anim = False

        frame = Image.new("RGBA", VIDEO_SIZE, BG_COLOR + (255,))
        layer = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
        if wrapped_upper and y_upper is not None: make_text_frame(layer, wrapped_upper, font_upper, (margin_x, y_upper))
        # Pastikan y_judul tidak None sebelum menggambar
        if y_judul is not None: make_text_frame(layer, wrapped_judul, font_judul, (margin_x, y_judul))
        if wrapped_sub and y_sub is not None: make_text_frame(layer, wrapped_sub, font_sub, (margin_x, y_sub))
        visible = render_wipe_layer(layer, t) if anim else layer
        frame = Image.alpha_composite(frame, visible)
        frames.append(np.array(frame.convert("RGB")))
    return frames_to_clip(frames)
