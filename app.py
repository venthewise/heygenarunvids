from flask import Flask, request, send_file
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
        return {"error": "No video URLs provided"}, 400

    # Unique working directory for this request
    workdir = f"/app/videos_{uuid.uuid4().hex}"
    os.makedirs(workdir, exist_ok=True)

    # Download videos sequentially
    concat_file = os.path.join(workdir, "files.txt")
    with open(concat_file, "w") as f:
        for i, url in enumerate(urls):
            video_path = os.path.join(workdir, f"clip{i+1:03}.mp4")
            subprocess.run(["wget", "-O", video_path, url], check=True)
            f.write(f"file '{video_path}'\n")

    # Output path
    output_path = f"/app/output_{uuid.uuid4().hex}.mp4"

    # Concatenate videos (re-encode to normalize)
    subprocess.run([
        "ffmpeg",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-r", "30", "-pix_fmt", "yuv420p",
        output_path
    ], check=True)

    # Cleanup temporary files
    shutil.rmtree(workdir)

    return send_file(output_path, as_attachment=True)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
