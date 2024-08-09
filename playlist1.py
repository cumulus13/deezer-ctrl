import logging
import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from mpd import MPDClient
from configset import configset
from pathlib import Path
from rich.console import Console
console = Console()
from rich.logging import RichHandler
from rich.text import Text  
from rich import traceback as rich_traceback
import shutil
rich_traceback.install(theme = 'fruity', max_frames = 30, width = shutil.get_terminal_size()[0])
import time

try:
    from .logger import setup_logging, get_def
except:
    from logger import setup_logging, get_def

os.environ.update({'LOGGING_COLOR': '1',})

if os.getenv('LOGGING_COLOR') == '1':
    setup_logging()
else:
    logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger()

class MPD(MPDClient):
    def __init__(self, host='localhost', port=6600):
        super().__init__()  # Initialize the parent MPDClient class
        self.CONFIGNAME = str(Path(__file__).parent / 'cdart.ini')
        self.CONFIG = configset(self.CONFIGNAME)
        
        self.HOST = self.CONFIG.get_config('host', 'name') or os.getenv('MPD_HOST') or host or '127.0.0.1'
        self.PORT = self.CONFIG.get_config('host', 'port') or os.getenv('MPD_PORT') or port or 6600
        self.CONFIGFILE_NEXT = str(Path(__file__).parent / Normalization.normalization_name(self.HOST.strip()).replace(".", "_")) + ".ini"
        self.CONFIG = configset(self.CONFIGFILE_NEXT)
        if self.CONFIG.get_config('logging', 'color', '1') == 1:
            setup_logging()
        
        self.connect_to_server()

    def connect_to_server(self):
        while True:
            try:
                self.connect(self.HOST, self.PORT)
                #print("Connected to MPD server.")
                logger.info("Connected to MPD server.")
                break
            except ConnectionRefusedError:
                #print("Connection refused. Retrying in 1 second...")
                logger.fatal("Connection refused. Retrying in 1 second...")
                time.sleep(1)

    @staticmethod
    def connection_check(fn):
        def wrapper(self, *args, **kwargs):
            while True:  # Keep trying to call the function until successful
                try:
                    return fn(self, *args, **kwargs)
                #except (mpd.ConnectionError, BrokenPipeError):
                except Exception as e:
                    while True:
                        if str(e) == 'Already connected':
                            try:
                                self.currentsong()
                                break
                            except:
                                pass
                        #print("Connection lost. Reconnecting...")
                        logger.critical("Connection lost. Reconnecting...")
                        try:
                            self.connect(self.HOST, self.PORT)
                            #print("Reconnected to MPD server.")
                            logger.fatal("Reconnected to MPD server.")
                            break  # Exit inner loop once reconnected
                        #except (mpd.ConnectionError, BrokenPipeError):
                        except Exception as e:
                            if os.getenv('TRACEBACK'):
                                logger.error(f"ERROR [2]: {traceback.format_exc()}")
                            else:
                                #print(make_colors("ERROR [1]:", 'lw', 'r') + " " + make_colors(str(e), 'lw', 'r'))
                                logger.error(f"ERROR [1]: {str(e)}")
                                #logger.error(str(e))
                            if str(e) == 'Already connected':
                                logger.alert('disconnecting ...')
                                self.disconnect()
                        time.sleep(1)
        return wrapper

class ImageWidget(QWidget):
    def __init__(self, image_path):
        super().__init__()
        
        self.initUI(image_path)

    def initUI(self, image_path):
        self.layout = QVBoxLayout()

        # Gambar dengan align top
        self.imageLabel = QLabel(self)
        self.imageLabel.setAlignment(Qt.AlignTop)
        pixmap = QPixmap(image_path)  # Ganti dengan path gambar yang sesuai
        self.imageLabel.setPixmap(pixmap)

        self.layout.addWidget(self.imageLabel)
        self.setLayout(self.layout)

class ListWidget(QWidget):
    def __init__(self, items):
        super().__init__()
        self.initUI(items)

    def initUI(self, items):
        self.layout = QVBoxLayout()

        # List vertikal
        self.listWidget = QListWidget(self)

        for item in items:
            listItem = QListWidgetItem(item)
            self.listWidget.addItem(listItem)

        self.layout.addWidget(self.listWidget)
        self.setLayout(self.layout)

        # Signal for selection
        self.listWidget.itemClicked.connect(self.onItemActivated)

    def onItemActivated(self, item):
        print(f'Selected: {item.text()}')

