# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
#
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from setuptools import find_packages, setup

__version__ = '0.1.0'

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
