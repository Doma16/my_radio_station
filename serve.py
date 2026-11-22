import socketserver

from my_radio_station.server import HLSHandler, ROOT, PORT


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
