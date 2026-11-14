# TikTok Viewbot

A simple bot where you input a video URL and how many views you want — and that video gets a boost.

**Status:** early scaffold — the CLI and project layout exist, but no views are delivered yet. See the [roadmap](#roadmap).

## What it will do

1. Paste a public TikTok video URL.
2. Enter the number of views you want.
3. The bot runs and boosts the video, showing progress along the way.

Planned UX:

```console
$ python main.py
Enter video URL: https://www.tiktok.com/@user/video/1234567890
Enter view count: 10000
Boosting video... done
```

Scripted form:

```console
$ python main.py https://www.tiktok.com/@user/video/1234567890 --views 1000
```

## Requirements

- Python 3.10+
- pip

## Install (development)

```console
git clone https://github.com/G1NG3R-exe/Tiktok-Viewbot.git
cd Tiktok-Viewbot
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux
pip install -e ".[dev]"
```

## Usage

Nothing is delivered to TikTok yet. The CLI only parses arguments and echoes the request:

```console
$ python main.py https://www.tiktok.com/@user/video/1234567890 --views 1000
TikTok Viewbot v0.1.0
  url:   https://www.tiktok.com/@user/video/1234567890
  views: 1000
Not implemented yet.
```

## Project layout

```text
Tiktok-Viewbot/
├── main.py              # entry point
├── src/tiktok_viewbot/
│   ├── __init__.py      # package metadata
│   ├── __main__.py      # `python -m tiktok_viewbot`
│   ├── cli.py           # argument parsing
│   └── bot.py           # ViewBot skeleton (the actual worker)
├── tests/
│   └── test_cli.py      # smoke tests
├── .github/workflows/ci.yml
├── pyproject.toml
└── requirements.txt
```

## Roadmap

- [ ] Validate and normalize TikTok URLs (including short `vm.tiktok.com` links)
- [ ] Resolve video metadata (ID, author, current view count)
- [ ] View boosting engine
- [ ] Interactive prompts for URL and view count
- [ ] Progress display while the bot runs
- [ ] Concurrency controls (workers, rate limiting)
- [ ] Retries with backoff for failed requests
- [ ] Config file for speed / delay settings
- [ ] `--dry-run` mode
- [ ] Optional proxy support
- [ ] Support for likes and shares

## Development

```console
pip install -e ".[dev]"
pytest
ruff check .
```

CI runs lint + tests on every push and pull request.

## Contributing

Issues and PRs are welcome. Keep changes focused, add a test where it makes sense, and run `ruff` + `pytest` before opening a PR.

## Disclaimer

This project is unofficial and not affiliated with TikTok. Artificially inflating views may violate TikTok's Terms of Service, and automated views may not count toward monetization or analytics the same way organic views do. Use at your own risk.

## License

[MIT](LICENSE)
