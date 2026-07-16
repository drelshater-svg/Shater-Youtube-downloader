import os
import glob
import shutil
import ffmpeg
import gradio as gr
from pytubefix import YouTube, Playlist

def get_dropdown_options():
    """Dynamically reads folder assets on initialization"""
    fonts = [os.path.basename(f) for f in glob.glob("fonts/*.ttf") + glob.glob("fonts/*.otf")]
    music = [os.path.basename(m) for m in glob.glob("music/*.mp3")]
    
    if not fonts: fonts = ["Default System Font"]
    if not music: music = ["No background music available"]
    return fonts, music

def sanitize_filename(filename):
    invalid_chars = '.()[]{};:,<>?/\\|"'
    sanitized = ''.join(c for c in filename if c not in invalid_chars)
    return sanitized.strip().replace(" ", "_")

def format_ffmpeg_path(path):
    """Safely formats path parameters to insulate against platform specific backslash crashes"""
    return path.replace("\\", "/").replace(":", "\\:")

def process_single_video(video_source, local_file, url, quality, 
                         add_watermark, watermark_text, corner, fontsize, watermark_color, 
                         add_subtitles, subtitle_fontsize, subtitle_color, subtitle_bg, subtitle_bg_color, font_name, 
                         add_music, music_track, music_volume, clear_temp):

    
    base_dir = os.getcwd()
    temp_dir = os.path.join(base_dir, "temp_downloads")
    final_dir = os.path.join(base_dir, "downloads")
    
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(final_dir, exist_ok=True)
    
    current_working_file = None
    clean_title = "processed_video"
    
    try:
        # 1. INPUT LAYER SELECTOR
        if video_source == "Local File Browse":
            if not local_file:
                raise ValueError("No local video file selected. Browse and upload a file first.")
            clean_title = sanitize_filename(os.path.splitext(os.path.basename(local_file))[0])
            current_working_file = os.path.join(temp_dir, f"{clean_title}_source.mp4")
            shutil.copy(local_file, current_working_file)
            print(f"Imported local file: {current_working_file}")
            
        else: # YouTube Download Selection
            if not url:
                raise ValueError("YouTube target URL field cannot be empty.")
            
            yt = YouTube(url)
            clean_title = sanitize_filename(yt.title)
            print(f"Downloading from YouTube: {yt.title}")
            
            # Sub-pipeline: Handle pure audio stream splits
            if quality == "Audio Only":
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                downloaded = audio_stream.download(output_path=temp_dir, filename=f"{clean_title}_audio.mp3")
                final_output = os.path.join(final_dir, f"{clean_title}.mp3")
                shutil.move(downloaded, final_output)
                return final_output
            
            # High-Resolution Adaptive Downloading Pipeline
            video_stream = yt.streams.filter(progressive=False, type='video', subtype='mp4', res=quality).first()
            if not video_stream:
                video_stream = yt.streams.filter(progressive=False, type='video', subtype='mp4').order_by('resolution').desc().first()
            
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if not video_stream or not audio_stream:
                raise ValueError("Required video or audio streams not found.")
                
            raw_v = video_stream.download(output_path=temp_dir, filename=f"{clean_title}_raw_v.mp4")
            raw_a = audio_stream.download(output_path=temp_dir, filename=f"{clean_title}_raw_a.mp3")
            
            # Base stitching step: Creates the foundational track that contains original audio!
            current_working_file = os.path.join(temp_dir, f"{clean_title}_base.mp4")
            ffmpeg.output(ffmpeg.input(raw_v), ffmpeg.input(raw_a), current_working_file, vcodec='copy', acodec='aac').run(overwrite_output=True, quiet=False)

        # 2. SUBTITLE HARDCODING LAYER
        if add_subtitles and video_source == "YouTube Link":
            # Attempt to find caption tracks
            yt = YouTube(url)
            caption_track = None
            if 'en' in yt.captions: caption_track = yt.captions['en']
            elif 'a.en' in yt.captions: caption_track = yt.captions['a.en']
            elif yt.captions: caption_track = list(yt.captions.values())[0]
            
            if caption_track:
                sub_file_path = os.path.join(temp_dir, f"{clean_title}_subs.srt")
                caption_track.download(title=f"{clean_title}_subs", srt=True, output_path=temp_dir)
                
                # Double-check filename mapping from pytubefix outputs
                inferred_path = os.path.join(temp_dir, f"{clean_title}_subs.srt")
                if not os.path.exists(inferred_path):
                    # Fallback capture if title mapping acts up
                    found_srts = glob.glob(os.path.join(temp_dir, "*.srt"))
                    if found_srts: inferred_path = found_srts[0]
                


                if os.path.exists(inferred_path):
                    subbed_out = os.path.join(temp_dir, f"{clean_title}_subbed.mp4")
                    
                    # Double escaping for Windows drives and forward slash mapping
                    safe_sub_path = inferred_path.replace("\\", "/").replace(":", "\\:")
                    
                    # Style Mapping Configurations
                    sub_hex = subtitle_color.lstrip('#')
                    ass_color = f"&H00{sub_hex[4:6]}{sub_hex[2:4]}{sub_hex[0:2]}"
                    
                    bg_hex = subtitle_bg_color.lstrip('#')
                    ass_bg_color = f"{bg_hex[4:6]}{bg_hex[2:4]}{bg_hex[0:2]}"
                    
                    style_args = f"FontSize={subtitle_fontsize},PrimaryColour={ass_color}"
                    if font_name != "Default System Font":
                        style_args += f",Fontname={os.path.splitext(font_name)[0]}"
                    
                    if subtitle_bg == "Opaque Solid Box":
                        style_args += f",BorderStyle=3,OutlineColour=&H00000000,BackColour=&H00{ass_bg_color}"
                    elif subtitle_bg == "Semi-Transparent Box":
                        style_args += f",BorderStyle=3,OutlineColour=&H00000000,BackColour=&H80{ass_bg_color}"
                    else:
                        style_args += ",BorderStyle=1,Outline=1,OutlineColour=&H00000000"
                    
                    # FIXED: Explicitly isolate inputs to map both video filter output and original audio channels
                    video_input = ffmpeg.input(current_working_file)
                    video_stream_with_subs = video_input.video.filter('subtitles', filename=safe_sub_path, force_style=style_args)
                    audio_stream = video_input.audio
                    
                    # Stitches the subtitle video filter output and audio channel back together cleanly
                    ffmpeg.output(
                        video_stream_with_subs, audio_stream, subbed_out, 
                        vcodec='libx264', pix_fmt='yuv420p', acodec='aac'
                    ).run(overwrite_output=True, quiet=True)
                    
                    current_working_file = subbed_out
                    print("Subtitles hardcoded completely with original audio preserved.")



        # =========================================================================
        # 3, 4 & 5. UNIFIED SINGLE-PASS FLUID FFMPEG RENDERING ENGINE
        # =========================================================================
        print("Configuring optimized single-pass filter graph...")
        
        # Define explicit base input layer from your current file state
        video_input = ffmpeg.input(current_working_file)
        
        # Check for existing audio tracks natively inside the source file
        probe = ffmpeg.probe(current_working_file)
        has_audio = any(stream['codec_type'] == 'audio' for stream in probe.get('streams', []))
        
        # Begin isolating our running video stream array in memory
        active_video_stream = video_input.video

        # --- A. SUBTITLE FILTER ELEMENT ---
        if add_subtitles and video_source == "YouTube Link":
            # Attempt to find caption tracks
            yt = YouTube(url)
            caption_track = None
            if 'en' in yt.captions: caption_track = yt.captions['en']
            elif 'a.en' in yt.captions: caption_track = yt.captions['a.en']
            elif yt.captions: caption_track = list(yt.captions.values())
            
            if caption_track:
                caption_track.download(title=f"{clean_title}_subs", srt=True, output_path=temp_dir)
                
                inferred_path = os.path.join(temp_dir, f"{clean_title}_subs.srt")
                if not os.path.exists(inferred_path):
                    found_srts = glob.glob(os.path.join(temp_dir, "*.srt"))
                    if found_srts: inferred_path = found_srts[0] if found_srts else None
                
                if inferred_path and os.path.exists(inferred_path):
                    # Double escaping for Windows drives and forward slash mapping
                    safe_sub_path = inferred_path.replace("\\", "/").replace(":", "\\:")
                    
                    # Style Mapping Configurations
                    sub_hex = subtitle_color.lstrip('#')
                    ass_color = f"&H00{sub_hex[4:6]}{sub_hex[2:4]}{sub_hex[0:2]}"
                    
                    bg_hex = subtitle_bg_color.lstrip('#')
                    ass_bg_color = f"{bg_hex[4:6]}{bg_hex[2:4]}{bg_hex[0:2]}"
                    
                    style_args = f"FontSize={subtitle_fontsize},PrimaryColour={ass_color}"
                    if font_name != "Default System Font":
                        style_args += f",Fontname={os.path.splitext(font_name)[0]}"
                    
                    if subtitle_bg == "Opaque Solid Box":
                        style_args += f",BorderStyle=3,OutlineColour=&H00000000,BackColour=&H00{ass_bg_color}"
                    elif subtitle_bg == "Semi-Transparent Box":
                        style_args += f",BorderStyle=3,OutlineColour=&H00000000,BackColour=&H80{ass_bg_color}"
                    else:
                        style_args += ",BorderStyle=1,Outline=1,OutlineColour=&H00000000"
                    
                    # Chain subtitle filter directly over our active in-memory track
                    active_video_stream = active_video_stream.filter('subtitles', filename=safe_sub_path, force_style=style_args)
                    print("-> Subtitle layer chained into the graph pipeline.")

        # --- B. WATERMARK FILTER ELEMENT ---
        if add_watermark and watermark_text:
            positions = {
                "Top Left": {"x": "10", "y": "10"},
                "Top Right": {"x": "w-tw-10", "y": "10"},
                "Bottom Left": {"x": "10", "y": "h-th-10"},
                "Bottom Right": {"x": "w-tw-10", "y": "h-th-10"}
            }
            pos = positions.get(corner, {"x": "10", "y": "10"})
            
            drawtext_args = {
                'text': watermark_text, 
                'fontsize': int(fontsize),
                'fontcolor': watermark_color, 
                'x': pos["x"], 
                'y': pos["y"]
            }
            
            # Cross-platform safe font file fallbacks if "Default System Font" is chosen
            if font_name and font_name != "Default System Font":
                font_path = os.path.abspath(os.path.join(base_dir, "fonts", font_name))
                if os.path.exists(font_path):
                    drawtext_args['fontfile'] = font_path
            else:
                if os.name == 'nt':  # Windows
                    win_font = "C:/Windows/Fonts/arial.ttf"
                    if os.path.exists(win_font): drawtext_args['fontfile'] = win_font
                elif os.path.exists("/System/Library/Fonts/Helvetica.ttc"):  # macOS
                    drawtext_args['fontfile'] = "/System/Library/Fonts/Helvetica.ttc"
                elif os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):  # Linux
                    drawtext_args['fontfile'] = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            
            # Chain watermark rendering consecutively over the active track state
            active_video_stream = active_video_stream.filter('drawtext', **drawtext_args)
            print("-> Watermark layer chained into the graph pipeline.")

        # --- C. AUDIO PROCESSING ENGINE ---
        if has_audio:
            active_audio_stream = video_input.audio
        else:
            active_audio_stream = None

        if add_music and music_track and music_track != "No background music available":
            music_path = os.path.join(base_dir, "music", music_track)
            if os.path.exists(music_path):
                # Load infinite background loop input stream
                music_input = ffmpeg.input(music_path, stream_loop=-1)
                audio_bgm = music_input.audio.filter('volume', float(music_volume))
                
                if has_audio:
                    print("Original voice track detected. Blending looped background music safely...")
                    # Mix channels natively via amix. normalize=0 prevents voice track volume dropping
                    active_audio_stream = ffmpeg.filter([active_audio_stream, audio_bgm], 'amix', duration='first', normalize=0)
                else:
                    print("No original audio found. mapping background music stream directly.")
                    v_duration = next((stream['duration'] for stream in probe.get('streams', []) if stream['codec_type'] == 'video'), None)
                    if v_duration:
                        audio_bgm = audio_bgm.filter('atrim', duration=float(v_duration))
                    active_audio_stream = audio_bgm

        # --- D. COMPILED EXPORT RENDER EXECUTION ---
        unified_output = os.path.join(temp_dir, f"{clean_title}_unified_render.mp4")
        
        # Build mapping inputs conditionally depending on track existence profiles
        output_streams = [active_video_stream]
        if active_audio_stream:
            output_streams.append(active_audio_stream)
            
        print("Compiling all filter graph configurations... Encoding single-pass target file...")
        
        # Run everything in ONE execution window. libx264 ensures clean web playback for Gradio
        ffmpeg.output(
            *output_streams, unified_output, 
            vcodec='libx264', pix_fmt='yuv420p', acodec='aac' if active_audio_stream else 'none'
        ).run(overwrite_output=True, quiet=False)
        
        current_working_file = unified_output
        print("Unified single-pass filtering pass completed perfectly.")

        # --- 5. FINAL FILENAME SAVE OUT ---
        final_output_path = os.path.join(final_dir, f"{clean_title}_final.mp4")
        if os.path.exists(current_working_file):
            shutil.move(current_working_file, final_output_path)
            print(f"File moved safely to destination: {final_output_path}")
        else:
            print(f"Error: The file {current_working_file} does not exist. Unable to move to {final_output_path}")
            return None, "File not found after processing"

        return final_output_path
        
    finally:
        # 6. ENFORCED CLEANUP COMPLIANCE LAYER
        if clear_temp and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)




