from getpass import getpass
from os import stat
import uuid 
import socket 
import logging 
import json 
from typing import Union, Mapping, List, Dict
from pathlib import Path
from appdirs import AppDirs
import datetime

JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]
logger = logging.getLogger(__name__)

class CliSettingsManager():
    def __init__(self) -> None:
        # preset constants
        self.APPNAME = 'jellyshuf'
        self.APPVER = '0.0.2' 
        self.AUTHOR = 'def'
        self.CLIENT_UUID = str(uuid.uuid4())
        self.HOSTNAME = socket.gethostname()
        self.MPD_PATH_PREFIX = 'Jellyfin/Music' # do not include trailing slash
        self.TRANSLATE_MPD_PATH = {
            ord('/'): None
        }
        self.DATEFMT = '%d/%m/%Y'
        self.CONFIG_KEYS = ['url', 'user', 'pass', 'view', 'cache'] # pass should be stored in keyring! eventually! maybe ..

        dirs = AppDirs(self.APPNAME, self.AUTHOR)
        self.userpath = Path(dirs.user_config_dir).joinpath("config.json")
        self.cachepath = Path(dirs.user_cache_dir).joinpath('jfcache.json')
        
        if self.userpath.is_file():
            with open(self.userpath, 'r') as cf: 
                try:    
                    self.user =  json.load(cf)
                except json.decoder.JSONDecodeError: 
                    self.cache = {}
                    self.cachepath.unlink() 
        else: 
            self.user = {} 
    
        if self.cachepath.is_file():
            with open(self.cachepath, 'r') as f: 
                try: 
                    self.cache = json.load(f)
                except json.decoder.JSONDecodeError: 
                    self.cache = {}
                    self.cachepath.unlink()
        else: 
            self.cache = {}

    def get_settings_cli(self, overwrite=False) -> None: 
        def bool_to_str(s: str) -> bool: 
            return s.lower() in ("yes", 'y', "true", "t", "1")
        
        if overwrite or self.user.get('url') is None: 
            url = str(input('Enter server url (including proto and port (if non-standard): '))
            if url.endswith('/'): 
                url = url[:-1]
            self.user['url'] = url

        if overwrite or self.user.get('user') is None: 
            self.user['user'] = input('Enter jellyfin username: ')

        if overwrite or self.user.get('pass') is None: 
            self.user['pass'] = getpass('Enter jellyfin password: ')

        if overwrite or self.user.get('cache') is None: 
            self.user['cache'] = bool_to_str(input('Do you want to cache results from jellyfin api (yes/no): '))
        
        if self.user['cache'] and (overwrite or self.user.get('cachedays') is None): 
            self.user['cachedays'] = int(input('How many days do you want to cache jellyfin data for (integer): '))
            
    def get_view_cli(self, views: List[Dict[str, str]], overwrite=False):
        try: 
            view = self.user['ViewId']
            if overwrite or view not in [e['Id'] for e in views]: 
                raise KeyError 
        except KeyError: 
            print("Please select a view.")
            for i, view in enumerate(views): 
                print('    {}: {}'.format(i, view['Name']))
            self.user['ViewId'] = views[int(input("Enter view index: "))]['Id']
    
    @staticmethod
    def _touch_file(path: Path):
        if not path.exists(): 
            path.parent.mkdir(parents=True, exist_ok=True) 
            path.touch()

    def get_cache(self, key: str) -> Union[dict, None]: 
        try: 
            cache = self.cache[key]
        except KeyError: 
            return None 
        if (datetime.datetime.today() - datetime.datetime.strptime(cache['date'], self.DATEFMT)).days < self.user['cachedays']: 
            return cache['data']
        return None

    def save_cache(self, key: str, data: dict) -> None: 
        self._touch_file(self.cachepath)
        self.cache[key] = {
            'date': datetime.date.today().strftime(self.DATEFMT),
            'data': data
        }
        with open(self.cachepath, 'w') as f: 
            json.dump(self.cache, f)

    def save_config(self) -> None:
        self._touch_file(self.userpath)
        with open(self.userpath, 'w') as f: 
            json.dump(self.user, f)