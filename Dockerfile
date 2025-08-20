# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PORT=8000 \
	WEB_CONCURRENCY=2 \
	GUNICORN_TIMEOUT=120

RUN apt-get update \
	&& apt-get install -y --no-install-recommends exiftool ffmpeg libx265-dev x264 \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

# Verificar se o ffmpeg foi instalado corretamente
RUN ffmpeg -version && exiftool -ver

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt gunicorn

COPY . /app

# Ensure folders exist for runtime writes
RUN mkdir -p /app/uploads /app/processed

EXPOSE 8000

CMD ["sh", "-c", "gunicorn -w ${WEB_CONCURRENCY} -k sync --timeout ${GUNICORN_TIMEOUT} -b 0.0.0.0:${PORT} app:app"]
