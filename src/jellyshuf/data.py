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

try: 
    import keyring 
    HAS_KEYRING = True
except ModuleNotFoundError: 
    HAS_KEYRING = False

from jellyshuf.shared import str_to_bool


JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]
logger = logging.getLogger(__name__)

class PersistantDataManager():
    def __init__(self) -> None:
        # preset constants
        self.APPNAME = 'jellyshuf'
        self.APPVER = '0.2.0'
        self.AUTHOR = 'def'
        self.CLIENT_UUID = str(uuid.uuid4())
        self.HOSTNAME = socket.gethostname()
        self.MPD_PATH_PREFIX = 'Jellyfin/Music' # do not include trailing slash
        self.TRANSLATE_MPD_PATH = {
            ord('/'): None
        }
        self.DATEFMT = '%d/%m/%Y'
        self.DEFAULT_CONFIG = {
            'url': None, 
            'user': None, 
            'pass': None, # None indicates no passwd yet OR that keyring is being used.
            'view': None, 
            'cache': True, 
            'cache_token': True,
            'cache_days': 10,
            'use_keyring': True,
            'set_keyring': None,
            'mpd_host': None, 
            'mpd_port': None
        }
        
        dirs = AppDirs(self.APPNAME, self.AUTHOR)
        self.userpath = Path(dirs.user_config_dir).joinpath("config.json")
        self.cachepath = Path(dirs.user_cache_dir).joinpath('jfcache.json')
        
        if self.userpath.is_file():
            with open(self.userpath, 'r') as cf: 
                try:    
                    self.user =  json.load(cf)
                except json.decoder.JSONDecodeError: 
                    self.user = {}
                    self.cachepath.unlink() 
        self.user = {**self.DEFAULT_CONFIG, **self.user} # use defaults if no value stored to disk

        self.use_keyring = self.user['use_keyring']
        if not HAS_KEYRING: # use this instance var instead of updating config value on disk so that if keyring later becomes avilable it will be used
            self.use_keyring = False 
        if self.user['set_keyring'] is not None: 
            keyring.set_keyring(self.user['set_keyring'])
    
        if self.cachepath.is_file():
            with open(self.cachepath, 'r') as f: 
                try: 
                    self.cache = json.load(f)
                except json.decoder.JSONDecodeError: 
                    self.cache = {}
                    self.cachepath.unlink()
        else: 
            self.cache = {}

    def set_user_cli(self, overwrite=False) -> None: 
        if overwrite or self.user.get('url') is None: 
            url = str(input('Enter jellyfin server url (include protocol and port (if not implied by protocol)): '))
            if url.endswith('/'): 
                url = url[:-1]
            self.user['url'] = url

        if overwrite or self.user.get('user') is None: 
            self.user['user'] = input('Enter jellyfin username: ')

        if (overwrite 
            or (not self.use_keyring and self.user.get('pass') is None) 
            or (self.use_keyring and keyring.get_password(self.APPNAME, self.user['user']) is None) 
        ):
            passw = getpass('Enter jellyfin password: ')
            if self.use_keyring:
                keyring.set_password(self.APPNAME,  self.user['user'], passw)
                # fallback.
                if keyring.get_password(self.APPNAME, self.user['user'], 'passw') != passw: 
                    print("WARNING: Failed to access system keyring to store password. Password will be stored in plaintext")
                    if str_to_bool(input("Continue? (yes/no): ")):
                        self.use_keyring = False
                        # enforce this as a config-on-disk value as otherwise user will be force to re-enter and then reconfirm plaintext password on each run
                        self.user['use_keyring'] = False 
                        self.user['pass'] = passw
            else:
                print("WARNING: use_keyring option set to false. Password will be stored in plaintext")
                if str_to_bool(input("Continue? (yes/no): ")):
                    self.user['use_keyring'] = False 
                    self.user['pass'] = passw

    def get_password(self) -> str: 
        if self.use_keyring:
            return keyring.get_password(self.APPNAME, self.user['user'])
        else: 
            return self.user['pass']
    
    def set_view_cli(self, views: List[Dict[str, str]], overwrite=False):
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
        if not self.user['cache']:
            return None
        
        cache_days = self.user['cache_days']
        if key == 'token':
            if not self.user['cache_token']:
                return None
            cache_days = 1
            
        cache = self.cache.get(key) 
        if cache is None: 
            return None 
        
        if (datetime.datetime.today() - datetime.datetime.strptime(cache['date'], self.DATEFMT)).days < cache_days: 
            return cache['data']
        else: 
            self.cache[key] = None 
            
        return None

    def save_cache(self, key: str, data: dict) -> None: 
        if not self.user['cache']: 
            return

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