import tkinter as tk

from tkinter import ttk
from PIL import Image, ImageTk
import os
import sys
import logging
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
from multiprocessing import Process, Manager
#from threading import Thread
#import queue
import traceback
from urllib.parse import quote
import deezer_art
from datetime import datetime
import bitmath
#import mpd
import win32gui, win32con
import ctypes

class CustomFormatter(logging.Formatter):

    info = "\x1b[32;20m"
    debug = "\x1b[33;20m"
    fatal = "\x1b[44;97m"
    error = "\x1b[41;97m"
    warning = "\x1b[43;30m"
    critical = "\x1b[45;97m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(process)d - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: debug + format + reset,
        logging.INFO: info + format + reset,
        logging.WARNING: warning + format + reset,
        logging.ERROR: error + format + reset,
        logging.CRITICAL: critical + format + reset, 
        logging.FATAL: fatal + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()

    # Update the handlers of the root logger
    for handler in logger.handlers:
        handler.setFormatter(CustomFormatter())

# Setup logging
if os.getenv('LOGGING_COLOR') == '1':
    setup_logging()
else:
    logging.basicConfig(level=logging.DEBUG)

CONFIGFILE = str(Path(__file__).parent / "ticker.ini")
CONFIG = configset(CONFIGFILE)

def logger(message, status="info"):
    if isinstance(message, str): message = bytes(message, encoding = "utf-8")
    HOST = os.getenv('MPD_HOST') or CONFIG.get_config('mpd', 'host', '127.0.0.1')
    if HOST in ['127.0.0.1', 'localhost', '::1']:
        HOST = ''
    else:
        HOST = HOST.replace(".", "_")
        HOST = HOST.replace(":", "")
        if HOST: HOST = HOST + "_"
        
    logfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.basename(CONFIG.configname).split(".")[0] + f"{HOST}.log")
    if not os.path.isfile(logfile):
        lf = open(logfile, 'wb')
        lf.close()
    real_size = bitmath.getsize(logfile).kB.value
    max_size = CONFIG.get_config("log", 'max_size')
    debug(max_size = max_size)
    if max_size:
        debug(is_max_size = True)
        try:
            max_size = bitmath.parse_string_unsafe(max_size).kB.value
        except:
            max_size = 0
        if real_size > max_size:
            try:
                os.remove(logfile)
            except Exception as e:
                logging.error(str(e))
                if os.getenv('TRACEBACK') in ['1', '2']:
                    logging.error(traceback.format_exc())
                if os.getenv('TRACEBACK') == '2':
                    print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} [{make_colors('logger', 'lw', 'm')}] {make_colors('[ERROR]', 'lw','r')} {make_colors('[1]', 'b', 'ly')} {make_colors(e, 'lw', 'r')}")
                    print(make_colors(traceback.format_exc(), 'lw', 'r'))                    
            try:
                lf = open(logfile, 'wb')
                lf.close()
            except Exception as e:
                if os.getenv('TRACEBACK') == '2':
                    print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} [{make_colors('logger', 'lw', 'm')}] {make_colors('[ERROR]', 'lw','r')} {make_colors('[2]', 'b', 'ly')} {make_colors(e, 'lw', 'r')}")
                    print(make_colors(traceback.format_exc(), 'lw', 'r'))
                logging.error(str(e))
                if os.getenv('TRACEBACK') in ['1', '2']: logging.error(traceback.format_exc())                

    str_format = datetime.strftime(datetime.now(), "%Y/%m/%d %H:%M:%S.%f") + " - [{}] {}".format(status, message) + "\n"
    with open(logfile, 'ab') as ff:
        if sys.version_info.major == 3:
            if not hasattr(str_format, 'decode'):
                ff.write(bytes(str_format, encoding='utf-8'))
            else:
                ff.write(str_format)
        else:
            ff.write(str_format)

