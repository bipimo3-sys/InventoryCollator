import logging
from mutagen import File as MutagenFile


def extract_audio_metadata(file_path: str) -> dict | None:
    """
    Extracts audio metadata using mutagen.

    Returns dictionary:
    {
        duration,
        bitrate,
        sample_rate,
        channels,
        artist,
        album,
        title,
        year
    }
    """

    try:
        audio = MutagenFile(file_path, easy=True)

        if audio is None:
            return None

        metadata = {
            "duration": None,
            "bitrate": None,
            "sample_rate": None,
            "channels": None,
            "artist": None,
            "album": None,
            "title": None,
            "year": None
        }

        # Technical info
        if hasattr(audio, "info") and audio.info:
            metadata["duration"] = getattr(audio.info, "length", None)
            metadata["bitrate"] = getattr(audio.info, "bitrate", None)
            metadata["sample_rate"] = getattr(audio.info, "sample_rate", None)
            metadata["channels"] = getattr(audio.info, "channels", None)

        # Tags
        if audio.tags:
            metadata["artist"] = _safe_get(audio.tags, "artist")
            metadata["album"] = _safe_get(audio.tags, "album")
            metadata["title"] = _safe_get(audio.tags, "title")
            metadata["year"] = _safe_get(audio.tags, "date") or _safe_get(audio.tags, "year")

        return metadata

    except Exception as e:
        logging.error(f"Metadata extraction failed for {file_path}: {e}")
        return None


def _safe_get(tags, key):
    try:
        value = tags.get(key)
        if isinstance(value, list):
            return value[0]
        return value
    except Exception:
        return None
