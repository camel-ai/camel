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
"""
Tests for the ArtifactToolkit.
"""

from datetime import datetime

from camel.toolkits.artifact_toolkit import ArtifactToolkit


class TestArtifactToolkit:
    """Test ArtifactToolkit class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.toolkit = ArtifactToolkit()

    def test_create_html_artifact_basic(self):
        """Test basic HTML artifact creation."""
        content = "<h1>Test Content</h1><p>This is a test.</p>"
        title = "Test HTML"

        result = self.toolkit.create_html_artifact(content, title)

        assert result["type"] == "html"
        assert result["title"] == title
        assert content in result["content"]
        assert "metadata" in result
        assert "created_at" in result["metadata"]
        assert "artifact_id" in result["metadata"]
        assert result["metadata"]["has_css"] is True

    def test_create_html_artifact_no_css(self):
        """Test HTML artifact creation without CSS."""
        content = "<p>Simple content</p>"

        result = self.toolkit.create_html_artifact(content, include_css=False)

        assert result["type"] == "html"
        assert result["metadata"]["has_css"] is False

    def test_create_html_artifact_with_custom_css(self):
        """Test HTML artifact creation with custom CSS."""
        content = "<div class='custom'>Styled content</div>"
        custom_css = ".custom { color: red; }"

        result = self.toolkit.create_html_artifact(
            content, css_styles=custom_css
        )

        assert result["type"] == "html"
        assert custom_css in result["content"]
        assert result["metadata"]["has_css"] is True

    def test_create_svg_artifact(self):
        """Test SVG artifact creation."""
        svg_content = '<circle cx="50" cy="50" r="40" fill="blue"/>'
        title = "Test SVG"

        result = self.toolkit.create_svg_artifact(svg_content, title)

        assert result["type"] == "svg"
        assert result["title"] == title
        assert svg_content in result["content"]
        assert "metadata" in result
        assert "created_at" in result["metadata"]

    def test_create_code_artifact(self):
        """Test code artifact creation."""
        code = 'print("Hello, World!")\nx = 42'
        language = "python"
        title = "Test Code"

        result = self.toolkit.create_code_artifact(code, language, title)

        assert result["type"] == "code"
        assert result["title"] == title
        assert result["language"] == language
        assert code in result["content"]
        assert "metadata" in result

    def test_create_markdown_artifact(self):
        """Test Markdown artifact creation."""
        markdown_content = "# Test\nThis is **bold** text."
        title = "Test Markdown"

        result = self.toolkit.create_markdown_artifact(markdown_content, title)

        assert result["type"] == "markdown"
        assert result["title"] == title
        assert markdown_content in result["content"]
        assert "metadata" in result

    def test_create_latex_math(self):
        """Test LaTeX math artifact creation."""
        latex_expression = "E = mc^2"
        title = "Einstein's Equation"

        result = self.toolkit.create_latex_math(latex_expression, title)

        assert result["type"] == "latex"
        assert result["title"] == title
        assert latex_expression in result["content"]
        assert "metadata" in result

    def test_create_mermaid_flowchart(self):
        """Test Mermaid flowchart creation."""
        mermaid_code = "graph TD\n    A[Start] --> B[End]"
        title = "Test Flowchart"

        result = self.toolkit.create_mermaid_flowchart(mermaid_code, title)

        assert result["type"] == "mermaid"
        assert result["title"] == title
        assert mermaid_code in result["content"]
        assert "metadata" in result

    def test_artifact_metadata_contains_timestamp(self):
        """Test that all artifacts contain proper metadata with timestamps."""
        before_time = datetime.now()

        result = self.toolkit.create_html_artifact("test")

        after_time = datetime.now()

        created_at = datetime.fromisoformat(result["metadata"]["created_at"])
        assert before_time <= created_at <= after_time

    def test_artifact_id_uniqueness(self):
        """Test that artifact IDs are unique."""
        import time
        result1 = self.toolkit.create_html_artifact("test1")
        time.sleep(0.001)  # Ensure different timestamp
        result2 = self.toolkit.create_html_artifact("test2")

        assert (
            result1["metadata"]["artifact_id"]
            != result2["metadata"]["artifact_id"]
        )

    def test_complete_html_document_passthrough(self):
        """Test that complete HTML documents are passed through unchanged."""
        complete_html = (
            '<!DOCTYPE html><html><head><title>Test</title></head>'
            '<body><h1>Complete</h1></body></html>'
        )

        result = self.toolkit.create_html_artifact(complete_html)

        assert result["content"] == complete_html

    def test_svg_artifact_with_custom_dimensions(self):
        """Test SVG artifact with custom width and height."""
        svg_content = '<rect width="100" height="50" fill="green"/>'

        result = self.toolkit.create_svg_artifact(
            svg_content, "Custom SVG", width=200, height=150
        )

        assert 'width="200"' in result["content"]
        assert 'height="150"' in result["content"]

    def test_code_artifact_different_languages(self):
        """Test code artifacts with different programming languages."""
        languages = ["python", "javascript", "java", "cpp", "html"]

        for lang in languages:
            result = self.toolkit.create_code_artifact(
                f"// {lang} code example", lang, f"Test {lang.title()}"
            )

            assert result["language"] == lang
            assert result["type"] == "code"

    def test_error_handling_empty_content(self):
        """Test handling of empty content."""
        result = self.toolkit.create_html_artifact("")

        assert result["type"] == "html"
        assert result["content"] is not None
        assert (
            len(result["content"]) > 0
        )  # Should have HTML wrapper even with empty content

    def test_special_characters_in_content(self):
        """Test handling of special characters in content."""
        special_content = '<script>alert("test");</script>&amp;&lt;&gt;'

        result = self.toolkit.create_html_artifact(special_content)

        assert result["type"] == "html"
        assert special_content in result["content"]

    def test_toolkit_get_tools_method(self):
        """Test that the toolkit properly exposes its tools."""
        tools = self.toolkit.get_tools()

        # Should have all 6 main artifact creation tools
        tool_names = [tool.func.__name__ for tool in tools]
        expected_tools = [
            "create_html_artifact",
            "create_svg_artifact",
            "create_code_artifact",
            "create_markdown_artifact",
            "create_latex_math",
            "create_mermaid_flowchart",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names
