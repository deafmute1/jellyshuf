# standard library
from typing import List, Dict, Generator
import logging
import random
from typing import List 
import requests
import urllib.parse

#internal
from jellyshuf import data 


""" This file contains modified source code from these files in mopidy-jellfin project:
        - mopidy-jellyfin/mopidy_jellyfin/remote.py 
        - mopidy-jellyfin/mopidy_jellyfin/http.py 
    
    See LICENSE.
"""

logger = logging.getLogger(__name__)

class HttpClient():
    def __init__(self, headers, user_agent):
        self.headers = headers
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.headers.update(user_agent)

    def get(self, url):
        # Perform HTTP Get to the provided URL
        counter = 0
        self.session.headers.update(self.headers)
        while counter <= 5:

            try:
                r = self.session.get(url)
                try:
                    rv = r.json()
                except Exception as e:
                    logger.info(
                        'Error parsing Jellyfin data: {}'.format(e)
                    )
                    rv = {}

                logger.debug(str(rv))

                return rv

            except Exception as e:
                logger.info(
                    'Jellyfin connection on try {} with problem: {}'.format(
                        counter, e
                    )
                )
                counter += 1

        raise Exception('Cant connect to Jellyfin API')

    def post(self, url, payload={}):
        # Perform HTTP Post to the provided URL
        self.session.headers.update(self.headers)
        r= {}
        counter = 0
        while counter <= 5:

            try:
                r = self.session.post(url, json=payload)
                if r.text:
                    rv = r.json()
                else:
                    rv = r.text

                logger.debug(rv)

                return rv

            except Exception as e:
                logger.info(
                    'Jellyfin connection on try {} with problem: {}'.format(
                        counter, e
                    )
                )
                counter += 1

        raise Exception('Cant connect to Jellyfin API. Resp: {}; url: {}; payload={}'.format(r, url, payload))

    def delete(self, url):
        # Perform HTTP Delete to the provided URL
        counter = 0
        self.session.headers.update(self.headers)
        while counter <= 5:

            try:
                r = self.session.delete(url)

                logger.debug(str(r))

                return r

            except Exception as e:
                logger.info(
                    'Jellyfin connection on try {} with problem: {}'.format(
                        counter, e
                    )
                )
                counter += 1

        raise Exception('Cant connect to Jellyfin API')

    def check_redirect(self, server):
        # Perform HTTP Get to public endpoint to check for redirects
        counter = 0
        self.session.headers.update(self.headers)
        path = '/system/info/public'

        if 'http' not in server:
            server = 'http://' + server

        while counter <= 5:

            try:
                r = self.session.get(f'{server}{path}')
                r.raise_for_status()

                return r.url.replace(path, '')

            except Exception as e:
                logger.error(
                    'Failed to reach Jellyfin public API on try {} with problem: {}'.format(
                        counter, e
                    )
                )
                counter += 1

        raise Exception('Unable to find Jellyfin server, check hostname config')

    def head(self, item_id, url):
        # Used to verify if an image exists
        try:
            r = self.session.head(url)
            r.raise_for_status()
            return True
        except:
            logger.debug(f'No primary image found for item {item_id}')
            return False 

