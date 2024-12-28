# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from unittest.mock import patch

from camel.toolkits import FunctionTool, GoogleScholarToolkit


def test_get_author_detailed_info_by_name():
    with patch('scholarly.scholarly') as mock_scholarly:
        mock_scholarly.fill.return_value = {
            'name': 'Author Name',
            'publications': [],
        }
        toolkit = GoogleScholarToolkit('Author Name')

        author_info = toolkit.get_author_detailed_info()
        assert author_info['name'] == 'Author Name'
        assert author_info['publications'] == []


def test_get_author_detailed_info_by_url():
    with patch('scholarly.scholarly') as mock_scholarly:
        mock_scholarly.fill.return_value = {
            'name': 'Author Name',
            'publications': [],
        }
        toolkit = GoogleScholarToolkit(
            'https://scholar.google.com/citations?user=J9K-D0sAAAAJ'
        )

        author_info = toolkit.get_author_detailed_info()
        assert author_info['name'] == 'Author Name'
        assert author_info['publications'] == []


def test_get_author_publications():
    with patch('scholarly.scholarly') as mock_scholarly:
        mock_scholarly.fill.return_value = {
            'publications': [
                {'bib': {'title': 'Publication 1'}},
                {'bib': {'title': 'Publication 2'}},
            ]
        }
        toolkit = GoogleScholarToolkit('Author Name')

        publications = toolkit.get_author_publications()
        assert publications == ['Publication 1', 'Publication 2']


def test_get_publication_by_title_found():
    with patch('scholarly.scholarly') as mock_scholarly:
        mock_scholarly.fill.side_effect = [
            {
                'publications': [
                    {'bib': {'title': 'Publication 1'}},
                    {'bib': {'title': 'Publication 2'}},
                ]
            },
            {'bib': {'title': 'Publication 1', 'abstract': 'An abstract'}},
        ]
        toolkit = GoogleScholarToolkit('Author Name')

        publication_info = toolkit.get_publication_by_title('Publication 1')
        assert publication_info is not None
        assert publication_info['bib']['title'] == 'Publication 1'


def test_get_publication_by_title_not_found():
    with patch('scholarly.scholarly') as mock_scholarly:
        mock_scholarly.fill.return_value = {'publications': []}
        toolkit = GoogleScholarToolkit('Author Name')

        publication_info = toolkit.get_publication_by_title(
            'Nonexistent Publication'
        )
        assert publication_info is None


def test_get_tools():
    toolkit = GoogleScholarToolkit('Author Name')
    tools = toolkit.get_tools()
    assert len(tools) == 4
    assert all(isinstance(tool, FunctionTool) for tool in tools)
