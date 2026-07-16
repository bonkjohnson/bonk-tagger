from difflib import SequenceMatcher
from dotenv import load_dotenv
import json
from mutagen.flac import FLAC, VCFLACDict
from os import getenv, path, scandir
import requests
from rich.console import Console
from rich.json import JSON
from rich.table import Table
from sys import argv, exit

console = Console()
load_dotenv()

# Only supporting FLAC for the time being due to our mutagen setup
AUDIO_FILE_EXTENSIONS = [
    ".flac",
]

LAST_FM_BASE_URL = "http://ws.audioscrobbler.com/2.0"

def get_directory_from_argv():
    if len(argv) < 2:
        console.print("A target directory must be provided")
        exit(1)
    directory_path = argv[1]
    if not path.isdir(directory_path):
        console.print("Provided path must be a directory")
        exit(1)
    return directory_path

def get_track_paths(directory_path):
    track_paths = []
    for entry in scandir(directory_path):
        if (entry.is_file() and
                path.splitext(entry.path)[1] in AUDIO_FILE_EXTENSIONS):
            track_paths.append(entry.name)
    console.print(f"Loaded directory with {len(track_paths)} audio files")
    return track_paths

def load_api_key():
    if not getenv("API_KEY"):
        console.print("LastFM API key must be provided in .env")
        exit(1)
    return str(getenv("API_KEY"))

def get_album_info(directory_path, track_paths):
    search_query = path.split(directory_path)[1]
    api_key = load_api_key()

    search_response = requests.get(
        LAST_FM_BASE_URL + "?method=album.search" +
        f"&album={search_query}" + "&format=json" + f"&api_key={api_key}")
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
        f"&api_key={api_key}")
    album_response.raise_for_status()
    album = album_response.json()["album"]

    local_track_count = len(track_paths)
    lastfm_track_count = len(album["tracks"]["track"])
    if not local_track_count == lastfm_track_count:
        console.print(
            f"Local track count ({local_track_count}) does not match " +
            f"LastFM track count ({lastfm_track_count})")
        exit(1)

    return album

def get_updated_track_tags(directory_path, track_paths, album):
    tracks = album["tracks"]["track"]

    for index, track_path in enumerate(track_paths):
        full_track_path = path.join(directory_path, track_path)
        track_file = FLAC(full_track_path)
        tags = track_file.tags

        existing_track_title = tags["title"][0] if len(tags["title"]) > 0 else ""

        matching_track = get_matching_track_by_title(
            existing_track_title, tracks)

        expected_file_name = f"{matching_track["@attr"]["rank"]:02}. {matching_track["name"]}"

        if not path.splitext(track_path)[0] == expected_file_name:
            console.print(f"{track_path} does not match {expected_file_name}")

def get_matching_track_by_title(existing_track_title, album_tracks):
    match_scores = {}
    for index, track in enumerate(album_tracks):
        score = SequenceMatcher(
            None, existing_track_title, track["name"]).ratio()
        match_scores[index] = score

    max_score = -1
    max_score_index = -1
    for index in match_scores:
        current_score = match_scores[index]
        if current_score > max_score:
            max_score = current_score
            max_score_index = index

    return album_tracks[max_score_index]

def main():
    directory_path = get_directory_from_argv()
    track_paths = get_track_paths(directory_path)
    album = get_album_info(directory_path, track_paths)

    get_updated_track_tags(directory_path, track_paths, album)

if __name__ == "__main__":
    main()

