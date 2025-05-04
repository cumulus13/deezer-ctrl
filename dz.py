import shutil   
import os
import sys
sys.path.insert(0, r"C:\PROJECTS\mpd_info_server")
from client import send_message
import json
import clipboard
from datetime import datetime
import asyncio
import traceback
import sqlite3
try:
    import deezer_art
except:
    pass
from urllib.parse import quote
# from rich import traceback as  rich_traceback
# rich_traceback.install(theme='fruity', max_frames=30, width=shutil.get_terminal_size()[0])
import ctraceback
sys.excepthook = ctraceback.CTraceback
from rich.panel import Panel
from rich.align import Align
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn
from textual import events, on
from textual.events import Key
from textual.app import App, ComposeResult
from textual.widgets import ProgressBar, Header, Footer, RichLog, DataTable, Static, Input, LoadingIndicator, Label
from textual.containers import ScrollableContainer, Container, Vertical, Horizontal
from textual.binding import Binding
#from asyncio import sleep
#from rich.live import Live
try:
    from .iit import display_image
except:
    from iit import display_image

try:
    from .qv import show as imshow
except:
    from qv import show as imshow

import re
import time
from mpd import MPDClient

from unidecode import unidecode
from configset import configset
from pathlib import Path
import mimetypes
from make_colors import make_colors
from multiprocessing import Process
import threading
import requests
from bs4 import  BeautifulSoup as bs
import gntp.notifier
import duckdb
import wikipediaapi
import base64
import logging
import bitmath
import importlib

try:
    from .deezer_ws import DeezerController as DeezerWs
except:
    from deezer_ws import DeezerController as DeezerWs

try:
    from .deezer import Deezer as DeezerController
except:
    from deezer import Deezer as DeezerController

DEBUG = False
APP = "Deezer"

from pydebugger.debug import debug

# if any('debug' in i.lower() for i in  os.environ):
#     from pydebugger.debug import debug
#     from jsoncolor import jprint
#     DEBUG = True
# else:
#     def debug(*args, **kwargs):
#         return
#     def jprint(*args, **kwargs):
#         return 

console = Console()

growl = gntp.notifier.GrowlNotifier(
    applicationName="MPD-N",
    notifications=["Playing", "Paused", "Stopped", "Next Song"],
    defaultNotifications=["Playing", "Paused", "Stopped", "Next Song"],
)
growl.register()

class ConfigMeta(type):
    def __new__(cls, name, bases, dct):
        # Go through all attributes of the new class
        for attr_name, attr_value in dct.items():
            if callable(attr_value):  # Check if the attribute is a method
                dct[attr_name] = classmethod(attr_value)
        return super().__new__(cls, name, bases, dct)

class MergedMeta(ConfigMeta, type):
    pass

class CONFIG(configset):
    CONFIGNAME = str(Path(__file__).parent / 'mpl.ini')
    config = configset(CONFIGNAME)
    client = MPDClient()
    client.timeout = config.get_config('host', 'timeout') or 30
    client.idletimeout = config.get_config('host', 'idletimeout') or 30

    HOSTNAME = config.get_config('host', 'name') or os.getenv('MPD_HOST') or '127.0.0.1'
    PORT =  config.get_config('host', 'port') or os.getenv('MPD_PORT') or 6600

    if PORT and not isinstance(PORT, int):
        if str(PORT).isdigit():
            PORT = int(PORT)
        else:
            PORT = 6600
    client.timeout = config.get_config('host', 'timeout') or 30
    client.idletimeout = config.get_config('host', 'idletimeout') or 30
    try:
        client.connect(HOSTNAME, PORT)
    except ConnectionRefusedError:
        console.print(f"[bold #00FFFF]{datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f')}[/] [#ffffff on #FF0000 blink]MPD Server is not running ![/]")
    except Exception as e:
        if __name__ == "__main__":
            console.print(f"[white on red blink] ERROR connect to MPD Server !:[/] [white on blue]{e}[/]")
            console.log(traceback.format_exc())

    def __init__(self):
        super().__init__(CONFIG.CONFIGNAME  )

console.log(f"CONFIG().get_config('database', 'type'): {CONFIG().get_config('database', 'type')}")
database = None

if CONFIG().get_config('database', 'type'):
    try:
        current_dir = str(Path(__file__).parent)
        
        # Load the module dynamically from the current directory
        spec = importlib.util.spec_from_file_location("database", os.path.join(current_dir, f"{CONFIG().get_config('database', 'type')}.py"))
        database = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(database)
    except:
        #logger.warning(traceback.format_exc())
        console.print_exception(theme = 'fruity', width = shutil.get_terminal_size()[0], max_frames = 30)
        
console.log(f"database: {database}")
Database = None
try:
    if database:
        Database = database.Database()
        console.log(f"Database: {Database}")
except:
    console.print_exception(theme = 'fruity', width = shutil.get_terminal_size()[0], max_frames = 30)

if not Database:    
    class Database:
        @classmethod
        def create_table(cls, *args, **kwargs) -> None:
            return
        
        @classmethod
        def insert(cls, *args, **kwargs) -> None:
            return
        
        @classmethod
        def update(cls, *args, **kwargs) -> None:
            return
        
        @classmethod
        def get(cls, *args, **kwargs) -> None:
            return

if os.getenv('LOGGING') == '1' and os.getenv('LOGGING_COLOR') == '1':
    try:
        from .logger import setup_logging, get_def
    except:
        from logger import setup_logging, get_def

    os.environ.update({'LOGGING_COLOR': '1',})
    print(f"LOGGING_COLOR: {os.getenv('LOGGING_COLOR')}")
    print(f"LOGGING: {os.getenv('LOGGING')}")
    if os.getenv('LOGGING_COLOR') == '1':
        setup_logging()
    else:
        if os.getenv('LOGGING') == '1':
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.CRITICAL)

    logger = logging.getLogger()
else:
    class logger:

        @staticmethod
        def debug(*args, **kwargs):
            log_file = str(Path(__file__).parent / 'mpl.log')
            max_size = CONFIG().get_config('log', 'max_size', '100')

            if not os.path.isfile(log_file):
                open(log_file, 'wb').close()
            else:
                if bitmath.getsize(log_file).MB.value > max_size: open(log_file, 'wb').close()
                with open(log_file, 'ab') as f:
                    for arg in args:
                        f.write(f'{datetime.strftime(datetime.now(), "%Y/%m/%d %H:%M:%S.%f")} {arg}\n'.encode())
            return None

        error = fatal = info = alert = warning = critical = emergency = notice = debug    

    logging.getLogger('mpd').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('urllib').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.basicConfig(level=logging.ERROR)

#class Logger:

    #def __init__(self, msg):
        #self.log(msg)

    #def log(self, msg):
        ##if not hasattr(msg, 'bytes'):
            ##msg = bytes(msg, encoding = 'utf-8')
        #file_log = str(Path(__file__).parent / 'mpl2.log')
        #if not os.path.isfile(file_log): open(file_log, 'wb').close()
        #with open(file_log, 'ab') as f:
            #f.write(bytes(f'{datetime.strftime(datetime.now(), "%Y/%m/%d %H:%M:%S.%f")} - {msg}\n', encoding = 'utf-8'))

class CONFIG_DUMP:

    @classmethod
    def get_config(cls, section = None, option = None, default = None):
        return default

    @classmethod
    def write_config(cls, section = None, option = None, default = None):
        return default
                
class CONFIG_DUMP:

    @classmethod
    def get_config(cls, section = None, option = None, default = None):
        return default

    @classmethod
    def write_config(cls, section = None, option = None, default = None):
        return default

class MPD(MPDClient):
    def __init__(self, host='localhost', port=6600):
        super().__init__()
        CONFIGFILE_NEXT = str(Path(__file__).parent / Normalization.normalization_name(self.HOST.strip()).replace(".", "_")) + ".ini"
        global CONFIG
        CONFIG = configset(CONFIGFILE_NEXT)

        self.connect_to_server()

    def connect_to_server(self):
        while True:
            try:
                self.connect(CONFIG().HOSTNAME, CONFIG().PORT)
                break
            except ConnectionRefusedError:
                time.sleep(1)
            except:
                console.log(traceback.format_exc())
                self.disconnect()

    @staticmethod
    def connection_check(fn):
        def wrapper(self, *args, **kwargs):
            while True:
                try:
                    return fn(self, *args, **kwargs)
                #except (mpd.ConnectionError, BrokenPipeError):
                except Exception as e:
                    ep = e
                    while True:
                        if str(ep) == 'Already connected':
                            try:
                                self.currentsong()
                                break
                            except:
                                self.disconnect()
                                if os.getenv('TRACEBACK') == '1':
                                    console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
                                else:
                                    console.log(f"[bold red]ERROR:[/][bold cyan]{e}[/]")
                        try:
                            self.connect(CONFIG().HOSTNAME, CONFIG().PORT)
                            break 
                        except Exception as e:
                            if os.getenv('TRACEBACK') == '1':
                                console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
                            else:
                                console.log(f"[bold red]ERROR:[/][bold cyan]{e}[/]")
                            #if str(e) == 'Already connected':
                            self.disconnect()
                        time.sleep(1)
        return wrapper

