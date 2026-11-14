# TikTok Viewbot

A simple bot where you input a video URL and how many views you want — and that video gets a boost.

## How it works

1. Paste a TikTok video URL
2. Enter the number of views you want
3. The bot runs and boosts the video

## Usage

```bash
python main.py
```

```
Enter video URL: https://www.tiktok.com/@user/video/1234567890
Enter view count: 10000
Boosting video... done ✔
```

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## Project structure

```
├── main.py            # Entry point — CLI for URL + view count
├── bot/               # View boosting logic
└── requirements.txt   # Python dependencies
```

## Roadmap

- [ ] CLI input for video URL and view count
- [ ] View boosting engine
- [ ] Progress display while the bot runs
- [ ] Config file for speed / delay settings
- [ ] Support for likes and shares

## Disclaimer

This tool is for educational purposes only. Artificially inflating views may violate TikTok's Terms of Service — use at your own risk.

## License

MIT
