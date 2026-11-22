import http.server
from pathlib import Path
from urllib.parse import quote
from .converter import HLS_DIR

ROOT = Path(HLS_DIR)
PORT = 8000


class HLSHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".m3u8": "application/vnd.apple.mpegurl",
        ".m3u": "audio/x-mpegurl",
        ".ts": "video/mp2t",
        ".mp3": "audio/mpeg",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def list_songs(self):
        """Return list of (song_name, m3u8_relpath) for every playlist found."""
        songs = []
        for playlist in sorted(ROOT.glob("*/playlist.m3u8")):
            songs.append(
                (playlist.parent.name, f"{playlist.parent.name}/playlist.m3u8")
            )
        return songs

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        # /all.m3u : a real playlist VLC can open
        if path == "/all.m3u":
            self.send_all_m3u()
            return

        # /songs.json : machine-readable list
        if path == "/songs.json":
            self.send_songs_json()
            return

        # Everything else: normal file serving
        super().do_GET()

    def send_all_m3u(self):
        """An .m3u (not .m3u8) listing every song's .m3u8 — VLC-friendly."""
        host = self.headers.get("Host", f"localhost:{PORT}")
        lines = ["#EXTM3U"]
        for name, rel in self.list_songs():
            lines.append(f"#EXTINF:-1,{name}")
            lines.append(f"http://{host}/{quote(rel)}")
        data = ("\n".join(lines) + "\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "audio/x-mpegurl")
        self.send_header("Content-Disposition", 'inline; filename="all.m3u"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_songs_json(self):
        import json

        host = self.headers.get("Host", f"localhost:{PORT}")
        payload = {
            "songs": [
                {"name": n, "url": f"http://{host}/{quote(rel)}"}
                for n, rel in self.list_songs()
            ]
        }
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
