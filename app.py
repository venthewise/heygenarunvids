from flask import Flask, request, send_file, jsonify
import subprocess
import os
import shutil
import uuid
import tempfile

app = Flask(__name__)

@app.route("/add_bgm", methods=["POST"])
def add_bgm():
    data = request.json
    video_url = data.get("video")
    bgm_url = data.get("bgm")

    if not video_url or not bgm_url:
        return jsonify({"error": "Missing 'video' or 'bgm' URL"}), 400

    workdir = f"/app/work_{uuid.uuid4().hex}"
    os.makedirs(workdir, exist_ok=True)

    video_path = os.path.join(workdir, "input.mp4")
    bgm_path = os.path.join(workdir, "bgm.mp3")
    output_path = os.path.join(workdir, "output.mp4")

    try:
        # Download input files
        subprocess.run(["wget", "-q", "-O", video_path, video_url], check=True)
        subprocess.run(["wget", "-q", "-O", bgm_path, bgm_url], check=True)

        # Mix video audio with background music (bgm volume lowered)
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-filter_complex", "[1:a]volume=0.10[a1];[0:a][a1]amix=inputs=2:duration=shortest",
            "-c:v", "copy",
            "-shortest",
            output_path
        ], check=True)

        response = send_file(output_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Ensure total cleanup — all files and temp data removed
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
