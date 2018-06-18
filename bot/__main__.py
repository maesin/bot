import asyncio
import bot
import bot.args
import datetime
import json
import importlib
import importlib.util
import re
import traceback


def hear(regex, channels=[], ambient=False):
    def wrapper(fn):
        p = re.compile(regex)

        def h(message):
            m = p.search(message.text)
            if m and ((not channels or message.channel in channels) and
                      (ambient or bot.space.me in message.mentions or
                       message.channel in bot.space.ims)):
                return m
            return None
        bot.hears.append((h, fn))
        return fn
    return wrapper


def task(trigger):
    def wrapper(fn):
        bot.tasks.append((trigger, fn))
        return fn
    return wrapper


async def call(callback, *args):
    try:
        await callback(*args)
    except Exception as e:
        await bot.space.post(bot.errorsto,
                             f'```{traceback.format_exc()}```')
        raise e

s = None
async def event_dispatcher(c):
    while True:
        try:
            m = await asyncio.wait_for(c.receive(), timeout=60)
        # async for m in c:
            print('Recived', m)
            try:
                e = bot.space.parse(m.data)
                if e and e.message and e.message.user != bot.space.me:
                    for hear, action in bot.hears:
                        r = hear(e.message)
                        if r:
                            a = r.groups()
                            asyncio.ensure_future(call(action, e.message, *a))
            except bot.spaces.ChannelNotFound:
                pass
        except asyncio.TimeoutError:
            if s == None:
                print('s is None')
            elif s.done():
                print('s was done', '(cancelled)' if s.cancelled() else '(not cancelled)')
            else:
                print('s is not done')


async def task_scheduler():
    last_consumed = {}
    while True:
        for trigger, task in bot.tasks:
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


async def main():
    global s
    while True:
        async with await bot.space.connect() as c:
            print('Connected')
            await bot.space.prepare(c)
            print('Prepared')
            try:
                s = asyncio.ensure_future(task_scheduler())
                await event_dispatcher(c)
            except:  # An unexpected error has occurred.
                print(traceback.format_exc())
            finally:
                s.cancel()
                print('Disconnected')
                await asyncio.sleep(30)


def start(command_line_args):
    bot.space = args.space(args.token)
    bot.hear = hear
    bot.task = task
    bot.hears = []
    bot.tasks = []
    bot.errorsto = args.errorsto
    for m in args.modules:
        importlib.import_module(m)
    print('Start bot')
    asyncio.get_event_loop().run_until_complete(main())

if __name__ == '__main__':
    args = bot.args.parse()
    start(args)
