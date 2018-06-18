import aiohttp
import asyncio
import json
import re


class Message:
    def __init__(self, space, channel, user, mentions, text,
                 create_mention):
        self.space = space
        self.channel = channel
        self.text = text
        self.user = user
        self.mentions = mentions
        self.create_mention = create_mention

    async def reply(self, message):
        m = self.create_mention(self.user) + ' ' + message
        await self.space.post(self.channel, m)


class Event:
    def __init__(self, space, channel=None, message=None):
        self.space = space
        self.channel = channel
        self.message = message


class Channel:
    def __init__(self, cid, name):
        self.id = cid
        self.name = name

    def __str__(self):
        return self.id

    def __eq__(self, o):
        if isinstance(o, self.__class__):
            return o.id == self.id
        elif isinstance(o, str):
            if o.startswith('#'):
                return o[1:] == self.name
            else:
                return o == self.id
        return False


class ChannelNotFound(Exception):
    def __init__(self, channel):
        super().__init__(f'Channel {channel} could not be found')


class WebSocketContextManager:
    def __init__(self, session, url):
        self.s = session
        self.w = self.s.ws_connect(url)

    async def __aenter__(self):
        return await self.w.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.w.__aexit__(exc_type, exc_val, exc_tb)
        await self.s.__aexit__(exc_type, exc_val, exc_tb)


class Slack:
    api = 'https://slack.com/api/{method}'

    def __init__(self, token):
        self.token = token

    def _create_channels(self, ims_or_channels):
        r = []
        for x in ims_or_channels:
            c = Channel(x['id'], x['user'] if 'user' in x else x['name'])
            r.append(c)
        return r

    async def connect(self):
        s = aiohttp.ClientSession()
        u = self.api.format(method='rtm.start')
        p = {'token': self.token}
        async with s.get(u, params=p) as r:
            assert 200 == r.status, r.reason
            j = await r.json()
            self.me = j['self']['id']
            self.ims = self._create_channels(j['ims'])
            self.channels = self._create_channels(j['channels'])
            return WebSocketContextManager(s, j['url'])

    async def prepare(self, ws):
        self.ws = ws

    def _find_channel(self, id_or_name):
        for x in self.ims + self.channels:
            if x == id_or_name:
                return x
        raise ChannelNotFound(id_or_name)

    def parse(self, event):
        e = json.loads(event)
        r = Event(self)
        if 'type' in e:
            if (e['type'] == 'message' and
                    'subtype' not in e and
                    'channel' in e and e['channel'] and
                    'text' in e and e['text']):
                r.channel = self._find_channel(e['channel'])
                r.message = Message(self, r.channel, e['user'],
                                    re.findall('<@([^>]+)>', e['text']),
                                    e['text'], lambda u: f'<@{u}>')
            elif e['type'] in ('channel_created', 'channel_joined'):
                c = Channel(e['channel']['id'], e['channel']['name'])
                self.channels.append(c)
            elif (e['type'] in ('channel_archive', 'channel_unarchive') and
                    e['channel'] in self.channels):
                c = self._find_channel(e['channel'])
                if c:
                    c.archived = e['type'] == 'channel_archive'
            elif (e['type'] == 'channel_deleted' and
                    e['channel'] in self.channels):
                c = self._find_channel(e['channel'])
                if c:
                    self.channels.remove(c)
        return r

    async def post(self, channel, message, attachments=None, thread_ts=None):
        if isinstance(channel, str):
            channel = self._find_channel(channel)
        data = {'type': 'message',
                'channel': str(channel),
                'text': re.sub('@(channel|here|everyone)', r'<!\1>', message),
                'attachments': attachments,
                'thread_ts': thread_ts}
        await self.ws.send_json(data)


class Discord:
    api = 'https://discordapp.com/api/{res}'

    def __init__(self, token):
        self.token = token
        self.ack = False
        self.reconnect = False
        self.ims = []

    async def connect(self):
        s = aiohttp.ClientSession()
        u = self.api.format(res='/gateway/bot')
        h = {'Authorization': f'Bot {self.token}'}
        async with s.get(u, headers=h) as r:
            assert 200 == r.status, r.reason
            j = await r.json()
            return WebSocketContextManager(s, f"{j['url']}?v=6&encoding=json")

    # TODO main にて任意でサポートする
    async def heartbeat(self, interval):
        """Send every interval ms the heatbeat message."""
        import datetime
        while True:
            print('Heatbeat', datetime.datetime.now())
            await self.ws.send_json({
                'op': 1,  # Heartbeat
                'd': 0
            })
            await asyncio.sleep(interval / 1000)  # seconds
            self.reconnect = not self.ack  # TODO main でサポートする際の参考

    async def prepare(self, ws):
        self.ws = ws
        async for m in self.ws:
            e = json.loads(m.data)
            if e['op'] == 10:
                n = e['d']['heartbeat_interval']
                asyncio.ensure_future(self.heartbeat(n))
                await self.ws.send_json({
                    'op': 2,  # Identify
                    'd': {
                        'token': self.token,
                        'properties': {},
                        'compress': False,
                        'large_threshold': 250
                    }
                })
            elif e['op'] == 0:
                if e['t'] == 'READY':
                    self.me = e['d']['user']['id']
                elif e['t'] == 'GUILD_CREATE':
                    c = e['d']['channels']
                    self.channels = [Channel(x['id'], x['name']) for x in c]
                    break

    def _find_channel(self, id_or_name):
        for x in self.ims + self.channels:
            if x == id_or_name:
                return x
        raise ChannelNotFound(id_or_name)

    def parse(self, event):
        e = json.loads(event)
        if e['op'] == 11:
            self.ack = True
            return None  # TODO None じゃなくて ack イベント定義してもいいかも
        r = Event(self)
        if 't' in e:
            if e['t'] == 'MESSAGE_CREATE':
                c = e['d']['channel_id']
                r.channel = self._find_channel(c)
                text = e['d']['content']
                r.message = Message(self, r.channel, e['d']['author']['id'],
                                    re.findall('<@([^>]+)>', text),
                                    text, lambda u: f'<@{u}>')
            elif e['t'] == 'CHANNEL_CREATE':
                if e['d']['type'] == 1:  # DM
                    c = e['d']['id']
                    if not [x for x in self.ims if x == c]:
                        self.ims.append(Channel(c, c))
        return r

    async def post(self, channel, message, attachments=None, thread_ts=None):
        if isinstance(channel, str):
            channel = self._find_channel(channel)
        async with aiohttp.ClientSession() as s:
            u = self.api.format(res=f"/channels/{channel.id}/messages")
            h = {'Authorization': f'Bot {self.token}'}
            async with s.post(u, headers=h, json={'content': message}) as r:
                assert 200 == r.status, r.reason
                return await r.json()
