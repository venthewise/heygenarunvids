FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg wget python3 python3-pip && \
    apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

EXPOSE 8080
CMD ["python3", "app.py"]
