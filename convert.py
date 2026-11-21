"""Convert an MP3 file to HLS (.m3u8 + .ts segments) using FFmpeg."""

import subprocess
import sys
from pathlib import Path

SONGS_DIR = Path("songs")
HLS_DIR = Path("hls")


def convert(mp3_path: Path) -> Path:
    """Convert one MP3 to HLS and return the .m3u8 path."""
    HLS_DIR.mkdir(exist_ok=True)
    out_dir = HLS_DIR / mp3_path.stem
    out_dir.mkdir(exist_ok=True)
    playlist = out_dir / "playlist.m3u8"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp3_path),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-f",
        "hls",
        "-hls_time",
        "10",
        "-hls_list_size",
        "0",
        "-hls_playlist_type",
        "vod",
        "-hls_segment_filename",
        str(out_dir / "seg_%03d.ts"),
        str(playlist),
    ]
    print(f"Converting: {mp3_path.name} -> {playlist}")
    subprocess.run(cmd, check=True)
    return playlist


def main():
    if len(sys.argv) > 1:
        files = [Path(sys.argv[1])]
    else:
        files = sorted(SONGS_DIR.glob("*.mp3"))

    if not files:
        print("No MP3 files found. Put .mp3 files in ./songs/ or pass a path.")
        return

    for f in files:
        convert(f)
    print("\nDone. Now run: python serve.py")


if __name__ == "__main__":
    main()
