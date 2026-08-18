FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        fonts-dejavu-core \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --gid 10001 word2jats \
    && useradd --uid 10001 --gid word2jats --home-dir /app --shell /usr/sbin/nologin word2jats \
    && mkdir -p /app/temp \
    && chown -R word2jats:word2jats /app
COPY --chown=word2jats:word2jats backend/ .
COPY --chown=word2jats:word2jats sample_documents/ /sample_documents/
COPY --chown=word2jats:word2jats 样例-最新版/ /样例-最新版/

EXPOSE 8000
USER word2jats
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
