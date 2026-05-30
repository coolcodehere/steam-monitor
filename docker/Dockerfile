FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY pagemonitor ./pagemonitor
COPY scripts ./scripts

RUN pip install --no-cache-dir .

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PAGEMONITOR_URL=https://store.steampowered.com/hardware/steamframe \
    PAGEMONITOR_SNAPSHOT=/app/snapshots/steamframe.html \
    PAGEMONITOR_INTERVAL=30

ENTRYPOINT ["/entrypoint.sh"]
