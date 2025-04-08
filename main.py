import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
import re
import os
import sys
from datetime import datetime

# client id & client secret
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"

# functions

def get_spotify_client(client_id, client_secret):
    """auth & cli creating"""
    # fuck placeholders (like cmon r u dumb or wha)
    if not client_id or client_id == "YOUR_CLIENT_ID" or \
       not client_secret or client_secret == "YOUR_CLIENT_SECRET":
        print("Error: Client ID &/or Client Secret aint set")
        print("Open the .py file & paste yo ID into the CLIENT_ID n CLIENT_SECRET shi at the beginnin of this shiahhcode")
        sys.exit(1)

    try:
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=auth_manager)
        # test auth
        sp.search(q='test', type='track', limit=1)
        print("Spotify API auth was ok")
        return sp
    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify API error when authing: {e}") # u cooked
        if e.http_status == 401:
            print("Check if the Client ID & Client Secret u put in the code r correct")
        sys.exit(1) # Exit the program in case of auth error
    except Exception as e:
        print(f"Unexpected error when connecting to Spotify: {e}") # u cooked
        sys.exit(1)

def extract_album_id(url):
    """Extracts the album ID from the Spotify URL"""
    match = re.search(r'spotify\.com/album[/:]([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    match_uri = re.search(r'spotify:album:([a-zA-Z0-9]+)', url)
    if match_uri:
        return match_uri.group(1)
    return None

def ms_to_min_sec(ms):
    """Converts ms to MM:SS format"""
    if ms is None:
        return "N/A"
    total_seconds = int(ms / 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02}"

def get_album_info(sp, album_id):
    """Receives and processes album info (basic ver)"""
    try:
        print(f"Requesting data for an album with ID: {album_id}...")
        album_data = sp.album(album_id)
        print("Data received, processing...")

        album_info = {
            "album_title": album_data.get('name', 'N/A'),
            "album_artists": [artist['name'] for artist in album_data.get('artists', [])],
            "release_date": album_data.get('release_date', 'N/A'),
            "label": album_data.get('label', 'N/A'),
            "spotify_url": album_data.get('external_urls', {}).get('spotify', 'N/A'),
            "cover_art_url_api_max": None,
            "copyright_phonogram": None,
            "copyright_composition": None,
            "total_tracks": album_data.get('total_tracks', 0),
            "tracks": []
        }

        # Looking for cover art from API
        images = album_data.get('images', [])
        if images:
            album_info["cover_art_url_api_max"] = images[0].get('url')
            print(f"Found the cover URL from the API: {album_info['cover_art_url_api_max']} (Resolution: {images[0].get('width')}x{images[0].get('height')})")
        else:
             print("Warning: Couldn't find the cover URL") # oops

        # Looking for copyright
        copyrights = album_data.get('copyrights', [])
        for cp in copyrights:
            text = cp.get('text', '')
            cp_type = cp.get('type', '')
            if cp_type == 'P' and album_info["copyright_phonogram"] is None:
                album_info["copyright_phonogram"] = text
            elif cp_type == 'C' and album_info["copyright_composition"] is None:
                album_info["copyright_composition"] = text

        # Retrieving track information
        tracks_data = album_data.get('tracks', {})
        track_items = tracks_data.get('items', [])

        for i, track in enumerate(track_items, 1):
             track_info = {
                 "track_number": track.get('track_number', i),
                 "track_title": track.get('name', 'N/A'),
                 "track_artists": [artist['name'] for artist in track.get('artists', [])],
                 "duration_ms": track.get('duration_ms'),
                 "duration_mmss": ms_to_min_sec(track.get('duration_ms')),
                 "spotify_url": track.get('external_urls', {}).get('spotify', 'N/A'),
                 "is_explicit": track.get('explicit', False)
             }
             album_info["tracks"].append(track_info)

        offset = len(track_items)
        limit = 50
        while tracks_data and tracks_data.get('next'):
            print(f"Requesting the next set of tracks (from {offset+1})...")
            try:
                more_tracks_data = sp.album_tracks(album_id, limit=limit, offset=offset)
                if not more_tracks_data or not more_tracks_data.get('items'):
                    break

                more_track_items = more_tracks_data.get('items', [])
                for i, track in enumerate(more_track_items, offset + 1):
                     track_info = {
                        "track_number": track.get('track_number', i),
                        "track_title": track.get('name', 'N/A'),
                        "track_artists": [artist['name'] for artist in track.get('artists', [])],
                        "duration_ms": track.get('duration_ms'),
                        "duration_mmss": ms_to_min_sec(track.get('duration_ms')),
                        "spotify_url": track.get('external_urls', {}).get('spotify', 'N/A'),
                        "is_explicit": track.get('explicit', False)
                     }
                     album_info["tracks"].append(track_info)

                offset += len(more_track_items)
                tracks_data = more_tracks_data

            except spotipy.exceptions.SpotifyException as e:
                print(f"Error when receiving additional tracks: {e}") # u cooked
                break
            except Exception as e:
                print(f"Unexpected error when getting additional tracks: {e}") # u cooked
                break

        print(f"Processed {len(album_info['tracks'])} tracks from {album_info['total_tracks']} received.")
        return album_info

    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify API error when retrieving album data: {e}") # u cooked
        if e.http_status == 404:
            print(f"Album with ID ‘{album_id}’ wasn't found") # u cooked
        elif e.http_status == 400:
             print(f"Invalid album ID: '{album_id}'")
        return None
    except Exception as e:
        print(f"Unexpected error while processing album data: {e}") # u cooked
        return None

def save_to_json(data, filename):
    """Saves data to a JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"The album information has been successfully saved to a file: {filename}")
    except IOError as e:
        print(f"Error when writing a file '{filename}': {e}") # u cooked
    except Exception as e:
        print(f"Unexpected error when saving to JSON: {e}") # u cooked

# main shi
if __name__ == "__main__":
    print("--- Spotify Album Info Extractor ---")

    # Get the album URL from the user
    album_url = input("Enter the Spotify album link (URL): ").strip()

    # Retrieve album ID
    album_id = extract_album_id(album_url)

    if not album_id:
        print(f"Error: Failed to retrieve album ID from link '{album_url}'.")
        print("Make sure the link is correct (e.g. https://open.spotify.com/album/1uLJgJnW5emYftpOOPtpjA)")
        sys.exit(1)

    # Create a Spotify client
    sp_client = get_spotify_client(CLIENT_ID, CLIENT_SECRET)

    # Get album info
    album_details = get_album_info(sp_client, album_id)

    # If the information is successfully received, save it to JSON
    if album_details:
        # Generate file name
        safe_album_name = re.sub(r'[\\/*?:"<>|]', "", album_details['album_title'][:50])
        output_filename = f"spotify_album_{safe_album_name}_{album_id}.json"
        save_to_json(album_details, output_filename)
    else:
        print("Failed to retrieve album information - the file hasn't been created") # u cooked

    print("--- Done ---")