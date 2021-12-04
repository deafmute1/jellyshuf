#future
from __future__ import annotations

# standard library
import logging
from typing import Union, Mapping, List
from sys import argv
import itertools 

# pip installable
import musicpd


from jellyshuf import jellyfin

""" Parts of this file are modified from mopidy-jellyfin. See LICENSE-mopidy-jellyfin.
"""

JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]
logger = logging.getLogger(__name__)
helpstr = '''
USAGE: jellyshuf <FLAGS> TYPE NUMBER
    
TYPE is one of artists, albums, songs (will take forever)
    
FLAGS: 
    --stdout        Instead of adding retrieved paths to mpd queue, emits them to stdout (line separated)
    --random|-r     Set mpd to random mode
    --start|-s      Start mpd after adding new items
    --config        Run config (overwriting existing info if necessary) then exit
    --help|-h       Display this message and exit
'''


def cli(): 
    add_to_mpd = True
    start_mpd = False
    set_mpd_random = False
    args = argv[1:] # discard binary/file name

    # consume flags
    while args[0].startswith('-'): 
        flag = args.pop(0).casefold()
        if flag == '--stdout': 
            add_to_mpd = False 
        elif flag == '--config': 
            jf = jellyfin.CliClient(overwrite=True)
            return 
        elif flag in ('--help', '-h'): 
            print(helpstr)
            return
        elif flag in ('--start', '-s'):
            start_mpd = True 
        elif flag in ('--random', 'r'):
            set_mpd_random = True

    mpd = musicpd.MPDClient()
    mpd.connect()
    jf = jellyfin.CliClient()

    if args[0].casefold() == 'albums'.casefold(): 
        gen = jf.shuf_all_albums()
    elif args[0].casefold() == 'artists'.casefold():
        gen = jf.shuf_all_artists()
    elif args[0].casefold() == 'songs'.casefold(): 
        gen = jf.shuf_all_songs()
    else: 
        print(helpstr)

    for path in itertools.islice(gen, int(args[1])):
        if add_to_mpd: 
            print(f'Adding {path}')
            mpd.add(path)
        else: 
            print('{}'.format(path))

    if set_mpd_random: 
        mpd.random(1)
    if start_mpd: 
        mpd.play()

    mpd.disconnect()