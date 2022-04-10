import datetime
import json
import logging
import socket
from getpass import getpass
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator, Union, Mapping, List, Dict
from importlib.metadata import version
from typing import NamedTuple
from urllib import parse

from appdirs import AppDirs
try: 
    import keyring 
    HAS_KEYRING = True
except ModuleNotFoundError: 
    HAS_KEYRING = False

JSONDict = Union[str, int, float, bool, None, Mapping[str, 'JSONDict'], List['JSONDict']]

logger = logging.getLogger(__name__)

class BackendError(Exception): 
    pass

class ConstantTuple(NamedTuple): 
    PROJECT_NAME: str 
    AUTHOR:str 
    SUBSONIC_API_VERSION:str
    APP_VERSION:str
    HOSTNAME:str
CONSTANTS = ConstantTuple('jellyshuf', 'def', '1.16.1', version('jellyshuf'), socket.gethostname())

class DataManager(ABC):
    @classmethod
    @property   
    @abstractmethod
    def BACKEND_NAME(cls) -> str:
        return NotImplementedError 
    
    @classmethod
    @property
    @abstractmethod
    def MPD_PREFIX(cls) -> str: 
        return NotImplementedError

    UUID: str = str(uuid.uuid4())
    # Replace characters in MPD path components using this dict
    TRANSLATE_MPD_PATH: Dict[int, Union[int, None]] = {
        ord('/'): None
    }
    DATEFMT: str = '%d/%m/%Y'
    TOKEN_KEY: str = 'token'
    
    class Config(NamedTuple):
        url: str = None 
        user: str = None 
        password: str = None 
        library: str|int = None 
        cache:bool = True
        cache_token:bool = True 
        cache_days: bool = True 
        use_keyring: bool = True 
        keyring_backend: str = None
        mpd_host: str = None
        mpd_port: str = None

        
    def __init__(self) -> None:
        appdirs = AppDirs(CONSTANTS.PROJECT_NAME, CONSTANTS.AUTHOR)
        self.CONFIG_PATH = Path(appdirs.user_config_dir).joinpath(f'{self.BACKEND_NAME}_config.json')
        self.CACHE_PATH = Path(appdirs.user_cache_dir).joinpath(f'{self.BACKEND_NAME}_cache.json')
        self.SERVICE_NAME = f'{CONSTANTS.PROJECT_NAME}/{self.BACKEND_NAME}'
        self.CLIENT_NAME = '{}/{}'.format(self.SERVICE_NAME, CONSTANTS.APP_VERSION)
        self._freeze_config = True
        
        config = {}
        if self.CONFIG_PATH.is_file():
            with open(self.CONFIG_PATH, 'r') as cf: 
                try:    
                    config = json.load(cf)
                except json.decoder.JSONDecodeError: 
                    self.CONFIG_PATH.unlink() # start with fresh config on disk and in class
        self.config = self.Config(**config)

        self.use_keyring = self.config.use_keyring
        if not HAS_KEYRING: 
        # use this instance var instead of updating config value on disk so that if keyring later becomes avilable it will be used
            self.use_keyring = False 
        if self.config.keyring_backend is not None: 
            keyring.set_keyring(self.config.keyring_backend)

        self.cache = {}
        if self.CACHE_PATH.is_file():
            with open(self.CACHE_PATH, 'r') as f: 
                try: 
                    self.cache = json.load(f)
                except json.decoder.JSONDecodeError: 
                    self.CACHE_PATH.unlink()
    
    @staticmethod
    def touch_file(path: Path):
        if not path.exists(): 
            path.parent.mkdir(parents=True, exist_ok=True) 
            path.touch()
    
    def update_config(self, **kwargs): 
        if not self._freeze_config:
            self.config = self.config._replace(**kwargs)

    def __getattr__(self, name) -> None:
        self.config.__getattr__(name)

    @property
    def password(self) -> str: 
        if self.use_keyring:
            return keyring.get_password(self.SERVICE_NAME, self.config.user)
        else: 
            return self.config.password
    
    def get_cache(self, key: str) -> Union[JSONDict, None]:
        if not self.config.cache:
            return None
        
        cache_days = self.config.cache_days
        if key == 'token':
            if not self.config.cache_token:
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
        if not self.config.cache: 
            return

        self.touch_file(self.CACHE_PATH)
        self.cache[key] = {
            'date': datetime.date.today().strftime(self.DATEFMT),
            'data': data
        }
        with open(self.CACHE_PATH, 'w') as f: 
            json.dump(self.cache, f)

    def save_config(self) -> None:
        self.touch_file(self.CONFIG_PATH)
        with open(self.CONFIG_PATH, 'w') as f: 
            json.dump(self.config._asdict(), f)
            
