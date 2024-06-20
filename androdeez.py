import subprocess
import re
from make_colors import make_colors
from pydebugger.debug import debug
import argparse
import sys
import os
import requests
from configset import configset
from pathlib import Path
import signal

class AndroDeez(object):
    CONFIGNAME = str(Path(__file__).parent / 'androdeez.ini')
    CONFIG = configset(CONFIGNAME)
    SERIAL = ''
    DEVICE = []
    
    
    @classmethod
    def check_adb(self):
        f = os.popen("adb")
        if f.read():
            return True
        elif self.CONFIG.get_config('adb', 'bin'):
            adb_bin_path = self.CONFIG.get_config('adb', 'bin')
            if os.path.isfile(adb_bin_path):
                self.ADB_BIN = adb_bin_path
                return True
            else:
                q = input("Where is ADB Bin?: ")
                if q:
                    if os.path.isdir(q):
                        self.ADB_BIN = q
                    elif q.lower() in ('x', 'q'):
                        sys.exit()
                    else:
                        return False
        return False

    @classmethod
    def check_serials(self):
        check = []
        if self.check_adb():
            check = [re.split(r'\tdevice\n', i)[0] for i in filter(lambda k: 'device\n' in k, os.popen('adb devices').readlines())]
            debug(check=check)
            if len(check) > 1:
                for n, i in enumerate(check, 1):
                    print(make_colors(f"{n:02}.", 'c') + " " + make_colors(i, 'b', 'y'))
                q = input(make_colors('Select number of devices', 'lw', 'bl') + ": ")
                if not q or q.lower() in ('q', 'x', 'exit', 'quit'):
                    print(make_colors('exit ....', 'lw', 'r'))
                    os.kill(os.getpid(), signal.SIGTERM)
                if q.isdigit():
                    if int(q) <= len(check):
                        self.SERIAL = f'-s {check[int(q) - 1]}'
                    else:
                        print(make_colors("Invalid Number!", 'lw', 'r'))
                        os.kill(os.getpid(), signal.SIGTERM)
                else:
                    print(make_colors('You did not select a number!', 'lw', 'r'))
                    os.kill(os.getpid(), signal.SIGTERM)
            elif len(check) == 1:
                self.SERIAL = f'-s {check[0]}'  # Automatically set SERIAL if only one device is found
            
            self.DEVICE = check
            
        return check
    
    @classmethod
    def get_current_song_details(self):
        # Run adb dumpsys command
        result = subprocess.run([self.CONFIG.get_config('adb', 'bin', r'c:\TOOLS\platform-tools\adb.exe'), 'shell', 'dumpsys', 'media_session'], capture_output=True, text=True)
        
        # Split the output into lines
        lines = result.stdout.split('\n')
        
        # Regular expression pattern to match metadata lines
        metadata_pattern = re.compile(r'metadata:\s.*description=(.*?),\s(.*?),\s(.*)')
        
        current_song = None
        current_artist = None
        current_album = None
        
        for line in lines:
            # Search for the metadata line containing song title, artist, and album
            metadata_match = metadata_pattern.search(line)
            
            if metadata_match:
                # Extract the song title, artist, and album
                current_song = metadata_match.group(1).strip()
                current_artist = metadata_match.group(2).strip()
                current_album = metadata_match.group(3).strip()
                break
        
        if current_song and current_artist and current_album:
            print(f"Currently playing: {make_colors(current_song, 'b', 'lc')} by {make_colors(current_artist, 'b', 'ly')} from the album {make_colors(current_album, 'lw', 'm')}")
        else:
            print("No current song found")
            
        return current_song, current_artist, current_album
    
    @classmethod
    def resume(self):
        return subprocess.run([self.CONFIG.get_config('adb', 'bin', r'c:\TOOLS\platform-tools\adb.exe'), 'shell', 'input', 'keyevent', '85'], capture_output=True, text=True)
    
    @classmethod
    def play(self):
        return subprocess.run([self.CONFIG.get_config('adb', 'bin', r'c:\TOOLS\platform-tools\adb.exe'), 'shell', 'input', 'keyevent', '126'], capture_output=True, text=True)
    
    @classmethod
    def pause(self):
        return subprocess.run([self.CONFIG.get_config('adb', 'bin', r'c:\TOOLS\platform-tools\adb.exe'), 'shell', 'input', 'keyevent', '127'], capture_output=True, text=True)
    
    @classmethod
    def next(self):
        return subprocess.run([self.CONFIG.get_config('adb', 'bin', r'c:\TOOLS\platform-tools\adb.exe'), 'shell', 'input', 'keyevent', '87'], capture_output=True, text=True)
    
    @classmethod
    def previous(self):
        return subprocess.run([self.CONFIG.get_config('adb', 'bin', r'c:\TOOLS\platform-tools\adb.exe'), 'shell', 'input', 'keyevent', '88'], capture_output=True, text=True)
    
    @classmethod
    def usage(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-x', '--play', action = 'store_true', help = "Play")
        parser.add_argument('-s', '--pause', action = 'store_true', help = "Pause")
        parser.add_argument('-n', '--next', action = 'store_true', help = "Next Song")
        parser.add_argument('-p', '--previous', action = 'store_true', help = "Previous Song")
        parser.add_argument('-i', '--info', action = 'store_true', help = "Get current song")
        
        if len(sys.argv) == 1:
            parser.print_help()
        else:
            if not self.check_serials():
                print(make_colors("No Device connected !", 'lw', 'r'))
                return 
            args = parser.parse_args()
            if args.play:
                self.play()
            elif args.pause:
                self.pause()
            elif args.next:
                self.next()
            elif args.previous:
                self.previous()
            elif args.info:
                self.get_current_song_details()
            
                
if __name__ == "__main__":
    AndroDeez.usage()