def connection_watch(shared_data, host, port, timeout):
    client = MPDClient()
    while True:
        try:
            if os.getenv('DEBUG') == '1': print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} [{make_colors('Connection Watch', 'lw', 'm')}] {make_colors('Start connecting ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
            client.connect(host, port, timeout)
            status = client.status()
            shared_data['current_song'] = client.currentsong()
            shared_data['status'] = status
            debug(shared_data = shared_data)
            #shared_data['client'] = client #error
        except Exception as e0:
            debug(E0 = e0)
            logger("E0: " + str(e0), 'error')
            if os.getenv('traceback') == '2':
                logging.error(traceback.format_exc())
                
            if os.getenv('DEBUG') == '1': print("E 0:", make_colors(str(e0), 'lw', 'm'), f"{make_colors(host, 'b', 'ly')}:{make_colors(port, 'b', 'lc')}")
            if str(e0).lower() == "already connected":
                try:
                    shared_data['current_song'] = client.currentsong()
                    status = client.status()
                    shared_data['status'] = status
                    debug(shared_data = shared_data)
                except Exception as e1:
                    debug(E1 = e1)
                    if os.getenv('DEBUG') == '1':print("E 1:", make_colors(str(e1), 'lw', 'm'))
                    logger("E1: " + str(e1), 'error')
                    logging.error("E1: " + str(e1))
                    logger(traceback.format_exc(), 'error')
                    if os.getenv('traceback') == '2':
                        print(make_colors(traceback.format_exc(), 'lw', 'bl'))
                    if os.getenv('traceback') == '1':
                        logging.error(traceback.format_exc())
                        
                    try:
                        client.disconnect()
                        client.connect(host, port, timeout)
                        status = client.status()
                        shared_data['current_song'] = client.currentsong()
                        shared_data['status'] = status
                        debug(shared_data = shared_data)
                    except Exception as e3:
                        debug(E3 = e3)
                        logger("E3: " + str(e3), 'error')
                        logger(traceback.format_exc(), 'error')
                        logging.error("E3: " + str(e3))
                        if os.getenv('traceback') == '1': logging.error(traceback.format_exc())
                        if os.getenv('traceback') == '2': print(make_colors(traceback.format_exc(), 'b', 'g'))
                        if os.getenv('DEBUG') == '1': print("E 3:", make_colors(str(e3), 'lw', 'm'), f"{make_colors(host, 'b', 'ly')}:{make_colors(port, 'b', 'lc')}")
            else:
                try:
                    client.connect(host, port, timeout)
                    status = client.status()
                    shared_data['current_song'] = client.currentsong()
                    shared_data['status'] = status
                    debug(shared_data = shared_data)
                except Exception as e2:
                    debug(E2 = e2)
                    logger("E2: " + str(e2), 'error')
                    logger(traceback.format_exc(), 'error')
                    logging.error("E2: " + str(e2))
                    if os.getenv('DEBUG') == '1':print("E 2:", make_colors(str(e2), 'lw', 'bl'), f"{make_colors(host, 'b', 'ly')}:{make_colors(port, 'b', 'lc')}")
                    if os.getenv('traceback') == '1': logging.error(traceback.format_exc())
                    if os.getenv('traceback') == '2': print(make_colors(traceback.format_exc(), 'lw', 'm'))
            time.sleep(5)

class LastFM(object):
    CONFIGNAME = str(Path(__file__).parent / 'ticker.ini')
    CONFIG = configset(CONFIGNAME)

    @classmethod
    def search_track(self, artist, track):
        logger("LastFM: search_track -> start")
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
            logger(f"LastFM: result: {data['results']['trackmatches']['track'][0]}")
            return data['results']['trackmatches']['track'][0]
        else:
            return None

    @classmethod
    def get_track_info(self, artist, track):
        logger(f"LastFM: get_track_info")
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
                logger(f"LastFM: get_track_info -> result: {album_info}")
                return {
                    'album_name': album_info['title'],
                    'album_url': album_info['url'],
                    'album_image': album_info['image'][-1]['#text'] if album_info['image'] else None
                }

        data_return = {
            'album_name': '',
            'album_url': '',
            'album_image': str(Path(__file__).parent / 'default_cover.png')
        }
        logger(f"LastFM: get_track_info -> result: {data_return}")
        return data_return

class Normalization:
    
    @classmethod
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
        logger(f"Normalization: {name0} -> {name}")
        return name
    

class MPD(MPDClient):
    def __init__(self, host='localhost', port=6600):
        super().__init__()  # Initialize the parent MPDClient class
        self.CONFIGFILE = str(Path(__file__).parent / "ticker.ini")
        self.CONFIG = configset(self.CONFIGFILE)
        logger(f"MPD: CONFIGFILE: {self.CONFIGFILE}")
        
        self.HOST = os.getenv('MPD_HOST') or self.CONFIG.get_config('mpd', 'host', '127.0.0.1')
        logger(f"MPD: HOST: {self.HOST}")
        self.PORT = os.getenv('MPD_PORT') or self.CONFIG.get_config('mpd', 'port', 6600)
        logger(f"MPD: PORT: {self.PORT}")
        self.CONFIGFILE_NEXT = str(Path(__file__).parent / Normalization.normalization_name(self.HOST.strip()).replace(".", "_")) + ".ini"
        logger(f"MPD: CONFIGFILE_NEXT: {self.CONFIGFILE_NEXT}")
        self.CONFIG = configset(self.CONFIGFILE_NEXT)
        
        self.connect_to_server()

    def connect_to_server(self):
        while True:
            try:
                self.connect(self.HOST, self.PORT)
                print("Connected to MPD server.")
                break
            except ConnectionRefusedError:
                print("Connection refused. Retrying in 1 second...")
                time.sleep(1)
            except:
                print(make_colors(traceback.format_exc(), 'lw', 'r'))

    @staticmethod
    def connection_check1(fn):
        def wrapper(self, *args, **kwargs):
            def try_connect():
                while True:
                    try:
                        self.connect(self.HOST, self.PORT)
                        print("Reconnected to MPD server.")
                        #self.update_song_info()
                        #self.update_image()
                        break
                    except Exception as e:
                        print(f"Reconnection attempt failed: {e}")
                        #self.update_song_info_initialize_clear()
                        self.root.after(1000, try_connect)  # Retry connection every second
                        if os.getenv('TRACEBACK') == '1':
                            print(make_colors("ERROR [2]:", 'lw', 'r') + " " + make_colors(traceback.format_exc(), 'lw', 'r'))
                        else:
                            print(make_colors("ERROR [1]:", 'lw', 'r') + " " + make_colors(str(e), 'lw', 'r'))
                        if str(e) == 'Already connected': self.disconnect()                        
                        break  # Exit the while loop, the next attempt will be scheduled

            while True:  # Keep trying to call the function until successful
                try:
                    return fn(self, *args, **kwargs)
                except Exception as e:
                    ep = e
                    print(f"Connection lost: {ep}")
                    if str(ep) == 'Already connected':
                        try:
                            self.currentsong()
                            break
                        except:
                            print(make_colors("ERROR [0]:", 'lw', 'r') + " " + make_colors(traceback.format_exc(), 'lw', 'r'))
                    
                    print("Connection lost. Reconnecting...")                                            
                    #self.update_song_info_initialize_clear()
                    self.root.after(1000, try_connect)  # Start reconnect attempts
                    break  # Exit the while loop, the next attempt will be scheduled
        return wrapper
    
    @staticmethod
    def connection_check(fn):
        def wrapper(self, *args, **kwargs):
            debug(args = args)
            debug(kwargs = kwargs)
            while True:  # Keep trying to call the function until successful
                try:
                    debug(fn = fn)
                    debug(fn__name__0 = fn.__name__)
                    debug(dir_fn = dir(fn))
                    debug(args = args)
                    debug(kwargs = kwargs)
                    self.status = ''
                    return fn(self, *args, **kwargs)
                #except (mpd.ConnectionError, BrokenPipeError):
                except Exception as e:
                    self.status = 'error'
                    debug(fn__name__1 = fn.__name__)
                    #if fn.__name__ in ['update_song_info', 'update_text_on_canvas']:
                        #self.status == 'error'
                        #fn(self, *args, **kwargs)()
                    ep = e
                    while True:
                        if str(ep) == 'Already connected':
                            try:
                                self.currentsong()
                                self.status = ''
                                break
                            except:
                                print(make_colors("ERROR [0]:", 'lw', 'r') + " " + make_colors(traceback.format_exc(), 'lw', 'r'))
                        print("Connection lost. Reconnecting...")                        
                        try:
                            self.connect(self.HOST, self.PORT)
                            self.status = ''
                            print("Reconnected to MPD server.")
                            break  # Exit inner loop once reconnected
                        except Exception as e:
                            if os.getenv('TRACEBACK') == '1':
                                print(make_colors("ERROR [2]:", 'lw', 'r') + " " + make_colors(traceback.format_exc(), 'lw', 'r'))
                            else:
                                print(make_colors("ERROR [1]:", 'lw', 'r') + " " + make_colors(str(e), 'lw', 'r'))
                            if str(e) == 'Already connected':
                                self.disconnect()
                        time.sleep(1)
        return wrapper

class Music:
    def __init__(self, host='localhost', port=6600):
        self.client = MPD(host, port)
        
    @MPD.connection_check
    def currentsong(self):
        return self.client.currentsong()  # Directly call currentsong on the MPD instance        
        
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MINMAXINFO(ctypes.Structure):
    _fields_ = [("ptReserved", POINT),
                ("ptMaxSize", POINT),
                ("ptMaxPosition", POINT),
                ("ptMinTrackSize", POINT),
                ("ptMaxTrackSize", POINT)]

class Ticker:
    
    def __init__(self, root = '', text=" Welcome to the MPD ticker! "):
        self.manager = Manager()
        self.shared_data = self.manager.dict()
        self.shared_data['current_song'] = None
        
        self.client = MPDClient()
        self.timer_id = None
        self.CONFIGFILE = str(Path(__file__).parent / "ticker.ini")
        self.CONFIG = configset(self.CONFIGFILE)
        
        self.last_song = self.CONFIG.get_config('last', 'song')
        self.last_artist = self.CONFIG.get_config('last', 'artist')
        self.last_album = self.CONFIG.get_config('last', 'album')
        
        self.HOST = os.getenv('MPD_HOST') or self.CONFIG.get_config('mpd', 'host', '127.0.0.1') or '127.0.0.1'
        logger(f"Ticker: HOST: {self.HOST}")
        self.PORT = os.getenv('MPD_PORT') or self.CONFIG.get_config('mpd', 'port', 6600) or 6600
        logger(f"Ticker: PORT: {self.PORT}")
        self.timeout = os.getenv('MPD_TIMEOUT') or self.CONFIG.get_config('mpd', 'timeout', 3) or 3
        logger(f"Ticker: timeout: {self.timeout}")
        self.CONFIGFILE_NEXT = str(Path(__file__).parent / self.normalization_name(self.HOST.strip()).replace(".", "_")) + ".ini"
        logger(f"Ticker: CONFIGFILE_NEXT: {self.CONFIGFILE_NEXT}")
        logging.warning(f"Ticker: CONFIGFILE_NEXT: {self.CONFIGFILE_NEXT}")
        self.CONFIG = configset(self.CONFIGFILE_NEXT)
        
        debug(self_HOSTNAME = self.HOST)
        debug(self_PORT = self.PORT)
        
        if not self.HOST in ['127.0.0.1', 'localhost', '1::']:
            print(f'{make_colors("connect to server", "ly")} {make_colors(self.HOST, "lc")}:{make_colors(self.PORT, "lr")}')
            
        self.client.connect(self.HOST, self.PORT, self.timeout)
                
        #self.process = Process(target=self.connection_watch)
        #self.process.start()
        #self.queue = queue.Queue()
        self.N = 0
        
        self.notify = notify('MPD-Ticker', ['New Song'])
        
        self.current_song = None
        self.last_current_song = None
        
        self.status = ''
        self.status_str = ''
        
        self.is_first = True
        
        self.process = Process(target=connection_watch, args=(self.shared_data, self.HOST, self.PORT, self.timeout))
        self.process.start()        
        
        if root:
            self.root = root or tk.Tk()
            self.root.withdraw()
            #self.root.overrideredirect(True)  # Remove window decorations
            self.root.attributes("-topmost", True)  # Keep window on top initially
            self.root.attributes("-alpha", self.CONFIG.get_config('transparent', 'level', 60) / 100)
            #self.root.attributes("-toolwindow", False)  # Ensure the window appears in the taskbar
            self.root.title(f"MPD Ticker [{self.HOST if not self.HOST in ['127.0.0.1', 'localhost', '::1'] else ''}]")  # Set a title for the window            
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
            self.canvas = tk.Canvas(self.frame, background=self.CONFIG.get_config('color', 'background', "#353535"), highlightthickness=0, borderwidth=0, width=600, height=53)
            self.canvas.pack(fill=tk.BOTH, expand=True)
        
            self.x = 0  # Starting position of the text
            self.ticker_job = self.root.after(50, self.update_ticker)  # Start the ticker
        
            # Initialize MPD client
            #self.connect_to_mpd()
            
            icon = self.set_icon()
            if os.path.isfile(icon):
                self.icon_image = Image.open(icon)
                self.icon = ImageTk.PhotoImage(self.icon_image)
                self.root.iconphoto(True, self.icon)
            
            self.update_song_info()
            
            self.bind_keys()
            
            self.root.update_idletasks()
            
            self.hwnd = int(self.root.wm_frame(), 16)
            self.set_borderless(self.hwnd)
            self.root.deiconify()
            
    def set_borderless(self, hwnd):
        #hwnd = int(self.root.wm_frame(), 16)  # Get the window handle
        hwnd = int(self.root.wm_frame(), 16)  # Get the window handle
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)  # Get current window style
        style = style & ~(win32con.WS_CAPTION | win32con.WS_MAXIMIZEBOX | win32con.WS_MINIMIZEBOX | win32con.WS_THICKFRAME)
        
        x = int(self.CONFIG.get_config('geometry', 'x') or 100)
        debug(x_3 = x)
        y = int(self.CONFIG.get_config('geometry', 'y') or 100)
        debug(y_3 = y)
        w = int(self.CONFIG.get_config('geometry', 'width') or 450)
        debug(w_3 = w)
        h = int(self.CONFIG.get_config('geometry', 'height') or 53)
        debug(h_3 = h)
        
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)  # Apply the new style
        win32gui.SetWindowPos(hwnd, None, x, y, w, h,
                              win32con.SWP_NOMOVE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)

        # Hook the window procedure to handle messages
        self.old_window_proc = win32gui.SetWindowLong(hwnd, win32con.GWL_WNDPROC, self.window_proc)
        
    def window_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_GETMINMAXINFO:
            info = MINMAXINFO.from_address(lparam)
            max_height = int(self.CONFIG.get_config('geometry', 'height') or 53)  # Load max height from config
            debug(max_height = max_height)
            info.ptMaxTrackSize.y = max_height
            return 0
        return win32gui.CallWindowProc(self.old_window_proc, hwnd, msg, wparam, lparam)
        
    def set_icon(self):
        # Open the PNG image
        png_image = Image.open(str(Path(__file__).parent / 'ticker.png'))
        
        # Convert to GIF (if transparency is not an issue)
        gif_image = png_image.convert('RGB')  # or 'RGBA' if transparency is needed
        
        # Save as GIF format
        gif_image.save(str(Path(__file__).parent / 'ticker.gif'))
        
        return str(Path(__file__).parent / 'ticker.gif')
        
            
    def bind_keys(self): 
        self.root.bind('<Escape>', self.quit_or_close_child)
        self.root.bind('<q>', self.quit_or_close_child)
        self.root.bind('<x>', self.quit_or_close_child)        
        
        self.root.bind('<s>', self.show_full_image)
        
        self.root.bind('<p>', self.play)        
        self.root.bind('<Shift-P>', self.pause)        
        self.root.bind('<n>', self.next)
        self.root.bind('<Shift-N>', self.previous)        
    
        # Bind keys to toggle always on top
        self.root.bind('a', self.set_always_on_top)
        self.root.bind('<Shift-A>', self.set_normal)
    
        # Bind window movement to save position
        #self.root.bind('<Configure>', self.save_position)
    
        # Bind mouse events for dragging
        self.canvas.bind("<Button-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)        
                
        
    def connect(self, host = None, port = None, timeout = 5):
        host = host or self.HOST
        port = port or self.PORT
        
        debug(host = host)
        debug(port = port)
        
        if isinstance(port, str) and str(port).isdigit(): port = int(port)
        if not str(port).isdigit(): port = 6600
        
        self.client.connect(host, port, timeout)
        return self.client
    
    def disconnect(self):
        return self.client.disconnect()
    
    @MPD.connection_check
    def play(self, event):
        #try:
        self.client.play()
        #except:
            #self.connect_to_mpd()
    
    @MPD.connection_check
    def pause(self, event):
        #try:
        self.client.pause()
        #except:
            #self.connect_to_mpd()
    
    @MPD.connection_check
    def next(self, event):
        #try:
        self.client.next()
        #except:
            #self.connect_to_mpd()
    
    @MPD.connection_check
    def previous(self, event):
        #try:
        self.client.previous()
        #except:
            #self.connect_to_mpd()
                    
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
    
    def connection_watch1(self):
        global current_song
        while True:
            try:
                print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} [{make_colors('Connection Watch', 'lw', 'm')}] {make_colors('Start connecting ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
                #self.client.connect(os.getenv('MPD_HOST') or self.CONFIG.get_config('mpd', 'host', '127.0.0.1'), int(os.getenv('MPD_PORT', 6600)) or self.CONFIG.get_config('mpd', 'port', 6600))
                self.connect(timeout=3)
                status = self.client.status()
                print(status)
                self.current_song = self.client.currentsong()
                #current_song = self.current_song
            #except Exception as e:
                #self.status = 'error'
                #try:
                    #self.client.disconnect()
                #except:
                    #pass
                #self.client.connect(os.getenv('MPD_HOST') or self.CONFIG.get_config('mpd', 'host', '127.0.0.1'), int(os.getenv('MPD_PORT', 6600)) or self.CONFIG.get_config('mpd', 'port', 6600))
            except Exception as e:
                print("E 0:", make_colors(str(e), 'lw', 'm'))
                self.status = 'error'
                if str(e) == 'Already connected':
                    try:
                        self.current_song = self.client.currentsong()
                        #current_song = self.current_song
                        self.status = ''
                        status = self.client.status()
                        print(status)                        
                    except Exception as e:
                        print("E 1:", make_colors(str(e), 'lw', 'm'))
                        try:
                            self.disconnect()
                            self.connect(timeout=3)
                            status = self.client.status()
                            print(status)                            
                            self.current_song = self.client.currentsong()
                            #current_song = self.current_song                            
                            self.status = ''
                        except:
                            self.status = 'error'
                else:
                    try:
                        self.connect(timeout=3)
                        status = self.client.status()
                        print(status)                        
                        self.status = ''
                        self.current_song = self.client.currentsong()
                        #current_song = self.current_song
                    except Exception as e:
                        print("E 2:", make_colors(str(e), 'lw', 'm'))
                        self.status = 'error'
                        
            time.sleep(self.CONFIG.get_config('watch', 'sleep', '5'))
            
    def connect_to_mpd(self):
        while 1:
            print(make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly') + " " +  make_colors("check process background [1]:", 'lw', 'm') + " " + make_colors(str(self.process.is_alive()), 'lw', 'r'))
            #if not self.process.is_alive():
                #self.process.start()            
            try:
                self.client.connect(os.getenv('MPD_HOST') or self.CONFIG.get_config('mpd', 'host', '127.0.0.1'), int(os.getenv('MPD_PORT', 6600)) or self.CONFIG.get_config('mpd', 'port', 6600))
                status = self.client.status()
                #print(status)
                break
            except Exception as e:
                if str(e) != 'Already connected':
                    print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('Could not connect to MPD', 'lw','r')} {make_colors('[1]', 'b', 'ly')}: {make_colors(e, 'lw','r')}")
                if os.getenv('traceback') == '1': print(traceback.format_exc())                    
                try:
                    print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('Try get current song ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
                    self.client.currentsong()
                except:
                    print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('ERROR', 'lw', 'r')} {make_colors('Try get current song ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
                    try:
                        print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('Try disconnecting ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
                        self.client.disconnect()
                    except:
                        print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('ERROR', 'lw', 'r')} {make_colors('Try disconnecting ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
                        if os.getenv('traceback') == '1': print(traceback.format_exc())
                    try:
                        print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('Try re-Connecting ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
                        self.client.connect(os.getenv('MPD_HOST') or self.CONFIG.get_config('mpd', 'host', '127.0.0.1'), int(os.getenv('MPD_PORT', 6600)) or self.CONFIG.get_config('mpd', 'port', 6600))
                        print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('SUCCESS', 'b', 'y')} {make_colors('Try disconnecting ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
                        break
                    except Exception as e:
                        print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('ERROR', 'lw', 'r')} {make_colors('Try re-Connecting ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
                        print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('Could not connect to MPD', 'lw','r')} {make_colors('[2]', 'b', 'ly')}: {make_colors(e, 'lw','r')}")
            print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('ERROR', 'lw', 'r')} {make_colors(f'Sleeping for ', 'lw','bl')} {make_colors(self.CONFIG.get_config('reconnection', 'sleep', '1') or 1,  'lw', 'r')} seconds ... {make_colors('[1]', 'b', 'ly')}")
            time.sleep(self.CONFIG.get_config('reconnection', 'sleep', '1') or 1)

    def load_position(self):
        x = self.CONFIG.get_config('geometry', 'x') or 100
        debug(x_1 = x)
        y = self.CONFIG.get_config('geometry', 'y') or 100
        debug(y_1 = y)
        w = self.CONFIG.get_config('geometry', 'width') or 450
        debug(w_1 = w)
        h = self.CONFIG.get_config('geometry', 'height') or 53
        debug(h_1 = h)                
        if x and y and w and h:
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        else:
            self.root.geometry("500x45+100+100")  # Default position and size

    def save_position(self): #, event=None):
        #if event:
        x = self.root.winfo_x()
        debug(x_2 = x)
        y = self.root.winfo_y()
        debug(y_2 = y)
        width = self.root.winfo_width()
        debug(w_2 = width)
        height = self.root.winfo_height()
        
        #if width > (self.CONFIG.get_config('geometry', 'width') or 400):
            #width -= 16
        #elif width < (self.CONFIG.get_config('geometry', 'width') or 400):
            #width = self.CONFIG.get_config('geometry', 'width')        
        
        #if height > (self.CONFIG.get_config('geometry', 'height') or 53):
            #height -= 39
        #elif height < (self.CONFIG.get_config('geometry', 'height') or 53):
            #height = self.CONFIG.get_config('geometry', 'height')
        
        debug(h_2 = height)
        self.CONFIG.write_config('geometry', 'x', x)
        self.CONFIG.write_config('geometry', 'y', y)
        #self.CONFIG.write_config('geometry', 'width', width)
        #self.CONFIG.write_config('geometry', 'height', height)

    #@MPD.connection_check   
    def write_canvas(self, text, image_width, host_str):
        # Adjust text coordinates to place it to the left of the resized image with more compact spacing
        self.canvas.create_text(image_width + 20, 10, text=text + self.status_str + host_str, fill=self.title_color, font=self.title_font, anchor='nw', tags="text")
        self.canvas.create_text(image_width + 20, 23, text=text, fill=self.album_color, font=self.album_font, anchor='nw', tags="text")
        self.canvas.create_text(image_width + 20, 35, text=text, fill=self.artist_color, font=self.artist_font, anchor='nw', tags="text")                    
    
    def update_text_on_canvas(self, image_width):
        debug(self_status = self.status)
        host_str = ''
        if not self.HOST in ['127.0.0.1', 'localhost', '1::']: host_str = f" [{self.HOST}]"
        #status_str = ''
        debug(self_status_str = self.status_str)
        if self.status == 'error':
            self.status_str = ' [disconnected]'
        else:
            if self.shared_data.get('status'):
                self.status_str = ' [' + self.shared_data['status'].get('state') + ']'
                if self.status_str == 'play': self.status_str = ''
        #else:
            #if not self.status_str:
                #try:
                    #status = self.client.status()
                    #if status.get('state') != 'play': self.status_str = ' [pause]'
                #except:
                    #status = {}
                    #self.status_str = self.status_str
            
        debug(self_status_str = self.status_str)
        #if not self.current_song and not self.status == 'error':
            #self.current_song = self.client.currentsong()
            
        debug(self_status = self.status)
        debug(self_current_song = self.current_song)
        
        debug(host_str = host_str)        
        # Ensure the text is overlayed on the image
        if self.status in ['error', 'disconnect']:
            self.canvas.delete("text")
            
        else:
            if self.current_song:                    
                debug(self_current_song_title = self.current_song.get('title'))
                debug(self_last_song = self.last_song)            
                #if self.current_song.get('title') != self.last_song:
                self.canvas.delete("text")
                # Adjust text coordinates to place it to the left of the resized image with more compact spacing
                self.canvas.create_text(image_width + 20, 10, text=self.current_song.get('title', 'Unknown Title') + self.status_str + host_str, fill=self.title_color, font=self.title_font, anchor='nw', tags="text")
                self.canvas.create_text(image_width + 20, 23, text=f"Album: {self.current_song.get('album', 'Unknown Album')} ({self.current_song.get('date', 'Unknown Year')})", fill=self.album_color, font=self.album_font, anchor='nw', tags="text")
                self.canvas.create_text(image_width + 20, 35, text=f"Artist: {self.current_song.get('artist', 'Unknown Artist')}", fill=self.artist_color, font=self.artist_font, anchor='nw', tags="text")
            else:
                self.canvas.delete("text")
                # Adjust text coordinates to place it to the left of the resized image with more compact spacing
                self.canvas.create_text(image_width + 20, 10, text='disconnected' + self.status_str + host_str, fill=self.title_color, font=self.title_font, anchor='nw', tags="text")
                self.canvas.create_text(image_width + 20, 23, text='disconnected', fill=self.album_color, font=self.album_font, anchor='nw', tags="text")
                self.canvas.create_text(image_width + 20, 35, text='disconnected', fill=self.artist_color, font=self.artist_font, anchor='nw', tags="text")                            
    
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
        #if self.current_song and self.current_song.get('title') != self.last_song:
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
        name = name.strip()
        if not name:
            return ''
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

    #@MPD.connection_check
    def find_cover_art(self):
        current_song = None
        if self.status == 'error':
            return str(Path(__file__).parent / 'no_cover.png')
        try:
            current_song = self.shared_data['current_song'] or self.client.currentsong()
        except:
            pass
        debug(current_song = current_song)
        if current_song:
            temp_dir = str(Path(os.getenv('temp', '/tmp')) / Path('cover') / Path((self.normalization_name(current_song.get('artist')) or 'Unknown Artist')))
            if not os.path.isdir(temp_dir):
                os.makedirs(temp_dir)
            logging.info(f"music_dir = {self.CONFIG.get_config('mpd', 'music_dir')}")
            logging.info(f"music file = {current_song.get('file')}")
            if self.CONFIG.get_config('mpd', 'music_dir'):
                cover_found = None
                for cover_name in ['cover.jpg', 'cover.png', 'cover.jpeg', 'cover.bmp', 'folder.jpg', 'folder.png', 'folder.bmp', 'folder.jpeg', 'Cover.jpg', 'Cover.png', 'Cover.jpeg', 'Cover.bmp', 'Folder.jpg', 'Folder.png', 'Folder.bmp', 'Folder.jpeg']:
                    if os.path.isfile(os.path.join(self.CONFIG.get_config('mpd', 'music_dir'), os.path.dirname(current_song.get('file')), cover_name)):
                        cover_found = os.path.join(self.CONFIG.get_config('mpd', 'music_dir'), os.path.dirname(current_song.get('file')), cover_name)
                        logging.info(f"cover_found = {cover_found}")
                        break
                if cover_found:
                    print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('use cover [3]:', 'lw', 'm')} {make_colors(cover_found, 'b','y')}")
                    return cover_found
                           
            elif os.path.isfile(str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title')) + ".jpg"))):
                print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('use cover [1]:', 'lw', 'm')} {make_colors(str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title')) + '.jpg')), 'b','y')}")
                debug(cover = str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title')) + ".jpg")))
                return str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title')) + ".jpg"))
            elif os.path.isfile(str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title')) + ".png"))):
                print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('use cover [2]:', 'lw', 'm')} {make_colors(str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title')) + '.png')), 'b','y')}")
                debug(cover = str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title')) + ".png")))
                return str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title')) + ".png"))
            #except Exception as e:
                #if str(e) == 'Already connected':
                    #self.client.disconnect()
                #self.connect_to_mpd()
                #return self.find_cover_art()
    
            try:
                #current_song = self.client.currentsong()
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
                        temp_path = str(Path(temp_dir) / Path((self.normalization_name(current_song.get('title')) or 'No Title') + (ext or ".jpg")))
                        debug(temp_path = temp_path)
                        with open(temp_path, 'wb') as img_file:
                            img_file.write(picture.get('binary'))
                        print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('use cover [3]:', 'lw', 'm')} {make_colors(temp_path, 'b','y')}")
                        debug(cover = temp_path)
                        return temp_path
    
            except Exception as e:
                print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('No embedded cover art found:', 'lw', 'bl')} {make_colors(e, 'lw', 'r')}")

            cover = deezer_art.get_album_art(current_song.get('artist'), current_song.get('title'), current_song.get('album'), True)
            if not cover:
                return self.find_cover_art_lastfm(current_song)
            else:
                print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} {make_colors('use cover [4]:', 'lw', 'm')} {make_colors(cover, 'b','y')}")
                return cover
        
        return str(Path(__file__).parent / 'no_cover.png')
    
    def find_cover_art_lastfm(self, data=None, to_file = True):
        print(make_colors("start get LastFM cover ...", 'lw', 'r'))
        max_try = 2
        n = 0
        def get_image(url):
            while 1:
                try:
                    a = requests.get(url, stream = True)
                    break
                except:
                    time.sleep(1)
                if n == max_try:
                    break
                else:
                    n += 1
            
            return a.content
        
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

        temp_dir = str(Path(os.getenv('temp', '/tmp')) / Path('cover') / Path((self.normalization_name(artist) or 'Unknown Artist')))
        if not os.path.isdir(temp_dir):
            os.makedirs(temp_dir)
        debug(temp_dir = temp_dir)
        if artist and album:
            #url = f"http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={api_key}&artist={quote(artist)}&album={quote(album)}&format=json"
            url = f"http://ws.audioscrobbler.com/2.0/"
            params = {
                'method': 'album.getinfo',
                'api_key': api_key,
                'artist': quote(artist),
                'album': quote(album),
                'format': 'json',
            }
            a = requests.get(url, params = params)
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
            cover_url = cover_from_lastfm.get('album_image')
            debug(cover_url = cover_url)
            debug(to_file = to_file)
            cover_file = str(Path(__file__).parent / 'no_cover.png')
            if cover_url and to_file:
                print(make_colors("LastFM Cover writing ...", 'b', 'y'))
                cover_file = os.path.join(temp_dir, self.normalization_name(title) + (os.path.splitext(cover_url)[-1] or ".jpg"))
                with open(cover_file, 'wb') as cover_data:
                    cover_data.write(get_image(cover_url))
                    debug(cover_file_name = cover_data.name)
                    print(make_colors("LastFM Cover writing finish", 'b', 'ly'))
                    cover_file = cover_data.name
                    
            debug(cover_file = cover_file)   
            if to_file:
                return cover_file
            return cover_url
        return ''
                    
    #@MPD.connection_check
    def update_song_info(self):
        self.current_song = self.shared_data['current_song']
        debug(self_status_str = self.status_str)
        
        if not self.status_str:
            try:
                status = self.shared_data['status'] or self.client.status()
                debug(status = status)
                if status.get('state') != 'play': self.status_str = ' [pause]'
            except:
                status = {}
                self.status_str = self.status_str
        
        debug(self_status_str = self.status_str)
        host_str = ''
        if not self.HOST in ['127.0.0.1', 'localhost', '1::']: host_str = f" [{self.HOST}]"
        debug(host_str = host_str)
        debug(self_status = self.status)
        debug(self_current_song = self.current_song)
        debug(self_last_song = self.last_song)
        debug(self_process_is_alive = self.process.is_alive())
        
        if self.status == 'error' or not self.current_song:
            self.canvas.delete("text")
            self.canvas.create_text(10, 10, text=f"{self.last_song}" + host_str, fill=self.title_color, anchor='nw', tags="text")
            self.canvas.create_text(10, 30, text=f"Album: {self.last_album}", fill=self.album_color, anchor='nw', tags="text")
            self.canvas.create_text(10, 50, text=f"Artist: {self.last_artist}", fill=self.artist_color, anchor='nw', tags="text")
            
            self.update_image(str(Path(__file__).parent / 'no_cover.png'))
                        
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
                self.timer_id = None
            
            self.status = '' 
            #self.notify.send(title = 'MPD Ticker [disconnected] ' , message = "---- DISCONNECTED ... \n", icon = str(Path(__file__).parent / 'no_cover.png'))
            #self.timer_id_error = self.root.after(10000, self.update_song_info)  # Update every 10 seconds                        
            #elif not self.status:
                #self.notify.send(title = 'MPD Ticker ---- initializing ... ' , message = "---- initializing ... \n", icon = str(Path(__file__).parent / 'no_cover.png'))
                #self.status = 'initialize'
                #self.timer_id_error = self.root.after(10000, self.update_song_info)  # Update every 10 seconds        

        else:
            debug(self_current_song = self.current_song)
            debug(self_last_current_song = self.last_current_song)
            debug(self_last_song = self.last_song)
            debug(self_status_str = self.status_str)
            
            if self.current_song and not self.current_song == self.last_current_song:
                self.last_current_song = self.current_song
                self.status = ""
                self.last_song = self.current_song.get('title')
                self.CONFIG.write_config('last', 'song', self.current_song.get('title'))
                
                self.last_album = self.current_song.get('album')
                self.CONFIG.write_config('last', 'song', self.current_song.get('album'))
                
                self.last_artist = self.current_song.get('artist')
                self.CONFIG.write_config('last', 'song', self.current_song.get('artist'))
                
                debug(self_status_str = self.status_str)
                debug(self_current_song = self.current_song)
                debug(self_last_song = self.last_song)                
                
                self.last_current_song = self.current_song
                self.canvas.delete("text")
                self.canvas.create_text(10, 10, text=self.current_song.get('title', 'Unknown Title') + self.status_str + host_str, fill=self.title_color, anchor='nw', tags="text")
                self.canvas.create_text(10, 30, text=f"Album: {self.current_song.get('album', 'Unknown Album')} ({self.current_song.get('date', 'Unknown Year')})", fill=self.album_color, anchor='nw', tags="text")
                self.canvas.create_text(10, 50, text=f"Artist: {self.current_song.get('artist', 'Unknown Artist')}", fill=self.artist_color, anchor='nw', tags="text")
                self.update_image()
                
                value_kwargs = {
                    "app": 'MPD-Ticker',
                    'event': ['New Song'],
                    "title": 'MPD Ticker' + host_str + self.status_str,
                    'message': f"{self.current_song.get('title')}\n{self.current_song.get('album')}\n{self.current_song.get('artist')}\n",
                    'icon': self.find_cover_art()
                }
                
                value = Process(target = self.notify.send, kwargs = value_kwargs)
                setattr(self, f'process_{self.N}', value)
                eval(f"self.process_{self.N}.start()")
                self.N += 1
                
                #self.notify.send(title = 'MPD Ticker' + host_str + status_str, message = f"{song.get('title')}\n{song.get('album')}\n{song.get('artist')}\n", icon = self.find_cover_art())
        
        if self.is_first:
            self.timer_id = self.root.after(1000, self.update_song_info)  # Update every 10 seconds
            if not self.current_song in [{}, None, ""]:
                self.is_first = False
        else:
            self.timer_id = self.root.after(10000, self.update_song_info)  # Update every 10 seconds
            
    def update_image(self, picture_path = None):
        debug(picture_path = picture_path)
        debug(self_status = self.status)
        if self.status == 'error':
            picture_path = str(Path(__file__).parent / 'no_cover.png')
            debug(picture_path = picture_path)
            #self.original_image = Image.open(picture_path)
            #self.resize_image_to_text_height()
        else:
            try:
                picture_path = self.find_cover_art()
            except Exception as e:
                print("E 2:", make_colors(str(e), 'lw', 'r'))
                if os.getenv('traceback') == '1': print(make_colors(traceback.format_exc(), 'lw', 'bl'))
                picture_path = str(Path(__file__).parent / 'no_cover.png')
            debug(picture_path = picture_path)
            #self.original_image = Image.open(picture_path)
            #self.resize_image_to_text_height()
            
        try:
            self.original_image = Image.open(picture_path)
            self.resize_image_to_text_height()
        except Exception as e:
            print("E 3: Error opening image:", make_colors(str(e), 'lw', 'r'))
            self.original_image = Image.open(str(Path(__file__).parent / 'no_cover.png'))
            self.resize_image_to_text_height()
            
    def read_picture(self):
        # Implement this function to read the picture associated with the current song
        return "icon.png"  # Replace with actual picture path

    def quit(self, event=None):
        self.save_position()  # Save position on quit
        print(make_colors("quit ...............", 'lr'))
        try:
            self.process.terminate()
        except:
            pass
        
        for i in range(0, self.N + 1):
            try:
                eval(f"self.process_{i}.terminate()")
            except:
                pass
        try:
            self.client.disconnect()
        except:
            pass
        self.root.after_cancel(self.ticker_job)  # Cancel the scheduled update_ticker call
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
    
    #c = Music()
    #print("current song:", c.currentsong())
