from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import re
from typing import List, Dict, Tuple, Optional

class HighlightStyle:
    """Definisi style untuk highlighting"""
    
    # Default color schemes
    BLUE_HIGHLIGHT = (0, 124, 188)      # Corporate blue
    RED_HIGHLIGHT = (220, 50, 50)       # Alert red  
    GREEN_HIGHLIGHT = (50, 150, 50)     # Success green
    YELLOW_HIGHLIGHT = (255, 200, 50)   # Warning yellow
    PURPLE_HIGHLIGHT = (150, 50, 200)   # Premium purple
    
    def __init__(self, 
                 color: Tuple[int, int, int] = BLUE_HIGHLIGHT,
                 opacity: float = 0.8,
                 padding: int = 4,
                 animation_speed: float = 0.25):
        self.color = color
        self.opacity = opacity
        self.padding = padding
        self.animation_speed = animation_speed

class AdvancedHighlightProcessor:
    """Advanced text highlighting dengan smooth animations"""
    
    def __init__(self, 
                 font: ImageFont.FreeTypeFont,
                 video_width: int = 720,
                 video_height: int = 1280,
                 margin_left: int = 70,
                 margin_right: int = 90,
                 bg_color: Tuple[int, int, int] = (0, 0, 0),
                 text_color: Tuple[int, int, int] = (255, 255, 255)):
        self.font = font
        self.video_width = video_width
        self.video_height = video_height
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.bg_color = bg_color
        self.text_color = text_color
        
        # Calculate available width for text
        self.text_width = video_width - margin_left - margin_right
        
        # Calculate line height from font
        self.line_height = self._calculate_line_height()
        
        # Default highlight style
        self.default_style = HighlightStyle()
    
    def _calculate_line_height(self) -> int:
        """Calculate line height from font metrics"""
        try:
            bbox = self.font.getbbox("Ag")
            return bbox[3] - bbox[1] + 8
        except:
            return int(self.font.size * 1.2)
    
    def parse_highlights(self, text: str) -> List[Dict]:
        """Parse text untuk extract highlight segments"""
        segments = []
        current_pos = 0
        
        # Regex untuk mendeteksi highlights dengan optional style
        highlight_pattern = r'\[\[(?:(\w+):)?(.*?)\]\]'
        
        for match in re.finditer(highlight_pattern, text):
            start, end = match.span()
            
            # Add text sebelum highlight sebagai normal text
            if start > current_pos:
                normal_text = text[current_pos:start]
                segments.append({
                    'text': normal_text,
                    'is_highlight': False,
                    'style': None
                })
            
            # Add highlighted text
            style_name = match.group(1)
            highlight_text = match.group(2)
            
            segments.append({
                'text': highlight_text,
                'is_highlight': True,
                'style': style_name
            })
            
            current_pos = end
        
        # Add remaining text
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            segments.append({
                'text': remaining_text,
                'is_highlight': False,
                'style': None
            })
        
        return segments
    
    def smart_wrap_with_highlights(self, text: str) -> List[List[Dict]]:
        """Smart text wrapping yang preserve highlights"""
        segments = self.parse_highlights(text)
        lines = []
        current_line = []
        current_width = 0
        
        for segment in segments:
            words = segment['text'].split()
            
            for word in words:
                word_info = {
                    'word': word,
                    'is_highlight': segment['is_highlight'],
                    'style': segment['style']
                }
                
                word_width = self._get_text_width(word + " ")
                
                if current_width + word_width <= self.text_width:
                    current_line.append(word_info)
                    current_width += word_width
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = [word_info]
                    current_width = word_width
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _get_text_width(self, text: str) -> float:
        """Get text width using font metrics"""
        try:
            return self.font.getlength(text)
        except:
            return len(text) * (self.font.size * 0.6)
    
    def calculate_highlight_segments(self, lines: List[List[Dict]], y_start: int) -> List[Dict]:
        """Calculate position dan size untuk setiap highlight segment"""
        highlight_segments = []
        char_counter = 0
        
        for line_idx, line in enumerate(lines):
            y_position = y_start + (line_idx * self.line_height)
            x_position = self.margin_left
            
            for word_info in line:
                word = word_info['word']
                is_highlight = word_info['is_highlight']
                style = word_info['style']
                
                if is_highlight:
                    word_width = self._get_text_width(word + " ")
                    
                    highlight_segments.append({
                        'text': word,
                        'x': x_position,
                        'y': y_position,
                        'width': word_width,
                        'height': self.line_height,
                        'char_start': char_counter,
                        'char_end': char_counter + len(word),
                        'style': style,
                        'line_idx': line_idx
                    })
                
                word_width = self._get_text_width(word + " ")
                x_position += word_width
                char_counter += len(word) + 1
        
        return highlight_segments
    
    def get_highlight_style(self, style_name: Optional[str]) -> HighlightStyle:
        """Get highlight style berdasarkan nama atau default"""
        if not style_name:
            return self.default_style
        
        styles = {
            'blue': HighlightStyle(HighlightStyle.BLUE_HIGHLIGHT),
            'red': HighlightStyle(HighlightStyle.RED_HIGHLIGHT),
            'green': HighlightStyle(HighlightStyle.GREEN_HIGHLIGHT),
            'yellow': HighlightStyle(HighlightStyle.YELLOW_HIGHLIGHT),
            'purple': HighlightStyle(HighlightStyle.PURPLE_HIGHLIGHT),
            'important': HighlightStyle(HighlightStyle.RED_HIGHLIGHT, opacity=0.9, animation_speed=0.2),
            'success': HighlightStyle(HighlightStyle.GREEN_HIGHLIGHT, opacity=0.8),
            'warning': HighlightStyle(HighlightStyle.YELLOW_HIGHLIGHT, opacity=0.7),
            'fast': HighlightStyle(HighlightStyle.BLUE_HIGHLIGHT, animation_speed=0.15),
            'slow': HighlightStyle(HighlightStyle.BLUE_HIGHLIGHT, animation_speed=0.4),
        }
        
        return styles.get(style_name.lower(), self.default_style)
    
    def render_frame_with_highlights(self, 
                                   lines: List[List[Dict]], 
                                   y_start: int,
                                   frame_idx: int, 
                                   total_frames: int,
                                   highlight_segments: List[Dict]) -> np.ndarray:
        """Render single frame dengan progressive highlighting"""
        
        # Create base image
        frame = Image.new("RGB", (self.video_width, self.video_height), self.bg_color)
        
        # Create highlight layer
        highlight_layer = Image.new("RGBA", (self.video_width, self.video_height), (0, 0, 0, 0))
        highlight_draw = ImageDraw.Draw(highlight_layer)
        
        # Calculate highlight progress
        highlight_progress = min(1.0, (frame_idx / max(1, total_frames * 0.25)))
        total_chars = sum(len(seg['text']) for seg in highlight_segments)
        current_highlight_chars = int(total_chars * highlight_progress)
        
        # Draw highlights
        highlighted_chars = 0
        for segment in highlight_segments:
            if highlighted_chars < current_highlight_chars:
                chars_available = current_highlight_chars - highlighted_chars
                chars_to_highlight = min(len(segment['text']), chars_available)
                
                if chars_to_highlight > 0:
                    style = self.get_highlight_style(segment['style'])
                    
                    if chars_to_highlight >= len(segment['text']):
                        highlight_width = segment['width'] - 8
                    else:
                        partial_text = segment['text'][:chars_to_highlight]
                        highlight_width = self._get_text_width(partial_text)
                    
                    alpha = int(255 * style.opacity)
                    highlight_color = style.color + (alpha,)
                    
                    # Adjust Y position (turun 6px)
                    adjusted_y = segment['y'] + 4
                    
                    highlight_draw.rectangle([
                        segment['x'] - style.padding,
                        adjusted_y,
                        segment['x'] + highlight_width + style.padding,
                        adjusted_y + segment['height']
                    ], fill=highlight_color)
                
                highlighted_chars += len(segment['text'])
        
        # Composite highlight layer
        frame = Image.alpha_composite(frame.convert("RGBA"), highlight_layer).convert("RGB")
        
        # Draw text on top
        text_draw = ImageDraw.Draw(frame)
        
        for line_idx, line in enumerate(lines):
            y_position = y_start + (line_idx * self.line_height)
            x_position = self.margin_left
            
            for word_info in line:
                word = word_info['word']
                text_draw.text((x_position, y_position), word, 
                             font=self.font, fill=self.text_color)
                
                word_width = self._get_text_width(word + " ")
                x_position += word_width
        
        return np.array(frame)
    
    def render_text_with_highlights(self, 
                                  text: str, 
                                  duration: float,
                                  y_position: int = 400,
                                  fps: int = 30) -> List[np.ndarray]:
        """Render complete text dengan smooth highlight animation"""
        
        # Parse dan wrap text
        lines = self.smart_wrap_with_highlights(text)
        
        # Calculate highlight segments
        highlight_segments = self.calculate_highlight_segments(lines, y_position)
        
        # Generate frames
        total_frames = int(fps * duration)
        frames = []
        
        for frame_idx in range(total_frames):
            frame = self.render_frame_with_highlights(
                lines, y_position, frame_idx, total_frames, highlight_segments
            )
            frames.append(frame)
        
        return frames

