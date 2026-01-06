FROM python:3.12-slim

# ติดตั้ง ffmpeg (จำเป็น)
RUN apt-get update \
    && apt-get install -y ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# คัดลอก requirements
COPY requirements.txt .

# อัปเดต pip + ติดตั้ง deps
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ด
COPY . .

# รันบอท
CMD ["python", "main.py"]
