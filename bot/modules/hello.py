from .. import hear


@hear('[Hh]ello')
async def hello(message):
    await message.reply('Hello!')
