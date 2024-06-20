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
from xnotify import notify
import time
from multiprocessing import Process
import traceback

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
        
        self.client = MPDClient()
        self.process = Process(target=self.connection_watch)
        self.process.start()
        
        self.notify = notify('MPD-Ticker', ['New Song'])
    
        self.root = root
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.attributes("-topmost", True)  # Keep window on top initially
        self.root.attributes("-alpha", self.CONFIG.get_config('transparent', 'level', 60) / 100)
        self.load_position()  # Load window position
        self.child_window = None        
        
        self.style = ttk.Style()
        
        self.style.configure("Custom.TFrame", background=self.CONFIG.get_config('color', 'background', "#353535"))
    
        # Configure styles for title, album, and artist
        self.title_color = self.CONFIG.get_config('color', 'title', "#00FFFF")
        self.album_color = self.CONFIG.get_config('color', 'album', "#FFFF00")
        self.artist_color = self.CONFIG.get_config('color', 'artist', "#21FF15")
        
        self.title_font = (self.CONFIG.get_config('font', 'title_name', "Helvetica"), self.CONFIG.get_config('font', 'title_size', 14))
        self.album_font = (self.CONFIG.get_config('font', 'album_name', "Helvetica"), self.CONFIG.get_config('font', 'album_size', 12))
        self.artist_font = (self.CONFIG.get_config('font', 'artist_name', "Helvetica"), self.CONFIG.get_config('font', 'artis_size', 12))
    
        self.frame = ttk.Frame(root, style="Custom.TFrame", padding = 0, borderwidth = 0)
        self.frame.pack(fill=tk.BOTH, expand=True, anchor='n')  # Align to top
    
        #self.canvas = tk.Canvas(self.frame, background=self.CONFIG.get_config('color', 'background', "#353535"), width=600, height=100)
        self.canvas = tk.Canvas(self.frame, background=self.CONFIG.get_config('color', 'background', "#353535"), highlightthickness=0, borderwidth=0, width=600, height=100)
        self.canvas.pack(fill=tk.BOTH, expand=True)
    
        self.x = 0  # Starting position of the text
        self.ticker_job = self.root.after(50, self.update_ticker)  # Start the ticker
    
        # Initialize MPD client
        self.connect_to_mpd()
        self.current_song = None
    
        # Start fetching song info
        self.update_song_info()
    
        # Bind keys to quit the application
        #self.root.bind('<Escape>', self.quit)
        #self.root.bind('<q>', self.quit)
        #self.root.bind('<x>', self.quit)
        
        self.root.bind('<Escape>', self.quit_or_close_child)
        self.root.bind('<q>', self.quit_or_close_child)
        self.root.bind('<x>', self.quit_or_close_child)        
        
        self.root.bind('<s>', self.show_full_image)        
    
        # Bind keys to toggle always on top
        self.root.bind('a', self.set_always_on_top)
        self.root.bind('<Shift-A>', self.set_normal)
    
        # Bind window movement to save position
        self.root.bind('<Configure>', self.save_position)
    
        # Bind mouse events for dragging
        self.canvas.bind("<Button-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)
    
    def quit_or_close_child(self, event):
        if self.child_window is not None:
            self.close_child()
        else:
            self.quit()
            
    def start_move(self, event):
        self.x_offset = event.x
        self.y_offset = event.y
    
    def do_move(self, event):
        x = self.root.winfo_pointerx() - self.x_offset
        y = self.root.winfo_pointery() - self.y_offset
        self.root.geometry(f"+{x}+{y}")

    def schedule_image_resize(self):
        self.root.after(100, self.resize_image_to_text_height)
    
    def connection_watch(self):
        while True:
            try:
                self.client.connect(self.CONFIG.get_config('mpd', 'host', '127.0.0.1') or os.getenv('MPD_HOST', '127.0.0.1'), self.CONFIG.get_config('mpd', 'port', 6600) or int(os.getenv('MPD_PORT', 6600)))
                status = self.client.status()
                print(status)
            except:
                try:
                    self.client.disconnect()
                except:
                    pass
                self.client.connect(self.CONFIG.get_config('mpd', 'host', '127.0.0.1') or os.getenv('MPD_HOST', '127.0.0.1'), self.CONFIG.get_config('mpd', 'port', 6600) or int(os.getenv('MPD_PORT', 6600)))
            time.sleep(self.CONFIG.get_config('watch', 'sleep', '5') or 5)
            
    def connect_to_mpd(self):
        while 1:
            try:
                self.client.connect(self.CONFIG.get_config('mpd', 'host', '127.0.0.1') or os.getenv('MPD_HOST', '127.0.0.1'), self.CONFIG.get_config('mpd', 'port', 6600) or int(os.getenv('MPD_PORT', 6600)))
                status = self.client.status()
                #print(status)
                break
            except Exception as e:
                if str(e) != 'Already connected':
                    print(f"{make_colors('Could not connect to MPD', 'lw','r')} {make_colors('[1]', 'b', 'ly')}: {make_colors(e, 'lw','r')}")
                if os.getenv('traceback') == '1': print(traceback.format_exc())                    
                try:
                    self.client.currentsong()
                except:
                    try:
                        self.client.disconnect()
                    except:
                        if os.getenv('traceback') == '1': print(traceback.format_exc())
                    try:
                        self.client.connect(self.CONFIG.get_config('mpd', 'host', '127.0.0.1') or os.getenv('MPD_HOST', '127.0.0.1'), self.CONFIG.get_config('mpd', 'port', 6600) or int(os.getenv('MPD_PORT', 6600)))
                        break
                    except Exception as e:
                        print(f"{make_colors('Could not connect to MPD', 'lw','r')} {make_colors('[2]', 'b', 'ly')}: {make_colors(e, 'lw','r')}")

            time.sleep(self.CONFIG.get_config('reconnection', 'sleep', '1') or 1)

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

    def update_text_on_canvas(self, image_width):
        # Ensure the text is overlayed on the image
        self.canvas.delete("text")
        # Adjust text coordinates to place it to the left of the resized image with more compact spacing
        self.canvas.create_text(image_width + 20, 10, text=self.current_song.get('title', 'Unknown Title'), fill=self.title_color, font=self.title_font, anchor='nw', tags="text")
        self.canvas.create_text(image_width + 20, 23, text=f"Album: {self.current_song.get('album', 'Unknown Album')} ({self.current_song.get('date', 'Unknown Year')})", fill=self.album_color, font=self.album_font, anchor='nw', tags="text")
        self.canvas.create_text(image_width + 20, 35, text=f"Artist: {self.current_song.get('artist', 'Unknown Artist')}", fill=self.artist_color, font=self.artist_font, anchor='nw', tags="text")
    
    def resize_image_to_text_height(self):
        self.root.update_idletasks()  # Ensure window is fully rendered
    
        # Get the height of the text elements
        text_height = 10 + 20 + 20  # Adjust these values as needed for spacing and font size
    
        # Calculate the width and height for the image
        aspect_ratio = self.original_image.width / self.original_image.height
        image_height = text_height - 12
        image_width = int(image_height * aspect_ratio)
    
        #print(f"Image size: {image_width}x{image_height}")  # Debugging statement
    
        # Resize the image to match the calculated size
        resized_image = self.original_image.resize((image_width, image_height), Image.LANCZOS)
        self.image = ImageTk.PhotoImage(resized_image)
    
        # Update the canvas with the resized image
        self.canvas.delete("image")
        self.canvas.create_image(10, 10, image=self.image, anchor='nw', tags="image")
        self.canvas.tag_bind("image", "<Button-1>", self.show_full_image)
        #print("Image added to canvas")  # Debugging statement
    
        # Ensure text is on top of the image
        self.update_text_on_canvas(image_width)
        
    def show_full_image(self, event):
        if self.child_window is not None:
            return
    
        self.child_window = tk.Toplevel(self.root)
        self.child_window.title("Full Image")
        self.child_window.geometry("800x800")
    
        # Resize image to fit within 800 pixels
        aspect_ratio = self.original_image.width / self.original_image.height
        if self.original_image.width > 800 or self.original_image.height > 800:
            if self.original_image.width > self.original_image.height:
                new_width = 800
                new_height = int(800 / aspect_ratio)
            else:
                new_height = 800
                new_width = int(800 * aspect_ratio)
        else:
            new_width = self.original_image.width
            new_height = self.original_image.height
    
        resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
        self.full_image = ImageTk.PhotoImage(resized_image)
    
        label = tk.Label(self.child_window, image=self.full_image)
        label.pack(expand=True)
    
        # Bind keys to close child window
        self.child_window.bind('<Escape>', self.close_child)
        self.child_window.bind('<q>', self.close_child)
        self.child_window.bind('<x>', self.close_child)
    
    def close_child(self, event=None):
        if self.child_window is not None:
            self.child_window.destroy()
            self.child_window = None
    
    def update_ticker(self):
        self.root.attributes("-alpha", self.CONFIG.get_config('transparent', 'level', 60) / 100)
        self.canvas.move("all", -2, 0)  # Move all elements to the left
        bbox = self.canvas.bbox("all")
        if bbox[2] < 0:  # If the text has moved off the screen
            self.canvas.move("all", self.root.winfo_width(), 0)  # Move it back to the right side
        self.ticker_job = self.root.after(self.CONFIG.get_config('sleep', 'time', 100), self.update_ticker)  # Update ticker every 100 milliseconds

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

    def find_cover_art_lastfm(self, data=None):
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
        except Exception as e:
            print(f"Could not fetch song info: {e}")
            self.connect_to_mpd()  # Try to reconnect if fetching failed
        try:
            status = self.client.status()
            status_str = ''
            if status.get('state') != 'play':
                status_str = ' [pause]'
            if song != self.current_song:
                self.current_song = song
                self.canvas.delete("text")
                self.canvas.create_text(10, 10, text=song.get('title', 'Unknown Title') + status_str, fill=self.title_color, anchor='nw', tags="text")
                self.canvas.create_text(10, 30, text=f"Album: {song.get('album', 'Unknown Album')} ({song.get('date', 'Unknown Year')})", fill=self.album_color, anchor='nw', tags="text")
                self.canvas.create_text(10, 50, text=f"Artist: {song.get('artist', 'Unknown Artist')}", fill=self.artist_color, anchor='nw', tags="text")
                self.update_image()
                self.notify.send(title = 'MPD Ticker', message = f"{song.get('title')}\n{song.get('album')}\n{song.get('artist')}\n", icon = self.find_cover_art())
            self.root.after(10000, self.update_song_info)  # Update every 10 seconds
        except Exception as e:
            print(f"Could not fetch song info: {e}")
            self.connect_to_mpd()  # Try to reconnect if fetching failed

    def update_image(self):
        try:
            picture_path = self.find_cover_art()
            #print(f"Picture path: {picture_path}")  # Debugging statement
            self.original_image = Image.open(picture_path)
            #print(f"Image loaded: {self.original_image}")  # Debugging statement
            self.resize_image_to_text_height()
        except Exception as e:
            print(f"Could not update image: {e}")

    def read_picture(self):
        # Implement this function to read the picture associated with the current song
        return "icon.png"  # Replace with actual picture path

    def quit(self, event=None):
        self.process.terminate()
        try:
            self.client.disconnect()
        except:
            pass
        self.root.after_cancel(self.ticker_job)  # Cancel the scheduled update_ticker call
        self.save_position()  # Save position on quit
        self.root.destroy()

    def set_always_on_top(self, event):
        self.root.attributes("-topmost", True)

    def set_normal(self, event):
        self.root.attributes("-topmost", False)

    #def start_move(self, event):
        #self.x_offset = event.x
        #self.y_offset = self.y_offset = event.y

    #def do_move(self, event):
        #x = self.root.winfo_pointerx() - self.x_offset
        #y = self.root.winfo_pointery() - self.y_offset
        #self.root.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    root = tk.Tk()
    text = "TRACK.TITLE\nAlbum: ALBUM\nArtist: ARTIST"
    app = Ticker(root, text)
    root.mainloop()
