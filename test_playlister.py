from my_radio_station.downloader import SongDownload
from my_radio_station.playlister import PlayLister


def main():
    downloader = SongDownload()
    playlister = PlayLister(downloader=downloader)

    test_songs = [
        "nedirajte mi ravnicu",
        "should i stay or should i go",
        "nothing else matters",
        "stairway to heaven",
        "snuff acoustic",
        "road to nowhere",
        "london callin!",
        "jesi li sama veceras",
        "bili cvitak",
        "lupi petama",
        "cvit od kamena",
        "brainstorm",
        "wish you were here",
        "brother in arms",
        "money for nothing",
        "street spirit fade out",
        "fade into you",
        "sparks",
        "winner take it all",
        "chain fleetwood mac",
        "purple rain prince",
    ]

    test2 = [
        "Teenage Kicks - The Undertones",
        "Ever Fallen in Love - Buzzcocks",
        "Psycho Killer - Talking Heads",
        "Love Will Tear Us Apart - Joy Division",
        "Just Like Heaven - The Cure",
        "There Is a Light That Never Goes Out - The Smiths",
        "Common People - Pulp",
        "Wonderwall - Oasis",
        "Sunday Bloody Sunday - U2",
        "Heroes - David Bowie",
        "Sultans of Swing - Dire Straits",
        "Comfortably Numb - Pink Floyd",
        "Hotel California - Eagles",
        "The Boys Are Back in Town - Thin Lizzy",
        "Born to Run - Bruce Springsteen",
        "Into the Mystic - Van Morrison",
        "Fade Into You - Mazzy Star",
        "Teardrop - Massive Attack",
        "Moja Domovina - Hrvatski Band Aid",
        "Jesi li sama večeras - Azra",
        "Gde ćeš biti - Parni Valjak",
    ]

    for song_name in test_songs:
        playlister.add(song_name)


if __name__ == "__main__":
    main()
