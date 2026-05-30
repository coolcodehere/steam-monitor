# Docker

Runs the Steam Frame checker every N seconds.

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```

Requires `.env` in the project root (see `../.env.example`). Snapshots are stored in `../snapshots/`.

Discord posts only when the **page content changes**, not on every check. After editing `.env`, recreate the container:

```bash
docker compose -f docker/docker-compose.yml up -d --build --force-recreate
```

Test Discord from the running stack:

```bash
docker compose -f docker/docker-compose.yml run --rm pagemonitor \
  python3 /app/scripts/simulate_change.py
```
