FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
# 使用国内镜像加速并设置超时
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple --default-timeout=120 -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
