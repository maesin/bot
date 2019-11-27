from setuptools import setup

setup(
    name='bot',
    version='0.0.0',
    description='A bot engine.',
    author='Osnk',
    author_email='osnk@renjaku.jp',
    url='https://github.com/maesin/bot',
    packages=['bot', 'bot.modules'],
    install_requires=['aiohttp'],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython'
    ]
)