def orchestrate_pipeline(video_source, local_file, url, download_playlist, quality, 
                         watermark_checkbox, watermark_text, watermark_position, watermark_size, watermark_color,
                         sub_check, sub_size, sub_color, sub_bg_style, sub_bg_color, font_picker,
                         music_check, music_dropdown, music_vol_slider, purge_check):


    try:
        if video_source == "YouTube Link" and download_playlist and "playlist" in url.lower():
            pl = Playlist(url)
            print(f"Playlist detected: {pl.title} ({len(pl.video_urls)} videos found)")
            processed_paths = []
            
            for index, video_url in enumerate(pl.video_urls, start=1):
                try:
                    print(f"Processing playlist tracking item ({index}/{len(pl.video_urls)}): {video_url}")
                    path = process_single_video("YouTube Link", None, video_url, quality, 
                            add_watermark, watermark_text, corner, fontsize, fontcolor, 
                            add_subtitles, subtitle_fontsize, subtitle_color, subtitle_bg, subtitle_bg_color, font_name, 
                            add_music, music_track, music_volume, clear_temp)


                    processed_paths.append(path)
                except Exception as e:
                    print(f"Skipping corrupt index file {index}: {str(e)}")
                    continue
            
            if processed_paths:
                return processed_paths, f"Successfully executed playlist processing! Saved: {len(processed_paths)}"
            else:
                return None, "No files inside the playlist could be parsed correctly."
        else:
            # Single Video File Mode
            res_path = process_single_video(video_source, local_file, url, quality, 
                            watermark_checkbox, watermark_text, watermark_position, watermark_size, watermark_color,
                            sub_check, sub_size, sub_color, sub_bg_style, sub_bg_color, font_picker,
                            music_check, music_dropdown, music_vol_slider, purge_check)
            
            if not res_path or not os.path.exists(res_path):
                return None, "Processing failed. Output file could not be generated."
                
            return res_path, "Pipeline executed successfully!"
            
    except Exception as err:
        print(f"Orchestration fatal catch: {str(err)}")
        # Returns None for the video window, and the text string cleanly for the console window
        return None, f"Process Error Exception: {str(err)}"

        