class MusicControl:
    
    def __init__(self, app = None, mpd_client = None, host = None, port = None, timeout = None):
        self.app = app
        self.client = mpd_client or CONFIG().client
        self.host = host or CONFIG().HOSTNAME or os.getenv('MPD_HOST') or CONFIG().get_config('host', 'name') or '127.0.0.1'
        self.port = port or CONFIG().PORT or os.getenv('MPD_CONFIG().PORT') or CONFIG().get_config('host', 'port') or 6600
        self.timeout = timeout
        debug(host = host)
        if host and not host == CONFIG().HOSTNAME and CONFIG().client:
            CONFIG().HOSTNAME = host
            debug(CONFIG_HOSTNAME = CONFIG().HOSTNAME)
            try:
                self.client.disconnect()
            except:
                pass
            try:
                self.client.connect(host, port or CONFIG().PORT, timeout or CONFIG().client.timeout)
            except Exception as e:
                if 'Already connected' in str(e):
                    pass
                else:
                    console.log(traceback.format_exc())
        self.process = None

    def reconnect(self, func, args = ()):
        if not isinstance(args, tuple): args = (args, )
        data = {}
        #debug(args = args)
        #debug(func = func)
        try:
            self.client.connect(self.host, self.port, self.timeout)
        except Exception as e:
            if 'Already connected' in str(e):
                pass
            else:
                console.log(traceback.format_exc())
        try:
            while 1:
                try:
                    data = getattr(self.client, func)(*args)
                    return data
                except:
                    if os.getenv('TRACEBACK') == "1": console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
                    try:        
                        if self.port and not isinstance(self.port, int): self.port = int(self.port) if str(self.port).isdigit() else 6600
                        self.client.connect(self.host, self.port)
                        data = getattr(self.client, func)(*args)
                        break
                    except Exception as e:
                        try:
                            self.client.disconnect()
                        except:
                            pass

                        if os.getenv('TRACEBACK') == "1": console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
                        console.print(f"[bold #00FFFF]{datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f')}[/] [#ffffff on #ff0000]Failed to re-connection to MPD Server !:[/] [black on #ffff00]{e}[/]")

                        try:
                            self.client.connect(self.host, self.port)
                            data = getattr(self.client, func)(*args)
                            break                        
                        except Exception as e:
                            console.print(f"[bold #00FFFF]{datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f')}[/] [#ffffff on #FF0000 blink]MPD Server error:[/] [black on #FFFF00]{e}[/]")
                            self.app.notify(str(e), title = f"{datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f')} MPD-N ERROR", timeout = 5, severity = "error")

                    time.sleep(1)
        except KeyboardInterrupt:
            console.print(f"[bold #00FFFF]{datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f')}[/] [#ffffff #FF00FF blink]Terminated[/]")
            sys.exit()

        return data

    async def reconnect_async(self, command):
        # Simulate an asynchronous operation
        await asyncio.sleep(1)  # Replace this with the actual asynchronous operation
        return self.reconnect(command)    

    def get_current_song(self):
        return self.reconnect('currentsong')

    def status(self):
        return self.reconnect('status')
    
    def playlist_info(self):
        return self.reconnect('playlistinfo')
        
    def diconnect(self):
        return self.client.disconnect()
    
    def normalization(self, text: list) -> list:
        pattern = r"\[\/?[a-zA-Z]+(?: #[0-9a-fA-F]{6})?\]|\[/\]"

        normal_text_list = [re.sub(pattern, '', text) for text in text]
        return normal_text_list

    def update_status(self):
        try:
            panel = self.app.query_one('#static_panel')
            panel.update_panel()
        except:
            logger.warning(traceback.format_exc())
            
    #@MPD.connection_check
    def play(self, number = None, force = False):
        debug("playing [control]")
        status = self.reconnect('status')
        if force:
            self.reconnect('play', (number, )) if number else self.reconnect('play')
        else:
            if status.get('state') == 'play':
                self.pause()
            else:
                self.reconnect('play', (number, )) if number else self.reconnect('play')
        self.update_status()

    #@MPD.connection_check    
    def pause(self):
        status = CONFIG().client.status()
        #song = client.currentsong()
        debug(status_for_pause = status)
        if status.get('state') == 'play':
            #logger.warning(f'''MPDNotify: Pausing : "{song['title']}" by "{song['artist']}" from "{song['album']}"''')
            self.update_status()
            return self.reconnect('pause')
        
    #@MPD.connection_check
    def stop(self):
        status = CONFIG().client.status()
        #song = client.currentsong()
        debug(status_for_pause = status)
        if status.get('state') == 'play':
            #logger.warning(f'''MPDNotify: Stoping : "{song['title']}" by "{song['artist']}" from "{song['album']}"''')
            self.update_status()
            return self.reconnect('stop')

    #@MPD.connection_check
    def next(self):
        status = CONFIG().client.status()
        debug(status_for_next = status)
        if not status.get('state') == 'play':
            self.reconnect('play')
        self.update_status()
        return self.reconnect('next')

    #@MPD.connection_check
    def previous(self):
        status = CONFIG().client.status()
        #song = client.currentsong()
        debug(status_previous = status)
        if not status.get('state') == 'play':
            #logger.warning(f'''MPDNotify: Playing : "{song['title']}" by "{song['artist']}" from "{song['album']}"''')
            self.reconnect('play')
        #logger.warning(f'''MPDNotify: Playing Previous : "{song['title']}" by "{song['artist']}" from "{song['album']}"''')
        self.update_status()
        return self.reconnect('previous')

    #@MPD.connection_check
    def seek(self):
        status = CONFIG().client.status()
        #song = client.currentsong()
        debug(status_previous = status)
        if not status.get('state') == 'play':
            #logger.warning(f'''MPDNotify: Playing : "{song['title']}" by "{song['artist']}" from "{song['album']}"''')
            self.reconnect('seek')
        #logger.warning(f'''MPDNotify: Playing Previous : "{song['title']}" by "{song['artist']}" from "{song['album']}"''')
        return self.reconnect('previous')

    #@MPD.connection_check
    def volume_up(self):
        data = self.reconnect('status')
        volume = CONFIG().get_config('volume', 'step') or 5
        if volume > 100: volume = 100
        if isinstance(data, dict) and data.get('volume'):
            volume = int(volume)
            self.reconnect('volume', (int(data.get('volume')) + volume, ))
        data = self.reconnect('status')

    #@MPD.connection_check
    def volume_down(self):
        data = self.reconnect('status')
        volume = CONFIG().get_config('volume', 'step') or 5
        if volume < 0: volume = 0
        if isinstance(data, dict) and data.get('volume'):
            volume = int(volume)
            self.reconnect('volume', (int(data.get('volume')) - volume, ))
        data = self.reconnect('status')

    #@MPD.connection_check
    def set_repeat(self):
        status = self.reconnect('status')
        if str(status.get('repeat')) == '1':
            self.reconnect('repeat', 0)
        else:
            self.reconnect('repeat', 1)

    #@MPD.connection_check
    def set_single(self):
        status = self.reconnect('status')
        if str(status.get('single')) == '1':
            self.reconnect('single', 0)
        else:
            self.reconnect('single', 1)

    #@MPD.connection_check
    def set_consume(self):
        status = self.reconnect('status')
        if str(status.get('consume')) == '1':
            self.reconnect('consume', 0)
        else:
            self.reconnect('consume', 1)

    #@MPD.connection_check
    def set_random(self):
        status = self.reconnect('status')
        if str(status.get('random')) == '1':
            self.reconnect('random', 0)
        else:
            self.reconnect('random', 1)

    def connect(self, host = None, port = None):
        host = host or CONFIG().HOSTNAME
        port = port or CONFIG().PORT

        debug(host = host)
        debug(port = port)

        if isinstance(port, str) and str(port).isdigit(): port = int(port)
        if not str(port).isdigit(): port = 6600

        #logger.info(f'MPDNotify: start connect to server: "{host}:{port}"')
        CONFIG().client.connect(host, port)
        #print("Connected to MPD server.")
        #logger.info(f'MPDNotify: Connected to MPD server: "{host}:{port}"')

        return CONFIG().client

    def disconnect(self):
        return CONFIG().client.disconnect()

    #@MPD.connection_check
    def find_cover_art_lastfm(self, artist = '', album = ''):
        #logger.info(f'MPDNotify: try to get cover from LastFM: "{artist}:{album}"')
        if not artist:
            current_song = self.reconnect('currentsong')
            artist = current_song.get('artist')
            album = current_song.get('album')
        debug(artist = artist)
        debug(album = album)

        if artist and album:
            if os.path.isfile(self.normalization_name(artist) + "_" + self.normalization_name(artist) + ".png"):
                #logger.warning(f'MPDNotify: use cover: "{self.normalization_name(artist) + "_" + self.normalization_name(artist) + ".png"}"')
                return self.normalization_name(artist) + "_" + self.normalization_name(artist) + ".png"

            elif os.path.isfile(self.normalization_name(artist) + "_" + self.normalization_name(artist) + ".jpg"):
                #logger.warning(f'MPDNotify: use cover: "{self.normalization_name(artist) + "_" + self.normalization_name(artist) + ".jpg"}"')
                return self.normalization_name(artist) + "_" + self.normalization_name(artist) + ".jpg"
            else:
                #logger.info(f'MPDNotify: start try to get cover from LastFM: "{artist}:{album}"')
                api_key = CONFIG().get_config('lastfm', 'api', "c725344c28768a57a507f014bdaeca79")
                url = f"http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={api_key}&artist={quote(artist)}&album={quote(album)}&format=json"
                debug(url = url)
                a = requests.get(url)
                if a.status_code == 200:
                    debug(responce = a.content)
                    try:
                        url1 = a.json()['album']['image'][-1]['#text']
                        if url1:
                            temp_path = str(Path(os.getenv('temp', '/tmp')) / Path(self.normalization_name(artist) + "_" + self.normalization_name(artist) + os.path.splitext(url1)[-1]))
                            with open(temp_path, 'wb') as f:
                                f.write(requests.get(url1).content)
                            #logger.warning(f'MPDNotify: use cover: "{temp_path}"')
                            return temp_path
                    except Exception as e:
                        print("failed to get cover art from LastFM:", e)
                        if os.getenv('TRACEBACK'):
                            console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
        return ''

    def normalization_name(self, name):
        if name:
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
            #logger.info(f"MPDNotify: normalization_name: '{name0}' --> '{name}'")
        return name    

    #@MPD.connection_check
    def send_notify1(self, status = None, song = None):
        if not status: status = CONFIG().client.status()
        if not song: song = CONFIG().client.currentsong()
        #if self.process == None and not isinstance(self.process, Thread):

        if self.process is None or not self.process.is_alive():
            #debug(is_alive = self.process.is_alive())
            debug("mpd_notify", monitor = "send_notify [2]")

            self.process = Process(target = self._send_notify, args = (status, song))
            self.process.daemon = True
            try:
                self.process.start()
            except Exception as e:
                if os.getenv('DEBUG') == '1': print(f"ERROR [1]: {e}")
        elif self.process is None and not isinstance(self.process, Process):
            debug("mpd_notify", monitor = "send_notify [1]")
            #self.process = Thread(target = self._send_notify, args = (status, song))
            self.process = Process(target = self._send_notify, args = (status, song))
            self.process.daemon = True
            try:
                self.process.start()
            except Exception as e:
                print(f"ERROR [2]: {e}")
        elif not self.process.is_alive():
            self.process = Process(target = self._send_notify, args = (status, song))
            self.process.daemon = True
            try:
                self.process.start()
            except Exception as e:
                print(f"ERROR [3]: {e}")
        else:
            if os.getenv('DEBUG') == '1': print(make_colors("process is still running !", 'lw', 'bl'))

        return self.process

    #@MPD.connection_check
    def find_cover_art(self, current_song = None):
        current_song = current_song or self.get_current_song()

        temp_dir = str(Path(os.getenv('temp', '/tmp')) / Path('cover') / Path((self.normalization_name(current_song.get('artist')) or 'Unknown Artist')))
        if not os.path.isdir(temp_dir): os.makedirs(temp_dir)        

        if os.path.isfile(str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title').lower()) + ".jpg"))):
            debug(use_cover = str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title').lower()) + ".jpg")))
            return str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title').lower()) + ".jpg"))
        elif os.path.isfile(str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title').lower()) + ".png"))):
            debug(use_cover = str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title').lower()) + ".png")))
            return str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title').lower()) + ".png"))

        song = current_song.get('file', '')
        debug(song = song)

        if song:
            try:
                picture = self.reconnect('readpicture', (song, ))
            except:
                try:
                    picture = self.client.readpicture(song)
                except:
                    pass
            debug(picture = picture.keys())
            if picture.get('binary'):
                debug(picture = len(picture.get('binary')))
                ext = mimetypes.guess_extension(picture.get('type'))
                debug(ext = ext)
                temp_path = str(Path(temp_dir) / Path(self.normalization_name(current_song.get('title').lower()) + (ext or ".jpg")))
                debug(temp_path = temp_path)
                with open(temp_path, 'wb') as img_file:
                    img_file.write(picture.get('binary'))
                return temp_path

        cover = None
        try:
            cover = deezer_art.get_album_art(current_song.get('artist'), current_song.get('title'), current_song.get('album'), True)
        except:
            pass
        if not cover:
            try:
                cover = self.find_cover_art_lastfm(current_song)
            except:
                pass
        if not cover: cover = str(Path(__file__).parent / 'default_cover.png')

        return cover

    async def _send_notify(self, state, song, cover):
        debug('_send_notify')
        
        description = ""

        state_to_notification_mapping = {
            "play": "Playing",
            "pause": "Paused",
            "stop": "Stopped",
        }

        noteType = state_to_notification_mapping.get(state, state)
        title = noteType
        debug(song = song)
        if song: description = f"{song.get('artist', '')}\n{song.get('album', '')})"

        if state and state.lower() == "pause":
            title += " [PAUSE]"
        elif state and state.lower() == "stop":
            title += " [STOP]"
        else:
            title += f" [{state.upper() if state else ''}]"

        data = {
            'noteType' : noteType,
            'title' : song.get('title', ''),
            'description' : description,
            'icon' : cover, 
            'sticky' : False,
            'priority' : 1,            
        }

        debug(data_notification = data)

        growl.notify(**data)

    def find_album(self, query, date):
        data = {}
        albums = self.reconnect('search', ('album', query))
        for album in albums:
            if not data.get(album.get('album')):
                if album.get('date') == date:
                    data.update({album.get('album'): {'songs': [album], 'date': album.get('date'),}, })
            else:
                if album.get('date') == date:
                    data.get(album.get('album')).get('songs').append(album)

        ##jprint(data)
        return data

    def find_artist(self, query):
        data = {}

        artists = self.reconnect('search', ('artist', query))
        for artist in artists:
            if not data.get(artist.get('artist')):
                data.update({artist.get('artist'): {}, })
                if not data.get(artist.get('artist')).get(artist.get('album')):
                    data.get(artist.get('artist')).update({artist.get('album'): {'songs': [artist], 'date': artist.get('date'), 'detail': self.find_album(artist.get('album'), artist.get('date'))},})
                else:
                    data.get(artist.get('artist')).get(artist.get('album')).get('songs').append(artist)

            else:
                if not data.get(artist.get('artist')).get(artist.get('album')):
                    data.get(artist.get('artist')).update({artist.get('album'): {'songs': [artist], 'date': artist.get('date'), 'detail': self.find_album(artist.get('album'), artist.get('date'))},})
                else:
                    data.get(artist.get('artist')).get(artist.get('album')).get('songs').append(artist)

        albums = self.reconnect('search', ('album', query))
        for album in albums:
            if not data.get(album.get('artist')):
                data.update({album.get('artist'): {}, })
                if not data.get(album.get('artist')).get(album.get('album')):
                    data.get(album.get('artist')).update({album.get('album'): {'songs': [album], 'date': album.get('date'), 'detail': self.find_album(album.get('album'), album.get('date')),},})
                else:
                    data.get(album.get('artist')).get(album.get('album')).get('songs').append(album)

            else:
                if not data.get(album.get('artist')).get(album.get('album')):
                    data.get(album.get('artist')).update({album.get('album'): {'songs': [album], 'date': album.get('date'), 'detail': self.find_album(album.get('album'), album.get('date')),},})
                else:
                    data.get(album.get('artist')).get(album.get('album')).get('songs').append(album)

        ##jprint(data)
        return data

    async def send_notify(self):
        status = self.reconnect('status')
        song = self.reconnect('currentsong')
        data = {
            'app': 'MPD-N',
            'event': 'new',
            'status': status,
            'song': song,
        }
        message = bytes(f"{data}", encoding = 'utf-8')
        try:
            await send_message(message)
        except Exception as e:
            if self.app:
                self.app.notify(f"Error send notification: {e}: server not running", title = 'Error Notification', severity = "error", timeout = 10)
                Logger(f"Error send notification: {e}")

            await self._send_notify(status, song)

class Genius:

    API_KEY = '7kzyaV4vDcf5qha37BD_McKiW064OGbB2HFMw1etADigvCV_h7pjcqXJWdNK5xHB'
    SEARCH_URL = 'https://api.genius.com/search'
    DATA = None
    music_control = MusicControl()

    def __init__(self, host = None, port = None, timeout = None):
        debug(host = host)
        debug(HOSTNAME = CONFIG().HOSTNAME)
        if host and not host == CONFIG().HOSTNAME:
            self.music_control = MusicControl(host = host, port = port, timeout = timeout)
            os.environ.update({'MPD_HOST': host})
        self.API_KEY = CONFIG().get_config('genius', 'api') or Genius.API_KEY
        self.SEARCH_URL = CONFIG().get_config('genius', 'url') + '/search' or Genius.SEARCH_URL

    @classmethod
    def get_data(self, song_title = None, artist_name = None):
        if not song_title and not artist_name:
            current_song = self.music_control.get_current_song()
            debug(current_song = current_song, debug = 1)
            song_title = current_song.get('title')
            artist_name = current_song.get('artist')
        if not song_title and not artist_name:
            return 
                
        params = {
            'q': f'{song_title} {artist_name}',
            'access_token': self.API_KEY
        }
        response = requests.get(self.SEARCH_URL, params=params)
        data = response.json()
        debug(data = data)
        #if DEBUG: jprint(data)

        return data

    @classmethod
    def get_artist(self, artist_name = None):
        if not artist_name:
            current_song = self.music_control.get_current_song()
            artist_name = current_song.get('artist')
        if not artist_name:
            return 
                
        data = None
        try:
            data = self.get_data('', artist_name)
            artist_id = ''
            if 'hits' in data['response'] and len(data['response']['hits']) > 0:
                artist_id = data['response'] and data['response']['hits'][0]['result']['id']
                debug(artist_id = artist_id)
                url = f'https://api.genius.com/{artist_id}'
                params = {
                    'q': f'{artist_name}',
                    'access_token': self.API_KEY
                }

                response = requests.get(url, params=params)
                data = response.json()
                debug(data = data)
                #if DEBUG: jprint(data)
        except:
            console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)

        return data

    @classmethod
    def get_song_lyrics(self, song_title = None, artist_name = None):
        """
        Find/Get lyrics by song title and artist name

        :param song_title: (str) Song/Title name
        :param artist_name: (str) Artist name
        :return: (str) lyric 
        """
        
        if not song_title and not artist_name:
            current_song = self.music_control.get_current_song()
            song_title = current_song.get('title')
            artist_name = current_song.get('artist')
        
        debug(song_title = song_title, debug = 1)
        debug(artist_name = artist_name, debug = 1)

        if not song_title and not artist_name:
            return 
        
        data = self.get_data(song_title, artist_name)
        debug(data_genius = data)
        self.DATA = data
        
        #jprint(data)

        if 'hits' in data['response'] and len(data['response']['hits']) > 0:
            song_url = data['response']['hits'][0]['result']['url']
            debug(song_url = song_url)
            try:
                lyrics_page_response = requests.get(song_url)
                #if DEBUG: console.print(lyrics_page_response.text)
                lyrics = self.parse_lyrics_from_html(lyrics_page_response.text)
                return lyrics
            except:
                console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
        else:
            return None

    @classmethod
    def parse_lyrics_from_html(self, html):
        soup = bs(html, 'html.parser')
        lyrics_div = soup.find('div', class_= re.compile("^Lyrics__Container"))
        debug(lyrics_div = lyrics_div, debug = 1)
        if lyrics_div:
            lyrics = lyrics_div.get_text(separator='\n').strip()
            return lyrics
        else:
            return None

class Wikipedia:

    music_control = MusicControl()
    
    @classmethod
    def get(self, artist_name = None):
        if not artist_name:
            current_song = self.music_control.get_current_song()
            artist_name = current_song.get('artist')
        if not artist_name:
            return '', '', '', ''
                
        wiki_wiki = wikipediaapi.Wikipedia(
            language='en',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
        )

        page_py = wiki_wiki.page(artist_name)
        debug(page_py = page_py)

        try:
            if page_py.exists():
                return page_py.text, page_py.title, page_py.summary, page_py.fullurl

        except Exception as e:
            print("An error occurred:", e)                    

        return '', '', '', ''

class Musixmatch:

    API_KEY = CONFIG().get_config('musixmatch', 'api') or '343f0dd64b402cb9407c6eb4df08be21'
    BASE_URL = 'https://api.musixmatch.com/ws/1.1/'
    music_control = MusicControl()

    @classmethod
    def search_track(self, song_title: str = None, artist_name: str = None) -> None:
        if not song_title and not artist_name:
            current_song = self.music_control.get_current_song()
            song_title = current_song.get('title')
            artist_name = current_song.get('artist')
        if not song_title and not artist_name:
            return 
        
        url = f'{self.BASE_URL}track.search'
        params = {
            'q_track': song_title,
            'q_artist': artist_name,
            'apikey': self.API_KEY,
            'format': 'json'
        }
        try:
            response = requests.get(url, params=params)
            data = response.json()
            debug(data = data)
            #jprint(data)
            debug(message_in_data = 'message' in data, debug = 1)
            debug(status_header = data['message']['header']['status_code'], debug = 1)
            debug(body_in_data = 'body' in data['message'] , debug = 1)
            debug(track_list_in_data_body = 'track_list' in data['message']['body'], debug = 1)
            debug(len_data_body_track_list = len(data['message']['body']['track_list']), debug = 1)
    
            if 'message' in data and data['message']['header']['status_code'] == 200:
                if 'body' in data['message'] and 'track_list' in data['message']['body'] and len(data['message']['body']['track_list']) > 0 and data['message']['body']['track_list'][0]['track']['track_share_url']:
                    url_shared = data['message']['body']['track_list'][0]['track']['track_share_url']
                    debug(url_shared = url_shared)
                    return url_shared
                    #track = data['message']['body']['track_list'][0]['track']
                    #debug(track = track)
                    ##jprint(track)
                    #debug(track_id = track['track_id'], debug = 1)
                    #debug(track_name = track['track_name'], debug = 1)
                    #debug(artist_name = track['artist_name'], debug = 1)
                    #return track['track_id'], track['track_name'], track['artist_name']
            #return None, None, None
        except:
            debug(error_search_artist_genius = traceback.format_exc())
            logger.error(traceback.format_exc())
            if os.getenv('TRACEBACK') == '1':
                console.print_exception(theme = 'fruity', width = shutil.get_terminal_size()[0], max_frames = 30)            
        return None

    @classmethod
    def search_artist(self, artist_name = None):
        if not artist_name:
            current_song = self.music_control.get_current_song()
            artist_name = current_song.get('artist')
            if not artist_name:
                return
        url = f'{self.BASE_URL}artist.search'
        params = {
            'q_artist': artist_name,
            'page_size': '1',
            'apikey': self.API_KEY,
        }
        
        try:
            a = requests.get(url, params = params)
            data = a.json()
            debug(data = data)
            #jprint(data)
            debug(message_in_data = 'message' in data, debug = 1)
            debug(status_header = data['message']['header']['status_code'], debug = 1)
            debug(body_in_data = 'body' in data['message'] , debug = 1)
            debug(track_list_in_data_body = 'artist_list' in data['message']['body'], debug = 1)
            debug(len_data_body_track_list = len(data['message']['body']['artist_list']), debug = 1)
            
            if 'message' in data and data['message']['header']['status_code'] == 200:
                if 'body' in data['message'] and 'artist_list' in data['message']['body'] and len(data['message']['body']['artist_list']) > 0:
                    debug(data = data['message']['body']['artist_list'])
                    return data['message']['body']['artist_list']
        except:
            debug(error_search_artist_genius = traceback.format_exc())
            logger.error(traceback.format_exc())
            if os.getenv('TRACEBACK') == '1':
                console.print_exception(theme = 'fruity', width = shutil.get_terminal_size()[0], max_frames = 30)
        return None
            
    
    @classmethod
    def get_artist(self, artist_name = None):
        data_search = self.search_artist(artist_name)
        if data_search:
            artist_id = data_search[0].get('artist').get('artist_id')
            params = {
                'artist_id': artist_id,
                'apikey': self.API_KEY,
            }
            try:
                data = requests.get(f"{self.BASE_URL}artist.get", params = params).json()
                debug(data = data)
                if 'message' in data and data['message']['header']['status_code'] == 200:
                    if 'body' in data['message'] and 'artist' in data['message']['body'] and len(data['message']['body']['artist']) > 0:
                        return data['message']['body']['artist']
            except:
                debug(error_search_artist_genius = traceback.format_exc())
                logger.error(traceback.format_exc())
                if os.getenv('TRACEBACK') == '1':
                    console.print_exception(theme = 'fruity', width = shutil.get_terminal_size()[0], max_frames = 30)
        return None
        
    @classmethod
    def get_lyrics(self, url = None):
        cover = None
        if not url:
            url = self.search_track()
            if not url:
                return None, None, None, None, None, None
            
        if not url[:4] == 'http':
            return '', '', '', '', '', ''
        a = requests.get(url, headers = {
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9', })
        content = a.content
        with open('result.html', 'wb') as f: f.write(content)
        b = bs(content, 'lxml')
        lyrics_json = b.find('script', {'type': 'application/json',})
        debug(lyrics_json = lyrics_json)
        lyrics = ''
        error = False
        if lyrics_json:
            lyrics_json = lyrics_json.text
            #clipboard.copy(lyrics_json)
            lyrics_json = json.loads(lyrics_json)
            #if DEBUG: jprint(lyrics_json)
            try:
                lyrics = lyrics_json.get('props').get('pageProps').get('data').get('trackInfo').get('data').get('lyrics').get('body')
                writer = lyrics_json.get('props').get('pageProps').get('data').get('trackInfo').get('data').get('lyrics').get('copyright')
                artist = lyrics_json.get('props').get('pageProps').get('data').get('trackInfo').get('data').get('track').get('artists')[0].get('name')
                song = lyrics_json.get('props').get('pageProps').get('data').get('trackInfo').get('data').get('track').get('name')
                cover = lyrics_json.get('props').get('pageProps').get('data').get('trackInfo').get('data').get('track').get('artists')[0].get('image')

                return lyrics, song + f' by {artist}', writer, artist, song, cover
            except:
                error = True
                console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
                logger.warning(traceback.format_exc())

        if not lyrics_json or error:
            error = False
            title = b.find('h2', string = re.compile('Lyrics of'))
            debug(title = title)
            lyrics = []
            writer = ''
            song_title = ''
            song = ''
            artist = ''
            if title:
                song = title.text.replace('Lyrics of ', '')
                lyrics_div = title.parent.find('div')
                lyrics_divs = lyrics_div.find_all('div', {'dir': 'auto',})
                debug(lyrics_div = lyrics_div)
                debug(lyrics_divs = lyrics_divs)
                lyrics = [i.text for i in lyrics_divs]
                #jprint(lyrics)

                writer = title.parent.find('div', {'dir': 'auto'}, string = re.compile('Writer'))
                if writer:
                    writer = writer.text.strip()
                    #lyrics.append(writer)
                debug(writer = writer)
            cover_data = b.find('img', {'src' : re.compile('images-storage')})
            if cover_data:
                cover = cover_data.get('src')
                debug(cover = cover)
                song_title_data = cover_data.parent.parent.parent.parent.find('h1')
                debug(song_title_data = song_title_data)
                if song_title_data:
                    song_title = song_title_data.text
                    artist = song_title_data.find_next('h2')
                    debug(artist = artist)
                    if artist:
                        artist = artist.text
                        debug(artist = artist)
            return "\n".join(lyrics), song, writer, artist, song_title, cover

    @classmethod
    def get_lyrics1(self, track_id):
        url = f'{self.BASE_URL}track.lyrics.get'
        params = {
            'track_id': track_id,
            'apikey': self.API_KEY,
            'format': 'json'
        }
        response = requests.get(url, params=params)
        data = response.json()
        #jprint(data)
        debug(data_lyric = data)

        debug(message_in_data = 'message' in data, debug = 1)
        debug(status_code = data['message']['header']['status_code'], debug = 1)
        debug(body_in_data = 'body' in data['message'], debug = 1)
        debug(lyric_in_message_body = 'lyrics' in data['message']['body'], debug = 1)

        if 'message' in data and data['message']['header']['status_code'] == 200:
            if 'body' in data['message'] and 'lyrics' in data['message']['body']:
                lyrics = data['message']['body']['lyrics']['lyrics_body']
                debug(lyrics = lyrics, debug = 1)
                return lyrics
        return None

    @classmethod
    def fetch_lyrics(self, song_title = None, artist_name = None):
        if not song_title and not artist_name:
            current_song = self.music_control.get_current_song()
            song_title = current_song.get('title')
            artist_name = current_song.get('artist')
            if not song_title and not artist_name:
                return 
        
        track_id, track_name, artist = self.search_track(song_title, artist_name)
        #sys.exit()
        debug(track_id = track_id, debug = 1)
        if track_id:
            lyrics = self.get_lyrics(track_id)
            if lyrics:
                return lyrics
        return 'Lyrics not found.'    

class Deezer:
    
    music_control = MusicControl()
    BASE_URL = "https://api.deezer.com"
    
    @classmethod
    def get_info(self, artist_name = None, song_name=None, album_name=None, to_json = True):
        
        current_song = self.music_control.get_current_song()
        artist_name = artist_name or current_song.get('artist')
        song_name = song_name or current_song.get('title')
        album_name = album_name or current_song.get('album')
        
        base_url = f'{self.BASE_URL}/search'
        
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
    
    @classmethod        
    def get_album_art(self, artist_name = None, song_name=None, album_name=None, to_file = False):
        current_song = self.music_control.get_current_song()
        artist_name = artist_name or current_song.get('artist')
        song_name = song_name or current_song.get('title')
        album_name = album_name or current_song.get('album')
        
        response = self.get_info(artist_name, song_name, album_name, False)
        if response and response.status_code == 200:
            data = response.json()
            if data['data']:
                # Assume the first result is the most relevant
                track_info = data['data'][0]
                album_id = track_info.get('album').get('id')
                #album_art_url = f"https://api.deezer.com/album/{album_id}/image"
                album_art_url = track_info.get('album').get('cover_xl') or track_info.get('album').get('cover_big') or track_info.get('album').get('cover') or f"https://api.deezer.com/album/{album_id}/image"
                if to_file:
                    filename = os.path.join(os.getenv('temp', '/tmp'), self.music_control.normalization_name(artist_name))
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
        
    @classmethod
    def get_artist_image(self, artist_name = None):
        '''
            # Example usage
            >>> artist_name = "Adele"
            >> get_artist_image(artist_name)
        '''
        artist_name = artist_name or self.music_control.get_current_song().get('artist')
        # Search for the artist
        search_url = f"{self.BASE_URL}/search/artist?q={artist_name}"
        response = requests.get(search_url)
        
        if response.status_code == 200:
            # Parse the response
            data = response.json()
            if data['data']:
                # Get the artist ID
                artist_id = data['data'][0]['id']
                
                # Get artist details using artist ID
                artist_url = f"{self.BASE_URL}/artist/{artist_id}"
                artist_response = requests.get(artist_url)
                
                if artist_response.status_code == 200:
                    artist_data = artist_response.json()
                    # Get the image URL
                    image_url = artist_data.get('picture_big')  # or 'picture_xl' for larger image
                    print(f"Artist Image URL: {image_url}")
                    return image_url
                else:
                    print("Error fetching artist details")
            else:
                print("Artist not found")
        else:
            print(f"Error: {response.status_code}")
    
class LastFM:
    
    music_control = MusicControl()
    API = CONFIG().get_config('lastfm', 'api', 'c725344c28768a57a507f014bdaeca79')
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"
    
    @classmethod
    def get_artist(self, artist = None):
        data = None
        
        if not artist:
            current_song = self.music_control.get_current_song()
            artist = current_song.get('artist')
            debug(artist = artist)
        debug(artist = artist)
        if not artist:
            return None
        
        try:
            artist = artist.replace(" ", "+")
            params = {
                'method': 'artist.getinfo',
                'artist': artist,
                'api_key': self.API,
                'format': 'json'
            }
            debug(params = params)
            max_try = 5
            n = 1
            while 1:
                try:
                    data = requests.get(self.BASE_URL, params = params).json()
                    debug(data = data)
                    break
                except:
                    logger.error(traceback.format_exc())
                    debug(lastfm_get_artist = traceback.format_exc())
                if n == max_try or n > max_try:
                    break
            #if DEBUG: jprint(data)
        except:
            console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)

        return data
    
    @classmethod
    def get_album_cover(self, artist = '', album = '', save_to = None):
        #logger.info(f'MPDNotify: try to get cover from LastFM: "{artist}:{album}"')
        current_song = ''
        try:
            current_song = self.music_control.get_current_song()
        except:
            logger.error(traceback.format_exc())
            debug(error_save_image = traceback.format_exc())        
        if not artist:
            current_song = self.music_control.get_current_song()
            artist = current_song.get('artist')
            album = current_song.get('album')
        debug(artist = artist)
        debug(album = album)

        if artist and album:
            params = {
                'method': 'album.getinfo',
                'artist': artist,
                'album': album,
                'api_key': self.API,
                'format': 'json'
            }
            a = requests.get(self.BASE_URL, params = params)
            if a.status_code == 200:
                debug(responce = a.content)
                try:
                    cover_url = None
                    #url1 = a.json()['album']['image'][-1]['#text']
                    lastfm_album_images = a.json().get('album').get('image')
                    if lastfm_album_images:
                        data_lastfm_album_images = list(filter(lambda k: k.get('size') in ['mega', 'extralarge', 'large', 'medium', 'small'], lastfm_album_images))
                        if data_lastfm_album_images:
                            cover_url = data_lastfm_album_images[0].get('#text')                    
                    if cover_url:
                        #temp_path = str(Path(os.getenv('temp', '/tmp')) / Path(self.normalization_name(artist) + "_" + self.normalization_name(artist) + os.path.splitext(cover_url)[-1]))
                        if save_to:
                            temp_path = save_to
                        else:
                            cover_dir = CONFIG().get_config('cover', 'dir') or str(Path(__file__).parent / 'cover')
                            if not os.path.isdir(cover_dir):
                                os.makedirs(cover_dir)                        
                            temp_path = os.path.join(
                                cover_dir,
                                Normalization.normalization_name(artist),
                                Normalization.normalization_name(album), 
                            )
                        if not os.path.isdir(temp_path):
                            os.makedirs(temp_path)
                        temp_path = os.path.join(temp_path, 
                            Normalization.normalization_name(current_song.get('title') if current_song else artist) + os.path.splitext(cover_url)[-1])
                        cover_data = None
                        max_try = 5
                        n = 0
                        while 1:
                            try:
                                cover_data = requests.get(cover_url).content
                                break
                            except:
                                logger.error(traceback.format_exc())
                                debug(error_save_image = traceback.format_exc())
                            if n == max_try or n > max_try:
                                break
                            else:
                                n += 1
                        if cover_data:
                            with open(temp_path, 'wb') as f:
                                f.write(cover_data)
                            #logger.warning(f'MPDNotify: use cover: "{temp_path}"')
                            return temp_path
                except Exception as e:
                    print("failed to get cover art from LastFM:", e)
                    if os.getenv('TRACEBACK'):
                        console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
        return ''
    
    @classmethod
    def get_similar(self, data = None):
        data = data or self.get_artist()
        if not data:
            return None
        return data.get('artist').get('similar')

class Cover(Static):

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app')
        self.cover = str(Path(__file__).parent / 'images' / 'no-cover.png')
        kwargs.pop('app')
        if kwargs.get('cover'):
            self.cover = kwargs.get('cover')
            kwargs.pop('cover')

        super().__init__(*args, **kwargs)

        self.music_control = MusicControl(app = self.app)

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value

    #def on_mount(self):
    async def update_cover(self, cover = None) -> None:
        self.cover = cover or self.music_control.find_cover_art()
        debug(self_cover = self.cover)
        self.update(
            Align(display_image(self.cover, width=40, whiteness_threshold=1, darkness_threshold=0, recursive=False, procedural_printing=False, no_center=True), "center")
        )
        
    async def run_update_cover(self) -> None:
        s_top = self.query_one(STop)
        try:
            await self.update_cover()
            debug("finish self.update_cover(cover)")
            debug("remove childred #cover_indicator")
            s_top.remove_children('#cover_indicator')            
            self.mount()     
        except:
            logger.warning(traceback.format_exc())
            
    async def run_tasks(self) -> None:
        asyncio.create_task(self.run_update_cover())    
        
    def on_mount(self) -> None:
        self.refresh()
        #self.update_cover()

class Info(Static):

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app')
        kwargs.pop('app')
        super().__init__(*args, **kwargs)

        self.music_control = MusicControl(app = self.app)

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value

    def replace_links(self, text):
        # Regular expression to find all <a>...</a> tags
        pattern = re.compile(r'<a href="([^"]*)">(.*?)</a>')

        # Function to replace each match with the rich link syntax
        def replace_match(match):
            url = match.group(1)
            link_text = match.group(2)
            return f'[link={url}]{link_text}[/link]'

        # Replace all matches in the text
        replaced_text = pattern.sub(replace_match, text)
        return replaced_text

    def get_info(self):
        error = False
        try:
            current_song = self.music_control.get_current_song()
        except:
            current_song = None
        try:
            title = f"{current_song.get('track')}. {current_song.get('title')}"
            check_db = Database.get(current_song.get('artist'), current_song.get('album'), title)
            debug(check_db = check_db)

            #SQL = f"""
                #SELECT b.id, b.name, b.bio, b.artist_cover, b.simillar, b.lyrics,
                       #a.name AS album_name, a.date AS album_date, a.album_cover, 
                       #t.name AS track_name
                #FROM {table} b
                #LEFT JOIN albums a ON b.id = a.bio_id
                #LEFT JOIN tracks t ON a.id = t.album_id
            #"""

            
            if check_db:
                bio = check_db[0].get('bio')
                lyrics = check_db[0].get('lyrics')
                lyrics_title = check_db[0].get('lyrics_title')
                lyrics_writer = check_db[0].get('lyrics_writer')
                artist_cover = check_db[0].get('artist_cover')
                similar = check_db[0].get('similiar')
                
                if lyrics:
                    debug(lyrics =  lyrics)
                    return Align(
                        f"[bold #FFFF00]{lyrics_title}[/]\n\n[bold #FF5500]{lyrics_writer}[/]\n\n[bold #AAFF00]{lyrics}[/]"
                    )
                elif bio:
                    return Align(
                        f"[bold #FFFF00]{current_song.get('title')}[/] [bold #FF55FF]by[/] [bold #55FFFF]{current_song.get('artist')}[/]\n\n[bold #FF5500]{bio}[/]"
                    )
                else:
                    error = True
            
            if not check_db or error:
                try:
                    data_musixmatch = None
                    #data_genius = None
                    #data_lastfm = None
                    data_wikipedia = None
                    
                    try:
                        data_musixmatch = Musixmatch.get_lyrics()
                    except:
                        logger.warning(traceback.format_exc())
                        console.log(traceback.format_exc())
                    #try:
                        #data_genius = Genius.get_data()
                    #except:
                        #logger.warning(traceback.format_exc())
                        #console.log(traceback.format_exc())
                    #try:
                        #data_lastfm = LastFM.get_artist()
                    #except:
                        #logger.warning(traceback.format_exc())
                        #console.log(traceback.format_exc())
                    try:
                        data_wikipedia = Wikipedia.get()
                    except:
                        logger.warning(traceback.format_exc())
                        console.log(traceback.format_exc())
                    
                    artist = current_song.get('artist')
                    album = current_song.get('album')
                    cover = self.music_control.find_cover_art()
                    
                    album_search = self.music_control.reconnect('search', ('album', album))
                    tracks = [f"{i.get('track')}. {i.get('title')}" for i in album_search]
                    
                    bio = data_wikipedia[0] if data_wikipedia else ''
                    similar = LastFM.get_similar()
                    
                    lyrics = artist_cover = lyrics_title = lyrics_writer = title = ''
                    
                    if data_musixmatch:    
                        lyrics = data_musixmatch[0]
                        artist_cover = data_musixmatch[5]
                        lyrics_title = data_musixmatch[1]
                        lyrics_writer = data_musixmatch[2]
                        title = data_musixmatch[4]
                        Database.update(artist, tracks, album, current_song.get('date'), bio, cover, artist_cover, similar, title, lyrics, lyrics_title, lyrics_writer)
                        
                    
                    if lyrics and "Let the music play" in lyrics or 'no lyrics' in lyrics or 'Still no lyrics' in lyrics:
                        text = f"{current_song.get('title')} by {current_song.get('artist')}\n\n{bio}"
                        return Align(text, "center")
                    elif lyrics:
                        return Align(
                            f"[bold #FFFF00]{lyrics_title}[/]\n\n[bold #FF5500]{lyrics_writer}[/]\n\n[bold #AAFF00]{lyrics}[/]"
                        )
                    else:
                        if bio:
                            return Align(
                                f"[bold #FFFF00]{current_song.get('title')}[/] [bold #FF55FF]by[/] [bold #55FFFF]{current_song.get('artist')}[/]\n\n[bold #FF5500]{bio}[/]"
                            )
                        else:
                            return Align(
                                f"[bold #FFFF00]{current_song.get('title')}[/] [bold #FF55FF]by[/] [bold #55FFFF]{current_song.get('artist')}[/]\n\n"
                            )                            
                except:
                    error = True
                    console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
                    
                    return Align(
                        f"[bold #FFFF00]{current_song.get('title')}[/] [bold #FF55FF]by[/] [bold #55FFFF]{current_song.get('artist')}[/]\n\n"
                    )                    
    
            else:
                if current_song:
                    return Align(
                        f"[bold #FFFF00]{current_song.get('title')}[/] [bold #FF55FF]by[/] [bold #55FFFF]{current_song.get('artist')}[/]\n\n"
                    )
                else:
                    return Align("ERROR [ see log file 'mpl.log' !", "center")
        except:
            logger.warning(traceback.format_exc())
            
        if current_song:
            return Align(
                f"[bold #FFFF00]{current_song.get('title')}[/] [bold #FF55FF]by[/] [bold #55FFFF]{current_song.get('artist')}[/]\n\n"
            )
        else:
            return Align("ERROR [ see log file 'mpl.log' !", "center")

    def update_info(self):
        self.update(self.get_info())
    
    async def update_info_async(self):
        try:
            self.update(self.get_info())
        except:
            logger.warning(traceback.format_exc())

    def on_mount(self) -> None:
        self.refresh()
        #self.update(self.get_info())        

class Cover_and_Info(Static):

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app')
        kwargs.pop('app')

        super().__init__(*args, **kwargs)

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value    

    def compose(self) -> ComposeResult:
        #yield Cover(app = self.app, id = 'cover_playlist')
        #yield ScrollableContainer(Info("This is static for info", app = self.app), id = "info_playlist")
        try:
            yield LoadingIndicator(id = "cover_indicator")
            yield LoadingIndicator(id = "info_indicator")
        except:
            logger.warning(traceback.format_exc())                    

    async def update_info(self, info: Info) -> None:
        try:
            info.update_info()
        except:
            logger.warning(traceback.format_exc())                    

    async def update_cover(self, cover: Cover) -> None:
        try:
            cover.update_cover()
        except:
            logger.warning(traceback.format_exc())                    

    async def run_update_cover(self) -> None:
        try:
            cover = Cover(app = self.app, id = 'cover_playlist')
            #s_top = self.query_one(STop)            
            await self.update_cover(cover)
            debug("finish self.update_cover(cover)")
            debug("remove childred #cover_indicator")
            self.remove_children('#cover_indicator')            
            self.mount(cover)            
        except:
            logger.warning(traceback.format_exc())
            
    async def run_update_info(self) -> None:
        try:
            info = Info(app = self.app, id = 'info_playlist')
            #s_top = self.query_one(STop)            
            await self.update_info(info)
            debug("finish self.update_info(info)")
            debug("remove childred #info_indicator")
            self.remove_children('#info_indicator')            
            self.mount(info)
        except:
            logger.warning(traceback.format_exc())        

    async def run_tasks(self) -> None:
        try:
            asyncio.create_task(self.run_update_info())
            asyncio.create_task(self.run_update_cover())
        except:
            logger.warning(traceback.format_exc())                    

    async def on_mount(self) -> None:
        try:
            self.refresh()
            asyncio.create_task(self.run_tasks())
        except:
            logger.warning(traceback.format_exc())                    

class Normalization:

    @classmethod
    def normalization_name(self, name):
        if not name:
            return name
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
        #logger.info(f"Normalization: normalization_name: '{name0}' --> '{name}'")
        return name

class CustomNotification(Static):
    def __init__(self, content: str, severity: str = "info", **kwargs):
        self.app = kwargs.get('app')
        kwargs.pop('app')
        super().__init__(content, **kwargs)
        self.severity = severity
        self.set_severity(severity)
        self.interval_id = None

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value

    def set_severity(self, severity: str):
        self.severity = severity
        self.add_class(f'notify-{severity}')

    def update_notification(self, content: str, severity: str = None):
        self.update(content)
        if severity:
            self.remove_class(f'notify-{self.severity}')
            self.set_severity(severity)

    def show_notification(self):
        self.remove_class('hidden')
        if self.interval_id is None:
            self.interval_id = self.set_interval(5, self.hide_notification)

    def hide_notification(self):
        self.add_class('hidden')
        self.app.clear_interval(self.interval_id)
        self.interval_id = None

class MusicPanel(Static):

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app')
        if not self.app == None: kwargs.pop('app')
        super().__init__(*args, **kwargs)
        self.music_control = MusicControl(app = self.app)
        self.current_song = self.music_control.get_current_song()

        self.app_name = "Deezer"

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value

    def get_status(self):
        status = self.music_control.status()
        debug(status = status)
        data = ''
        if status.get('state') == 'pause':
            #data += "[bold #55ffff]||[/] "
            data += "[bold #ffff00]||[/] "
        elif status.get('state') == 'stop':
            #data += "[bold #ff00ff]■[/] "
            data += "[bold #ffff00]■[/] "

        if status.get('repeat') == '1':
            data += "[bold #ffff00]Ω[/] "
        if status.get('single') == '1':
            #data += "[bold #aaff00]Σ[/] "
            data += "[bold #ffff00]Σ[/] "
        if status.get('random') == '1':
            #data += "[bold #ff5500]Ϣ[/] "
            data += "[bold #ffff00]Ϣ[/] "
        if status.get('consume') == '1':
            #data += "[bold #ff0000]Δ[/] "
            data += "[bold #ffff00]Δ[/] "

        debug(data = data)
        return data

    def get_deezer_tab(self):
        tab = DeezerController.find_deezer_tab()
        return tab

    async def get_controller(self):
        tab = self.get_deezer_tab()
        websocket_url = f"ws://127.0.0.1:9222/devtools/page/{tab.id}"
        controller = DeezerWs(websocket_url)
        await controller.connect()
        return controller

    async def get_progress_data(self):
        # progress_task = progress.add_task(
        #     "[bold green]Deezer Player", total=100, current_song="Loading...", time="0:00"
        # )
        
        controller = await self.get_controller()
        progress_data = await controller.get_song_progress()
        
        return progress_data #, progress_task

    def create_info_panel(self):
        progress_data = self.get_progress_data()
        if progress_data:
            current_song = progress_data['song']
            current_artist = progress_data['artist']
            current_album = progress_data['album']
        
        
        debug("""Creates the Rich Panel with current song info.""")
        return Align(
                Panel(
                    f"Current song: [bold #55ffff]{current_song}[/]\n" 
                    f"Artist: [bold #aaff00]{current_artist}[/]\n"
                    f"Album: [bold #ff55ff]{current_album}[/]", 
                    title=f"[bold #aaaaff]Now Playing\[{self.app_name}][/]",
                    title_align="center",
                    width=shutil.get_terminal_size()[0], 
                    height = 5
                    ),
                "center"
        )            

    def update_panel(self) -> None:
        self.current_song = self.music_control.get_current_song()
        self.update(self.create_info_panel())
        
    async def update_panel_async(self) -> None:
        self.current_song = self.music_control.get_current_song()
        self.update(self.create_info_panel())    

    def on_mount(self) -> None:
        self.update(self.create_info_panel())

class Table(DataTable):

    #music_control = MusicControl()
    #playlistinfo = music_control.reconnect('playlistinfo')
    #current_song = music_control.reconnect('currentsong')

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app')
        kwargs.pop('app')
        self.music_control = MusicControl(app = self.app)
        self.playlistinfo = None
        self.current_song = None        
        super().__init__(*args, **kwargs)

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value

    def on_mount(self) -> None:
        """Called when the widget is mounted (added to the app)."""
        self.refresh()
        #self.focus()  # Focus on the table
        ##self.add_columns("Track", "Artist", "Title", "Album", "Year")
        #self.add_column("Track", width=5, key = 'track')
        #self.add_column("Artist", width=30, key = 'artist')
        #self.add_column("Title", width=50, key = 'title')
        #self.add_column("Album", width=50, key = 'album')
        #self.add_column("Year", width=10, key = 'year')        
        #self.populate_table()

        ##debug(row_height_30 = self.get_row_height('Track'))

        #self.fixed_columns = 1
        #self.cursor_type = "row"
        #self.zebra_stripes = True   

        #self.select_current_song_row()

    async def load_data(self):
        """Load data and populate the table."""
        debug("Load data and populate the table")
        try:
            # Run the data loading operation in a separate thread
            #self.playlistinfo = await asyncio.to_thread(self.music_control.reconnect, 'playlistinfo')
            #self.current_song = await asyncio.to_thread(self.music_control.reconnect, 'currentsong')
            self.playlistinfo = await self.music_control.reconnect_async('playlistinfo')
            debug("success load self.playlistinfo")
            self.current_song = await self.music_control.reconnect_async('currentsong')
            debug("success load self.current_song")

            ## Populate the table with the loaded data
            #self.populate_table()
            #debug("finish populate table")
        except Exception as e:
            # Handle any exceptions that may occur during the data loading process
            console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
            debug(error=str(e))
            self.ap.notify(str(e), severity = 'error', timeout = 10, title = "Error load DataTable")
            debug(error = e)
            debug(error_full = traceback.format_exc())


    def populate_table(self, playlist = None, is_find = False):
        """Populates the table with playlist information and applies styling."""

        self.clear()
        if self.playlistinfo:
            if not is_find:
                zfill = len(str(self.playlistinfo[-1].get('id')))
                playlist = playlist or self.playlistinfo
            else:
                zfill = len(str(len(playlist)))
        else:
            zfill = 0

        if is_find:
            #index_title = self.columns.index('title')
            self.remove_column('title')
        if playlist:
            for track in playlist:
                style1 = "[bold #ff5500]"
                style2 = "[bold #aaff00]"
                style3 = "[bold #00ffff]"
                style4 = "[bold #ffff00]"
                style5 = "[bold #ffaaff]"

                if not is_find:
                    try:
                        self.add_row(
                            f"{style1}{str(int(track.get('pos')) + 1).zfill(zfill) + '.'}[/]",
                            f"{style2}{track.get('artist')}[/]",
                            f"{style3}{track.get('title')}[/]",
                            f"{style4}{track.get('album')}[/]",
                            f"{style5}{track.get('date') if track.get('date') else ''}[/]"
                        )
                    except:
                        self.remove_column('album')
                        self.remove_column('year')
                        self.add_column("Title", width=50, key = 'title')
                        self.add_column("Album", width=50, key = 'album')
                        self.add_column("Year", width=10, key = 'year')                            
                        self.add_row(
                            f"{style1}{str(int(track.get('pos')) + 1).zfill(zfill) + '.'}[/]",
                            f"{style2}{track.get('artist')}[/]",
                            f"{style3}{track.get('title')}[/]",
                            f"{style4}{track.get('album')}[/]",
                            f"{style5}{track.get('date') if track.get('date') else ''}[/]"
                        )
                else:

                    self.add_row(
                        f"{style1}{str(int(track.get('pos')) + 1).zfill(zfill) + '.'}[/]",
                        f"{style2}{track.get('artist')}[/]",
                        f"{style4}{track.get('album')}[/]",
                        f"{style5}{track.get('date') if track.get('date') else ''}[/]"
                    )


    def select_current_song_row(self, pos = None):
        self.refresh()
        debug("select_current_song_row")
        debug(pos = pos)
        if not pos:
            try:
                self.current_song = CONFIG().client.currentsong()
                debug(f"self.current_song: {self.current_song}")
                pos = self.current_song.get('pos')
                debug(pos = pos)
            except:
                debug("mpd disconnectin ...")
                CONFIG().client.disconnect()
                CONFIG().client.connect(CONFIG().HOSTNAME, CONFIG().PORT)
                self.current_song = CONFIG().client.currentsong()
                pos = self.current_song.get('pos')            
                debug(pos = pos)
            debug(pos = pos)
            debug(terminal_size = shutil.get_terminal_size())
        if pos is not None:
            self.move_cursor(row = int(pos))

    def search(self, query):
        """
        Search for tracks in the playlist by matching the search value against any value in each track.

        :param query: The value to match against any field in the track's metadata
        :return: List of tracks that match the search criteria
        """
        os.environ.update({'MPDN_IS_SEARCH': '1',})
        data = []
        playlist = []
        try:
            playlist = CONFIG().client.playlistinfo()
            debug(playlist = playlist)
            for track in playlist:
                # Check if the search value exists in any of the track's fields
                if any(query.lower() in str(value).lower() for value in track.values()):
                    data.append(track)

        except Exception as e:
            console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
            debug(error = str(e))

        debug(data = data)
        if data:
            self.populate_table(data)
            if len(data) == len(playlist):
                os.environ.update({'MPDN_IS_SEARCH': '0',})
                self.select_current_song_row()
        return data

    def find(self, query):
        """
        Search for tracks in the playlist by matching the search value against any value in each track.

        :param query: The value to match against any field in the track's metadata
        :return: List of tracks that match the search criteria
        """

        data = []
        playlists = self.music_control.find_artist(query)
        index = 0
        for artist, albums in playlists.items():
            for album, details in albums.items():
                date = details.get('date', 'Unknown')
                entry = {
                    'pos': index,
                    'artist': artist,
                    'album': album,
                    'date': date,
                }
                data.append(entry)
                index += 1

        debug(data = data)
        if data:
            self.populate_table(data, is_find = True)
        return data, playlists

class PBar(Static):
    progress = Progress(
        TextColumn("{task.fields[current_song]}", justify="left"),
                    BarColumn(bar_width = shutil.get_terminal_size()[0]),
                    TextColumn("{task.completed}/{task.total}", justify="right"),
                    TextColumn("[bold red]-{task.fields[time]}", justify="right"),
                    console=console
    )

    progress_task = progress.add_task(
        f"[bold green]{APP}", total=1.0, current_song="[bold yellow]Unknown Title by Unknown Artist[/bold yellow]", time="0:01"
    )

    #music_control = MusicControl()
    #current_song = client.currentsong()
    last_title = None
    last_state = None

    first = True

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app')
        kwargs.pop('app')
        super().__init__(*args, **kwargs)
        self.music_control = MusicControl(self.app)

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value

    def reconnect(self, func, args = ()):
        if not isinstance(args, tuple):
            args = (args, )
        #logger.warning(f'MPDNotify: run command: "{func}:{str(args)}"')
        data = {}
        #debug(args = args)
        #debug(func = func)
        while 1:
            try:
                data = getattr(CONFIG().client, func)(*args)
                return data
            except:
                if os.getenv('TRACEBACK') == "1": console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
                try:
                    CONFIG().HOSTNAME = os.getenv('MPD_HOST') or CONFIG().get_config('host', 'name') or '127.0.0.1'
                    CONFIG().PORT = os.getenv('MPD_CONFIG().PORT') or CONFIG().get_config('host', 'port') or 6600

                    if CONFIG().PORT and not isinstance(CONFIG().PORT, int):
                        if str(CONFIG().PORT).isdigit():
                            CONFIG().PORT = int(CONFIG().PORT)
                        else:
                            CONFIG().PORT = 6600

                    CONFIG().client.connect(CONFIG().HOSTNAME, CONFIG().PORT)
                    data = getattr(CONFIG().client, func)(*args)
                    break
                except Exception as e:
                    try:
                        CONFIG().client.disconnect()
                    except:
                        pass

                    if os.getenv('TRACEBACK') == "1": console.print_exception(theme='fruity', width=shutil.get_terminal_size()[0], max_frames=30)
                    print(make_colors(f"Failed to re-connection to MPD Server !: {e}", 'lw', 'r'))
                    try:
                        CONFIG().client.connect(CONFIG().HOSTNAME, CONFIG().PORT)
                        data = getattr(CONFIG().client, func)(*args)
                        break
                    except Exception as e:
                        self.app.notify(str(e), title = f"{datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f')} MPD-N ERROR", timeout = 5, severity = "error")

                time.sleep(1)

        return data

    def get_current_song(self, data1 = None, data2 = None):
        #data1 = self.music_control.get_current_song()
        data1 = self.reconnect('currentsong')
        #data2 = self.music_control.status()
        data2 = self.reconnect('status')
        return data1, data2

    async def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        #self.app.set_message_handler("table_ready", self.select_current_song_row)
        self.set_interval(1, self.update_bar)

    def update_table(self):
        table = Table()
        table.clear()
        table.populate_table()
        table.refresh()

    def move_cursor(self, index):
        datatable = Table()
        datatable.move_cursor(row=int(index))

    def select_current_song_row(self, pos = None):
        try:
            """Selects the row corresponding to the currently playing song."""
            s_top = self.app.query_one('#s_top', STop)
            table = s_top.query_one('#table_playlist', Table)    
            if os.getenv('MPDN_IS_SEARCH') == '1' and os.getenv('MPDN_ROW_SELECTED'):
                table.select_current_song_row(int(os.getenv('MPDN_ROW_SELECTED')))
            else:
                pos = pos or self.music_control.reconnect('currentsong').get('pos')
                table.select_current_song_row(pos)

        except Exception as e:
            pass
            #self.app.notify(str(e), title = f"{datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f')} MPD-N ERROR", timeout = 20, severity = "error")
            #logger.debug(str(traceback.format_exc()))

    async def update_panel(self):
        try:
            panel = self.app.query_one(MusicPanel)
            await panel.update_panel_async()
        except:
            logger.warning(traceback.format_exc())            
    
    async def update_cover(self, cover = None):
        try:
            covers = self.app.query(Cover)
            if covers:
                for cover_widget in covers:
                    cover_widget.update_cover(cover)
            else:
                raise ValueError("No Cover widget found")
        except:
            logger.warning(traceback.format_exc())
            
    async def update_info(self):
        try:
            info = self.app.query('#info_playlist')
    
            try:
                indicator_exists = self.app.vertical.query_one('#info_indicator')
            except:
                indicator_exists = None
                logger.warning(traceback.format_exc())
            
            if indicator_exists:
                # Remove the existing LoadingIndicator
                try:
                    self.app.vertical.remove_children('#info_indicator')
                except:
                    logger.warning(traceback.format_exc())
            #else:
            try:
                # Mount the LoadingIndicator only if it doesn't already exist
                self.app.vertical.mount(LoadingIndicator(id="info_indicator"))
            except:
                logger.warning(traceback.format_exc())
                
            #self.app.vertical.remove_children('#info_playlist_scroll')
            #self.app.vertical.mount(LoadingIndicator(id = "info_indicator"))
            try:
                if info:
                    for info_widget in info:
                        await info_widget.update_info_async()
                        await self.finish_update_info()
                        #info_widget.update(info_widget.get_info())
                else:
                    self.app.notify("No Info widget found for 'Info'", title = "Info Widget Error", severity = "error", timeout = 12)
                    #raise ValueError("No Info widget found")
            except:
                logger.warning(traceback.format_exc())
        except:
            logger.warning(traceback.format_exc())
            
    async def finish_update_info(self):
        try:
            debug("finish_update_info")
            info = self.app.query_one('#info_playlist')
            info.update_info()
            self.app.vertical.remove_children('#info_indicator')
            self.app.vertical.refresh()
            #self.app.vertical.remove_children('#info_playlist_scroll')
            #self.app.vertical.mount(ScrollableContainer(info, id = 'info_playlist_scroll'))
            debug("finish_update_info -> END")
        except:
            logger.warning(traceback.format_exc())
            console.log(traceback.format_exc())
        
    async def run_finish_update_info(self, task: asyncio.Task) -> None:
        asyncio.create_task(self.finish_update_info())

    async def update_bar(self) -> None:
        """Method to update the time to the current time."""
        progress_data = await MusicPanel().get_progress_data()
        current_song = ' --- '
        current_artist = ' --- '
        current_album = ' --- '
        value = 0
        max_value = shutil.get_terminal_size()[0]
        remaining_time = 0
        current_state = None
        cover = None


        if progress_data:
            current_song = progress_data['song']
            current_artist = progress_data['artist']
            current_album = progress_data['album']
            value = float(progress_data['current'])
            max_value = float(progress_data['max'])
            remaining_time = progress_data['time']
            current_state = progress_data['state']
            cover = progress_data['cover']
            # debug(cover_image = cover_image)
        
        # song, status = self.get_current_song()
        current_song = f"[bold #ffff00]{current_song}[/]"
        current_artist = f"[bold #55ff00]{current_artist}[/]"
        current_album = f"[bold #FF55FF]{current_album}[/]"
        # elapsed_time = float(status.get('elapsed', 0))
        # total_time = float(status.get('duration', 1))
        # remaining_time = total_time - elapsed_time

        if not self.progress.finished:
            self.progress.update(
                self.progress_task,
                completed=int(value),
                total= int(max_value),
                current_song=f"{current_song} [bold #ffaaff]by[/] {current_artist}",
                current_album = current_album,
                time=int(remaining_time)
            )
        else:
            self.last_title = None

        self.update(self.progress)

        #if song and status and (self.last_state != status.get('state') or self.last_songid != song.get('id')):
        if current_song and (self.last_title != current_song or self.last_state != current_state):
        #if self.last_songid != song.get('id'):
            self.last_title = current_song
            self.last_state = current_state
            
            self.select_current_song_row()
            
            asyncio.create_task(self.update_cover(cover))
            
            asyncio.create_task(self.update_info())
            
            #task_info = asyncio.create_task(self.update_info())
            #task_info.add_done_callback(lambda _: self.finish_update_info())
            #task_info.add_done_callback(self.run_finish_update_info)
            
            asyncio.create_task(self.update_panel())
            
            
            #try:
                #cover_app = self.app.query_one('#cover_playlist')
                #asyncio.create_task(cover_app.update_cover(cover))
            #except:
                #logger.warning(traceback.format_exc())
            #self.app.query_one(Cover).update(Align(display_image(cover, width=50, whiteness_threshold=1, darkness_threshold=0, recursive=False, procedural_printing=False, no_center=True), "center"))
                
            # zfill = len(str(status.get('playlistlength')))
            self.app.notify(f"{current_song} - {current_artist} - {current_album}", title = f'{APP} [{current_state}]', timeout = 10)

            #asyncio.create_task(self.music_control.send_notify())
            asyncio.create_task(self.music_control._send_notify(current_state, {'title': current_song, 'album': current_album}, cover))

class CustomInput(Input):
    """Custom Input widget that overrides key handling."""
    def key_down(self, event: Key) -> None:
        debug(event_key = event.key)
        if event.key == "e":
            # Trigger the app's focus_table action when 'e' is pressed
            self.app.action_focus_table()
            return
        super().key_down(event)  # Call the default key handling for other keys

class STop(Static):

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app')
        kwargs.pop('app')
        super().__init__(*args, **kwargs)
        self.vertical = None

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value

    def compose(self) -> ComposeResult:
        #yield LoadingIndicator(id = "table_stop")
        #yield Cover_and_Info(id = "info_stop", app = self.app)
        yield self.app.table_load_indicator
        #yield Vertical(Cover(id = "cover_playlist"), Info(id = "info_playlist"), id = "info_stop2")
        yield self.app.vertical

    async def on_mount(self) -> None:
        self.refresh()
        #asyncio.sleep(0.1)
        asyncio.create_task(self.run_tasks())

    async def run_update_info(self) -> None:
        info = Info(app = self.app, id = 'info_playlist')
        try:
            await self.update_info(info)
            debug("finish self.update_info(info)")
            debug("remove childred #info_stop")
            self.app.vertical.remove_children('#info_indicator')            
            self.app.vertical.mount(ScrollableContainer(info, id = 'info_playlist_scroll'))
        except:
            logger.warning(traceback.format_exc())        

    async def run_update_cover(self) -> None:
        cover = Cover(app = self.app, id = 'cover_playlist')
        try:
            await self.update_cover(cover)
            debug("finish self.update_info(cover)")
            debug("remove childred #info_stop")
            self.app.vertical.remove_children('#cover_indicator')            
            self.app.vertical.mount(cover)
        except:
            logger.warning(traceback.format_exc())        

    async def run_update_table(self) -> None:
        debug("run_task")

        table = Table(app = self.app, id = "table_playlist")

        await table.load_data()
        #self.run_worker(table.load_data(), exclusive = True)
        debug("self.update_table(table)")
        await self.update_table(table)
        #self.run_worker(self.update_table(table), exclusive = True)
        debug("finish self.update_table(table)")


        #debug("remove childred #table_stop")
        #self.remove_children('#table_stop')
        self.remove_children('#table_playlist')
        debug("mount table")
                
        self.mount(table)
        
    async def run_tasks(self) -> None:    
        #asyncio.create_task(self.run_update_cover_and_info())
        asyncio.create_task(self.run_update_cover())
        asyncio.create_task(self.run_update_info())
        asyncio.create_task(self.run_update_table())

    async def update_table(self, table: Table) -> None:

        debug("Focus on the table")
        table.focus()  # Focus on the table
        debug("add column Track")
        #self.add_columns("Track", "Artist", "Title", "Album", "Year")
        table.add_column("Track", width=5, key = 'track')
        debug("add column Artist")
        table.add_column("Artist", width=30, key = 'artist')
        debug("add column Title")
        table.add_column("Title", width=50, key = 'title')
        debug("add column album")
        table.add_column("Album", width=50, key = 'album')
        debug("add column Year")
        table.add_column("Year", width=10, key = 'year')        
        table.populate_table()

        #debug(row_height_30 = self.get_row_height('Track'))

        debug("set: table.fixed_columns = 1")
        table.fixed_columns = 1
        debug('set: table.cursor_type = "row"')
        table.cursor_type = "row"
        debug("set: table.zebra_stripes = True")
        table.zebra_stripes = True   

        table.select_current_song_row()
        self.app.FIRST = False

        #debug("remove childred")
        #self.remove_children()
        #debug("mount table")
        #self.mount(table)

    async def update_info(self, info: Info) -> None:
        try:
            #info.update_info()
            asyncio.create_task(info.update_info_async())
        except:
            logger.warning(traceback.format_exc())          
    
    async def update_cover(self, cover: Cover) -> None:
        await cover.update_cover()

class SBottom(Static):
    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app')
        kwargs.pop('app')
        super().__init__(*args, **kwargs)

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value

    def compose(self) -> ComposeResult:
        yield MusicPanel(id='static_panel', app=self.app)
        yield PBar(
            Progress(TextColumn("[bold blue]{task.fields[current_song]}", justify="left"),
                     BarColumn(bar_width=shutil.get_terminal_size()[0]),
                     TextColumn("{task.completed}/{task.total}", justify="right"),
                     TextColumn("[bold red]-{task.fields[time]}", justify="right"),
                     console=console),
            id="pbar",
            app=self.app
        )
        yield CustomInput(placeholder='Search', id='input_search')
        #self.app.notify(
            #f"self.app.table_after_header: {self.app.table_after_header}",
            #severity="warning",
            #title = "Table Movement INFO [Bottom]"
        #)        
        #if not self.app.table_after_header:
            #table = Table(id="table_playlist", app=self.app)
            #yield table

            #notification.update_notification(
            #self.app.notify(
                #f"Table position: {'after header' if self.app.table_after_header else 'before footer'}",
                #severity="warning",
                #title = "Table Movement INFO [Bottom]",
                #timeout = 20
            #)
            #notification.show_notification()

#class WrappedFooter(Footer):
    #def __init__(self, *keys, **kwargs):
        #super().__init__(*keys, **kwargs)
        #self.key_texts = [f"{key[0]}: {key[1]}" for key in keys]

    #def render(self) -> Container:
        #lines = []
        #line = []
        #width = 0
        #max_width = self.size.width if self.size else 10  # Default width if not available

        #for key in self.key_texts:
            #if width + len(key) + 1 > max_width:  # Account for spacing
                #lines.append(" ".join(line))
                #line = []
                #width = 0
            #line.append(key)
            #width += len(key) + 1  # Account for spacing
        #lines.append(" ".join(line))  # Append the last line

        ## Combine the lines into the final text
        #wrapped_text = "\n".join(lines)
        #return wrapped_text

class MusicApp(App):

    CSS_PATH = str(Path(__file__).parent / 'css' / 'mpl.tcss')
    BINDINGS = [
        ('x', "play", "Play/Pause"), 
        ('X', "stop", "Stop"), 
        ('n', "next", "Next"), 
        ('p', "previous", "Previous"), 
        Binding(key = 'r', action = "repeat", description = "Repeat All (Ω)"),
        ('S', "single", "Repeat One/Single (Σ)"),
        ('c', "consume", "Consume (Δ)"),
        ('z', "random", "Random (Ϣ)"),
        ('i', "show_cover", "Show Cover"),
        #Binding(key = 'e', action = "focus_table", description = "Move Focus"), 
        Binding(key = 's', action = "focus_search", description = "Search"), 
        Binding(key = 'f', action = "find", description = "Find"), 
        Binding(key = 'b', action = "back", description = "Back Playlist"), 
        Binding(key = 't', action = "move_table", description = "Move Playlist Top/Bottom"), 
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "app.quit", "Quit"),        
        ("esc", "app.quit", "Quit"),        
    ]

    process = None
    TITLE = "MPD-N"
    current_song = CONFIG().client.currentsong()
    FIND = False
    DATA_FIND = []
    table_after_header = True
    FIRST = True

    def __init__(self):
        super().__init__()
        #self.mpd = MusicControl(self)
        self.music_control = MusicControl(app = self)
        #self.s_top = STop(app = self, id = 's_top')
        #self.s_bottom = SBottom(app = self, id = 's_bottom')
        
        self.s_top = STop(app = self, id = 's_top')
        self.s_bottom = SBottom(app = self, id = 's_bottom')
        
        self.vertical = Vertical(LoadingIndicator(id = "cover_indicator"), LoadingIndicator(id = "info_indicator"), id = "info_vertical")
        
        self.table_load_indicator = LoadingIndicator(id = "table_stop")
        self.cover_load_indicator = LoadingIndicator(id = "cover_indicator")
        self.info_load_indicator = LoadingIndicator(id = "info_indicator")

    def compose(self) -> ComposeResult:
        #table = Table(id="table_playlist", app=self)
        #notification = CustomNotification("This is a notification", severity="info", id="notification", app = self)

        yield Header(show_clock=True)
        if self.table_after_header:
            yield self.s_top
            yield self.s_bottom

        else:
            yield self.s_bottom
            yield self.s_top
        #yield notification

        #if self.table_after_header:
            ##notification.update_notification(
            #self.notify(
                #f"Table position: {'after header' if self.table_after_header else 'before footer'}",
                #severity="warning",
                #title = "Table Movement"
            #)
            ##notification.show_notification()
            #table.set_class('dock-top')
            #yield table

        #yield MusicPanel(id='static_panel', app=self)
        #yield PBar(
            #Progress(TextColumn("[bold blue]{task.fields[current_song]}", justify="left"),
                        #BarColumn(bar_width=shutil.get_terminal_size()[0]),
                        #TextColumn("{task.completed}/{task.total}", justify="right"),
                        #TextColumn("[bold red]-{task.fields[time]}", justify="right"),
                        #console=console),
            #id="pbar",
            #app=self
        #)
        #yield CustomInput(placeholder='Search', id='input_search')

        #if not self.table_after_header:
            ##notification.update_notification(
            #self.notify(
                #f"Table position: {'after header' if self.table_after_header else 'before footer'}",
                #severity="warning",
                #title = "Table Movement"
            #)
            ##notification.show_notification()
            #table.set_class('dock-bottom')
            #yield table

        yield Footer()
        #yield WrappedFooter()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection events from the DataTable."""
        selected_row = event.cursor_row  # Use cursor_row instead of row
        os.environ.update({'MPDN_ROW_SELECTED': f'{selected_row}',})
        debug(selected_row = selected_row)
        row_data = self.query_one(Table).get_row_at(selected_row)
        debug(row_data = row_data)
        row_data = self.music_control.normalization(row_data)
        debug(row_data = row_data)

        number = row_data[0][:-1]
        debug(number = number)
        debug(self_FIND = self.FIND)
        debug(self_DATA_FIND = self.DATA_FIND)
        if self.FIND and self.DATA_FIND:
            index = 1
            number_selected = int(number)
            for artist, albums in self.DATA_FIND.items():
                for album, details in albums.items():
                    if index == number_selected:
                        for song in details.get('detail').get(album).get('songs'):
                            debug(song = song)
                            self.music_control.reconnect('add', (song.get('file'), ))
                            time.sleep(0.3)
                        index += 1
                    else:
                        index += 1
            index = 1
            self.FIND = False
            self.DATA_FIND = None
        else:
            play_number = int(number)
            debug(play_number = play_number)
            self.music_control.play(play_number - 1, force = True)
            table = self.query_one(Table)
            table.select_current_song_row(selected_row)

    def on_mount(self) -> None:
        #self.query_one('#s_top').styles.dock = "top"
        #self.query_one('#s_bottom').styles.dock = "bottom"
        self.refresh()
        #table = self.query_one("#table_playlist", Table)
        #table.select_current_song_row()
        #self.footer = self.query_one(WrappedFooter)        

    def action_play(self):
        debug("playing [main]")
        self.music_control.play()

    def action_stop(self):
        return self.music_control.stop()

    def action_pause(self):
        return self.music_control.pause()

    def action_next(self):
        return self.music_control.next()

    def action_previous(self):
        return self.music_control.previous()

    def action_repeat(self):
        self.music_control.set_repeat()
        panel = self.query_one('#static_panel', MusicPanel)
        panel.update_panel()

    def action_single(self):
        self.music_control.set_single()
        panel = self.query_one('#static_panel', MusicPanel)
        panel.update_panel()        

    def action_random(self):
        self.music_control.set_random()
        panel = self.query_one('#static_panel', MusicPanel)
        panel.update_panel()        

    def action_consume(self):
        self.music_control.set_consume()
        panel = self.query_one('#static_panel', MusicPanel)
        panel.update_panel()

    #async def on_key(self, event: Key) -> None:
        #"""Handle key events explicitly."""
        #if self.focused.id == "input_search" and event.key == "e":
            #event.prevent_default()  # Prevent the Input widget from capturing the key
            #await self.action_focus_table()    

    def action_show_cover(self):
        cover = self.music_control.find_cover_art()
        debug(cover = cover)
        if os.path.isfile(cover): imshow(cover)
            #app, viewer = imshow(cover)
            #self.run_qt_event_loop(app, viewer)

            #app = QApplication(sys.argv)
            #viewer = ImageViewer(cover)
            #viewer.show()
            #app.exec_()

    #def run_qt_event_loop(self, app, viewer):
        #def event_loop():
            #app.exec_()
            #self.app.exit()

        #th = threading.Thread(target = event_loop)
        #th.start()
        #th.join()


    @on(Input.Submitted)
    async def search(self, message: Input.Submitted) -> None:
        if self.FIND:
            table = self.query_one(Table)
            _, self.DATA_FIND = table.find(message.value)
            self.set_focus(table)
            
        else:
            table = self.query_one(Table)
            table.search(message.value)
            self.set_focus(table)
            
        self.query_one('#input_search', CustomInput).value = ''

    async def action_focus_table(self) -> None:
        table = self.query_one("#table_playlist", Table)
        self.set_focus(table)

    async def action_focus_search(self) -> None:
        input_part = self.query_one("#input_search", CustomInput)
        self.set_focus(input_part)

    #async def key_home(self) -> None:
        #return self.music_control.play()

    async def action_find(self) -> None:
        self.FIND = True
        input_part = self.query_one("#input_search", CustomInput)
        self.set_focus(input_part)

    async def action_back(self) -> None:
        self.FIND = False
        self.DATA_FIND = None
        table = self.query_one(Table)
        table.populate_table()
        table.select_current_song_row()

    async def action_move_table(self):
        self.table_after_header = not self.table_after_header
        await self.recompose()
        #table = self.query_one("#table_playlist")
        #header = self.query_one(Header)
        #footer = self.query_one(Footer)

        #if table and header and footer:
            #self.notify(f"Table position: {'after header' if self.table_after_header else 'before footer'}", severity="warning", timeout=5, title='Move Table Position')

            #if self.table_after_header:
                ## Remove table and re-add it before footer
                #self.screen.remove_child(table)
                #self.screen.add_child(table, before=footer)
                #self.table_after_header = False
            #else:
                ## Remove table and re-add it after header
                #self.screen.remove_child(table)
                #self.screen.add_child(table, after=header)
                #self.table_after_header = True

            #self.notify(f"Table moved. New position: {'after header' if self.table_after_header else 'before footer'}", severity="warning", timeout=5, title='Move Table Position')

        #else:
            #self.notify("Table, header, or footer not found.", severity="error", timeout=5, title='Move Table Position')

    #async def key_home(self) -> None:
        #return self.music_control.play()


if __name__ == "__main__":
    app = MusicApp()
    app.run()
    