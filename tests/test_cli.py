from tiktok_viewbot.cli import main


def test_version_flag(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "viewbot" in capsys.readouterr().out


def test_echoes_request(capsys):
    assert main(["https://www.tiktok.com/@user/video/123", "--views", "1000"]) == 0

    out = capsys.readouterr().out
    assert "https://www.tiktok.com/@user/video/123" in out
    assert "1000" in out