class VideoGenerator:
    def __init__(self):
        # Original initialization code tetap sama
        self.setup_fonts()
        self.setup_templates()
        
        # Enhanced: Initialize highlight processors
        self.highlight_processors = {}
        self._initialize_highlight_system()
        
        # GUI setup
        self.root = tk.Tk()
        self.root.title("Enhanced Video Generator with Advanced Highlights")
        self.root.geometry("500x600")
        
        self.setup_gui()
        
        # Variables
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.selected_template = tk.StringVar(value="default")
        self.processing = False
    
    def setup_fonts(self):
        """Setup fonts - tetap sama seperti original"""
        self.fonts = {}
        
        # Default font paths (flat structure)
        font_files = [
            "DMSerifDisplay-Regular.ttf",
            "Poppins-Bold.ttf", 
            "ProximaNova-Regular.ttf",
            "ProximaNova-Bold.ttf"
        ]
        
        # Load fonts dengan fallback
        for font_file in font_files:
            if os.path.exists(font_file):
                try:
                    base_name = font_file.split('.')[0]
                    self.fonts[base_name] = {
                        'title': ImageFont.truetype(font_file, 54),
                        'subtitle': ImageFont.truetype(font_file, 28),
                        'content': ImageFont.truetype(font_file, 34)
                    }
                except Exception as e:
                    print(f"Warning: Could not load {font_file}: {e}")
        
        # Fallback jika tidak ada fonts
        if not self.fonts:
            default_font = ImageFont.load_default()
            self.fonts['default'] = {
                'title': default_font,
                'subtitle': default_font,
                'content': default_font
            }
    
    def setup_templates(self):
        """Setup templates - existing logic"""
        self.templates = {
            "default": {
                "video_size": (720, 1280),
                "bg_color": (0, 0, 0),
                "text_color": (255, 255, 255),
                "fps": 30
            }
        }
    
    def _initialize_highlight_system(self):
        """Initialize highlight processors untuk setiap font"""
        for font_family, font_dict in self.fonts.items():
            self.highlight_processors[font_family] = {}
            for font_type, font in font_dict.items():
                self.highlight_processors[font_family][font_type] = AdvancedHighlightProcessor(
                    font=font,
                    video_width=720,
                    video_height=1280,
                    bg_color=(0, 0, 0),
                    text_color=(255, 255, 255)
                )
    
    def setup_gui(self):
        """Setup GUI - enhanced version"""
        # Title
        title_label = tk.Label(self.root, text="Enhanced Video Generator", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Highlight info
        highlight_info = tk.Label(self.root, 
                                 text="✨ Now with Advanced Highlights!\nUse [[text]] or [[style:text]]",
                                 font=("Arial", 10), fg="blue")
        highlight_info.pack(pady=5)
        
        # Input folder selection
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(input_frame, text="Input Folder:").pack(anchor="w")
        input_path_frame = tk.Frame(input_frame)
        input_path_frame.pack(fill="x", pady=5)
        
        tk.Entry(input_path_frame, textvariable=self.input_folder, width=50).pack(side="left", fill="x", expand=True)
        tk.Button(input_path_frame, text="Browse", command=self.select_input_folder).pack(side="right", padx=(5,0))
        
        # Output folder selection
        output_frame = tk.Frame(self.root)
        output_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(output_frame, text="Output Folder:").pack(anchor="w")
        output_path_frame = tk.Frame(output_frame)
        output_path_frame.pack(fill="x", pady=5)
        
        tk.Entry(output_path_frame, textvariable=self.output_folder, width=50).pack(side="left", fill="x", expand=True)
        tk.Button(output_path_frame, text="Browse", command=self.select_output_folder).pack(side="right", padx=(5,0))
        
        # Template selection
        template_frame = tk.Frame(self.root)
        template_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(template_frame, text="Template:").pack(anchor="w")
        template_menu = tk.OptionMenu(template_frame, self.selected_template, *self.templates.keys())
        template_menu.pack(anchor="w", pady=5)
        
        # Highlight styles info
        styles_frame = tk.Frame(self.root)
        styles_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(styles_frame, text="Available Highlight Styles:", font=("Arial", 10, "bold")).pack(anchor="w")
        styles_text = """• [[important:text]] - Red highlight for important info
• [[success:text]] - Green highlight for positive news  
• [[warning:text]] - Yellow highlight for warnings
• [[fast:text]] - Quick animation
• [[slow:text]] - Slow animation
• [[text]] - Default blue highlight"""
        
        tk.Label(styles_frame, text=styles_text, font=("Arial", 9), 
                justify="left", fg="gray").pack(anchor="w", pady=5)
        
        # Process button
        self.process_button = tk.Button(self.root, text="🎬 Generate Videos with Highlights", 
                                       command=self.start_processing, 
                                       font=("Arial", 12, "bold"),
                                       bg="#4CAF50", fg="white", 
                                       state="normal")
        self.process_button.pack(pady=20)
        
        # Progress area
        self.progress_text = tk.Text(self.root, height=10, width=60)
        self.progress_text.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Scrollbar untuk progress text
        scrollbar = tk.Scrollbar(self.progress_text)
        scrollbar.pack(side="right", fill="y")
        self.progress_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.progress_text.yview)
    
    def select_input_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_folder.set(folder)
    
    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
    
    def log_progress(self, message):
        """Log progress to GUI"""
        self.progress_text.insert(tk.END, f"{message}\n")
        self.progress_text.see(tk.END)
        self.root.update()
    
    def has_highlights(self, text: str) -> bool:
        """Check if text contains highlight markers"""
        return "[[" in text and "]]" in text
    
    def calculate_smart_duration(self, text: str) -> float:
        """Calculate duration berdasarkan reading speed"""
        # Remove highlight markers
        clean_text = re.sub(r'\[\[.*?\]\]', lambda m: m.group(0)[2:-2], text)
        word_count = len(clean_text.split())
        
        # Reading speed: 160 WPM
        base_duration = (word_count / 160) * 60
        duration = base_duration + 1.5  # Buffer
        
        return max(3.0, min(10.0, duration))
    
    def create_highlighted_clip(self, text: str, duration: float, y_position: int = 400) -> ImageClip:
        """Create clip dengan advanced highlighting"""
        
        # Get appropriate font and processor
        font_family = list(self.fonts.keys())[0]  # Use first available font
        processor = self.highlight_processors[font_family]['content']
        
        # Generate frames dengan highlights
        frames = processor.render_text_with_highlights(
            text=text,
            duration=duration,
            y_position=y_position,
            fps=30
        )
        
        # Convert frames ke ImageClip
        clips = []
        for frame in frames:
            clip = ImageClip(frame, duration=1.0/30)
            clips.append(clip)
        
        return concatenate_videoclips(clips, method="compose")
    
    def create_basic_clip(self, text: str, duration: float, y_position: int = 400) -> ImageClip:
        """Create basic clip tanpa highlights - fallback method"""
        
        # Simple implementation untuk compatibility
        template = self.templates[self.selected_template.get()]
        video_size = template["video_size"]
        bg_color = template["bg_color"]
        text_color = template["text_color"]
        
        # Create simple frame
        frame = Image.new("RGB", video_size, bg_color)
        draw = ImageDraw.Draw(frame)
        
        # Get font
        font_family = list(self.fonts.keys())[0]
        font = self.fonts[font_family]['content']
        
        # Draw text (simple implementation)
        try:
            draw.text((70, y_position), text, font=font, fill=text_color)
        except:
            draw.text((70, y_position), text, fill=text_color)
        
        return ImageClip(np.array(frame), duration=duration)
    
    def process_text_file(self, file_path: str) -> bool:
        """Process single text file dengan highlight support"""
        try:
            self.log_progress(f"📝 Processing: {os.path.basename(file_path)}")
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                self.log_progress(f"⚠️ Empty file: {file_path}")
                return False
            
            # Split into segments
            segments = self.split_content(content)
            self.log_progress(f"   Found {len(segments)} segments")
            
            # Generate clips
            all_clips = []
            
            for i, segment in enumerate(segments, 1):
                self.log_progress(f"   Processing segment {i}/{len(segments)}")
                
                # Calculate duration
                duration = self.calculate_smart_duration(segment)
                
                # Create clip dengan atau tanpa highlights
                if self.has_highlights(segment):
                    self.log_progress(f"   ✨ Using advanced highlights")
                    clip = self.create_highlighted_clip(segment, duration, 400)
                else:
                    self.log_progress(f"   📝 Using basic rendering")
                    clip = self.create_basic_clip(segment, duration, 400)
                
                all_clips.append(clip)
                
                # Add separator except last segment
                if i < len(segments):
                    black_frame = np.zeros((1280, 720, 3), dtype=np.uint8)
                    separator = ImageClip(black_frame, duration=0.5)
                    all_clips.append(separator)
            
            # Combine clips
            self.log_progress("   🎬 Combining clips...")
            final_video = concatenate_videoclips(all_clips, method="compose")
            
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_file = os.path.join(self.output_folder.get(), f"{base_name}_enhanced.mp4")
            
            # Write video
            self.log_progress("   🎥 Encoding video...")
            final_video.write_videofile(
                output_file,
                fps=30,
                codec='libx264',
                audio=False,
                verbose=False,
                logger=None
            )
            
            self.log_progress(f"✅ Success: {base_name}_enhanced.mp4")
            return True
            
        except Exception as e:
            self.log_progress(f"❌ Error processing {file_path}: {str(e)}")
            return False
    
    def split_content(self, content: str) -> List[str]:
        """Split content into segments"""
        # Split by double newlines first
        segments = [s.strip() for s in content.split('\n\n') if s.strip()]
        
        # If only one segment and it's long, split by sentences
        if len(segments) == 1 and len(content) > 300:
            sentences = content.split('. ')
            segments = []
            current_segment = ""
            
            for sentence in sentences:
                if not sentence.strip():
                    continue
                    
                test_segment = current_segment + ". " + sentence if current_segment else sentence
                
                if len(test_segment) > 200 and current_segment:
                    segments.append(current_segment.strip())
                    current_segment = sentence
                else:
                    current_segment = test_segment
            
            if current_segment.strip():
                segments.append(current_segment.strip())
        
        return segments
    
    def start_processing(self):
        """Start processing in separate thread"""
        if self.processing:
            return
        
        if not self.input_folder.get() or not self.output_folder.get():
            messagebox.showerror("Error", "Please select input and output folders")
            return
        
        self.processing = True
        self.process_button.config(state="disabled", text="Processing...")
        self.progress_text.delete(1.0, tk.END)
        
        # Start processing thread
        thread = threading.Thread(target=self.process_files)
        thread.daemon = True
        thread.start()
    
    def process_files(self):
        """Process all files in input folder"""
        try:
            input_dir = self.input_folder.get()
            output_dir = self.output_folder.get()
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Find text files
            text_files = []
            for file in os.listdir(input_dir):
                if file.endswith('.txt'):
                    text_files.append(os.path.join(input_dir, file))
            
            if not text_files:
                self.log_progress("❌ No .txt files found in input folder")
                return
            
            self.log_progress(f"🎬 Found {len(text_files)} text files")
            self.log_progress("🚀 Starting processing with advanced highlights...")
            
            successful = 0
            for i, file_path in enumerate(text_files, 1):
                self.log_progress(f"\n📹 {i}/{len(text_files)}: Processing...")
                
                if self.process_text_file(file_path):
                    successful += 1
                
                # Update progress
                progress = (i / len(text_files)) * 100
                self.log_progress(f"Progress: {progress:.1f}% ({i}/{len(text_files)})")
            
            self.log_progress(f"\n🎉 Processing completed!")
            self.log_progress(f"✅ Successfully generated {successful}/{len(text_files)} videos")
            self.log_progress(f"📁 Output saved to: {output_dir}")
            
        except Exception as e:
            self.log_progress(f"❌ Processing error: {str(e)}")
        
        finally:
            self.processing = False
            self.process_button.config(state="normal", text="🎬 Generate Videos with Highlights")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

def main():
    """Main function"""
    print("🎬 Enhanced Video Generator with Advanced Highlights")
    print("=" * 50)
    print("Features:")
    print("✨ Multi-line progressive highlighting")
    print("🎨 Custom highlight styles (important, success, warning)")
    print("⚡ Smooth character-by-character animation")
    print("🇮🇩 Indonesian text optimization")
    print("📁 Flat file structure support")
    print("🔄 Backward compatibility maintained")
    print("=" * 50)
    
    app = VideoGenerator()
    app.run()

if __name__ == "__main__":
    main()