# Run dynamic folder discovery checks
available_fonts, available_tracks = get_dropdown_options()

# --- GRAPHICAL INTERFACE BUILDING ---
with gr.Blocks(title="Shater Youtube downloader") as demo:
    gr.Markdown("# 🎛️ Shater Youtube downloader")
    with gr.Row():
        with gr.Column():
            video_mode = gr.Radio(["YouTube Link", "Local File Browse"], label="Source Input Selection", value="YouTube Link")
            
            with gr.Group() as yt_group:
                url_input = gr.Textbox(label="YouTube Link", placeholder="Paste video or playlist link here...")
                playlist_check = gr.Checkbox(label="Enable Entire Playlist Extraction Mode", value=False)
                quality_input = gr.Dropdown(choices=["1080p", "720p", "480p", "360p", "Video Only", "Audio Only"], value="1080p", label="Quality Stream Output Profile")
                
            with gr.Group(visible=False) as local_group:
                file_input = gr.File(label="Upload Local Video File", file_types=["video"])
                
            def update_visibility(mode):
                return gr.update(visible=(mode == "YouTube Link")), gr.update(visible=(mode == "Local File Browse"))
                
            video_mode.change(update_visibility, inputs=[video_mode], outputs=[yt_group, local_group])
            
            font_picker = gr.Dropdown(choices=available_fonts, value=available_fonts[0], label="Active Project Font Family")
            purge_check = gr.Checkbox(label="Delete Temp Files and Folders Automatically After Export", value=True)
            
            with gr.Tab("Captions Styling Engine"):
                sub_check = gr.Checkbox(label="Hardcode Subtitles Tracking Layer", value=False)
                sub_size = gr.Slider(minimum=10, maximum=60, step=1, value=20, label="Text Scale Size")
                sub_color = gr.ColorPicker(value="#FFFFFF", label="Text Fill Color")
                sub_bg_style = gr.Dropdown(choices=["Transparent", "Opaque Solid Box", "Semi-Transparent Box"], value="Semi-Transparent Box", label="Backdrop Layer Style Pattern")
                # ADD interactive=True to force Gradio to unlock the component
                sub_bg_color = gr.ColorPicker(value="#000000", label="Backdrop Box Color", interactive=True)




            with gr.Tab("Background Music Engine"):
                music_check = gr.Checkbox(label="Mix Background Music Overlay", value=False)
                music_dropdown = gr.Dropdown(choices=available_tracks, value=available_tracks[0], label="Select Target Backing Loop Track")
                music_vol_slider = gr.Slider(minimum=0.1, maximum=1.0, step=0.1, value=0.3, label="Backing Loop Output Attenuation / Volume Level")
                
            with gr.Tab("Watermark Text Stamp"):
                watermark_checkbox = gr.Checkbox(label="Burn Watermark Text", value=False)
                watermark_text = gr.Textbox(label="Watermark Text", value="My Studio Tag")
                watermark_position = gr.Dropdown(choices=["Top Left", "Top Right", "Bottom Left", "Bottom Right"], value="Bottom Right", label="Screen Corner Positioning")
                watermark_size = gr.Slider(minimum=12, maximum=100, step=2, value=32, label="Font Rendering Scale")
                watermark_color = gr.ColorPicker(value="#FFFFFF", label="Watermark Text Fill Color")
                
            submit_btn = gr.Button("Execute Automation Pipeline Sequences", variant="primary")
            
        with gr.Column():
            video_output = gr.Video(label="Render Engine Output Stream Preview")
            logs_output = gr.Textbox(label="System Tracer Output Pipeline Diagnostics Console")
            
    submit_btn.click(
        fn=orchestrate_pipeline,
        inputs=[
            video_mode, file_input, url_input, playlist_check, quality_input,
            watermark_checkbox, watermark_text, watermark_position, watermark_size, watermark_color, # <-- Watermark block comes first!
            sub_check, sub_size, sub_color, sub_bg_style, sub_bg_color, font_picker,
            music_check, music_dropdown, music_vol_slider, purge_check
        ],
        outputs=[video_output, logs_output]
    )

    gr.Markdown("---")
    gr.Markdown(
        "### Shater-Youtube-downloader -Customization & Processing Suite v:1.0\n"
        "Made by : Hesham Elshater \n"
        "Email: dr.elshater@gmail.com \n"
        "Subscribe to YouTube for more: [youtube.com/@elshater007](https://www.youtube.com/@elshater007)"
    )



if __name__ == "__main__":
    demo.launch(share=False)