class MainWindow(QWidget):
    def __init__(self):
        self.CONFIGNAME = str(Path(__file__).parent / 'cdart.ini')
        self.CONFIG = configset(self.CONFIGNAME)
                
        self.client = MPDClient()
        
        self.HOSTNAME = self.CONFIG.get_config('host', 'name') or os.getenv('MPD_HOST') or '127.0.0.1'
        self.HOST = self.HOSTNAME
        self.PORT = self.CONFIG.get_config('host', 'port') or os.getenv('MPD_PORT') or 6600
        
        if self.PORT and not isinstance(self.PORT, int):
            if str(self.PORT).isdigit():
                self.PORT = int(self.PORT)
            else:
                self.PORT = 6600
        
        self.timeout = self.CONFIG.get_config('host', 'timeout', 3600) or os.getenv('MPD_TIMEOUT') or 3600
        
        if self.HOST not in ['127.0.0.1', 'localhost', '::1']:
            self.CONFIGFILE_NEXT = str(Path(__file__).parent / self.normalization_name(self.HOST.strip()).replace(".", "_")) + f"_{self.PORT}.ini"
            self.CONFIG = configset(self.CONFIGFILE_NEXT)
                
        super().__init__()
        self.initUI()
        
    @MPD.connection_check
    def reconnect(self, func, args = ()):
        data = None
        if not isinstance(args, tuple): args = (args, )
        while 1:
            try:
                if args:
                    data = getattr(self.client, func)(*args)
                else:
                    data = getattr(self.client, func)()
                break
            except:
                if os.getenv('TRACEBACK'):
                    console.print_exception(show_locals=True, theme = 'fruity', width = shutil.get_terminal_size()[0], max_frames = 30)
                try:
                    self.HOSTNAME = os.getenv('MPD_HOST') or self.CONFIG.get_config('host', 'name') or '127.0.0.1'
                    self.PORT = os.getenv('MPD_PORT') or self.CONFIG.get_config('host', 'port') or 6600
                    
                    if self.PORT and not isinstance(self.PORT, int):
                        if str(self.PORT).isdigit():
                            self.PORT = int(self.PORT)
                        else:
                            self.PORT = 6600
                    try:
                        self.client.disconnect()
                    except:
                        pass
                    logger.warning(f're-connecting to {self.HOSTNAME}:{self.PORT}')
                    self.client.connect(self.HOSTNAME, self.PORT)
                    data = getattr(self.client, func)(*args)
                    break
                except Exception as e:
                    if str(e) == 'Already connected':
                        try:
                            self.client.disconnect()
                        except:
                            pass
                        self.client.connect(self.HOSTNAME, self.PORT)                        
                        break
                    if os.getenv('TRACEBACK'):
                        console.print_exception(show_locals=True, theme = 'fruity', width = shutil.get_terminal_size()[0], max_frames = 30)
                    #print(make_colors(datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f'), 'lc'), make_colors("Failed to re-connection to MPD Server !", 'lw', 'r'))
                    logger.error("Failed to re-connection to MPD Server !")
                    
            time.sleep(1)
            
        return data    

    def parse_data(self, data):
        parsed_data = {}  # Initialize an empty dictionary to store the parsed data
    
        for track in data:  # Iterate through each track in the input data
            album_name = track['album']  # Get the album name of the track
            track_info = {  # Create a dictionary to store track information
                key: track[key] 
                for key in track 
                if key != 'album' and key != 'file'
            }  # Exclude 'album' and 'file' from the track information
    
            # If the album is not in the parsed_data dictionary, add it with an empty playlist
            if album_name not in parsed_data:
                parsed_data[album_name] = {'playlist': []}
    
            # Append the track information to the playlist of the corresponding album
            parsed_data[album_name]['playlist'].append(track_info)  
    
        return parsed_data  # Return the parsed data            
        
    def initUI(self):
        self.layout = QVBoxLayout()

        self.imageListWidget1 = self.createImageListWidget('no_cover1.png', [f'Item {str(i).zfill(3)}' for i in range(1, 50)])
        self.imageListWidget2 = self.createImageListWidget('no_cover2.png', [f'Item {str(i+49).zfill(3)}' for i in range(1, 50)])

        self.layout.addLayout(self.imageListWidget1)
        self.layout.addLayout(self.imageListWidget2)

        self.setLayout(self.layout)

        self.setWindowTitle('Playlist')
        self.setGeometry(100, 100, 800, 800)
        self.show()

    def createImageListWidget(self, image_path, items):
        layout = QHBoxLayout()

        imageWidget = ImageWidget(image_path)
        listWidget = ListWidget(items)

        layout.addWidget(imageWidget)
        layout.addWidget(listWidget)

        return layout

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self.moveListSelection(-1)
        elif event.key() == Qt.Key_Down:
            self.moveListSelection(1)
        elif event.key() == Qt.Key_Return:
            self.selectListItem()

    def moveListSelection(self, step):
        currentListWidget = None
        nextListWidget = None
        currentListWidgetObj = None

        if self.imageListWidget1.itemAt(1).widget().listWidget.hasFocus():
            currentListWidget = self.imageListWidget1.itemAt(1).widget().listWidget
            currentListWidgetObj = self.imageListWidget1.itemAt(1).widget()
            nextListWidget = self.imageListWidget2.itemAt(1).widget().listWidget
        elif self.imageListWidget2.itemAt(1).widget().listWidget.hasFocus():
            currentListWidget = self.imageListWidget2.itemAt(1).widget().listWidget
            currentListWidgetObj = self.imageListWidget2.itemAt(1).widget()
            nextListWidget = self.imageListWidget1.itemAt(1).widget().listWidget

        if currentListWidget:
            currentRow = currentListWidget.currentRow()
            newRow = currentRow + step

            if newRow >= 0 and newRow < currentListWidget.count():
                currentListWidget.blockSignals(True)
                currentListWidget.setCurrentRow(newRow)
                currentListWidget.blockSignals(False)
            elif newRow >= currentListWidget.count() and step > 0:
                nextListWidget.setFocus()
                nextListWidget.setCurrentRow(0)
            elif newRow < 0 and step < 0:
                nextListWidget.setFocus()
                nextListWidget.setCurrentRow(nextListWidget.count() - 1)

    def selectListItem(self):
        currentListWidget = None
        currentListWidgetObj = None

        if self.imageListWidget1.itemAt(1).widget().listWidget.hasFocus():
            currentListWidget = self.imageListWidget1.itemAt(1).widget().listWidget
            currentListWidgetObj = self.imageListWidget1.itemAt(1).widget()
        elif self.imageListWidget2.itemAt(1).widget().listWidget.hasFocus():
            currentListWidget = self.imageListWidget2.itemAt(1).widget().listWidget
            currentListWidgetObj = self.imageListWidget2.itemAt(1).widget()

        if currentListWidget:
            currentItem = currentListWidget.currentItem()
            if currentItem:
                currentListWidgetObj.onItemActivated(currentItem)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    sys.exit(app.exec_())
