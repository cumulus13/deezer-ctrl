from mpd import MPDClient
from pydebugger.debug import debug
from make_colors import make_colors
from multiprocessing import Process, Manager
import traceback
import time
import os
import sys
from datetime import datetime

def connection_watch(shared_data, host, port, timeout):
    client = MPDClient()
    while True:
        try:
            print(f"{make_colors(datetime.strftime(datetime.now(),  '%Y/%m/%d %H:%M:%S,%f'), 'b', 'ly')} [{make_colors('Connection Watch', 'lw', 'm')}] {make_colors('Start connecting ...', 'lw','bl')} {make_colors('[1]', 'b', 'ly')}")
            client.connect(host, port, timeout)
            status = client.status()
            shared_data['current_song'] = client.currentsong()
        except Exception as e:
            print("E 0:", make_colors(str(e), 'lw', 'm'))
            if str(e) == 'Already connected':
                try:
                    shared_data['current_song'] = client.currentsong()
                    status = client.status()
                except Exception as e:
                    print("E 1:", make_colors(str(e), 'lw', 'm'))
                    if os.getenv('traceback') == '1': print(make_colors(traceback.format_exc(), 'lw', 'bl'))
                    try:
                        client.disconnect()
                        client.connect(host, port, timeout)
                        status = client.status()
                        shared_data['current_song'] = client.currentsong()
                    except:
                        if os.getenv('traceback') == '1': print(make_colors(traceback.format_exc(), 'b', 'g'))
            else:
                try:
                    client.connect(host, port, timeout)
                    status = client.status()
                    shared_data['current_song'] = client.currentsong()
                except Exception as e:
                    print("E 2:", make_colors(str(e), 'lw', 'm'))
                    if os.getenv('traceback') == '1': print(make_colors(traceback.format_exc(), 'lw', 'm'))
            time.sleep(5)

class Ticker:

    def __init__(self):
        self.manager = Manager()
        self.shared_data = self.manager.dict()
        self.shared_data['current_song'] = None

        self.HOST = os.getenv('MPD_HOST') or '127.0.0.1'
        self.PORT = os.getenv('MPD_PORT') or 6600
        self.timeout = 5

        self.process = Process(target=connection_watch, args=(self.shared_data, self.HOST, self.PORT, self.timeout))
        self.process.start()        

    def check(self):
        try:
            while True:
                debug(self_current_song=self.shared_data['current_song'], debug=1)
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit()

if __name__ == '__main__':
    c = Ticker()
    c.check()
