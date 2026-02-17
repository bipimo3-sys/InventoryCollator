import os

try:
    from mutagen import File as MutagenFile
except:
    MutagenFile = None


def extract_metadata(filepath):
    metadata = {
        "title": None,
        "artist": None,
        "album": None,
        "duration": None,
        "bitrate": None,
    }

    if MutagenFile:
        try:
            audio = MutagenFile(filepath)
            if audio:
                metadata["duration"] = getattr(audio.info, "length", None)
                metadata["bitrate"] = getattr(audio.info, "bitrate", None)

                if audio.tags:
                    metadata["title"] = str(audio.tags.get("TIT2", [None])[0])
                    metadata["artist"] = str(audio.tags.get("TPE1", [None])[0])
                    metadata["album"] = str(audio.tags.get("TALB", [None])[0])
        except:
            pass

    # Fallback: derive from filename
    if not metadata["title"]:
        metadata["title"] = os.path.splitext(os.path.basename(filepath))[0]

    return metadata
