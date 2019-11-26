import argparse
import asyncio
import datetime
import importlib
import importlib.util
import os
import re
import traceback

from . import spaces

space = None
errorsto = None
hears = []
tasks = []
s = None


def hear(regex, channels=[], ambient=False):
    def wrapper(fn):
        p = re.compile(regex)

        def h(message):
            m = p.search(message.text)
            if m and ((not channels or message.channel in channels) and
                      (ambient or space.me in message.mentions or
                       message.channel in space.ims)):
                return m
            return None
        hears.append((h, fn))
        return fn
    return wrapper


def task(trigger):
    def wrapper(fn):
        tasks.append((trigger, fn))
        return fn
    return wrapper


async def call(callback, *args):
    try:
        await callback(*args)
    except Exception as e:
        await space.post(errorsto, f'```{traceback.format_exc()}```')
        raise e


async def event_dispatcher(c):
    while True:
        try:
            m = await asyncio.wait_for(c.receive(), timeout=60)
        # async for m in c:
            print('Recived', m)
            try:
                e = space.parse(m.data)
                if e and e.message and e.message.user != space.me:
                    for hear, action in hears:
                        r = hear(e.message)
                        if r:
                            a = r.groups()
                            asyncio.ensure_future(call(action, e.message, *a))
            except spaces.ChannelNotFound:
                pass
            except TypeError as e:  # FIXME json.load エラー
                raise Exception(f'{m.data} is error') from e
        except asyncio.TimeoutError:
            if s is None:
                print('s is None')
            elif s.done():
                print('s was done', '(cancelled)'
                      if s.cancelled() else '(not cancelled)')
            else:
                print('s is not done')


async def task_scheduler():
    last_consumed = {}
    while True:
        for trigger, task in tasks:
            since = last_consumed[task] if task in last_consumed else None
            if isinstance(trigger, datetime.datetime):
                n = datetime.datetime.now(tz=trigger.tzinfo)
                w = trigger
            elif isinstance(trigger, datetime.timedelta):
                n = datetime.datetime.now()
                w = since + trigger if since else n
            elif isinstance(trigger, datetime.time):
                n = datetime.datetime.now(tz=trigger.tzinfo)
                w = n.replace(hour=trigger.hour,
                              minute=trigger.minute,
                              second=trigger.second,
                              microsecond=trigger.microsecond)
            else:
                m = 'Invalid trigger type {0}'.format(type(trigger))
                raise Exception(m)
            if (w <= n and (not since or since < w) and
                    (n - w).total_seconds() <= 60):
                asyncio.ensure_future(call(task))
                last_consumed[task] = n
        await asyncio.sleep(1)


async def async_main():
    global s
    while True:
        async with await space.connect() as c:
            print('Connected')
            await space.prepare(c)
            print('Prepared')
            try:
                s = asyncio.ensure_future(task_scheduler())
                await event_dispatcher(c)
            except Exception:  # An unexpected error has occurred.
                print(traceback.format_exc())
            finally:
                s.cancel()
                print('Disconnected')
                await asyncio.sleep(30)


def space_type(s):
    try:
        m, classname = s.rsplit('.', 1)
        return getattr(importlib.import_module(m), classname)
    except Exception:
        raise argparse.ArgumentTypeError('Unknown space')


class DefaultSpace:
    def __init__(self, space_class):
        self.space_class = space_class

    def __call__(self, *args, **kwargs):
        return self.space_class(*args, **kwargs)

    def __str__(self):
        return f'{self.space_class.__module__}.{self.space_class.__name__}'


class DefaultModules(list):
    def __str__(self):
        return ' '.join(x for x in self)


def parse_args():
    prog = os.path.basename(os.path.dirname(__file__))
    parser = argparse.ArgumentParser(prog, description='A bot engine')
    parser.add_argument('--space',
                        type=space_type,
                        default=DefaultSpace(spaces.Discord),
                        help='Space name (default: %(default)s)')
    parser.add_argument('--token',
                        required=True,
                        help='Space auth token')
    parser.add_argument('--modules',
                        nargs='*',
                        default=DefaultModules(['bot.modules.hello']),
                        metavar='MODULE',
                        help='Bot modules (default: %(default)s)')
    parser.add_argument('--errorsto',
                        default='#errors',
                        help='Error destination channel (default: %(default)s)')
    return parser.parse_args()


def main():
    global space, errorsto
    _args = parse_args()
    space = _args.space(_args.token)
    errorsto = _args.errorsto
    for m in _args.modules:
        importlib.import_module(m)
    print('Start bot')  # TODO Logger 使う
    asyncio.run(async_main())


if __name__ == '__main__':
    main()
