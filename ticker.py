import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from pathlib import Path
from configset import configset
from mpd import MPDClient
from pydebugger.debug import debug
from make_colors import make_colors
import mimetypes
import re
from unidecode import unidecode
import requests

class LastFM(object):
    CONFIGNAME = str(Path(__file__).parent / 'ticker_job.ini')
    CONFIG = configset(CONFIGNAME)

    @classmethod
    def search_track(self, artist, track):
        url = 'http://ws.audioscrobbler.com/2.0/'
        params = {
            'method': 'track.search',
            'track': track,
            'artist': artist,
            'api_key': self.CONFIG.get_config('lastfm', 'api') or "c725344c28768a57a507f014bdaeca79",
            'format': 'json'
        }

        response = requests.get(url, params=params)
        data = response.json()
        if data['results']['trackmatches']['track']:
            return data['results']['trackmatches']['track'][0]
        else:
            return None

    @classmethod
    def get_track_info(self, artist, track):
        track_info = self.search_track(artist, track)
        if track_info:
            track_name = track_info['name']
            artist_name = track_info['artist']
            url = 'http://ws.audioscrobbler.com/2.0/'
            params = {
                'method': 'track.getInfo',
                'track': track_name,
                'artist': artist_name,
                'api_key': self.CONFIG.get_config('lastfm', 'api') or "c725344c28768a57a507f014bdaeca79",
                'format': 'json'
            }
            response = requests.get(url, params=params)
            data = response.json()
            debug(data = data)
            if 'track' in data and 'album' in data['track']:
                album_info = data['track']['album']
                return {
                    'album_name': album_info['title'],
                    'album_url': album_info['url'],
                    'album_image': album_info['image'][-1]['#text'] if album_info['image'] else None
                }

        return {
            'album_name': '',
            'album_url': '',
            'album_image': str(Path(__file__).parent / 'default_cover.png')
        }

