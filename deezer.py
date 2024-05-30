import sys

import pychrome
from pydebugger.debug import debug
from configset import configset
from pathlib import Path
import requests
import argparse
from bs4 import BeautifulSoup as bs
from make_colors import make_colors
import re
from urllib.parse import quote
try:
    from . import deezer_ws
except:
    import deezer_ws

class Deezer(object):
    CONFIGNAME = str(Path(__file__).parent / 'deezer.ini')
    CONFIG = configset(CONFIGNAME)
    PORT = CONFIG.get_config('general', 'port', '9222') or 9222
    URL = CONFIG.get_config('general', 'url', f"http://127.0.0.1:{PORT}") or f"http://127.0.0.1:{PORT}"
    BROWSER = pychrome.Browser(url=URL)
    TAB = None
    
    def __init__(self, url: str | None = None, configname: str | None = None, port: int | None = 9222) -> None:
        self.URL = url or self.URL
        if configname:
            self.CONFIG = configset(configname)
        self.PORT = port or self.PORT
            
    @classmethod
    def find_deezer_tab(self):
        a = requests.get(f"{self.URL}/json").json()
        debug(json = a)
        tab_id = list(filter(lambda k: '- Deezer' in k['title'], a))[0].get('id')
        debug(tab_id = tab_id)
        
        # Get the list of open tabs
        tabs = self.BROWSER.list_tab()
        tab = None
        for t in tabs:
            if t.id == tab_id:
                tab = t
                debug(tab = tab)
                break
        
        if tab is None:
            raise ValueError(f"Tab with ID {tab_id} not found")
        
        return tab
        
    @classmethod
    def play(self):
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        script = """document.querySelector('button[data-testid="play_button_play"]').click();"""
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        return result['result']
    
    @classmethod
    def pause(self):
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        script = """document.querySelector('button[data-testid="play_button_pause"]').click();"""
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        return result['result']
    
    @classmethod
    def next(self):
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        script = """document.querySelector('button[data-testid="next_track_button"]').click();"""
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        return result['result']
    
    @classmethod
    def previous(self):
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        script = """document.querySelector('button[data-testid="previous_track_button"]').click();"""
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        return result['result']
    
    @classmethod
    def repeat(self):
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        script = """document.querySelector('button[data-testid="repeat_button_all"]').click();"""
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        return result['result']
        
    
    @classmethod
    def get_repeat_status(self, repeat_type = None):
        '''
            @repeat_type :option:str "all", "one", "off" 
        '''
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        script = """document.querySelector('button[data-testid*="repeat_button_"]').getAttribute('data-testid');"""
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        
        if repeat_type == 'all':
            while 1:
                script = """document.querySelector('button[data-testid*="repeat_button_"]').click();"""
                result = tab.Runtime.evaluate(expression=script)
                debug(result = result)
                
                script = """document.querySelector('button[data-testid*="repeat_button_"]').getAttribute('data-testid');"""
                result = tab.Runtime.evaluate(expression=script)
                debug(result = result)
                if result.get('result').get('value') == 'repeat_button_all':
                    break
        elif repeat_type == 'one':
            while 1:
                script = """document.querySelector('button[data-testid*="repeat_button_"]').click();"""
                result = tab.Runtime.evaluate(expression=script)
                debug(result = result)
                
                script = """document.querySelector('button[data-testid*="repeat_button_"]').getAttribute('data-testid');"""
                result = tab.Runtime.evaluate(expression=script)
                debug(result = result)
                if result.get('result').get('value') == 'repeat_button_single':
                    break            
        
        elif repeat_type == 'off':
            while 1:
                script = """document.querySelector('button[data-testid*="repeat_button_"]').click();"""
                result = tab.Runtime.evaluate(expression=script)
                debug(result = result)
                
                script = """document.querySelector('button[data-testid*="repeat_button_"]').getAttribute('data-testid');"""
                result = tab.Runtime.evaluate(expression=script)
                debug(result = result)
                if result.get('result').get('value') == 'repeat_button_off':
                    break            
        
        return result['result']
    
    @classmethod
    def play_song(self, aria_label):
        if aria_label.isdigit():
            all_title = self.get_current_playlist(interactive=False)
            debug(all_title = all_title)
            if int(aria_label) <= len(all_title):
                aria_label = all_title[int(aria_label) - 1].get('title')
            else:
                print(make_colors("Invalid Number !", 'lw', 'r'))
                
        tab = self.TAB or self.find_deezer_tab()
        debug(tab = tab)    
        debug(tab_status = tab.status_started)    
        debug(dir_tab = dir(tab))
        debug(tab_id = tab.id)
        tab.start()
        #tab.Page.reload(ignoreCache=True) 
        script = f"""document.querySelector('button[aria-label*="{aria_label}"]').click();"""
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        data = result.get('result').get('value')
        debug(data = data)
        return result
    
    @classmethod
    def get_current_playlist(self, interactive = True) -> bs:
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        
        script = """
            (function() {
                const button = document.querySelector('button[data-testid="queue_list_button"]');
                return button && button.hasAttribute('data-active');
            })();
        """
        
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        
        if isinstance(result.get('result').get('value'), bool) and result.get('result').get('value') == False:
            script0 = """document.querySelector('button[data-testid="queue_list_button"]').click();"""
            debug(script0 = script0)
            result0 = tab.Runtime.evaluate(expression=script0)
            debug(result0 = result0)
            
        script1 = """document.querySelector('.queuelist-content').innerHTML;"""
        debug(script1 = script1)
        result1 = tab.Runtime.evaluate(expression=script1)
        debug(result1 = result1)
        data = result1.get('result').get('value')
        debug(data = data)
        
        playlist = []
        b = bs(data, 'lxml')
        all_div = b.find_all('div', {'class': re.compile('JIYRe'),})
        debug(all_div = all_div)
        
        for div in all_div:
            title = div.find('span', {'data-testid': 'title',}).text
            debug(title = title)
            artist_data = div.find('a', {'data-testid': 'artist',})
            debug(artist_data = artist_data)
            artist_name = artist_data.text
            debug(artist_name = artist_name)
            artist_link = artist_data.get('href')
            debug(artist_link = artist_link)
            duration = div.find('span', string = re.compile("\d{0,2}:\d{0,2}")).text
            debug(duration = duration)
            
            playlist.append({
                'title': title,
                'artist': artist_name,
                'artist_link': artist_link,
                'duration': duration,
            })
            
        debug(playlist = playlist)
            
        if interactive:
            n = 1
            
            for song in playlist:
                print(
                    f"{make_colors(str(n).zfill(2), 'lc') + '. '} {make_colors(song.get('title'), 'ly')} - {make_colors(song.get('artist'), 'lg')} [{make_colors(song.get('duration'), 'lm')}]"
                )
                
                n += 1
            
            q = input(make_colors("Select number to play:", 'lw', 'bl') + " ")
            if q and q.isdigit() and int(q) <= len(playlist):
                title_selected = playlist[int(q) - 1].get('title')
                self.play_song(title_selected)
        
        return playlist
    
    @classmethod
    def get_current_playlist_page(self, interactive = True) -> bs:
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        script = """document.querySelector('.ZOZXb').innerHTML;"""
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        data = result.get('result').get('value')
        debug(data = data)
        
        b = bs(data, 'lxml')
        all_title = b.find_all('span', {'data-testid': 'title',})
        debug(all_title = all_title)
        
        if interactive:
            n = 1
            
            for title in all_title:
                print(
                    f"{make_colors(str(n).zfill(2), 'lc') + '. '} {make_colors(title.text, 'ly')}"
                )
                
                n += 1
            
            q = input(make_colors("Select number to play:", 'lw', 'bl') + " ")
            if q and q.isdigit() and int(q) <= len(all_title):
                title_selected = all_title[int(q) - 1].text
                self.play_song(title_selected)
        
        return all_title
    
    @classmethod
    def search(self, text):
        #still not working (any idea ?)
        tab = self.TAB or self.find_deezer_tab()
        tab.start()
        url = f'https://www.deezer.com/search/{quote(text.strip())}'
        ##tab.Page.navigate(url = f'https://www.deezer.com/search/{quote(text.strip())}')
        #tab.Page.navigate(url=f"javascript:window.location.href='{url}'")
        #tab.wait(1)
        
        #script = """document.querySelector('body').innerHTML;"""
        new_url = url
        
        script = f"""
                    (function() {{
                        // Fetch content from the new URL
                        fetch('{new_url}')
                            .then(response => response.text())
                            .then(data => {{
                                // Create a temporary container to hold the fetched content
                                const tempContainer = document.createElement('div');
                                tempContainer.innerHTML = data;
        
                                // Wait for the DOMContentLoaded event to ensure the content is fully loaded
                                document.addEventListener('DOMContentLoaded', () => {{
                                    // Update the content of the page with content from the new URL
                                    document.body.innerHTML = tempContainer.innerHTML;
                                }});
        
                                return true;
                            }})
                            .catch(error => {{
                                console.error('Error fetching content:', error);
                                return false;
                            }});
                    }})();
                """        
        
        result = tab.Runtime.evaluate(expression=script)
        debug(result = result)
        data = result.get('result').get('value')
        debug(data = data)
    
    @classmethod
    def usage(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-x', '--play', action = 'store_true', help = 'Play')
        parser.add_argument('-X', '--play-song', action = 'store', help = 'Play song number (direct)')
        parser.add_argument('-s', '--pause', action = 'store_true', help = 'Pause')
        parser.add_argument('-n', '--next', action = 'store_true', help = 'Next')
        parser.add_argument('-p', '--previous', action = 'store_true', help = 'Previous')
        parser.add_argument('-r', '--repeat', action = 'store', help = 'Repeat "all" | "one" | "off" or you can insert number as "1" == "all", "2" == "one", "0" == "off"')
        parser.add_argument('-l', '--current-playlist', action = 'store_true', help = 'Current Playlist Info')
        parser.add_argument('--port', action = 'store', type = int, default = 9222, help = 'Remote debugging port "--remote-debugging-port=?", default = 9222')
        parser.add_argument('--host', action = 'store', type = str, default = '127.0.0.1', help = 'Remote debugging host, default = 127.0.0.1')
        parser.add_argument('-m', '--monitor', action = 'store_true', help = 'Run monitor mode')
        
        if len(sys.argv) == 1:
            parser.print_help()
        else:
            args = parser.parse_args()
            if args.port != 9222:
                self.URL = f"http://{args.host}:{args.port}"
                self.BROWSER = pychrome.Browser(url=self.URL)
                
            if args.play:
                self.play()
            elif args.pause:
                self.pause()
            elif args.next:
                self.next()
            elif args.previous:
                self.previous()
            elif args.current_playlist:
                self.get_current_playlist()
            elif args.play_song:
                self.play_song(args.play_song)
            elif args.repeat:
                if args.repeat == "1" or args.repeat == "all":
                    self.get_repeat_status('all')
                elif args.repeat == "2" or args.repeat == "one":
                    self.get_repeat_status('one')
                elif args.repeat == "0" or args.repeat == "off":
                    self.get_repeat_status('off')
            elif args.monitor:
                deezer_ws.start()
    
if __name__ == '__main__':
    #Deezer.get_repeat_status()
    Deezer.usage()
    #Deezer.next()
    #Deezer.get_current_playlist()
    #Deezer.search(sys.argv[1])
