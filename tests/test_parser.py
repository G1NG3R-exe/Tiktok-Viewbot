import pytest

from bot.parser import canonical_url, extract_video_id


@pytest.mark.parametrize(
    "url",
    [
        "https://www.tiktok.com/@user/video/1234567890",
        "https://www.tiktok.com/@user/video/1234567890?is_from_webapp=1",
        "https://m.tiktok.com/v/1234567890.html?lang=en",
    ],
)
def test_extract_video_id(url):
    assert extract_video_id(url) == "1234567890"


def test_extract_video_id_rejects_non_video_url():
    with pytest.raises(ValueError, match="Could not find a video ID"):
        extract_video_id("https://www.tiktok.com/@user")


def test_canonical_url():
    assert canonical_url("123") == "https://www.tiktok.com/tiktokstudio/video/123"
