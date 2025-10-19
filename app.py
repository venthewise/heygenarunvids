from flask import Flask, request, send_file, jsonify
import subprocess
import os
import shutil
import uuid

app = Flask(__name__)

@app.route("/stitch_videos", methods=["POST"])
def stitch_videos():
    data = request.json
    urls = data.get("videos", [])

    if not urls:
        return jsonify({"error": "No video URLs provided"}), 400

    # Unique working directory per request
    workdir = f"/app/videos_{uuid.uuid4().hex}"
    os.makedirs(workdir, exist_ok=True)

    concat_file = os.path.join(workdir, "files.txt")

    try:
        # Download + Normalize each video
        with open(concat_file, "w") as f:
            for i, url in enumerate(urls):
                raw_path = os.path.join(workdir, f"raw_{i+1:03}.mp4")
                norm_path = os.path.join(workdir, f"norm_{i+1:03}.mp4")

                # Download
                subprocess.run(["wget", "-O", raw_path, url], check=True)

                # Normalize to prevent audio desync
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", raw_path,
                    "-r", "30",           # normalize FPS
                    "-ar", "44100",       # normalize audio rate
                    "-ac", "2",           # stereo
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    norm_path
                ], check=True)

                f.write(f"file '{norm_path}'\n")

        # Output stitched file
        output_path = f"/app/output_{uuid.uuid4().hex}.mp4"

        # Stitch normalized clips
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-r", "30",
            "-ar", "44100",
            "-af", "aresample=async=1",
            output_path
        ], check=True)

        return send_file(output_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up temporary working directory
        shutil.rmtree(workdir, ignore_errors=True)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))  # Render expects 8080
    app.run(host="0.0.0.0", port=port)
