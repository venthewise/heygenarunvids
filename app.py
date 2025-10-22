from flask import Flask, request, send_file, jsonify
import subprocess
import os
import shutil
import uuid

app = Flask(__name__)

@app.route("/add_captions", methods=["POST"])
def add_captions():
    data = request.json
    video_url = data.get("video")
    caption_url = data.get("caption")

    if not video_url or not caption_url:
        return jsonify({"error": "Missing 'video' or 'caption' URL"}), 400

    workdir = f"/app/work_{uuid.uuid4().hex}"
    os.makedirs(workdir, exist_ok=True)

    video_path = os.path.join(workdir, "input.mp4")
    caption_path = os.path.join(workdir, "caption.ass")
    output_path = os.path.join(workdir, "output.mp4")

    try:
        # Download input video and caption
        subprocess.run(["wget", "-O", video_path, video_url], check=True)
        subprocess.run(["wget", "-O", caption_path, caption_url], check=True)

        # Inject global style override to make text centered, bold, and large
        style_override = """
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, 
ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,64,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,2,5,20,20,20,1
"""
        # Prepend or override in caption.ass file
        with open(caption_path, "r+", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if "[V4+ Styles]" not in content:
                f.seek(0)
                f.write("[Script Info]\nTitle: AutoStyled\nScriptType: v4.00+\n\n" + style_override + "\n[Events]\n")
                f.write(content)
            else:
                f.seek(0)
                f.write(style_override + "\n" + content)

        # Apply captions
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vf", f"ass={caption_path}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            output_path
        ], check=True)

        return send_file(output_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Cleanup
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
