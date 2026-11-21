"""Serve HLS files, auto-list songs, and expose a .m3u playlist."""

import http.server
import socketserver
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

PORT = 8000
ROOT = Path("hls")


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

        # Root: HTML index
        if path == "/":
            self.send_index()
            return

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

    def send_index(self):
        songs = self.list_songs()
        host = self.headers.get("Host", f"localhost:{PORT}")
        base = f"http://{host}"

        rows = []
        for name, rel in songs:
            url = f"{base}/{quote(rel)}"
            rows.append(
                f"<tr><td>{escape(name)}</td>"
                f'<td><a href="{url}">{escape(url)}</a></td></tr>'
            )

        html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>HLS songs</title>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
code {{ background: #eee; padding: 2px 4px; }}
</style></head>
<body>
<h1>HLS songs</h1>
<p>Open any URL below in VLC (Media → Open Network Stream),
or open the whole list at <a href="/all.m3u">{base}/all.m3u</a>.</p>
<table>
<tr><th>Song</th><th>Stream URL</th></tr>
{"".join(rows) if rows else "<tr><td colspan=2>No songs yet. Run convert.py first.</td></tr>"}
</table>
</body></html>"""
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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


def main():
    if not ROOT.exists():
        print(f"Directory '{ROOT}' not found. Run convert.py first.")
        return
    with socketserver.TCPServer(("0.0.0.0", PORT), HLSHandler) as httpd:
        print(f"Serving {ROOT.resolve()} at http://0.0.0.0:{PORT}/")
        print(f"  Song list:        http://<server-ip>:{PORT}/")
        print(f"  VLC playlist:     http://<server-ip>:{PORT}/all.m3u")
        print(f"  JSON list:        http://<server-ip>:{PORT}/songs.json")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
