from setuptools import find_packages, setup

__version__ = '0.0.1'

install_requires = [
    'numpy',
    'openai',
    'tenacity',
    'tiktoken',
    'colorama',
]

test_requires = [
    'pytest',
    'pytest-cov',
]

dev_requires = [
    'pre-commit',
    'yapf',
    'isort',
    'flake8',
]

setup(
    name='camel',
    version=__version__,
    install_requires=install_requires,
    extras_require={
        'test': test_requires,
        'dev': dev_requires,
    },
    packages=find_packages(),
)
