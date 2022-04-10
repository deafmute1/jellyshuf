import logging
from pathlib import Path
from re import template
from typing import List, Mapping, Union
import argparse
from importlib.metadata import version

import musicpd

from jellyshuf import jellyfin, sonic, base

JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]
logger = logging.getLogger(__name__)

def parse_args(bin_name) -> argparse.ArgumentParser: 
    parser = argparse.ArgumentParser(
        description='Randomly add items to mpd queue from jellyfin or subsonic server.'
    )
    parser.add_argument('--stdout', action='store_true',
        help='Instead of adding retrieved paths to mpd queue, emits them to stdout (line separated)'
    )
    parser.add_argument('-i', '--interactive', action='store_true',
        help='''If not in stdout mode, interactively confirms albums before adding them;
                {name} runs until NUMBER has been added to queue.'''.format(name=bin_name)                
    )
    parser.add_argument('-r', '--random', action='store_true',
        help='Set mpd to random mode after adding new items'
    )
    parser.add_argument('-s', '--start', action='store_true',
        help='Start mpd after adding new items'
    )
    parser.add_argument('-c', '--clear', action='store_true', 
        help='Clear mpd queue before adding items'
    )
    parser.add_argument('--config', action='store_true', 
        help='Run interactive config (overwriting existing settings on disk), then exit'
    )
    parser.add_argument('--default-config', action='store_true',
        help='Replace config on disk with default one' 
    )
    parser.add_argument('-v', '--version', action='version', 
        help='Print version and exit',
        version=version(base.CONSTANTS.PROJECT_NAME)
    )
    parser.add_argument('backend', type=str, 
        help='Server backend to use (either subsonic/sonic/ss or jellyfin/jf)'
    )
    parser.add_argument('size', type=int, 
        help='Number of items to add to queue'     
    )
    parser.add_argument('type', type=str, 
        help='Type of items to add (either albums, artists or songs)'                   
    )
    return parser, parser.parse_args()


def cli() -> None:
    bin_name = 'jellyshuf'
    parser, args = parse_args(bin_name)

    if args.backend in ('subsonic', 'sonic', 'ss'):
        client = sonic.CliClient(args.size)
    elif args.backend in ('jellyfin', 'jf'): 
        client = jellyfin.CliClient()
    else: 
        logger.error('\nServer backend not one of subsonic or jellyfin')
        parser.print_help()
        return 

    if args.default_config: 
        client.data = client.data.DEFAULT_CONFIG 
        client.data.save_config()
        return
    
    if args.config: 
        client.start(True)
        return
    
    client.start()
    
    #sanitisise cli input
    if args.interactive and args.stdout: 
        args.interactive = False

    # stand up objects
    if not args.stdout:
        mpd = musicpd.MPDClient()
        mpd.connect(client.data.config.mpd_host, client.data.config.mpd_port)

    # make generator
    try: 
        if args.type.casefold() == 'albums'.casefold(): 
            gen = client.shuf_all_albums()
        elif args.type.casefold() == 'artists'.casefold():
            gen = client.shuf_all_artists()
        elif args.type.casefold() == 'songs'.casefold(): 
            gen = client.shuf_all_songs()
        else:
            print("\nType not one of albums, artists, songs\n") 
            parser.print_help()
            return
    except NotImplementedError: 
        print("This type is not yet implemented for this backend ... you could contribute it!")
    
    if args.clear:
        mpd.clear()
    
    for _ in range(args.size): 
        try:     
            path = next(gen)
            
            if args.stdout: 
                print(path)
                continue
            
            if args.interactive:
                while not base.CliClient.str_to_bool(input("Would you like to add {} to queue (y/n)? ".format(path))): 
                    path = next(gen)
            
            try: 
                mpd.add(path)
                print('Added {}'.format(path))
            except musicpd.CommandError as e:
                print('Failed to add {}'.format(path)) 
                print(str(e))

        except StopIteration: 
            print("Ran out of new candidate mpd paths.")
            break 
    
    if args.random: 
        mpd.random()
    if args.start: 
        mpd.play()
    if not args.stdout:
        mpd.disconnect()
