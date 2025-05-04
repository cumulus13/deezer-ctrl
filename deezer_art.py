import mimetypes

import requests
from PIL import Image
from io import BytesIO
import os
import re
from unidecode import unidecode
from make_colors import make_colors
import traceback
from pydebugger.debug import debug

def download_image(image_url, save_path = None, verbose = True):
    if save_path and not os.path.isdir(save_path) and not str(save_path.split(".")[-1]).lower() in [".jpg", ".png", ".bmp", ".jpeg", ".webp"]:
        os.makedirs(save_path)
    ext = os.path.splitext(image_url)[-1] if len(os.path.splitext(image_url)) > 1 else None
    debug(ext = ext, debug = 1)
    response = requests.get(image_url)
    if not ext and response.headers.get('content-type'): ext = mimetypes.guess_extension(response.headers.get('content-type'))
    debug(ext = ext, debug = 1)
    if not ext: ext = ".jpg"
    debug(ext = ext, debug = 1)
    debug(save_path = save_path, debug = 1)
    if str(save_path.split(".")[-1]).lower() in [".jpg", ".png", ".bmp", ".jpeg", ".webp"]:
        save_path = save_path
    else:
        cover = os.path.splitext(os.path.basename(image_url))[0] + ext
        if save_path:
            save_path = os.path.join(save_path, cover)
        else:
            save_path = cover
    debug(save_path = save_path, debug = 1)
    
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        image.save(save_path)
        if verbose: print(f"[deezer_art] Image downloaded and saved to {save_path}")
        return save_path
    else:
        if os.getenv('TRACEBACK') == '1':
            print(f"[{make_colors(response.status_code, 'lw', 'r')}] {make_colors(response.content, 'lw', 'r')}")        
        if verbose: print(f"[deezer_art] Failed to download image. Status code: {response.status_code}")
        return ''
    
def normalization_name(name):
    name = name.strip()
    name = re.sub("\: ", " - ", name)
    name = re.sub("\?|\*", "", name)
    name = re.sub("\:", "-", name)
    name = re.sub("\.\.\.", "", name)
    name = re.sub("\.\.\.", "", name)
    name = re.sub(" / ", " - ", name)
    name = re.sub("/", "-", name)
    name = re.sub(" ", ".", name)
    name = name.encode('utf-8', errors = 'ignore').strip()
    name = unidecode(name.decode('utf-8', errors = 'ignore')).strip()
    name = re.sub("\^", "", name)
    name = re.sub("\[|\]|\?", "", name)
    name = re.sub("  ", " ", name)
    name = re.sub("   ", " ", name)
    name = re.sub("    ", " ", name)
    name = re.sub("\(|\)", "", name)
    name = name.strip()
    while 1:
        if name.strip()[-1] == ".":
            name = name.strip()[:-1]
        else:
            break
    debug(name = name)
    return name    

def get_info(artist_name, song_name=None, album_name=None, to_json = True):
    base_url = 'https://api.deezer.com/search'
    
    query = f"artist:'{artist_name}'"
    if song_name:
        query += f" track:'{song_name}'"
    if album_name:
        query += f" album:'{album_name}'"
    
    params = {
        'q': query
    }

    try:
        response = requests.get(base_url, params=params, timeout = 60)
        if to_json:
            return response.json()
        else:
            return response#.json()
    except Exception as e:
        print(make_colors("ERROR [deezer_art]:", 'lw', 'r') + " " + make_colors(e, 'lw', 'bl'))
        if os.getenv('TRACEBACK') == "1":
            print(make_colors("ERROR [deezer_art]:", 'lw', 'r') + " " + make_colors(traceback.format_exc(), 'lw', 'bl'))
    
    return {}
        
def get_album_art(artist_name, song_name=None, album_name=None, to_file = False):
    response = get_info(artist_name, song_name, album_name, False)
    if response and response.status_code == 200:
        data = response.json()
        if data['data']:
            # Assume the first result is the most relevant
            track_info = data['data'][0]
            album_id = track_info.get('album').get('id')
            #album_art_url = f"https://api.deezer.com/album/{album_id}/image"
            album_art_url = track_info.get('album').get('cover_xl') or track_info.get('album').get('cover_big') or track_info.get('album').get('cover') or f"https://api.deezer.com/album/{album_id}/image"
            if to_file:
                filename = os.path.join(os.getenv('temp', '/tmp'), normalization_name(artist_name))
                return download_image(album_art_url, filename)
            return album_art_url
        else:
            print("[Deezer-art] No results found.")
    else:
        if response:
            print(f"[Deezer-art] Error: {response.status_code} - {response.reason}")
        else:
            print(f"[Deezer-art] Error: Failed to get cover art album !")
        
    return ""

if __name__ == "__main__":
    print("Example usage .........")
    # Example usage
    artist = 'Coldplay'
    print("ARTIST:", artist)
    song = 'Adventure of a Lifetime'
    print("TITLE:", song)
    album = 'A Head Full of Dreams'
    print("ALBUM:", album)
    
    album_art_url = get_album_art(artist, song, album)
    print("ALBUM_ART_URL:", album_art_url)
    if album_art_url.startswith("http"):
        download_image(album_art_url, 'album_art.jpg')
    else:
        print(album_art_url)
