import subprocess
import shutil
from pathlib import Path

HLS_DIR = "hls"


class Converter:
    def __init__(self) -> None:
        self.hls_dir = Path(HLS_DIR)
        self.hls_dir.mkdir(exist_ok=True)

    def convert(self, filepath: Path):
        out_dir = self.hls_dir / filepath.stem
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(exist_ok=True)
        playlist = out_dir / "playlist.m3u8"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(filepath),
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
        print(f"Converting: {filepath.name} -> {playlist}")
        subprocess.run(cmd, check=True)
        return playlist
