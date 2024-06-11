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
        
        self.settings = QSettings("CUMULUS13", "Deezer Art")
        self.loadSettings()
        
        self.tab = Deezer.find_deezer_tab()
        debug(self_tab = self.tab)
        debug(dir_self_tab = dir(self.tab))
        self.ID = self.tab.id
        debug(self_ID = self.ID)
        
        self.URL = f"ws://127.0.0.1:9222/devtools/page/{self.ID}"
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
            await self.deezer_controller.connect()
            while True:
                data = await self.deezer_controller.get_song_progress()
                if data is not None: self.update_ui_signal.emit(data)  # Emit signal with the new data
                #if data.get('status') == 'pause':
                    #await asyncio.sleep(5)
                #else:
                await asyncio.sleep(1)
    
        loop.run_until_complete(task())    

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
            return self.fetch_cover_lastfm(data.get('artist'), data.get("album"))
    
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
                
                self.titleLabel.setText(data.get('song', 'Unknown Title'))
                self.artistLabel.setText(data.get('artist', 'Unknown Artist'))
                self.albumLabel.setText(data.get('album', 'Unknown Album'))            
                #self.trackDetails.setText(track_info)
    
                if data['state'] == 'play':
                    elapsed_time = float(data.get('current', 0))
                    total_time = float(data.get('max', 1))
                    #self.progressBar.setValue(int(((total_time - elapsed_time) / total_time) * 1000))  # Update progress bar based on song progress
                    self.progressBar.setValue(int((elapsed_time / total_time) * 1000))
    
                cover_art_path = self.find_cover_art(data.get('cover', str(Path(__file__).parent / 'default_cover.png')), data)
                self.albumCover.setPixmap(QPixmap(cover_art_path).scaled(200, 200))
            except Exception as e:
                print("Failed to fetch or update track info:", e)

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
    app = QApplication(sys.argv)
    ex = MusicPlayerGUI()
    ex.show()
    sys.exit(app.exec_())