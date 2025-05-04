import threading
import time
from tkinter import Tk, Label, Button
from mpd import MPDClient, ConnectionError

# Function to connect to MPD server
def connect_to_mpd(host, port, label):
    try:
        # Create an MPD client object
        client = MPDClient()
        # Connect to the MPD server
        client.connect(host, port)
        # If connection successful, update the label
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
                break
            except:
                try:
                    client.disconnect()
                    client = MPDClient()
                    # Connect to the MPD server
                    client.connect(host, port)                
                    client.currentsong()                    
                except:
                    pass

# Function to run in a thread
def run_mpd_thread(host, port, label):
    while True:
        client = connect_to_mpd(host, port, label)
            
        if client:
            # Connection successful, break the loop
            break
        else:
            # Retry after 5 seconds if connection fails
            time.sleep(5)

# Function to start connection in a new thread
def start_connection_thread(host, port, label):
    thread = threading.Thread(target=run_mpd_thread, args=(host, port, label))
    thread.daemon = True  # Daemonize thread to exit with the main program
    thread.start()

# GUI setup
def create_gui():
    root = Tk()
    root.title("MPD Connection Checker")

    label = Label(root, text="Checking MPD connection...", font=("Arial", 14))
    label.pack(pady=20)

    #button = Button(root, text="Start Connection", command=lambda: start_connection_thread("localhost", 6600, label))
    #button.pack(pady=10)
    
    # no need button just start immediatly and show result from client.currentsong() to a label and if client.currentsong() has changed then update/refresh label

    root.geometry("300x150")
    root.mainloop()

if __name__ == "__main__":
    create_gui()
