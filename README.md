# PageMonitor

Monitors the [Steam Frame](https://store.steampowered.com/hardware/steamframe) store page for **waitlist** and **reserve** signals. Discord is notified only when a new signal appears compared to the saved snapshot — routine page churn does not trigger alerts.

## Usage

### Python API

```python
from pagemonitor import check_for_changes

if check_for_changes(
    "https://store.steampowered.com/hardware/steamframe",
    "snapshots/steamframe.html",
):
    print("New waitlist/reserve signal!")
```

Behavior:

- **No snapshot yet** — saves the body inner HTML and returns `False`.
- **No new signals** — updates the snapshot and returns `False`.
- **New waitlist/reserve signal** — notifies Discord and returns `True`.

### Discord notifications

PageMonitor posts to a Discord channel when new waitlist or reserve UI appears on the Steam Frame page. The outgoing request is printed to the console (token redacted).

New signals ping the **@Steam Frame Interest** role (Discord requires `allowed_mentions` in the API payload for the ping to fire). Set `DISCORD_NOTIFY_ROLE_ID` to that role's ID; the bot needs permission to mention the role in that channel. Heartbeat messages are sent **four times per day** (every 6 hours) with no role ping.

Test the ping:

```bash
python3 scripts/ping_role.py
```

Simulate a waitlist/reserve alert (role ping, no fetch):

```bash
python3 scripts/simulate_change.py
```

Send a heartbeat manually (no role ping):

```bash
python3 scripts/heartbeat.py
```

Copy `.env.example` to `.env` in the project root (or run from a directory that has its own `.env`):

```bash
cp .env.example .env
# edit .env with your bot token and channel id
```

| Variable | Description |
|----------|-------------|
| `DISCORD_BOT_TOKEN` | Bot token from the [Discord Developer Portal](https://discord.com/developers/applications) |
| `DISCORD_CHANNEL_ID` | Channel ID to post in (bot needs **Send Messages** in that channel) |
| `DISCORD_NOTIFY_USER_ID` | Your Discord **user** ID — @mentioned when a new signal is detected |
| `DISCORD_NOTIFY_ROLE_ID` | **@Steam Frame Interest** role ID — @mentioned on new signals |

```bash
python3 scripts/check_page.py https://store.steampowered.com/hardware/steamframe snapshots/steamframe.html
```

Values in `.env` are loaded automatically. Variables already set in your shell take precedence. If Discord variables are missing, monitoring still works; notifications are skipped. Pass `notify=False` to `check_for_changes()` to disable Discord posts.

### CLI

```bash
python scripts/check_page.py https://store.steampowered.com/hardware/steamframe snapshots/steamframe.html
```

Or after install:

```bash
pip install -e .
check-page https://store.steampowered.com/hardware/steamframe snapshots/steamframe.html
```

### Docker (Steam Frame every 60 seconds)

All Docker files live in [`docker/`](docker/). See [`docker/README.md`](docker/README.md).

```bash
cp .env.example .env   # Discord token + channel id
docker compose -f docker/docker-compose.yml up -d
```

- Loads secrets from `.env` in the project root
- Persists `snapshots/steamframe.html` on the host
- Checks every **60 seconds** (`PAGEMONITOR_INTERVAL` to override)
- Heartbeat every **6 hours** (`PAGEMONITOR_HEARTBEAT_INTERVAL` to override)

Stop: `docker compose -f docker/docker-compose.yml down`

### Tests

```bash
python3 -m unittest discover -s tests -v
```

The suite mocks page fetches and verifies waitlist/reserve signal detection and Discord notification behavior.

Note: This is slopcoded so I cannot guarantee performance.
