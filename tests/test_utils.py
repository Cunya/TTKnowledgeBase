from processors.utils import normalize_text, slugify, youtube_url


def test_normalize_text() -> None:
    assert normalize_text("  forehand\n\tloop  ") == "forehand loop"


def test_slugify() -> None:
    assert slugify("Forehand Loop / Topspin") == "forehand-loop-topspin"


def test_youtube_url_uses_whole_seconds() -> None:
    assert youtube_url("abc123xyz00", 83_999).endswith("&t=83s")
