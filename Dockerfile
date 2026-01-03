FROM python:3.12-slim

# ติดตั้ง ffmpeg
RUN apt-get update \
    && apt-get install -y ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ตั้ง working directory
WORKDIR /app

# คัดลอกไฟล์
COPY requirements.txt .

# ติดตั้ง Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดทั้งหมด
COPY . .

# รันบอท
CMD ["python", "main.py"]
