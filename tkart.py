import threading
import time
from tkinter import Tk, Label, PhotoImage, Canvas, Toplevel
from mpd import MPDClient, ConnectionError
from PIL import Image, ImageTk
import io
import os
from datetime import datetime
from pydebugger.debug import debug
import traceback
from rich import traceback as rich_traceback, console
console = console.Console()
import shutil
rich_traceback.install(theme='fruity', max_frames=30, width=shutil.get_terminal_size()[0])

def get_date():
    return datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S.%f')

# Function to connect to MPD server
def connect_to_mpd(host, port, label):
    print(f"{get_date()} try connect_to_mpd ...")
    client = MPDClient()
    try:
        # Connect to the MPD server
        client.connect(host, port)
        label.config(text="Connected to MPD Server")
        return client
    except ConnectionError as e:
        label.config(text="Connection failed: " + str(e))
        return None
    except Exception as e:
        if 'already connect' in str(e):
            try:
                client = MPDClient()
                # Connect to the MPD server
                client.connect(host, port)                
                client.currentsong()
                return client
            except:
                try:
                    client.disconnect()
                    client = MPDClient()
                    # Connect to the MPD server
                    client.connect(host, port)                
                    client.currentsong()
                    return client
                except:
                    return None
        else:
            try:
                client.disconnect()
                client = MPDClient()
                # Connect to the MPD server
                client.connect(host, port)                
                client.currentsong()
                return client
            except:
                label.config(text="Connection failed [2]: " + str(e))
                return None

# Function to update the current song, artist, album, and cover art
def update_current_song(client, label_track, label_artist, label_album, canvas, progress_canvas):
    previous_song = None
    while True:
        try:
            current_song = client.currentsong()
            song_title = current_song.get('title', 'Unknown Track')
            artist = current_song.get('artist', 'Unknown Artist')
            album = current_song.get('album', 'Unknown Album')
            date = current_song.get('date', 'Unknown Year')
            
            # Update the labels if the song has changed
            if current_song != previous_song:
                label_track.full_text = f"{song_title}"
                label_artist.full_text = f"{artist}"
                label_album.full_text = f"{album} ({date})"

                update_cover_art(client, current_song, canvas)  # Update the cover art
                reset_ticker(label_track)
                reset_ticker(label_artist)
                reset_ticker(label_album)

                previous_song = current_song

            # Update progress bar
            update_progress_bar(client, progress_canvas)

            time.sleep(1)
        
        except ConnectionError as e:
            label_track.config(text="Lost connection to MPD server")
            break

# Ticker (running text) function
def reset_ticker(label):
    full_text = label.full_text
    label.config(text=full_text)  # Reset to the full text

    # Update the label so we can calculate the text width
    label.update_idletasks()

    # If the text is wider than the label's visible width, start the ticker
    if label.winfo_reqwidth() > label.winfo_width():
        label.after(1000, lambda: start_ticker(label))  # Delay the start of the ticker by 1 second

def start_ticker(label):
    current_text = label.cget("text")
    # Move the first character to the end and update the label
    label.config(text=current_text[1:] + current_text[0])
    label.after(200, lambda: start_ticker(label))  # Update every 200ms

# Function to update cover art from MPD
def update_cover_art(client, current_song, canvas):
    try:
        file_path = current_song.get('file')
        debug(file_path = file_path, debug = 1)
        if file_path:
            cover_data = client.readpicture(file_path)
            if cover_data and cover_data.get('binary'):
                image_data = io.BytesIO(cover_data['binary'])
                image = Image.open(image_data)
                image = image.resize((100, 100), Image.ANTIALIAS)  # Resize to fit canvas
                photo = ImageTk.PhotoImage(image)

                canvas.delete("all")
                canvas.create_image(50, 50, image=photo)
                canvas.image = photo  # Keep reference to avoid garbage collection
                
                # Store image for displaying in the new window
                canvas.full_image = ImageTk.PhotoImage(image)  # Store the full image
    except Exception as e:
        console.print_exception(theme = 'fruity', width = shutil.get_terminal_size()[0], max_frames = 30)
        print("Failed to load cover art:", e)
        print("-" * shutil.get_terminal_size()[0])
        print(traceback.format_exc())

