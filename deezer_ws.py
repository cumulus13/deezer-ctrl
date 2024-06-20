import asyncio
import os
import traceback

import make_colors
import websockets
import json
from pydebugger.debug import debug
#from jsoncolor import jprint
from rich.progress import Progress, BarColumn, TextColumn
from rich.console import Console
from rich.panel import Panel
import gntp.notifier
import requests
import sys
import time


class DeezerController:
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url
        self.next_id = 1
        self.pending_responses = {}

    async def connect(self):
        self.connection = await websockets.connect(self.websocket_url)
        asyncio.ensure_future(self.receive_messages())

    async def receive_messages(self):
        while 1:
            try:
                async for message in self.connection:
                    message_data = json.loads(message)
                    if 'id' in message_data and message_data['id'] in self.pending_responses:
                        future = self.pending_responses.pop(message_data['id'])
                        future.set_result(message_data)
                break
            except:
                if os.getenv('TRACEBACK') == "1":
                    print(traceback.format_exc())

    async def send_message(self, method, params=None):
        message_id = self.next_id
        self.next_id += 1

        message = {
            'id': message_id,
            'method': method,
        }

        if params:
            message['params'] = params

        future = asyncio.get_event_loop().create_future()
        self.pending_responses[message_id] = future
        
        while 1:
            try:
                await self.connection.send(json.dumps(message))
                break
            except:
                time.sleep(1)
                
        return await future

    async def evaluate_script(self, script):
        response = await self.send_message('Runtime.evaluate', {'expression': script})
        return response

    async def get_properties(self, object_id):
        response = await self.send_message('Runtime.getProperties', {'objectId': object_id})
        debug(response = response)
        #jprint(response)
        return response
    
    async def get_song_progress1(self):
        script = """
                (function() {
                    const progressBar = document.querySelector('input[data-testid="progress_bar"]');
                    if (progressBar) {
                        return {
                            value: progressBar.value,
                            ariaValueNow: progressBar.ariaValueNow,
                            max: progressBar.max
                        };
                    } else {
                        return null;
                    }
                })();
            """
        response = await self.evaluate_script(script)
        if response.get('result') and 'objectId' in response['result']['result']:
            object_id = response['result']['result']['objectId']
            properties_response = await self.get_properties(object_id)
            properties = {}
            for prop in properties_response['result']['result']:
                name = prop['name']
                if 'value' in prop:
                    value = prop['value']['value']
                else:
                    value = None
                properties[name] = value
            return properties
        else:
            return None

    async def get_song_progress(self):
        script = """
            (function() {
                const progressBar = document.querySelector('input[data-testid="progress_bar"]');
                const remaining_time = document.querySelector('p[data-testid="remaining_time"]');
                const current_play_song = document.querySelector('p[data-testid="item_title"]');
                const current_play_artist = document.querySelector('p[data-testid="item_subtitle"]');
                //const current_play_album = document.querySelector('h2[class="chakra-heading css-1hhrzpx"]');
                const current_play_album = document.querySelector('meta[itemprop="name"]');
                const current_status = document.querySelector('button[data-testid="play_button_pause"]');
                let state = 'pause';
                let current_play_cover = null;
                if (current_play_song) {
                    current_play_cover = document.querySelector(`img[alt="${current_play_song.innerText}"]`);
                }
                
                if (current_status) {
                    state = 'play'
                }
                if (progressBar) {
                    return {
                        value: progressBar.value,
                        ariaValueNow: progressBar.ariaValueNow,
                        max: progressBar.max,
                        time: remaining_time ? remaining_time.innerText : null,
                        current_song: current_play_song ? current_play_song.innerText : null,
                        current_artist: current_play_artist ? current_play_artist.innerText : null,
                        //current_album: current_play_album ? current_play_album.innerText : null,
                        current_album: current_play_album ? current_play_album.content : null,
                        cover: current_play_cover ? current_play_cover.src : null,
                        state: current_status ? state : null
                    };
                } else {
                    return null;
                }
            })();
        """


        response = await self.evaluate_script(script)
        debug(response = response)
        if response.get('result') and 'objectId' in response['result']['result']:
            object_id = response['result']['result']['objectId']
            debug(object_id = object_id)
            properties_response = await self.get_properties(object_id)
            #properties = {prop['name']: prop['value']['value'] for prop in properties_response['result']['result']}
            properties = {}
            while 1:
                try:
                    properties = {
                        'current': list(filter(lambda k: k.get('name') == 'value', properties_response.get('result').get('result')))[0].get('value').get('value'),
                        'now': list(filter(lambda k: k.get('name') == 'ariaValueNow', properties_response.get('result').get('result')))[0].get('value').get('value'),
                        'max': list(filter(lambda k: k.get('name') == 'max', properties_response.get('result').get('result')))[0].get('value').get('value'),
                        'time': list(filter(lambda k: k.get('name') == 'time', properties_response.get('result').get('result')))[0].get('value').get('value'),
                        'song': list(filter(lambda k: k.get('name') == 'current_song', properties_response.get('result').get('result')))[0].get('value').get('value'),
                        'artist': list(filter(lambda k: k.get('name') == 'current_artist', properties_response.get('result').get('result')))[0].get('value').get('value'),
                        'album': list(filter(lambda k: k.get('name') == 'current_album', properties_response.get('result').get('result')))[0].get('value').get('value') or '',
                        'cover': list(filter(lambda k: k.get('name') == 'cover', properties_response.get('result').get('result')))[0].get('value').get('value'),
                        'state': list(filter(lambda k: k.get('name') == 'state', properties_response.get('result').get('result')))[0].get('value').get('value'),
                    }
                    debug(properties = properties)
                    break
                except:
                    pass
            return properties
        else:
            return None

