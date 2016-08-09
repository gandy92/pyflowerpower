try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Python for FlowerPower',
    'author': 'Andy Thaller',
    'url': 'URL to get it at.',
    'download_url': 'Where to download it.',
    'author_email': 'gandy92@googlemail.com',
    'version': '0.1',
    'install_requires': ['nose'],
    'packages': ['NAME'],
    'scripts': [],
    'name': 'pyFlowerPower'
}

setup(**config)
