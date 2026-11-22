from my_radio_station.downloader import SongDownload


def main():
    sd = SongDownload()
    fetched = sd.fetch("London calling!")
    print(fetched)


if __name__ == "__main__":
    main()
