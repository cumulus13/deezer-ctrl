import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QStackedWidget#, QDesktopWidget
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from mpd import MPDClient
from pydebugger.debug import debug
from rich.console import Console
console = Console()
from rich import traceback as rich_traceback
import shutil
rich_traceback.install(theme = 'fruity', max_frames = 30, width = shutil.get_terminal_size()[0])

class ImageWidget(QWidget):
    def __init__(self, album):
        super().__init__()
        self.initUI(album)

    def initUI(self, album):
        self.layout = QVBoxLayout()

        # QLabel untuk album dan tahun
        self.albumLabel = QLabel(f"{album['album']} ({album['year']})")
        self.albumLabel.setAlignment(Qt.AlignCenter)
        self.albumLabel.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.layout.addWidget(self.albumLabel)

        # Gambar dengan align top
        self.imageLabel = QLabel(self)
        self.imageLabel.setAlignment(Qt.AlignTop)

        pixmap = self.read_picture(album['album'])
        if pixmap:
            self.imageLabel.setPixmap(pixmap)

        self.layout.addWidget(self.imageLabel)
        self.setLayout(self.layout)

    def read_picture(self, album):
        client = MPDClient()
        client.connect("localhost", 6600)
        album_info = client.list('album', album)
        if album_info:
            album_art = client.albumart(album_info[0])['binary']
            pixmap = QPixmap()
            pixmap.loadFromData(album_art)
            client.close()
            client.disconnect()
            return pixmap
        client.close()
        client.disconnect()
        return None

class ListWidget(QWidget):
    def __init__(self, album):
        super().__init__()
        self.initUI(album)

    def initUI(self, album):
        self.layout = QVBoxLayout()

        # List vertikal
        self.listWidget = QListWidget(self)

        client = MPDClient()
        client.connect("localhost", 6600)
        songs = client.find('album', album['album'])

        max_digits = len(str(len(songs)))

        for i, song in enumerate(songs, start=1):
            listItem = QListWidgetItem(f"{str(i).zfill(max_digits)}. {song['title']} / {song['artist']} / {song['album']}")
            self.listWidget.addItem(listItem)

        client.close()
        client.disconnect()

        self.layout.addWidget(self.listWidget)
        self.setLayout(self.layout)

        # Signal for selection
        self.listWidget.itemClicked.connect(self.onItemActivated)

    def onItemActivated(self, item):
        print(f'Selected: {item.text()}')

class LoadingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.loadingLabel = QLabel(self)
        self.loadingLabel.setAlignment(Qt.AlignCenter)

        movie = QMovie('loading.gif')  # Path to your loading GIF
        self.loadingLabel.setMovie(movie)
        movie.start()

        self.layout.addWidget(self.loadingLabel)
        self.setLayout(self.layout)

class AlbumLoader(QThread):
    albumsLoaded = pyqtSignal(list)

    def run(self):
        client = MPDClient()
        client.connect("localhost", 6600)
        with console.status("[cyan bold]Get playlist info[/]", spinner = "dots2") as status:
            while 1:
                try:
                    status.update("[cyan bold]Get playlist info[/]", spinner = "dots2")
                    playlist = client.playlistinfo()
                    break
                except Exception as e:
                    status.update(str(e), spinner = 'point')

        album_data = {}
        for song in playlist:
            album = song.get('album', 'Unknown Album')
            year = song.get('year', 'Unknown')
            if album not in album_data:
                album_data[album] = {
                    'album': album,
                    'year': year,
                    'songs': []
                }
            album_data[album]['songs'].append(song)
        
        debug(album_data = album_data, debug = 1)
        client.close()
        client.disconnect()
        self.albumsLoaded.emit(list(album_data.values()))

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: black;")
        self.layout = QVBoxLayout()
        self.stackedWidget = QStackedWidget(self)
        
        self.loadingWidget = LoadingWidget()
        self.stackedWidget.addWidget(self.loadingWidget)

        self.setLayout(self.layout)
        self.layout.addWidget(self.stackedWidget)

        self.setWindowTitle('Playlist')
        gif = QMovie('loading.gif')
        self.gif = gif.currentImage()
        #self.setGeometry(10, 75, self.gif.width(), self.gif.height())
        
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())
        self.move(frameGm.topLeft().x(), 75)
        self.resize(self.gif.width(), self.gif.height())
        #self.resize(800, 600)
        #self.stackedWidget.setFixedSize(self.gif.width(), self.gif.height())
        #self.stackedWidget.setFixedSize(1000, 600)
            
        self.albumLoader = AlbumLoader()
        self.albumLoader.albumsLoaded.connect(self.onAlbumsLoaded)
        self.albumLoader.start()

        self.show()

    def onAlbumsLoaded(self, albums):
        self.albums = albums
        debug(self_albums = self.albums, debug = 1)
        self.setStyleSheet("background-color: white;")
        #self.setGeometry(10, 35, 600, 800)
        #self.resize(600, 800)
        self.imageListWidget1 = self.createImageListWidget(self.albums[0])
        self.imageListWidget2 = self.createImageListWidget(self.albums[1])

        mainWidget = QWidget()
        mainLayout = QVBoxLayout()
        mainLayout.addLayout(self.imageListWidget1)
        mainLayout.addLayout(self.imageListWidget2)
        mainWidget.setLayout(mainLayout)

        self.stackedWidget.addWidget(mainWidget)
        self.stackedWidget.setCurrentWidget(mainWidget)

    def createImageListWidget(self, album):
        layout = QHBoxLayout()

        imageWidget = ImageWidget(album)
        listWidget = ListWidget(album)

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