class CliClient(ABC): 
    DATA_MANAGER: DataManager
    
    def __init__(self) -> None: 
        self.data: DataManager = self.DATA_MANAGER()
        
    def start(self, overwrite=False) -> None:
        self.data._freeze_config = False
        self._pre_connect_cli(overwrite)
        self._connect()
        self._post_connect_cli(overwrite)
        self.data._freeze_config = True
        self.data.save_config()

    @staticmethod
    def str_to_bool(s: str) -> bool: 
        return s.lower() in ("yes", 'y', "true", "t", "1")

    def _pre_connect_cli(self, overwrite) -> None: 
        new_config = {}
        if overwrite or self.data.config.url is None: 
            url = str(input('Enter server url: '))
            if url.endswith('/'): 
                url = url[:-1]
            new_config['url'] = url


        if overwrite or self.data.config.user is None: 
            user = new_config['user'] = input('Enter username: ')
        else:
            user = self.data.config.user

        if (overwrite 
            or (not self.data.use_keyring and self.data.config.password is None) 
            or (self.data.use_keyring and keyring.get_password(self.data.SERVICE_NAME, user) is None) 
        ):
            password = getpass('Enter password: ')
            if self.data.use_keyring:
                keyring.set_password(self.data.SERVICE_NAME,  user, password)
                # fallback.
                if keyring.get_password(self.data.SERVICE_NAME, user) != password: 
                    print("WARNING: Failed to access system keyring to store password. Password will be stored in plaintext")
                    if self.str_to_bool(input("Continue? (yes/no): ")):
                        self.data.use_keyring = False
                        # enforce this as a config-on-disk value as otherwise user will be force to re-enter and then reconfirm plaintext password on each run
                        self.data.config.use_keyring = False 
                        new_config['password'] = password
            else:
                print("WARNING: use_keyring option set to false. Password will be stored in plaintext")
                if self.str_to_bool(input("Continue? (yes/no): ")):
                    self.data.config.use_keyring = False 
                    new_config['password'] = password
        
        self.data.update_config(**new_config)

    def state_info(self, *args) -> str: 
        return ''' 
            Application State Info
            Loaded Config: {}
            Current Backend: {}
            MPD Prefix: {}
            MPD Path Translation Dictionary: {}
        '''.format(self.data.config, self.data.BACKEND_NAME, self.data.MPD_PREFIX, self.data.TRANSLATE_MPD_PATH)

    def make_api_url(self, endpoint: str) -> str:
        scheme, netloc, path, query, fragment = parse.urlsplit(self.data.config.url) 
    
        path = path + endpoint
        
        return parse.urlunsplit((scheme, netloc, path, query, fragment))
    
    @abstractmethod
    def _connect(self) -> None: 
        pass

    @abstractmethod
    def _post_connect_cli(self, overwrite=False) -> None: 
        pass

    @abstractmethod
    def shuf_all_albums(self) -> Generator[str, None, None]:
        pass 
    
    @abstractmethod
    def shuf_all_artists(self) -> Generator[str, None, None]:
        pass 
    
    @abstractmethod
    def shuf_all_songs(self) -> Generator[str, None, None]:
        pass 
