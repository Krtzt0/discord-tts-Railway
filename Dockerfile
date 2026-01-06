FROM python:3.12-slim

# ติดตั้ง ffmpeg + libs ที่ discord voice ใช้
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
