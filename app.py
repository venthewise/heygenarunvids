from flask import Flask, request, send_file, jsonify
import subprocess
import os
import shutil
import uuid
import tempfile

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
        # Download input files
        subprocess.run(["wget", "-q", "-O", video_path, video_url], check=True)
        subprocess.run(["wget", "-q", "-O", caption_path, caption_url], check=True)

        # Override caption style (small, centered, no shadow)
        style_override = """
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,10,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,5,20,20,40,1
"""

        # Inject or replace style section
        with open(caption_path, "r+", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if "[V4+ Styles]" in content:
                before, after = content.split("[V4+ Styles]", 1)
                after = after.split("[Events]", 1)[-1]
                f.seek(0)
                f.write(before + style_override + "\n[Events]\n" + after)
                f.truncate()
            else:
                f.seek(0)
                f.write("[Script Info]\nTitle: AutoStyled\nScriptType: v4.00+\n\n" + style_override + "\n[Events]\n" + content)

        # Apply captions with ffmpeg
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

        response = send_file(output_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Ensure total cleanup — no cached, temp, or intermediate files left behind
        shutil.rmtree(workdir, ignore_errors=True)
        tempdir = tempfile.gettempdir()
        for name in os.listdir(tempdir):
            path = os.path.join(tempdir, name)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
            except Exception:
                pass

    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