async def main(_id = "89EC7900019308E752BEAE72C9AD378E"):
    websocket_url = f"ws://127.0.0.1:9222/devtools/page/{_id}"
    controller = DeezerController(websocket_url)
    await controller.connect()
    
    console = Console()
    growl = gntp.notifier.GrowlNotifier(
        applicationName="Deezer",
        notifications=["Song Change"],
        defaultNotifications=["Song Change"],
    )
    growl.register()

    previous_song = None
    
    with Progress(
        TextColumn("[bold blue]{task.fields[current_song]}", justify="left"),
        BarColumn(bar_width = 100),
        TextColumn("{task.completed}/{task.total}", justify="right"),
        TextColumn("[bold red]{task.fields[time]}", justify="right"),
        console=console
    ) as progress:

        progress_task = progress.add_task(
            "[bold green]Deezer Player", total=100, current_song="Loading...", time="0:00"
        )
        
        progress_data = await controller.get_song_progress()
        
        if progress_data:
            current_song = progress_data['song']
            current_artist = progress_data['artist']
            current_album = progress_data['album']
            
            # Clear previous panel and print updated info
            console.clear()
            info_panel = Panel(f"Current song: [bold bright_red]{current_song}[/bold bright_red]\nArtist: [bold cyan]{current_artist}[/bold cyan]\nAlbum: [bold chartreuse1]{current_album}[/bold chartreuse1]", title="[bold yellow]Now Playing[/bold yellow]")
            console.print(info_panel)        

        # Real-time monitoring of song progress
        while True:
            try:
                progress_data = await controller.get_song_progress()
                if progress_data:
                    current_song = progress_data['song']
                    current_artist = progress_data['artist']
                    current_album = progress_data['album']
                    value = float(progress_data['current'])
                    max_value = float(progress_data['max'])
                    remaining_time = progress_data['time']
                    cover_image = progress_data['cover']
                    debug(cover_image = cover_image)
    
                    progress.update(progress_task, completed=value, total=max_value, current_song=f"{current_song} by {current_artist}", current_album = current_album, time=remaining_time)
    
                    # Clear previous panel and print updated info
                    #console.clear()
                    #info_panel = Panel(f"Current song: [bold]{current_song}[/bold]\nArtist: [bold]{current_artist}[/bold]", title="[bold yellow]Now Playing[/bold yellow]")
                    #console.print(info_panel)
    
                    # Check if the song has changed
                    if current_song != previous_song:
                        # Send a notification
                        growl.notify(
                            noteType="Song Change",
                            title="Deezer - Now Playing",
                            description=f"{current_song} by {current_artist} - {current_album}",
                            icon=requests.get(cover_image).content, 
                            sticky=False,
                            priority=1,
                        )
                        previous_song = current_song
                        # Clear previous panel and print updated info
                        console.clear()
                        info_panel = Panel(f"Current song: [bold bright_red]{current_song}[/bold bright_red]\nArtist: [bold cyan]{current_artist}[/bold cyan]\nAlbum: [bold chartreuse1]{current_album}[/bold chartreuse1]", title="[bold yellow]Now Playing[/bold yellow]")
                        console.print(info_panel)
    
            except KeyboardInterrupt:
                print(make_colors("exit ... !", 'lw', 'bl'))
                sys.exit()
            except:
                print(make_colors(traceback.format_exc()), 'lw', 'r')
                
            await asyncio.sleep(1)  # Adjust the interval as needed

def start(_id = "89EC7900019308E752BEAE72C9AD378E"):
    while 1:
        try:
            asyncio.get_event_loop().run_until_complete(main(_id))
            break
        except Exception as e:
            print("Loop error:", str(e))
        time.sleep(1)

if __name__ == '__main__':
    try:
        #asyncio.get_event_loop().run_until_complete(main())
        start()
    except KeyboardInterrupt:
        sys.exit()

        