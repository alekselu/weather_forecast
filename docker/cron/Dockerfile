FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends cron procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker/cron/weather-cron /etc/cron.d/weather-cron

RUN sed -i 's/\r$//' /etc/cron.d/weather-cron \
    && echo "" >> /etc/cron.d/weather-cron \
    && chmod 0644 /etc/cron.d/weather-cron

CMD ["cron", "-f"]