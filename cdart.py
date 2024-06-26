import mimetypes
import sys
import os
import asyncio
import requests
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, QSizePolicy, QProgressBar
from PyQt5.QtGui import QPixmap, QIcon, QFont, QKeySequence, QPainter
from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QPoint, pyqtSlot, QSize, QSettings
from mpd import MPDClient
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from deezer_ws import DeezerController
from deezer import Deezer
from pydebugger.debug import debug
import threading
import asyncio
from asyncqt import QEventLoop
from pathlib import Path
from unidecode import unidecode
import re
from make_colors import make_colors
import traceback
from xnotify import notify
from configset import configset
import deezer_art
import traceback

class Deezer:
    def __init__(self, host='localhost', port=6600):
        self.CONFIGNAME = str(Path(__file__).parent / 'cdart.ini')
        self.CONFIG = configset(self.CONFIGNAME)
        
        self.HOST = os.getenv('MPD_HOST') or self.CONFIG.get_config('host', 'name', '127.0.0.1')
        self.PORT = os.getenv('MPD_PORT') or self.CONFIG.get_config('host', 'port', 6600)
        self.CONFIGFILE_NEXT = str(Path(__file__).parent / Normalization.normalization_name(self.HOST.strip()).replace(".", "_")) + ".ini"
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

    @staticmethod
    def connection_check(fn):
        def wrapper(self, *args, **kwargs):
            while True:  # Keep trying to call the function until successful
                try:
                    return fn(self, *args, **kwargs)
                except (ConnectionError, BrokenPipeError):
                    print("Connection lost. Reconnecting...")
                    while True:
                        try:
                            self.connect(self.HOST, self.PORT)
                            print("Reconnected to MPD server.")
                            break  # Exit inner loop once reconnected
                        except (mpd.ConnectionError, BrokenPipeError):
                            time.sleep(1)
        return wrapper



class LastFM(object):
    
    CONFIGNAME = str(Path(__file__).parent / 'cdart.ini')
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

