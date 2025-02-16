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
import unittest
from unittest.mock import MagicMock, patch

from camel.toolkits import SemanticScholarToolkit


class TestSemanticScholarToolkit(unittest.TestCase):
    def setUp(self):
        """
        Executed before each test, initialize the toolkit instance.
        """
        self.toolkit = SemanticScholarToolkit()

    @patch("requests.get")
    def test_fetch_paper_data_title_success(self, mock_get):
        """
        Test fetch_paper_data_title returning 200 successfully.
        """
        mock_response_data = {"data": "some paper data"}
        # Configure the mock to return the response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        paper_title = "A Test Paper"
        response = self.toolkit.fetch_paper_data_title(paper_title)

        # Verify the call details of requests.get
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]  # The first argument is the URL
        called_params = mock_get.call_args[1]["params"]
        self.assertIn("paper/search", called_url)
        self.assertEqual(called_params["query"], paper_title)

        # Verify the returned result
        self.assertEqual(response, mock_response_data)

    @patch("requests.get")
    def test_fetch_paper_data_title_error(self, mock_get):
        """
        Test fetch_paper_data_title returning a non-200 status.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {
            "error": "Request failed with status code 404",
            "message": "Not Found",
        }
        mock_get.return_value = mock_response

        paper_title = "Nonexistent Paper"
        response = self.toolkit.fetch_paper_data_title(paper_title)

        self.assertIn("error", response)
        self.assertIn("Request failed", response["error"])
        self.assertEqual(response["message"], "Not Found")

    @patch("requests.get")
    def test_fetch_paper_data_id_success(self, mock_get):
        """
        Test fetch_paper_data_id returning 200 successfully.
        """
        mock_response_data = {"title": "Paper Title by ID"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        paper_id = "abcdef123456"
        response = self.toolkit.fetch_paper_data_id(paper_id)
        mock_get.assert_called_once()
        self.assertEqual(response, mock_response_data)

        # Get the URL used in the call for confirmation
        called_url = mock_get.call_args[0][0]
        self.assertIn(paper_id, called_url)

    @patch("requests.get")
    def test_fetch_paper_data_id_failure(self, mock_get):
        """
        Test fetch_paper_data_id returning a non-200 status.
        """
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {
            "error": "Request failed with status code 500",
            "message": "Internal Server Error",
        }
        mock_get.return_value = mock_response

        paper_id = "xyz789"
        response = self.toolkit.fetch_paper_data_id(paper_id)

        self.assertIn("error", response)
        self.assertIn("500", response["error"])
        self.assertEqual(response["message"], "Internal Server Error")

    @patch("requests.get")
    def test_fetch_bulk_paper_data_success(self, mock_get):
        """
        Test fetch_bulk_paper_data returning 200 successfully.
        """
        mock_response_data = {"data": ["paper1", "paper2"]}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        query_str = "cloud computing"
        response = self.toolkit.fetch_bulk_paper_data(query_str)

        mock_get.assert_called_once()
        self.assertEqual(response, mock_response_data)

        # Check the parameters
        called_url = mock_get.call_args[0][0]
        called_params = mock_get.call_args[1]["params"]
        self.assertIn("bulk", called_url)
        self.assertEqual(called_params["query"], query_str)

    @patch("requests.get")
    def test_fetch_bulk_paper_data_failure(self, mock_get):
        """
        Test fetch_bulk_paper_data returning a non-200 status.
        """
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.json.return_value = {
            "error": "Request failed with status code 403",
            "message": "Forbidden",
        }
        mock_get.return_value = mock_response

        query_str = "quantum computing"
        response = self.toolkit.fetch_bulk_paper_data(query_str)

        self.assertIn("error", response)
        self.assertIn("403", response["error"])
        self.assertEqual(response["message"], "Forbidden")

    @patch("requests.post")
    def test_fetch_recommended_papers_success(self, mock_post):
        """
        Test fetch_recommended_papers returning 200 successfully.
        """
        mock_response_data = {"papers": [{"id": "123"}, {"id": "456"}]}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        pos_ids = ["111", "222"]
        neg_ids = ["333"]
        result = self.toolkit.fetch_recommended_papers(
            positive_paper_ids=pos_ids,
            negative_paper_ids=neg_ids,
            save_to_file=False,
        )

        mock_post.assert_called_once()
        # Validate the request body, URL, and parameters
        called_url = mock_post.call_args[0][0]
        self.assertIn("recommendations/v1/papers", called_url)

        called_json = mock_post.call_args[1]["json"]
        self.assertEqual(called_json["positive_paper_ids"], pos_ids)
        self.assertEqual(called_json["negative_paper_ids"], neg_ids)

        self.assertEqual(result, mock_response_data)

    @patch("requests.post")
    def test_fetch_recommended_papers_failure(self, mock_post):
        """
        Test fetch_recommended_papers returning a non-200 status.
        """
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {
            "error": "Request failed with status code 400",
            "message": "Bad Request",
        }
        mock_post.return_value = mock_response

        result = self.toolkit.fetch_recommended_papers(
            positive_paper_ids=["p1"], negative_paper_ids=["p2"]
        )

        self.assertIn("error", result)
        self.assertIn("400", result["error"])

    @patch("requests.post")
    def test_fetch_author_data_success(self, mock_post):
        """
        Test fetch_author_data returning 200 successfully.
        """
        mock_response_data = {
            "data": [
                {"authorId": "A1", "name": "Author One"},
                {"authorId": "A2", "name": "Author Two"},
            ]
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        author_ids = ["A1", "A2"]
        result = self.toolkit.fetch_author_data(author_ids, save_to_file=False)
        mock_post.assert_called_once()
        self.assertEqual(result, mock_response_data)

        # Check if JSON body includes the correct IDs
        called_json = mock_post.call_args[1]["json"]
        self.assertEqual(called_json["ids"], author_ids)

    @patch("requests.post")
    def test_fetch_author_data_failure(self, mock_post):
        """
        Test fetch_author_data returning a non-200 status.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {
            "error": "Request failed with status code 404",
            "message": "Not Found",
        }

        # Let raise_for_status throw an HTTPError to trigger the except branch
        from requests.exceptions import HTTPError

        mock_response.raise_for_status.side_effect = HTTPError(
            "404 Client Error"
        )

        mock_post.return_value = mock_response
        result = self.toolkit.fetch_author_data(["A999"])

        self.assertIn("error", result)
        self.assertIn("404 Client Error", result["error"])

    def test_get_tools(self):
        """
        Test whether get_tools returns the correct number of tool functions
        and references.
        """
        tools = self.toolkit.get_tools()
        self.assertEqual(len(tools), 5)
        # Simply assert whether the callable of each tool matches our methods
        self.assertEqual(tools[0].func, self.toolkit.fetch_paper_data_title)
        self.assertEqual(tools[1].func, self.toolkit.fetch_paper_data_id)
        self.assertEqual(tools[2].func, self.toolkit.fetch_bulk_paper_data)
        self.assertEqual(tools[3].func, self.toolkit.fetch_recommended_papers)
        self.assertEqual(tools[4].func, self.toolkit.fetch_author_data)


if __name__ == "__main__":
    unittest.main()
