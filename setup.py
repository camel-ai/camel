from setuptools import find_packages, setup

__version__ = '0.0.1'

install_requires = [
    'numpy',
    'openai',
    'tenacity',
    'tiktoken',
]

full_requires = []
test_requires = []
dev_requires = []

setup(
    name='camel',
    version=__version__,
    install_requires=install_requires,
    extras_require={
        'full': full_requires,
        'test': test_requires,
        'dev': dev_requires,
    },
    packages=find_packages(),
)
