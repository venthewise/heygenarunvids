FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y ffmpeg wget python3 python3-pip && \
    apt-get clean

WORKDIR /app
RUN pip install flask

COPY app.py .

EXPOSE 8080
CMD ["python3", "app.py"]
