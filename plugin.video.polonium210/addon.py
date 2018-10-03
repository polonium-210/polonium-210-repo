from __future__ import absolute_import 
import json
import math
import os
import re
import sys
import urllib2
import urlparse
import time

import requests
from xml.dom.minidom import parseString

from kodiswift import logger
from kodiswift import Plugin
from kodiswift import Request
from kodiswift import xbmc
from kodiswift import xbmcgui
from kodiswift import xbmcaddon

__version__ = '0.3.1'


class ExtendedPlugin(Plugin):

    @staticmethod
    def _parse_request(url=None, handle=None):
        """Handles setup of the plugin state, including request
        arguments, handle, mode.
        This method never needs to be called directly. For testing, see
        plugin.test()
        """
        # To accommodate self.redirect, we need to be able to parse a full
        # url as well
        if url is None:
            url = sys.argv[0]
            if len(sys.argv) >= 3:
                url += sys.argv[2]
        if handle is None:
            handle = sys.argv[1]
        return Request(url, handle)

    @property
    def addon_path(self):
        return xbmc.translatePath(self.addon.getAddonInfo('path'))

    @property
    def settings_file(self):
        return os.path.join(self.addon_path, 'resources', 'settings.xml')


class Polonium210IPTV(object):

    base_url = 'https://api.polonium-210.pl/iptv/'

    def get_playlist_url(self, plugin_id, auth_token):
        uri = '{0}/playlist.m3u8?auth_token={1}'.format(plugin_id, auth_token)
        return urlparse.urljoin(self.base_url, uri)


class SimpleIPTVPlugin(object):

    def __init__(self, plugin):
        self.plugin = plugin

    @property
    def addon_path(self):
        return xbmc.translatePath(self.plugin.addon.getAddonInfo('path'))

    @property
    def settings_file(self):
        return os.path.join(
            self.plugin.addon_path, '..', '..', 'userdata', 'addon_data',
            'pvr.iptvsimple', 'settings.xml',
        )

    def set_m3u_url(self, url):
        dom = parse(self.settings_file)

        tree = etree.parse(self.settings_file)
        nodes = tree.xpath("//setting[@id = 'm3uUrl']")
        nodes[0].text = url
        tree.write(self.settings_file)

        dom = parseString(data)
        for setting_element in dom.getElementsByTagName("setting"):

    def read_settings_xml(self):
        with open(self.settings_file, 'r') as f:
            return f.read()

    def write_settings_xml(self, new_xml):
        with open(self.settings_file, 'w') as f:
            f.write(new_xml)


