#future
from __future__ import annotations

# standard library
import logging
from typing import Union, Mapping, List
from sys import argv
import itertools 
from pathlib import Path

# pip installable
import musicpd


from jellyshuf import jellyfin, data
from jellyshuf.shared import str_to_bool

JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]
logger = logging.getLogger(__name__)

helpstr = '''
USAGE: jellyshuf <FLAGS> TYPE NUMBER
    
TYPE is one of artists, albums, songs 
    
FLAGS: 
    --stdout            Instead of adding retrieved paths to mpd queue, emits them to stdout (line separated)
    --interactive|-i    If not in stdout mode, interactively confirms albums before adding them;
                            jellyshuf runs until NUMBER has been added to queue.
    --random|-r         Set mpd to random mode after adding new items
    --start|-s          Start mpd after adding new items
    --clear|-c          Clear mpd queue before adding items
    --config            Run config (overwriting any existing info) then exit
    --empty-config      Generate an empty config file at config location.
    --version           Print version and exit
    --help|-h           Display this message and exit
'''
def cli() -> None:
    add_to_mpd = True
    start_mpd = False
    set_mpd_random = False
    mpd_clear = False
    interactive = False
    args = argv[1:] # discard binary/file name

    while args[0].startswith('-'): 
        flag = args.pop(0).casefold()
        if flag.startswith('--'):
            if flag == '--stdout': 
                add_to_mpd = False 
            elif flag == '--config': 
                jf = jellyfin.CliClient(overwrite=True)
                return 
            elif flag  == '--help': 
                print(helpstr)
                return
            elif flag == '--start':
                start_mpd = True 
            elif flag == '--random': 
                set_mpd_random = True 
            elif flag == '--clear':
                mpd_clear = True
            elif flag == '--empty-config': 
                s = data.PersistantDataManager()
                s.user = s.DEFAULT_CONFIG 
                s.save_config()
                return
            elif flag == '--version':
                print(data.PersistantDataManager().APPVER)
                return
            elif flag == '--interactive':
                interactive = True 
        else:
            flag = flag[1:] 
            while flag != '':
                if flag == 'h': 
                    print(helpstr)
                    return
                elif flag == 's':
                    start_mpd = True 
                elif flag == 'r':
                    set_mpd_random = True
                elif flag == 'h': 
                    print(helpstr)
                    return
                elif flag == 'c': 
                    mpd_clear = True
                elif flag == 'i': 
                    interactive = True
                flag = flag[1:]

    d = data.PersistantDataManager()
    mpd = musicpd.MPDClient()
    mpd.connect(d.user['mpd_host'], d.user['mpd_port'])
    jf = jellyfin.CliClient()

    if args[0].casefold() == 'albums'.casefold(): 
        gen = jf.shuf_all_albums()
    elif args[0].casefold() == 'artists'.casefold():
        gen = jf.shuf_all_artists()
    elif args[0].casefold() == 'songs'.casefold(): 
        gen = jf.shuf_all_songs()
    else:
        print("ERROR: Invalid argument for type") 
        print(helpstr)
        return
    
    if mpd_clear:
        mpd.clear()
        
    def add(path: Path) -> None: 
        try: 
            mpd.add(path)
            print(f'Added {path}')
        except musicpd.CommandError as e: 
            print('Failed to add {}'.format(path))
            print(str(e))
            
    if add_to_mpd:
        for path in itertools.islice(gen, int(args[1])):
            if interactive: 
                while not str_to_bool(input("Would you like to add {} to queue (y/n)? ".format(path))): 
                    path = next(gen) 
            try: 
                mpd.add(path)
                print(f'Added {path}')
            except musicpd.CommandError as e: 
                print('Failed to add {}'.format(path))
                print(str(e))
    else: 
        for path in itertools.islice(gen, int(args[1])):
            print(path)

    if set_mpd_random: 
        mpd.random()
    if start_mpd: 
        mpd.play()

    mpd.disconnect()