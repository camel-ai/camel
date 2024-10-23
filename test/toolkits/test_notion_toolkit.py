# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
from unittest.mock import patch

from camel.toolkits import FunctionTool, NotionToolkit


def test_get_notion_block_text_content():
    with patch('notion_client.Client') as mock_client:
        # Mock the list_children method to return a sample block structure
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "This is a sample paragraph"
                                },
                            },
                        ]
                    },
                },
                {
                    "type": "unsupported",
                },
            ],
            "has_more": False,
        }

        notion_client = NotionToolkit()

        block_id = "block id"

        text_content = notion_client.get_notion_block_text_content(block_id)

        expected_text = "This is a sample paragraph [Unsupported block type]"

        assert text_content == expected_text

        mock_client.blocks.children.list.assert_called_once_with(
            block_id=block_id, start_cursor=None
        )


def test_list_all_pages():
    # Mock the search method to return sample page data
    with patch('notion_client.Client') as mock_client:
        mock_client.search.return_value = [
            {
                "results": [
                    {
                        "id": "page-id-1",
                        "properties": {
                            "title": [
                                {"type": "text", "text": {"content": "Page 1"}}
                            ]
                        },
                    },
                    {
                        "id": "page-id-2",
                        "properties": {
                            "title": [
                                {"type": "text", "text": {"content": "Page 2"}}
                            ]
                        },
                    },
                ],
                "has_more": True,
            },
            {
                "results": [
                    {
                        "id": "page-id-3",
                        "properties": {
                            "title": [
                                {"type": "text", "text": {"content": "Page 3"}}
                            ]
                        },
                    },
                ],
                "has_more": False,
            },
        ]

        # Create a NotionToolkit instance
        notion_client = NotionToolkit()

        # Call the method under test
        all_pages = notion_client.list_all_pages()

        # Expected list of pages with titles and IDs
        expected_pages = [
            {"id": "page-id-1", "title": "Page 1"},
            {"id": "page-id-2", "title": "Page 2"},
            {"id": "page-id-3", "title": "Page 3"},
        ]

        # Assert that the returned list matches the expectation
        assert all_pages == expected_pages


def test_get_tools():
    toolkit = NotionToolkit()
    tools = toolkit.get_tools()
    assert len(tools) == 2
    assert all(isinstance(tool, FunctionTool) for tool in tools)
