from setuptools import setup

setup(
    name='bot',
    version='0.0.0',
    description='A bot engine.',
    author='Shintaro Maeda',
    author_email='maesin@renjaku.jp',
    url='https://github.com/maesin/bot',
    packages=['bot'],
    install_requires=['aiohttp', 'aioredis'],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython'
    ]
)
