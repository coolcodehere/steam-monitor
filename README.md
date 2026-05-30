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

Note: This is slopcoded so I cannot guarantee performance