# Bot

![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)

This is a bot engine using asyncio, requires Python >= 3.8.

All behaviors run in a single thread.

```python
from bot import hear, space, task
from datetime import time


@hear('[Hh]ello', ambient=True)
async def hello(message):
    await message.reply('Hello!')


@task(time(hour=8))
async def wakeup():
    await space.post('#general', 'Good morning!')
```

## Installation

It's a very small package, so you can easily install, update and delete it.

```bash
pip install -U git+https://github.com/oshinko/bot.git
```

## Creating module

Try with a simple program that returns a greeting.

```bash
cat <<EOF> hello.py
from bot import hear


@hear('[Hh]ello')
async def hello(message):
    await message.reply('Hello!')
EOF
```

## Startup

On the Discord:

```bash
python -m bot --space bot.spaces.Discord \
              --token ${DISCORD_BOT_TOKEN} \
              --modules hello \
              --errorsto "#errors"
```

To run on the Slack:

```bash
python -m bot --space bot.spaces.Slack \
              --token ${SLACK_BOT_TOKEN} \
              --modules hello \
              --errorsto "#errors"
```
