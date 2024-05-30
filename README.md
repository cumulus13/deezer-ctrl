# Deezer-Ctrl

## Control Deezer on Chrome running with "--remote-debugging-port=?" and PyChrome.

### Requirements (pip)

- pychrome
- pydebugger
- configset
- requests
- beautifulsoup4 (or bs4)
- make_colors
- websockets
- rich
- gntp

GROWL Notification support.

### Usage
```bash
usage: deezer.py [-h] [-x] [-X PLAY_SONG] [-s] [-n] [-p] [-r REPEAT] [-l] [--port PORT] [--host HOST] [-m]

options:
  -h, --help            show this help message and exit
  -x, --play            Play
  -X PLAY_SONG, --play-song PLAY_SONG
                        Play song number (direct)
  -s, --pause           Pause
  -n, --next            Next
  -p, --previous        Previous
  -r REPEAT, --repeat REPEAT
                        Repeat "all" | "one" | "off" or you can insert number as "1" == "all", "2" == "one", "0" == "off"
  -l, --current-playlist
                        Current Playlist Info
  --port PORT           Remote debugging port "--remote-debugging-port=?", default = 9222
  --host HOST           Remote debugging host, default = 127.0.0.1
  -m, --monitor         Run monitor mode
```

### Author

[cumulus13](mailto:cumulus13@gmail.com)

Contributions welcome while working.