class ScrollingLabel(QLabel):
    
    update_ui_signal = pyqtSignal(dict)
    
    def __init__(self, text='', parent=None):
        super(ScrollingLabel, self).__init__(text, parent)  # Initialize QLabel part
        self.textWidth = self.fontMetrics().width(self.text())
        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_timeout)
        
        # Only start the timer if the text is wider than the label
        if self.textWidth > self.width():
            self.timer.start(100)
        else:
            self.timer.stop()

    def setText(self, text):
        super().setText(text)
        self.textWidth = self.fontMetrics().width(text)
        if self.textWidth > self.width():
            if not self.timer.isActive():
                self.timer.start(100)
        else:
            self.timer.stop()
        self.update()

    def timer_timeout(self):
        self.offset += 1
        if self.offset > self.textWidth + self.width():
            self.offset = 0  # Reset offset to create a continuous loop
        self.update()

    #def paintEvent(self, event):
        #painter = QPainter(self)
        #if self.textWidth > self.width():
            ## Draw text at the calculated offset to create a scrolling effect
            #painter.drawText(-self.offset, self.height() // 2 + self.fontMetrics().ascent() / 2, self.text())
        #else:
            #super().paintEvent(event)  # Use the default painting method
            
    def paintEvent(self, event):
        painter = QPainter(self)
        if self.textWidth > self.width():
            # Create a QPoint object for the position
            position = QPoint(-self.offset, self.height() // 2 + self.fontMetrics().ascent() // 2)
    
            # Draw the text using the QPoint position
            painter.drawText(position, self.text())
        else:
            super().paintEvent(event)
    

class MusicPlayerGUI(QWidget):
    update_ui_signal = pyqtSignal(dict)
    
    def __init__(self):
        #super().__init__()
        super(MusicPlayerGUI, self).__init__()
        
        self.CONFIGNAME = str(Path(__file__).parent / 'cdart.ini')
        self.CONFIG = configset(self.CONFIGNAME)
        
        self.ALBUM = {}
        
        self.settings = QSettings("CUMULUS13", "Deezer Art")
        self.loadSettings()
        
        self.tab = Deezer.find_deezer_tab()
        debug(self_tab = self.tab)
        debug(dir_self_tab = dir(self.tab))
        self.ID = self.tab.id
        debug(self_ID = self.ID)
        
        self.URL = f"ws://127.0.0.1:{self.CONFIG.get_config('debugging', 'port', 9222)}/devtools/page/{self.ID}"
        self.deezer_controller = DeezerController(self.URL)
                
        self.initUI()
        
        #self.startTimer()
        self.oldPos = self.pos()  # Position tracking for moving window
        
        self.update_ui_signal.connect(self.update_gui)

        self.start_deezer_thread()
        #self.timer = QTimer(self)
        #self.timer.timeout.connect(self.fetch_and_update_song_progress)
        #self.timer.start(1000)  # Update every second
        
    def start_deezer_thread(self):
        # Start the asyncio event loop in a separate thread
        threading.Thread(target=self.run_deezer_controller, daemon=True).start()
        
    def run_deezer_controller(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
        async def task():
            last_song = ''
            await self.deezer_controller.connect()
            while True:
                data = await self.deezer_controller.get_song_progress()
                if data:
                    debug(cover = data.get('cover'))
                    album = data.get('album')
                    if not album:
                        if self.ALBUM.get(data.get('artist')):
                            if self.ALBUM.get(data.get('artist')).get(data.get('song')):
                                album = self.ALBUM.get(data.get('artist')).get(data.get('song')).get('album')
                    if not album:
                        album = deezer_art.get_info(data.get('artist'), data.get('song'))
                        if album and album.get('data'):
                            album = album.get('data')[0].get('album').get('title')
                            update_data = {data.get('artist'): {data.get('song'): {'album': album,},}}
                            if not self.ALBUM.get(data.get('artist')): self.ALBUM.update({data.get('artist'): {},})
                            self.ALBUM.get(data.get('artist')).update(
                                update_data.get(data.get('artist'))
                            )
                            
                    self.update_ui_signal.emit(data)  # Emit signal with the new data
                    debug(album_1 = album)
                    debug(self_ALBUM_1 = self.ALBUM)
                    if data.get('song') != last_song:
                        last_song = data.get('song')
                        debug(album_send_to_growl = album)
                        notify.send('Deezer CDArt', 'New Song', 'Deezer CDArt', f"{data.get('song')}\n{data.get('artist')}\n{(album or '')}", ['New Song'], icon = (self.find_cover_art(data.get('cover'), data) or str(Path(__file__).parent / 'icon.png')))
                        print()
                #if data.get('status') == 'pause':
                    #await asyncio.sleep(5)
                #else:
                await asyncio.sleep(1)
    
        #loop.run_until_complete(task())
        
        while 1:
            try:
                #loop = asyncio.get_event_loop()
                loop.run_until_complete(task())
            except Exception as e:
                print(make_colors("ERROR:", 'lw', 'r') + " " + make_colors(e, 'lw', 'bl'))
                if os.getenv('TRACEBACK') == '1' or self.CONFIG.get_config('debug', 'traceback') == 1:
                    print(make_colors("ERROR [1]:", 'lw', 'r') + " " + make_colors(traceback.format_exc(), 'lw', 'bl'))
                

    def initUI(self):
        
        self.setAttribute(Qt.WA_TranslucentBackground)  # Make the background transparent
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)  # Remove window frame

        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(1)  # Reduced spacing between widgets

        self.albumCover = QLabel(self)
        self.albumCover.setPixmap(QPixmap('default_cover.png').scaled(200, 200))
        self.albumCover.setStyleSheet("position: top; bottom: 0; left: 50%; max-height: 200px; ")
        
        #self.trackDetails = QLabel("Track details will appear here", self)
        #self.trackDetails = ScrollingLabel(self)
        #self.trackDetails.setStyleSheet("QLabel { color : lightgreen; }")  # Set text color to light green
        ##self.trackDetails.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        #self.trackDetails.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        #self.trackDetails.setFixedHeight(20)
        
        self.titleLabel = ScrollingLabel("Title will appear here", self)
        self.titleLabel.setStyleSheet("QLabel { color: #1EFF05; }")
        
        self.artistLabel = ScrollingLabel("Artist will appear here", self)
        self.artistLabel.setStyleSheet("QLabel { color: #FFF000; }")
        
        self.albumLabel = ScrollingLabel("Album will appear here", self)
        self.albumLabel.setStyleSheet("QLabel { color: #00FFFF; }")
        
        for label in (self.titleLabel, self.artistLabel, self.albumLabel):
            #label.setStyleSheet("QLabel { color: lightgreen; }")
            label.setFixedHeight(17)
            #label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(1000)  # Arbitrary max value for the progress bar
        self.progressBar.setFixedHeight(5)  # Make the progress bar thinner
        self.progressBar.setStyleSheet(
            "QProgressBar {border: 1px solid grey; border-radius: 2px; background-color: #333;}"
            "QProgressBar::chunk {background-color: #00FF00; width: 1px;}"
        )
        self.progressBar.setTextVisible(False)  # Turn off text visibility

        self.mainLayout.addWidget(self.albumCover)
        #self.mainLayout.addWidget(self.trackDetails)
        self.mainLayout.addWidget(self.titleLabel)
        self.mainLayout.addWidget(self.artistLabel)
        self.mainLayout.addWidget(self.albumLabel)        
        self.mainLayout.addWidget(self.progressBar)
        self.setLayout(self.mainLayout)

        self.setWindowTitle('Deezer CD Art')
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icon.png')))
        self.setFixedSize(230, 310)  # Fixed size of the window
        
    def play(self):
        #self.connect().pause()
        return Deezer.play(tab = self.tab)
    
    def pause(self):
        return Deezer.pause(tab = self.tab)
    
    def stop(self):
        return Deezer.pause(tab = self.tab)
    
    def next(self):
        return Deezer.next(tab = self.tab)
    
    def previous(self):
        return Deezer.previous(tab = self.tab)
    
    def set_repeat(self):
        pass    

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Q or event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_P and event.modifiers() & Qt.ShiftModifier:
            self.pause()
        elif event.key() == Qt.Key_P:
            self.play()        
        elif event.key() == Qt.Key_N and event.modifiers() & Qt.ShiftModifier:
            self.previous()        
        elif event.key() == Qt.Key_N:
            self.next()
        elif event.key() == Qt.Key_A and event.modifiers() & Qt.ShiftModifier:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self.show()
        elif event.key() == Qt.Key_A:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            self.show()
            
    def find_cover_art(self, song_path, data):
            
        if sys.platform == 'win32':
            temp_dir = os.getenv('TEMP') or os.getenv('TMP', str(Path(__file__).parent))
        else:
            temp_dir = os.getenv('TEMP') or os.getenv('TMP', "/tmp")
            
        if (Path(temp_dir) / self.normalization_name(data.get('song'))).is_file():
            debug("song_path is FILE !")
            return str(Path(temp_dir) / self.normalization_name(data.get('song')))        
                
        if os.path.isfile(os.path.join(temp_dir, self.normalization_name(data.get('song'))) + ".jpg"):
            return os.path.join(temp_dir, self.normalization_name(data.get('song'))) + ".jpg"
        elif os.path.isfile(os.path.join(temp_dir, self.normalization_name(data.get('song'))) + ".png"):
            return os.path.join(temp_dir, self.normalization_name(data.get('song'))) + ".png"
        elif os.path.isfile(song_path):
            directory = os.path.dirname(song_path)
            for filename in os.listdir(directory):
                if filename.lower() in ['cover.jpg', 'album.jpg', 'folder.jpg']:
                    return os.path.join(directory, filename)
                
            try:
                audio = MP3(song_path, ID3=ID3)
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        cover_data = tag.data
                        temp_path = 'temp_cover.jpg'
                        with open(temp_path, 'wb') as img_file:
                            img_file.write(cover_data)
                        return temp_path
            except Exception as e:
                print("No embedded cover art found:", e)
            
                
        elif song_path[:7] == 'http://' or song_path[:8] == 'https://':    
            ext = ".jpg"
            debug(song_path = song_path)
            cover_data = requests.get(song_path, stream = True)
            debug(cover_data_headers = cover_data.headers)
            if 'content-type' in cover_data.headers:
                ext = mimetypes.guess_extension(cover_data.headers.get('content-type'))
            with open(str(Path(temp_dir) / self.normalization_name(data.get('song'))) + ext, 'wb') as cover_file:
                cover_file.write(cover_data.content)
            
            return str(Path(temp_dir) / self.normalization_name(data.get('song'))) + ext
        else:
            cover = deezer_art.get_album_art(data.get('artist'), data.get('title'), data.get('album'), True)
            if not cover:
                return self.find_cover_art_lastfm(data)
        return str(Path(__file__).parent / 'default_cover.png')    
        
    def find_cover_art_lastfm(self, data):
        if os.path.isfile(str(Path(os.getenv('temp', '/tmp')) / Path('lastfm_' + self.normalization_name(data.get('title')) + ".jpg"))):
            return str(Path(os.getenv('temp', '/tmp')) / Path(self.normalization_name(data.get('title')) + ".jpg"))
        elif os.path.isfile(str(Path(os.getenv('temp', '/tmp')) / Path('lastfm_' + self.normalization_name(data.get('title')) + ".png"))):
            return str(Path(os.getenv('temp', '/tmp')) / Path(self.normalization_name(data.get('title')) + ".png"))
        
        artist = data.get('artist') or ''
        album = data.get('album') or ''
        track = data.get('song') or ''
        
        if artist and album:
            api_key = self.CONFIG.get_config('lastfm', 'api') or "c725344c28768a57a507f014bdaeca79"
            url = f"http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={api_key}&artist={artist}&album={album}&format=json"
            a = requests.get(url)
            if a.status_code == 200:
                try:
                    url1 = a.json()['album']['image'][-1]['#text']
                    ext = os.path.splitext(url1)[-1]
                    if not ext in ['.png', '.jpg', '.jpeg']:
                        ext = ".png"
                    temp_path = str(Path(os.getenv('temp', '/tmp')) / Path('lastfm_' + self.normalization_name(data.get('title')) + ext))
                    with open(temp_path, 'wb') as f:
                        f.write(requests.get(url1).content)
                    return temp_path
                except Exception as e:
                    print("failed to get cover art from LastFM:", e)
    
        elif artist and track:
            cover_data = LastFM.get_track_info(artist, track)
            if cover_data.get('album_image')[:4] == "http" and "://" in cover_data.get('album_image'):
                ext = os.path.splitext(url1)[-1]
                cover_stream = requests.get(cover_data.get('album_image'))
                if not ext and cover_stream.headers.get('content-type'):
                    ext = mimetypes.guess_extension(cover_stream.get('content-type'))
                if not ext in ['.png', '.jpg', '.jpeg']: ext = ".png"
                temp_path = str(Path(os.getenv('temp', '/tmp')) / Path('lastfm_' + self.normalization_name(data.get('title')) + ext))
                with open(temp_path, 'wb') as f:
                    f.write(cover_stream.content)
                return temp_path
        return False
    
    def normalization_name(self, name):
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

    @pyqtSlot(dict)
    def update_gui(self, data):
        '''
            example: data = {'current': '94', 'now': '93.96239100000003', 'max': '194', 'time': '03:14', 'song': 'haruka', 'artist': 'Aimer', 'album': 'haruka / 800 / End of All / Ref:rain -3 nuits version-', 'cover': 'https://e-cdns-images.dzcdn.net/images/cover/ef9b2fecea3af73ffb33dc73fdfd8e07/500x500.jpg', 'state': 'play'}
        '''
        debug(data = data)
        if data:
            try:
                #current_song = data.get('song')
                #album = current_song.get('album') or ''
                #track_info = f"{current_song.get('title', 'Unknown Title')}\n{current_song.get('artist', 'Unknown Artist')}\n{album}"
                album = data.get('album')
                if not album:
                    if self.ALBUM.get(data.get('artist')):
                        if self.ALBUM.get(data.get('artist')).get(data.get('song')):
                            album = self.ALBUM.get(data.get('artist')).get(data.get('song')).get('album')
                if not album:
                    album = deezer_art.get_info(data.get('artist'), data.get('song'))
                    if album and album.get('data'):
                        album = album.get('data')[0].get('album').get('title')
                        update_data = {data.get('artist'): {data.get('song'): {'album': album,},}}
                        if not self.ALBUM.get(data.get('artist')): self.ALBUM.update({data.get('artist'): {},})
                        self.ALBUM.get(data.get('artist')).update(
                            update_data.get(data.get('artist'))
                        )
                        
                debug(album_0 = album)
                debug(self_ALBUM_0 = self.ALBUM)                
                    
                self.titleLabel.setText(data.get('song', 'Unknown Title'))
                self.artistLabel.setText(data.get('artist', 'Unknown Artist'))
                self.albumLabel.setText((album or 'Unknown Album'))            
                #self.trackDetails.setText(track_info)
    
                if data['state'] == 'play':
                    elapsed_time = float(data.get('current', 0))
                    total_time = float(data.get('max', 1))
                    #self.progressBar.setValue(int(((total_time - elapsed_time) / total_time) * 1000))  # Update progress bar based on song progress
                    self.progressBar.setValue(int((elapsed_time / total_time) * 1000))
    
                cover_art_path = self.find_cover_art(data.get('cover'), data)
                self.albumCover.setPixmap(QPixmap(cover_art_path).scaled(200, 200))
            except Exception as e:
                print("Failed to fetch or update track info:", e)
                #if os.getenv('TRACEBACK') == "1":
                print(traceback.format_exc())

    #def startTimer(self):
        #self.timer = QTimer(self)
        #self.timer.timeout.connect(self.updateTrackInfo)
        #self.timer.start(1000)  # Update every second for smoother progress bar updates
        
    def fetch_and_update_song_progress(self):
        data = self.deezer_controller.get_song_progress()
        print("data:", data)  # Debugging output
        self.update_ui_signal.emit(data)
        
    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()
    
    def saveSettings(self):
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("size", self.size())
    
    def loadSettings(self):
        pos = self.settings.value("pos", QPoint(200, 200))
        size = self.settings.value("size", QSize(400, 300))
        self.move(pos)
        self.resize(size)    
        
    def closeEvent(self, event):
        self.saveSettings()
        event.accept()

if __name__ == '__main__':
    print(make_colors("PID:", 'lw', 'bl') + " " + make_colors(os.getpid(), 'lw', 'r'))
    print(make_colors('Deezer CDArt', 'lw', 'm'))
    app = QApplication(sys.argv)
    ex = MusicPlayerGUI()
    ex.show()
    sys.exit(app.exec_())