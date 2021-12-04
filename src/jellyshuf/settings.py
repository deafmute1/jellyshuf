from getpass import getpass
import uuid 
import socket 
import logging 
import json 
from typing import Union, Mapping, List, Dict
from pathlib import Path
from appdirs import AppDirs

JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]
logger = logging.getLogger(__name__)

class SettingsManager():
    def __init__(self) -> None:
        # preset constants
        self.APPNAME = 'jellyshuf'
        self.APPVER = '0.0.2' 
        self.AUTHOR = 'def'
        self.CLIENT_UUID = str(uuid.uuid4())
        self.HOSTNAME = socket.gethostname()
        self.MPD_PATH_PREFIX = 'Jellyfin/Music' # do not include trailing slash
        self.KEYS = ['url', 'user', 'pass', 'view'] # pass should be stored in keyring! eventually! maybe ..

        self.filepath = Path(AppDirs(self.APPNAME, self.AUTHOR).user_config_dir).joinpath("user.json")
        
        if self.filepath.exists():
            with open(self.filepath, 'r') as cf: 
                self.data =  json.load(cf) 
        else: 
            self.data = {} 

        for key in self.KEYS: 
            try: 
                _ = self.data[key]
            except KeyError: 
                self.data[key] = None

    def get_settings_cli(self, overwrite=False) -> None: 
        if overwrite or self.data['url'] is None: 
            url = str(input('Enter server url (including proto and port (if non-standard): '))
            if url.endswith('/'): 
                url = url[:-1]
            self.data['url'] = url

        if overwrite or self.data['user'] is None: 
            self.data['user'] = str(input('Enter jellyfin username: '))

        if overwrite or self.data['pass'] is None: 
            self.data['pass'] = str(getpass('Enter jellyfin password: '))

        if self.data['url'].endswith('/'): 
            self.data['url'] = self.data['url'][:-1]

    def get_view_cli(self, views: List[Dict[str, str]], overwrite=False):
        try: 
            view = self.data['ViewId']
            if overwrite or view not in [e['Id'] for e in views]: 
                raise KeyError 
        except KeyError: 
            print("Please select a view. \n")
            for i, view in enumerate(views): 
                print('    {}: {}'.format(i, view['Name']))
            self.data['ViewId'] = views[int(input("Enter view index: "))]['Id']
        

    def save(self) -> None:
        if not self.filepath.exists(): 
            self.filepath.parent.mkdir(parents=True, exist_ok=True) 
            self.filepath.touch()
        with open(self.filepath, 'w') as f: 
            return json.dump(self.data, f)