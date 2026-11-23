import json
import datetime as dt
from pathlib import Path
from enum import StrEnum
from pydantic import BaseModel

from .downloader import SongDownload


ROOT = "playlists"


class PlayListSong(BaseModel):
    song_name: str
    yt_name: str | None
    date: dt.date


class PlayLister:
    current_json = "current.json"
    last_json = "last.json"
    all_time_json = "all_time.json"

    def __init__(self, downloader=None, limit=20) -> None:
        self.root = Path(ROOT)
        self.root.mkdir(exist_ok=True)
        self.downloader: SongDownload | None = downloader
        self.limit = limit

        self.current: list[PlayListSong] = []
        current_json_file = self.root / self.current_json
        if current_json_file.exists():
            self.current = self._load_list(self.root / self.current_json)

    def _load_list(self, filename):
        with open(filename, "r") as f:
            obj = json.load(f)
            breakpoint()
            return obj

    def _write_list(self, filename, playlist: list[PlayListSong]):
        with open(filename, "w") as f:
            dump_list = [obj.model_dump(mode="json") for obj in playlist]
            json.dump(dump_list, f, indent=4)

    def add(self, song_name):
        today = dt.date.today()

        yt_name = None
        if self.downloader:
            yt_name = self.downloader.fetch(song_name).name

        addition = PlayListSong(
            song_name=song_name,
            yt_name=yt_name,
            date=today,
        )

        self.current.append(addition)
        if len(self.current) > self.limit:
            self.current.pop(0)

        self._write_list(self.root / self.current_json, self.current)

    def remove(self, song_name): ...
