import yt_dlp
from pathlib import Path

SONGS_DIR = "songs"


class SongDownload:
    def __init__(self):

        out_dir = Path(SONGS_DIR)

        self.outtmpl = str(out_dir / "%(title)s.%(ext)s")
        self.ydl_opts = {
            "default_search": "ytsearch1",
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": self.outtmpl,
            "quiet": True,
            "noplaylist": True,
        }

    def fetch(self, song_name):

        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(song_name, download=True)
            path = Path(info["entries"][0]["requested_downloads"][0]["filename"])
            return str(path.with_suffix(".mp3"))
