FROM python:3.12-slim
WORKDIR /app

# WeasyPrint/Cairo + Chromium/Node for Mermaid→SVG in proposal exports
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    fonts-noto-cjk \
    nodejs npm \
    chromium \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tools/mermaid/package.json /app/tools/mermaid/package.json
RUN cd /app/tools/mermaid && npm install --omit=dev

COPY . .
RUN chmod +x docker-entrypoint.sh

CMD ["./docker-entrypoint.sh"]
