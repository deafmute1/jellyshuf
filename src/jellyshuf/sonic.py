from typing import Generator, Union
import logging
import hashlib
import secrets
import requests

from jellyshuf import base

logger = logging.getLogger(__name__)

class DataManager(base.DataManager):
    MPD_PREFIX = "Subsonic/Directories"
    BACKEND_NAME = "Subsonic"

class CliClient(base.CliClient): 
    DATA_MANAGER = DataManager 
    
    def __init__(self, return_size=500) -> None:
        super().__init__() 
        self.return_size = return_size 
    
    def _connect(self) -> None:
        self.session = requests.Session()
        salt = secrets.token_hex()
        
        self.params = {
            'f': 'json',
            'v': base.CONSTANTS.SUBSONIC_API_VERSION,
            'u': self.data.config.user,
            'c': self.data.CLIENT_NAME,
            's': salt,
            't': hashlib.md5((self.data.password+salt).encode('utf-8')).hexdigest()
        }
        
        try: 
            r = self.session.get(
                self.make_api_url('/rest/ping'),
                params=self.params
            )
            r.raise_for_status()
            rj = r.json()['subsonic-response']
        except Exception as e: 
            raise base.BackendError("Error authenticating to *sonic server:\n" + self.state_info(r))
        
        if rj['status'] != 'ok': 
            raise base.BackendError("Non-ok status in Subsonic API response when authenticating:\n" + self.state_info(r))
        else: 
            logger.info("Succesfully authenticated to subsonic server")
        
        
    def state_info(self, response:requests.Response) -> str: 
        rj = response.json()['subsonic-response']
        return super().state_info() + """
            Base URL: {}

            Details of the last response:
            Subsonic Status: {}
            Error: {} 
            Server Type: {}
            Server Version: {}               
            Server API Version: {}
            Request URL: {}
        """.format(
            self.data.config.url,
            rj.get('status'),
            rj.get('error'),
            rj.get('type'),
            rj.get('serverVersion'),
            rj.get('version'),
            response.url,
        )
    
    def _post_connect_cli(self, overwrite) -> None:
        try:
            r = self.session.get(
                self.make_api_url('/rest/getMusicFolders'),
                params=self.params
            )
            libraries = r.json()['subsonic-response']['musicFolders']['musicFolder']
        except Exception as e: 
            raise base.BackendError("Error when trying to fetch music folders:\n" + self.state_info(r)) from e
        
        
        if overwrite or self.data.config.library not in [e['id'] for e in libraries]:
            print("Please select a top level folder: ")
            for i, folder in enumerate(libraries): 
                print('    {}: {}'.format(i+1, folder['name']))
            folder_i = int(input("Enter folder number: "))-1
            self.data.update_config(library=libraries[folder_i]['id'])
    
    def shuf_all_albums(self) -> Generator[str, None, None]:
        url = self.make_api_url('/rest/getAlbumList')
        params = {   
            **self.params, 
            'type': 'random',
            'size': str(self.return_size), 
            'musicFolderId': str(self.data.config.library)
        }
        
        try: 
            res = self.session.get(url, params=params)
            res.raise_for_status()
            albums = res.json()['subsonic-response']['albumList']['album']
        except Exception as e: 
            raise base.BackendError("Error when trying to access getAlbumList backend" + self.state_info()) from e
        
        for album in albums: 
            yield '{}/{}/{}'.format(
                self.data.MPD_PREFIX,
                album['artist'].translate(self.data.TRANSLATE_MPD_PATH),
                album['title'].translate(self.data.TRANSLATE_MPD_PATH)
            )
            
    def shuf_all_artists(self): 
        raise NotImplementedError
    
    def shuf_all_songs(self): 
        url = self.make_api_url('/rest/getRandomSongs')
        params = {   
            **self.params,
            'size': str(self.return_size),
            'musicFolderId': str(self.data.config.library)
        }       
        try:
            res = self.session.get(url, params=params)
            res.raise_for_status()
            songs = res.json()['subsonic-response']['randomSongs']['song']
        except Exception as e:  
            raise base.BackendError("Error when trying to access getAlbumList backend" + self.state_info()) from e
        
        for song in songs: 
            yield '{}/{}'.format(
                self.data.MPD_PREFIX,
                song['path']
            )