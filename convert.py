"""Convert an MP3 file to HLS (.m3u8 + .ts segments) using FFmpeg."""

import sys
from pathlib import Path

from my_radio_station.converter import Converter

SONGS_DIR = Path("songs")


def main():
    if len(sys.argv) > 1:
        files = [Path(sys.argv[1])]
    else:
        files = sorted(SONGS_DIR.glob("*.mp3"))

    converter = Converter()

    if not files:
        print("No MP3 files found. Put .mp3 files in ./songs/ or pass a path.")
        return

    for f in files:
        converter.convert(f)
    print("\nDone. Now run: python serve.py")


if __name__ == "__main__":
    main()
