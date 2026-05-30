# PageMonitor

Fetch a web page, compare the **`<body>`** inner HTML to a local snapshot, and update the snapshot when the body changes. Head, scripts, and other markup outside `<body>` are ignored. Volatile bits (hidden config blocks, large `data-*` blobs, session hashes, timestamps) are stripped before compare so routine session noise does not trigger updates.

## Usage

### Python API

```python
from pagemonitor import check_for_changes

if check_for_changes("https://example.com", "snapshots/example.html"):
    print("Page changed!")
```

Behavior:

- **No snapshot yet** — saves the body inner HTML and returns `False`.
- **Snapshot matches** — returns `False` (snapshot is left as-is).
- **Snapshot differs** — prints only the changed fragments to stdout, overwrites the snapshot, and returns `True`.

### Discord notifications

After each check, PageMonitor posts the result to a Discord channel using the [bot API](https://discord.com/developers/docs/resources/channel#create-message)—changed, unchanged, or first-time baseline. The outgoing request is printed to the console (token redacted).

For [Steam Frame](https://store.steampowered.com/hardware/steamframe), any detected **change** pings `@everyone` (Discord requires `allowed_mentions` in the API payload for the ping to fire). The bot needs **Mention @everyone** permission in that channel.

Test the ping:

```bash
python3 scripts/ping_everyone.py
```

Simulate a Steam Frame change (reserve/buy detected, `@everyone`, no fetch):

```bash
python3 scripts/simulate_change.py
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

```bash
python3 scripts/check_page.py https://example.com snapshots/example.html
```

Values in `.env` are loaded automatically. Variables already set in your shell take precedence. If Discord variables are missing, monitoring still works; notifications are skipped. Pass `notify=False` to `check_for_changes()` to disable Discord posts.

### CLI

```bash
python scripts/check_page.py https://example.com snapshots/example.html
```

Or after install:

```bash
pip install -e .
check-page https://example.com snapshots/example.html
```

### Tests

```bash
python3 -m unittest discover -s tests -v
```

The suite mocks page fetches and injects HTML changes between runs to verify detection works and session noise is ignored.

Note: This is slopcoded so I cannot guarantee performance.