class CountdownDialog(object):
    __INTERVALS = 5
    
    def __init__(self, heading, line1='', line2='', line3='', countdown=60, interval=5):
        self.heading = heading
        self.countdown = countdown
        self.interval = interval
        self.line3 = line3
        self.pd = xbmcgui.DialogProgress()
        if not self.line3: line3 = 'Expires in: %s seconds' % (countdown)
        self.pd.create(self.heading, line1, line2, line3)
        self.pd.update(100)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.pd is not None:
            self.pd.close()
            del self.pd

    def start(self, func, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        result = func(*args, **kwargs)
        if result:
            return result

        if self.pd is not None:
            start = time.time()
            expires = time_left = self.countdown
            interval = self.interval
            while time_left > 0:
                for _ in range(CountdownDialog.__INTERVALS):
                    xbmc.sleep(interval * 1000 / CountdownDialog.__INTERVALS)
                    if self.is_canceled():
                        raise Exception('CountdownDialog Cancelled')
                    time_left = expires - int(time.time() - start)
                    if time_left < 0: time_left = 0
                    progress = time_left * 100 / expires
                    line3 = 'Expires in: %s seconds' % (time_left) if not self.line3 else ''
                    self.update(progress, line3=line3)
                    
                result = func(*args, **kwargs)
                if result:
                    return result

            raise Exception('CountdownDialog Expired')

    def is_canceled(self):
        if self.pd is None:
            return False
        else:
            return self.pd.iscanceled()

    def update(self, percent, line1='', line2='', line3=''):
        if self.pd is not None:
            self.pd.update(percent, line1, line2, line3)


class Authenticator(object):

    def __init__(self, plugin, client):
        self.plugin = plugin
        self.client = client

    def authenticate(self):
        tokens = self.client.get_tokens()
        access_code = tokens['access_code']
        verification_url = tokens['verification_url']
        auth_data = self.get_auth_data(access_code, verification_url, 5)
        self.client.auth_token = auth_data['auth_token']
        self.client.refresh_token = auth_data['refresh_token']
        self.plugin.set_setting('auth_token', auth_data['auth_token'])
        self.plugin.set_setting('refresh_token', auth_data['refresh_token'])

    def check_auth(self, access_code):
        try:
            return self.client.get_tokens(access_code)
        except:
            return None

    def get_auth_data(self, access_code, verification_url, interval=5):
        title = 'Polonium-210 Authorization'
        line1 = 'Go to URL: {0}'.format(verification_url)
        line2 = 'When prompted enter: [B]{0}[/B]'.format(access_code)
        with CountdownDialog(
                title, line1, line2, countdown=120, interval=interval) as cd:
            return cd.start(self.check_auth, [access_code])

    def auth_required(self, func):
        def decorated(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as exc:
                if exc.response.status_code == 401:
                    self.authenticate()
                    return func(*args, **kwargs)
                logger.log.warning("Request failed: %s", exc)
                raise
            except requests.exceptions.ConnectionError as exc:
                icon = self.plugin.addon.getAddonInfo('icon')
                xbmcgui.Dialog().notification(
                    'Polonium-210', 'API connection error', icon=icon)

            except requests.exceptions.SSLError as exc:
                icon = self.plugin.addon.getAddonInfo('icon')
                xbmcgui.Dialog().notification(
                    'Polonium-210', 'SSL certificate error', icon=icon)

        return decorated


class Polonium210Client(object):

    # @todo: move to prod
    # base_url = 'https://api.polonium-210.pl/v1/'
    base_url = 'http://localhost:5000/v1/'

    default_params = {
        'format': 'kodi',
    }

    def __init__(self, auth_token=None, refresh_token=None):
        self.auth_token = auth_token
        self.refresh_token = refresh_token

    def request(self, method, uri, params=None, data=None, parser='json'):
        url = urlparse.urljoin(self.base_url, uri)
        headers = self.get_headers()
        params_all = self.get_default_params()

        if params is not None:
            params_all.update(params)

        if data is not None:
            data = json.dumps(data)

        method_callable = getattr(requests, method)
        resp = method_callable(
            url, params=params_all, data=data, headers=headers)

        resp.raise_for_status()

        if parser == 'json':
            return resp.json()

        return resp

    def get_default_params(self):
        params = self.default_params.copy()

        # if self.auth_token is not None:
        #     params.update({'auth_token': self.auth_token})

        return params

    def get_user_agent(self):
        try:
            return xbmc.getUserAgent()
        except AttributeError:
            return 'Kodi/16'

    def get_headers(self):
        headers = {
            'User-Agent': self.get_user_agent(),
            'Content-type': 'application/json',
            'Accept': 'text/plain',
        }
        if self.auth_token is not None:
            headers['Authorization'] = 'Bearer {0}'.format(self.auth_token)

        return headers

    def get_tokens(self, access_code=None):
        uri = 'tokens'

        params = {}
        if access_code is not None:
            params = {'access_code': access_code}

        return self.request('get', uri, params=params)['data']

    def get_plugins(self):
        uri = 'plugins'
        return self.request('get', uri)

    def get_plugin_request(self, plugin_id, path):
        params = {
            'path': path,
        }
        uri = 'plugins/{0}/'.format(plugin_id)
        return self.request('get', uri, params=params)

    def get_settings(self):
        uri = 'settings'
        return self.request('get', uri)

    def update_settings(self, settings):
        uri = 'settings'
        return self.request('put', uri, data=settings, parser=None)


class ResponseDispatcher(object):

    apiVersion = '0.3'

    def __init__(self, plugin, client):
        self.plugin = plugin
        self.client = client

    def dispatch(self, response):
        if response['apiVersion'] != self.apiVersion:
            icon = self.plugin.addon.getAddonInfo('icon')
            xbmcgui.Dialog().notification(
                'Polonium-210',
                'API version mismatch. Please update your plugin.',
                icon=icon,
            )

        if response['kind'] == 'pluginList':
            return self.plugin_list(response['data'])

        if response['kind'] == 'itemList':
            return self.item_list(response['data'])

        if response['kind'] == 'itemPlay':
            return self.item_play(response['data'])

        if response['kind'] == 'globalSettings':
            return self.global_settings(response['data'])

        icon = self.plugin.addon.getAddonInfo('icon')
        xbmcgui.Dialog().notification(
            'Polonium-210', 'Unexpected API response kind', icon=icon)

    def plugin_list(self, data):
        return data['items']

    def item_list(self, data):
        return data['items']

    def item_play(self, data):
        progress = xbmcgui.DialogProgress()
        try:
            progress.create('Polonium-210', 'Stream is starting ...')
            progress.update(25)
            item = data['item'].copy()
            item['is_playable'] = True
            if 'streams' not in data:
                icon = self.plugin.addon.getAddonInfo('icon')
                xbmcgui.Dialog().notification(
                    'Polonium-210', 'No stream', icon=icon)

            streams_qualities = data['streams'].keys()
            original_streams_qualities = list(filter(
                lambda x: x not in ['best', 'worst'], streams_qualities))
            original_streams_qualities_len = len(original_streams_qualities)
            if original_streams_qualities_len > 1:
                selected = self._select_dialog("Select stream", streams_qualities)
                if selected < 0:
                    return
            else:
                selected = 0

            progress.update(50)

            selected_quality = streams_qualities[selected]
            stream = data['streams'][selected_quality]

            if stream['type'] in ('http', 'hls'):
                item['path'] = stream['url']
            elif stream['type'] == 'rtmp':
                params = stream['params'].copy()
                url = params.pop('rtmp')
                args = " ".join(["=".join([k, str(v)]) for k, v in params.items()])
                item['path'] = " ".join([url, args])
            else:
                icon = self.plugin.addon.getAddonInfo('icon')
                xbmcgui.Dialog().notification(
                    'Polonium-210',
                    "Unsupported stream type {0}".format(stream['type']),
                    icon = icon,
                )
            self.plugin.play_video(item)
            # self.plugin.set_resolved_url(item)
            progress.update(75)
        finally:
            if progress:
                progress.close()

    def global_settings(self, data):
        self.write_settings_xml(data)
        # self.plugin.open_settings()
        # settings = self.plugin.get_settings()
        # settings_xml = self._read_settings_xml()
        # raise Exception(settings)

    def _select_dialog(self, title, choices):
        dialog = xbmcgui.Dialog()
        return dialog.select(title, choices)

    def write_settings_xml(self, new_xml):
        with open(self.plugin.settings_file, 'w') as f:
            f.write(new_xml)


class SettingsManager(object):

    def __init__(self, plugin, client, response_dispatcher):
        self.plugin = plugin
        self.client = client
        self.response_dispatcher = response_dispatcher

    def update_settings_xml(self, func):
        def decorated(*args, **kwargs):
            response = self.client.get_settings()
            self.response_dispatcher.dispatch(response)
            settings = self.get_settings()
            self.client.update_settings(settings)
            return func(*args, **kwargs)
        return decorated

    def get_settings(self):
        data = self.read_settings_xml()
        settings = {}
        dom = parseString(data)
        for setting_element in dom.getElementsByTagName("setting"):
            setting_id, value = self.parse_setting(setting_element)
            if setting_id is None:
                continue
            settings[setting_id] = value
        return settings

    def parse_setting(self, setting_element):
        if not setting_element.hasAttribute("id"):
            return None, None

        setting_id = setting_element.getAttribute("id")

        values = None
        if setting_element.hasAttribute("values"):
            values = setting_element.getAttribute("values").split('|')

        try:
            value = self.plugin.get_setting(setting_id, choices=values)
        except ValueError:
            value = None

        return setting_id, value

    def read_settings_xml(self):
        with open(self.plugin.settings_file, 'r') as f:
            return f.read()


plugin = ExtendedPlugin('Polonium-210', addon_id='plugin.video.polonium210')
client = Polonium210Client(
    auth_token=plugin.get_setting('auth_token'),
    refresh_token=plugin.get_setting('refresh_token'),
)
iptv = Polonium210IPTV()
simple_iptv_plugin = SimpleIPTVPlugin(plugin)
authenticator = Authenticator(plugin, client)
response_dispatcher = ResponseDispatcher(plugin, client)
settings_manager = SettingsManager(plugin, client, response_dispatcher)


@authenticator.auth_required
@settings_manager.update_settings_xml
def index():
    response = client.get_plugins()
    return response_dispatcher.dispatch(response)


@authenticator.auth_required
@settings_manager.update_settings_xml
def plugin_request(plugin_id):
    path = plugin.request.args.get('path', '/')
    response = client.get_plugin_request(plugin_id, path)
    return response_dispatcher.dispatch(response)


@authenticator.auth_required
@settings_manager.update_settings_xml
def iptv():
    plugin_id = plugin.request.args['plugin_id']
    url = iptv.get_playlist_url(plugin_id)
    simple_iptv_plugin.set_m3u_url(url)


plugin.add_url_rule("/", index, name='index')
plugin.add_url_rule("/iptv/", iptv, name='iptv')
plugin.add_url_rule(
    "/<plugin_id>/", plugin_request, name='plugin_request')

if __name__ == '__main__':
    plugin.run()
