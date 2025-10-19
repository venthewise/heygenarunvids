from flask import Flask, request, jsonify
import subprocess
import os
import requests
import time

app = Flask(__name__)
TMP_DIR = "tmp"
os.makedirs(TMP_DIR, exist_ok=True)

def run_ffmpeg(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise Exception(stderr.decode("utf-8"))
    return stdout.decode("utf-8")

@app.route("/stitch", methods=["POST"])
def stitch_videos():
    try:
        data = request.get_json()
        videos = data.get("videos", [])
        if not videos:
            return jsonify({"error": "No videos provided"}), 400

        normalized_files = []

        # Step 1: Download + Normalize
        for i, vid in enumerate(videos):
            url = vid["video"] if isinstance(vid, dict) else vid
            raw_path = os.path.join(TMP_DIR, f"clip_{i}.mp4")
            norm_path = os.path.join(TMP_DIR, f"norm_{i}.mp4")

            # Download
            r = requests.get(url)
            with open(raw_path, "wb") as f:
                f.write(r.content)

            # Normalize (FPS, audio rate, codec)
            run_ffmpeg([
                "ffmpeg", "-y",
                "-i", raw_path,
                "-r", "30",
                "-ar", "44100",
                "-ac", "2",
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "aac",
                "-movflags", "+faststart",
                norm_path
            ])
            normalized_files.append(norm_path)

        # Step 2: Write concat list
        list_file = os.path.join(TMP_DIR, "list.txt")
        with open(list_file, "w") as f:
            for file in normalized_files:
                f.write(f"file '{os.path.abspath(file)}'\n")

        # Step 3: Stitch videos together
        output_path = os.path.join(TMP_DIR, f"stitched_{int(time.time())}.mp4")
        run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-r", "30",
            "-ar", "44100",
            "-af", "aresample=async=1",
            output_path
        ])

        # Step 4: Return result path (or upload to storage)
        return jsonify({
            "success": True,
            "output": f"/{output_path}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