class Ticker:
    def __init__(self, root, text=" Welcome to the MPD ticker! "):
        self.CONFIGFILE = str(Path(__file__).parent / "ticker.ini")
        self.CONFIG = configset(self.CONFIGFILE)

        self.root = root
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.attributes("-topmost", True)  # Keep window on top initially
        self.load_position()  # Load window position

        self.style = ttk.Style()
        self.style.configure("Custom.TFrame", background=self.CONFIG.get_config('color', 'background', "#353535"))

        # Configure styles for title, album, and artist
        self.title_color = self.CONFIG.get_config('color', 'title', "#00FFFF")
        self.album_color = self.CONFIG.get_config('color', 'album', "#FFFF00")
        self.artist_color = self.CONFIG.get_config('color', 'artist', "#21FF15")

        self.frame = ttk.Frame(root, style="Custom.TFrame")
        self.frame.pack(fill=tk.BOTH, expand=True, anchor='n')  # Align to top

        self.canvas = tk.Canvas(self.frame, background=self.CONFIG.get_config('color', 'background', "#353535"))
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.x = 0  # Starting position of the text
        self.ticker_job = self.root.after(50, self.update_ticker)  # Start the ticker

        # Initialize MPD client
        self.client = MPDClient()
        self.connect_to_mpd()
        self.current_song = None

        # Start fetching song info
        self.update_song_info()

        # Bind keys to quit the application
        self.root.bind('<Escape>', self.quit)
        self.root.bind('<q>', self.quit)
        self.root.bind('<x>', self.quit)

        # Bind keys to toggle always on top
        self.root.bind('a', self.set_always_on_top)
        self.root.bind('<Shift-A>', self.set_normal)

        # Bind window movement to save position
        self.root.bind('<Configure>', self.save_position)

        # Bind mouse events for dragging
        self.frame.bind("<Button-1>", self.start_move)
        self.frame.bind("<B1-Motion>", self.do_move)

    def connect_to_mpd(self):
        try:
            self.client.connect("localhost", 6600)
        except Exception as e:
            print(f"Could not connect to MPD: {e}")

    def load_position(self):
        if self.CONFIG.get_config('geometry', 'x') and self.CONFIG.get_config('geometry', 'y') and self.CONFIG.get_config('geometry', 'width') and self.CONFIG.get_config('geometry', 'height'):
            self.root.geometry(f"{self.CONFIG.get_config('geometry', 'width')}x{self.CONFIG.get_config('geometry', 'height')}+{self.CONFIG.get_config('geometry', 'x')}+{self.CONFIG.get_config('geometry', 'y')}")
        else:
            self.root.geometry("500x45+100+100")  # Default position and size

    def save_position(self, event=None):
        if event:
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            self.CONFIG.write_config('geometry', 'x', x)
            self.CONFIG.write_config('geometry', 'y', y)
            self.CONFIG.write_config('geometry', 'width', width)
            self.CONFIG.write_config('geometry', 'height', height)

    def resize_image_to_text_height(self):
        self.root.update_idletasks()  # Ensure window is fully rendered
        # Get the height of the text
        text_height = self.canvas.winfo_height()

        # Resize the image to match the canvas height
        resized_image = self.original_image.resize((text_height, text_height), Image.LANCZOS)
        self.image = ImageTk.PhotoImage(resized_image)

        # Update the canvas with the resized image
        self.canvas.create_image(0, 0, image=self.image, anchor='nw')

    def update_ticker(self):
        self.canvas.move("all", -2, 0)  # Move all elements to the left
        bbox = self.canvas.bbox("all")
        if bbox[2] < 0:  # If the text has moved off the screen
            self.canvas.move("all", self.root.winfo_width(), 0)  # Move it back to the right side
        self.ticker_job = self.root.after(self.CONFIG.get_config('sleep', 'time', 100), self.update_ticker)  # Update ticker every 100 milliseconds

        # Update geometry from config
        self.load_position()
        self.root.update()  # Allow event processing
        
    def normalization_name(self, name):
        name0 = name
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

    def find_cover_art(self):
        try:
            current_song = self.client.currentsong()
            if os.path.isfile(str(Path(os.getenv('temp', '/tmp')) / Path(self.normalization_name(current_song.get('title')) + ".jpg"))):
                return str(Path(os.getenv('temp', '/tmp')) / Path(self.normalization_name(current_song.get('title')) + ".jpg"))
            elif os.path.isfile(str(Path(os.getenv('temp', '/tmp')) / Path(self.normalization_name(current_song.get('title')) + ".png"))):
                return str(Path(os.getenv('temp', '/tmp')) / Path(self.normalization_name(current_song.get('title')) + ".png"))
        except Exception as e:
            if str(e) == 'Already connected':
                self.client.disconnect()
                self.connect_to_mpd()
                return self.find_cover_art()

        try:
            current_song = self.client.currentsong()
            debug(current_song = current_song)
            song = current_song.get('file', '')
            debug(song = song)
            if song:
                picture = self.client.readpicture(song)
                debug(picture = picture.keys())
                if picture.get('binary'):
                    debug(picture = len(picture.get('binary')))
                    ext = mimetypes.guess_extension(picture.get('type'))
                    debug(ext = ext)
                    temp_path = str(Path(os.getenv('temp', '/tmp')) / Path('temp_cover' + (ext or ".jpg")))
                    debug(temp_path = temp_path)
                    with open(temp_path, 'wb') as img_file:
                        img_file.write(picture.get('binary'))
                    return temp_path

        except Exception as e:
            print("No embedded cover art found:", e)

        return self.find_cover_art_lastfm()

    def find_cover_art_lastfm(self, data):
        api_key = self.CONFIG.get_config('lastfm', 'api') or "c725344c28768a57a507f014bdaeca79"
        if not data:
            current_song = self.client.currentsong()
            artist = current_song.get('artist')
            album = current_song.get('album')
            title = current_song.get('title')
        else:
            artist = data.get('artist')
            album = data.get('album')
            title = data.get('title')

        if artist and album:
            url = f"http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={api_key}&artist={artist}&album={album}&format=json"
            a = requests.get(url)
            if a.status_code == 200:
                try:
                    url1 = a.json()['album']['image'][-1]['#text']
                    temp_path = str(Path(os.getenv('temp', '/tmp')) / Path('temp_cover' + os.path.splitext(url1)[-1]))
                    with open(temp_path, 'wb') as f:
                        f.write(requests.get(url1).content)
                    return temp_path
                except Exception as e:
                    print("failed to get cover art from LastFM:", e)

        if artist and title:
            cover_from_lastfm = LastFM.get_track_info(artist, title)
            return cover_from_lastfm.get('album_image')

        return str(Path(__file__).parent / 'default_cover.png')

    def update_song_info(self):
        try:
            song = self.client.currentsong()
            status = self.client.status()
            status_str = ''
            if status.get('state') != 'play':
                status_str = ' [pause]'
            if song != self.current_song:
                self.current_song = song
                self.canvas.delete("text")
                self.canvas.create_text(10, 10, text=song.get('title', 'Unknown Title'), fill=self.title_color, anchor='nw', tags="text")
                self.canvas.create_text(10, 30, text=f"Album: {song.get('album', 'Unknown Album')} ({song.get('date', 'Unknown Year')})", fill=self.album_color, anchor='nw', tags="text")
                self.canvas.create_text(10, 50, text=f"Artist: {song.get('artist', 'Unknown Artist')}", fill=self.artist_color, anchor='nw', tags="text")
                self.update_image()
            self.root.after(10000, self.update_song_info)  # Update every 10 seconds
        except Exception as e:
            print(f"Could not fetch song info: {e}")
            self.connect_to_mpd()  # Try to reconnect if fetching failed

    def update_image(self):
        try:
            picture_path = self.find_cover_art()
            self.original_image = Image.open(picture_path)
            self.resize_image_to_text_height()
        except Exception as e:
            print(f"Could not update image: {e}")

    def read_picture(self):
        # Implement this function to read the picture associated with the current song
        return "icon.png"  # Replace with actual picture path

    def quit(self, event=None):
        self.root.after_cancel(self.ticker_job)  # Cancel the scheduled update_ticker call
        self.save_position()  # Save position on quit
        self.root.destroy()

    def set_always_on_top(self, event):
        self.root.attributes("-topmost", True)

    def set_normal(self, event):
        self.root.attributes("-topmost", False)

    def start_move(self, event):
        self.x_offset = event.x
        self.y_offset = event.y

    def do_move(self, event):
        x = self.root.winfo_pointerx() - self.x_offset
        y = self.root.winfo_pointery() - self.y_offset
        self.root.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    root = tk.Tk()
    text = "TRACK.TITLE\nAlbum: ALBUM\nArtist: ARTIST"
    app = Ticker(root, text)
    root.mainloop()

