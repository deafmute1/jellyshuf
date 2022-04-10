import logging
import random
from typing import Dict, Generator, List

import requests

from jellyshuf import base

""" This file contains modified source code from these files in mopidy-jellfin project:
        - mopidy-jellyfin/mopidy_jellyfin/remote.py 
        - mopidy-jellyfin/mopidy_jellyfin/http.py 
    
    See LICENSE.
"""

logger = logging.getLogger(__name__)

class DataManager(base.DataManager):
    MPD_PREFIX = 'Jellyfin/Music'
    BACKEND_NAME = 'jellyfin'

class CliClient(base.CliClient): 
    DATA_MANAGER = DataManager
    
    def _connect(self) -> None: 
        self.session = requests.Session()
        self.session.headers.update({
            'user-agent': self.data.CLIENT_NAME, 
            'x-emby-authorization': 'MediaBrowser, Client="{}", Device="{}", DeviceId="{}", Version="{}"'.format(
                self.data.SERVICE_NAME,
                base.CONSTANTS.HOSTNAME,
                self.data.UUID, 
                base.CONSTANTS.APP_VERSION
            )
        })
        
        self.user_id = None
        token = self.data.get_cache('token')
        
        #try: 
        res = 'None'
        if token is not None: #attempt to connect on valid token
            self.session.headers.update({'x-mediabrowser-token': token})
            res = self.session.get(self.make_api_url('/User/Me'))
            self.user_id= res.get('Id')
        
        if token is None or self.user_id is None:
            res = self.session.post(
                self.make_api_url('/Users/AuthenticateByName'),
                json = {
                    'Username': self.data.config.user,
                    'Pw': self.data.password
                }
            )
            print(self.session.headers) 
            res.raise_for_status()
            res = res.json()
            token = res.get('AccessToken')

            if token is not None:
                self.user_id = res.get('User').get('Id')
                self.http.session.headers.update({'x-mediabrowser-token': token})
                self.data.save_cache('token', token)
            else:
                raise base.BackendError('Token is None after trying /Users/AuthenticateByName.' + self.state_info(res))
        
        logger.info('Succesfully logged into jellyfin')
        #except Exception as e: 
        #    raise base.BackendError('Failed to login to jellyfin' + self.state_info(res)) from e
        
    def _post_connect_cli(self, overwrite) -> None: 
        try: 
            view = self.data.config.library
            views = self.get_music_views()
            if overwrite or view not in [e['Id'] for e in views]: 
                raise KeyError 
        except KeyError: 
            print("Please select a library.")
            for i, view in enumerate(views): 
                print('    {}: {}'.format(i, view['Name']))
            self.data.update_config(library=views[int(input("Enter library index: "))]['Id'])

    def get_music_views(self) -> List[Dict[str, str]]: 
        res = self.session.post(self.make_api_url('/Users/{}/Views'.format(self.data.config_id)))
        return [{'Name': library.get('Name'), 'Id': library.get('Id')}   
            for library in res.get('Items')
            if library.get('CollectionType') == 'music'
        ]
    
    def shuf_all_albums(self) -> Generator[str, None, None]: 
        albums = self.data.get_cache('albums')
        
        if albums is None: 
            try: 
                res = self.session.get(
                    self.make_api_url( '/Items'),
                    {            
                        'UserId': self.data.config_id,
                        'ParentId': self.data.config.library,
                        'IncludeItemTypes': 'MusicAlbum',
                        'Recursive': 'true'
                    }
                )
                res.raise_for_status()
                albums = res.json()['Items']
                self.data.save_cache('albums', albums)
            except Exception as e: 
                raise base.Exception('Exception whilst trying to access albums on /Items' + self.state_info(res))

        random.shuffle(albums)

        for album in albums:
            yield '{}/{}/{}'.format(
                self.data.MPD_PREFIX, 
                album['AlbumArtist'].translate(self.data.TRANSLATE_MPD_PATH),
                album['Name'].translate(self.data.TRANSLATE_MPD_PATH)
            )

    def shuf_all_artists(self) -> Generator[str, None, None]: 
        artists = self.data.get_cache('artists')

        if artists is None:
            try: 
                res = self.http.get(
                    self.make_api_url('/Artists/AlbumArtists'),
                    {
                        'ParentId': self.data.config.library,
                        'UserId': self.data.config_id
                    }
                )
                artists = res.json()['Items']
                self.data.save_cache('artists', artists)
            except Exception as e: 
                raise base.BackendError('Exception whilst trying to access artists on /Artists/AlbumArtists' + self.state_info(res))

        random.shuffle(artists)
        for artist in artists: 
            yield '{}/{}'.format(
                self.data.MPD_PREFIX, 
                artist['Name'].translate(self.data.TRANSLATE_MPD_PATH)
            )

    def shuf_all_songs(self) -> Generator[str, None, None]: 
        songs = self.data.get_cache('songs')
        
        if songs is None: 
            try: 
                res = self.http.get(
                    self.make_api_url('/Items'), 
                    {
                        'UserId': self.data.config_id,
                        'ParentId': self.data.config.library,
                        'IncludeItemTypes': 'Audio',
                        'Recursive': 'true'
                    }
                )
                songs = res.json()['Items']
                self.data.save_cache('songs', songs) 
            except Exception as e:
                raise base.BackendError('Exception whilst trying to access songs on /Items' + self.state_info(res))
            
        random.shuffle(songs) 

        for song in songs: 
            yield '{}/{}/{}/{}'.format(
                self.data.MPD_PREFIX, 
                song['AlbumArtist'].translate(self.data.TRANSLATE_MPD_PATH),
                song['Album'].translate(self.data.TRANSLATE_MPD_PATH),
                song['Name'].translate(self.data.TRANSLATE_MPD_PATH)
            )

