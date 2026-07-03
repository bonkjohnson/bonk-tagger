from dotenv import load_dotenv
from hashlib import md5
from os import getenv, path, scandir
import requests
from rich.console import Console
from sys import argv, exit

console = Console()
load_dotenv()

AUDIO_FILE_EXTENSIONS = [
    ".flac",
    ".mp3",
    ".wav",
    ".alac"
]

LAST_FM_BASE_URL = "http://ws.audioscrobbler.com/2.0"

if len(argv) < 2:
    console.print("A target directory must be provided")
    exit(1)

directory_path = argv[1]

if not path.isdir(directory_path):
    console.print("Provided path must be a directory")
    exit(1)

audio_files = []
for entry in scandir(directory_path):
    if (entry.is_file() and
            path.splitext(entry.path)[1] in AUDIO_FILE_EXTENSIONS):
        audio_files.append(entry.name)

console.print(f"Loaded directory with {len(audio_files)} audio files")

if not getenv("API_KEY"):
    console.print("LastFM API key must be provided in .env")
    exit(1)
API_KEY = str(getenv("API_KEY"))

search_query = path.split(directory_path)[1]

search_response = requests.get(
    LAST_FM_BASE_URL + "?method=album.search" +
    f"&album={search_query}" + "&format=json" + f"&api_key={API_KEY}")
search_response.raise_for_status()
album_matches = search_response.json()["results"]["albummatches"]["album"]

console.print(f"Found {len(album_matches)} total albums")

result_count = 5 if len(album_matches) > 5 else len(album_matches)
console.print(f"Top {result_count} LastFM album search results")
for i in range(result_count):
    album = album_matches[i]
    console.print(f"({i + 1}) {album["name"]} - {album["artist"]}")

select_index = int(console.input("Enter your selection: ")) - 1

album_response = requests.get(
    LAST_FM_BASE_URL + "?method=album.getInfo" +
    f"&mbid={album_matches[select_index]["mbid"]}" + "&format=json" +
    f"&api_key={API_KEY}")
album_response.raise_for_status()
album = album_response.json()["album"]

console.print(
    "Track count - " + f"({len(album["tracks"]["track"])}) LastFM" +
    f", ({len(audio_files)}) Local Directory")

