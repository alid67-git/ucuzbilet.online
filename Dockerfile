FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt

COPY app ./app
COPY scraper ./scraper
COPY web ./web
COPY data/places.json data/regions.json data/explore_destinations.json ./data/
RUN mkdir -p data/searches data/results

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