# Function to update the progress bar
def update_progress_bar(client, progress_canvas):
    try:
        status = client.status()
        elapsed_time = float(status.get('elapsed', 0))
        total_time = float(status.get('duration', 1))
        progress = (elapsed_time / total_time) * 100 if total_time > 0 else 0
        
        # Clear the previous progress bar
        progress_canvas.delete("progress_bar")
        
        # Draw a thin rectangle as the progress bar
        progress_canvas.create_rectangle(0, 0, progress, 5, fill="blue", tags="progress_bar")
    except:
        pass

# Function to run MPD connection in a thread
def run_mpd_thread(host, port, label_track, label_artist, label_album, canvas, progress_canvas):
    client = None
    while not client:
        client = connect_to_mpd(host, port, label_track)
        if client:
            update_current_song(client, label_track, label_artist, label_album, canvas, progress_canvas)
        else:
            time.sleep(5)  # Retry connection every 5 seconds if connection fails

# Start connection in a new thread
def start_connection_thread(host, port, label_track, label_artist, label_album, canvas, progress_canvas):
    thread = threading.Thread(target=run_mpd_thread, args=(host, port, label_track, label_artist, label_album, canvas, progress_canvas))
    thread.daemon = True
    thread.start()

# Function to make the window borderless and transparent
def toggle_borderless(root):
    root.attributes('-fullscreen', False)
    root.overrideredirect(True)
    root.config(bg='systemTransparent')  # Windows
    root.attributes('-alpha', 0.0)  # Set transparency (for Unix/Linux systems)

# Function to display the cover image in a new window
def show_cover(canvas):
    if hasattr(canvas, 'full_image'):
        new_window = Toplevel()
        img = canvas.full_image._PhotoImage__photo  # Get the original image
        width, height = img.width(), img.height()

        # Limit the size of the new window
        max_size = 1200
        if width > max_size or height > max_size:
            aspect_ratio = width / height
            if width > height:
                width = max_size
                height = int(width / aspect_ratio)
            else:
                height = max_size
                width = int(height * aspect_ratio)

        new_window.geometry(f'{width}x{height}')
        new_window.title('Cover Art')
        new_canvas = Canvas(new_window, width=width, height=height)
        new_canvas.pack()

        # Display the image in the new window
        new_canvas.create_image(width//2, height//2, image=canvas.full_image)

# GUI setup
def create_gui():
    root = Tk()
    root.title("MPD Current Song Display")
    
    # Set max size to 150x150 pixels
    root.geometry("165x165")
    root.resizable(False, False)

    # Create a canvas to display the album cover
    canvas = Canvas(root, width=100, height=100)
    canvas.pack(pady=2)

    # Create labels for track title, artist, and album (with year)
    label_track = Label(root, text="Track", anchor='w', justify='left', font=("Arial", 7))
    label_track.pack()

    label_artist = Label(root, text="Artist", anchor='w', justify='left', font=("Arial", 7))
    label_artist.pack()

    label_album = Label(root, text="Album", anchor='w', justify='left', font=("Arial", 7))
    label_album.pack()

    # Add text attributes to store full text for ticker
    label_track.full_text = label_track.cget("text")
    label_artist.full_text = label_artist.cget("text")
    label_album.full_text = label_album.cget("text")

    # Create a canvas for a custom thin progress bar
    progress_canvas = Canvas(root, width=100, height=5)
    progress_canvas.pack(pady=2)

    # Start the connection thread immediately
    host = os.getenv('MPD_HOST') or '127.0.0.1'
    port = os.getenv('MPD_PORT') or 6600
    start_connection_thread(host, port, label_track, label_artist, label_album, canvas, progress_canvas)

    # Bind 'q' and 'esc' keys to quit
    root.bind('<q>', lambda event: root.quit())
    root.bind('<Escape>', lambda event: root.quit())

    # Bind 'a' key to toggle borderless and transparency
    root.bind('<a>', lambda event: toggle_borderless(root))

    # Bind 's' key to open the cover image in a new window
    root.bind('<s>', lambda event: show_cover(canvas))

    root.mainloop()

if __name__ == "__main__":
    create_gui()

