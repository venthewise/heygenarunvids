from flask import Flask, request, send_file, jsonify
import subprocess
import os
import requests
import uuid

app = Flask(__name__)
TMP_DIR = "/app/tmp"
os.makedirs(TMP_DIR, exist_ok=True)

@app.route("/add_captions", methods=["POST"])
def add_captions():
    try:
        data = request.get_json()
        video_url = data.get("video")
        caption_url = data.get("caption")

        if not video_url or not caption_url:
            return jsonify({"error": "Missing video or caption URL"}), 400

        job_id = uuid.uuid4().hex
        video_path = os.path.join(TMP_DIR, f"{job_id}_input.mp4")
        caption_path = os.path.join(TMP_DIR, f"{job_id}_caption.ass")
        output_path = os.path.join(TMP_DIR, f"{job_id}_output.mp4")

        # Download files
        for url, path in [(video_url, video_path), (caption_url, caption_path)]:
            r = requests.get(url)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)

        # Apply styled captions
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles={caption_path}:force_style='FontName=Arial,FontSize=48,PrimaryColour=&HFFFFFF&,Outline=0,Shadow=0,BorderStyle=1,Alignment=5'",
            "-c:a", "copy",
            output_path
        ]
        subprocess.run(cmd, check=True)

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