class CliClient(): 
    def __init__(self, overwrite=False) -> None:
        self.settings = data.PersistantDataManager() 
        self.settings.set_user_cli(overwrite) # required for below

        self.user_agent = {'user-agent': '/'.join((self.settings.APPNAME, self.settings.APPVER))}
        self.http = HttpClient(self._make_headers(), self.user_agent)
        self.server_url = self.http.check_redirect(self.settings.user['url'])
        self.user_id = None
        
        self._login()   
        self.settings.set_view_cli(self.get_music_views(), overwrite) # requires login, but should be before any further api queries
        self.settings.save_config()
    
    def _login(self) -> None: 
        token = self.settings.get_cache('token')
        
        if token is not None: #attempt to connect on valid token
            self.http.session.headers.update({'x-mediabrowser-token': token})
            res = self.http.get(self._make_api_url('/User/Me'))
            self.user_id = res.get('Id')
        elif self.settings.cache.get('token') is not None: # logout if outdated
            self.http.session.headers.update({'x-mediabrowser-token': self.settings.cache['token']})
            self.http.post(self._make_api_url('/Sessions/Logout'))
        
        if token is None or self.user_id is None:
            res = self.http.post(
                self._make_api_url('/Users/AuthenticateByName'),  
                {
                    'Username': self.settings.user['user'],
                    'Pw': self.settings.get_password()
                }
            )
            token = res.get('AccessToken')

            if token is not None:
                self.user_id = res.get('User').get('Id')
                self.http.session.headers.update({'x-mediabrowser-token': token})
                self.settings.save_cache('token', token)
            else:
                raise Exception('Unable to login to Jellyfin')

    def _make_api_url(self, endpoint: str, params:dict={}) -> None:
        scheme, netloc, path, query_string, fragment  = urllib.parse.urlsplit(self.server_url)
        path = path + endpoint
        
        query_params = urllib.parse.parse_qs(query_string)
        query_params['format'] = 'json'
        query_params.update(params)
        new_query_string = urllib.parse.urlencode(query_params, doseq=True)

        return urllib.parse.urlunsplit((scheme, netloc, path, new_query_string, fragment))
    
    def _make_headers(self) -> dict: 
        authorization = (
            'MediaBrowser , '
            'Client="{client}", '
            'Device="{device}", '
            'DeviceId="{device_id}", '
            'Version="{version}"'
        ).format(
            client=self.settings.APPNAME,
            device=self.settings.HOSTNAME,
            device_id=self.settings.CLIENT_UUID, 
            version=self.settings.APPVER
        )

        return  {'x-emby-authorization':  authorization}

    def get_music_views(self) -> List[Dict[str, str]]: 
        res = self.http.get(self._make_api_url('/Users/{}/Views'.format(self.user_id)))
        return [{'Name': library.get('Name'), 'Id': library.get('Id')}   
            for library in res.get('Items')
            if library.get('CollectionType') == 'music'
            ]
    
    def shuf_all_albums(self) -> Generator[str, None, None]: 
        albums = self.settings.get_cache('albums')
        
        if albums is None: 
            albums = self.http.get(self._make_api_url( 
                '/Items',
                {            
                    'UserId': self.user_id,
                    'ParentId': self.settings.user['ViewId'],
                    'IncludeItemTypes': 'MusicAlbum',
                    'Recursive': 'true'
                }
            ))['Items']
            self.settings.save_cache('albums', albums)

        random.shuffle(albums)

        for album in albums:
            yield '{}/{}/{}'.format(
                self.settings.MPD_PATH_PREFIX, 
                album['AlbumArtist'].translate(self.settings.TRANSLATE_MPD_PATH),
                album['Name'].translate(self.settings.TRANSLATE_MPD_PATH)
            )


    def shuf_all_artists(self) -> Generator[str, None, None]: 
        artists = self.settings.get_cache('artists')

        if artists is None:
            artists = self.http.get(self._make_api_url(
                '/Artists/AlbumArtists',
                {
                    'ParentId': self.settings.user['ViewId'],
                    'UserId': self.user_id
                }
            ))['Items']
            self.settings.save_cache('artists', artists)

        random.shuffle(artists)
        for artist in artists: 
            yield '{}/{}'.format(
                self.settings.MPD_PATH_PREFIX, 
                artist['Name'].translate(self.settings.TRANSLATE_MPD_PATH)
            )

    def shuf_all_songs(self) -> Generator[str, None, None]: 
        songs = self.settings.get_cache('songs')
        
        if songs is None: 
            songs = self.http.get(self._make_api_url(
                '/Items', 
                {
                    'UserId': self.user_id,
                    'ParentId': self.settings.user['ViewId'],
                    'IncludeItemTypes': 'Audio',
                    'Recursive': 'true'
                }
            ))['Items']
            self.settings.save_cache('songs', songs)
            
        random.shuffle(songs) 

        for song in songs: 
            yield '{}/{}/{}'.format(
                self.settings.MPD_PATH_PREFIX, 
                song['AlbumArtist'].translate(self.settings.TRANSLATE_MPD_PATH),
                song['Album'].translate(self.settings.TRANSLATE_MPD_PATH),
                song['Name'].translate(self.settings.TRANSLATE_MPD_PATH)
            )

