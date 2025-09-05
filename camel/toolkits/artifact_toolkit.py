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

from datetime import datetime
from typing import Any, Dict, List, Optional

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer


@MCPServer()
class ArtifactToolkit(BaseToolkit):
    r"""A toolkit for creating and managing artifacts like HTML, SVG, charts, and diagrams.

    This toolkit enables agents to generate visual content that can be previewed
    in the CAMEL web application, similar to Claude's artifact system.

    Supported artifact types:
    - HTML documents
    - SVG graphics
    - Mermaid flowcharts and diagrams
    - Code snippets (with syntax highlighting)
    - Markdown documents
    - LaTeX math expressions
    """

    def _generate_artifact_id(self, artifact_type: str) -> str:
        """Generate a unique artifact ID with microsecond precision."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[
            :-3
        ]  # Include milliseconds
        return f"{artifact_type}_{timestamp}"

    def create_html_artifact(
        self,
        content: str,
        title: str = "HTML Artifact",
        include_css: bool = True,
        css_styles: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Create an HTML artifact that can be rendered in the web interface.

        Args:
            content (str): The HTML content to be displayed.
            title (str, optional): Title for the artifact. (default: :obj:`"HTML Artifact"`)
            include_css (bool, optional): Whether to include basic CSS styling.
                (default: :obj:`True`)
            css_styles (str, optional): Additional CSS styles to include.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing the artifact data with metadata.
        """
        # Check if content is already a complete HTML document
        if content.strip().lower().startswith(('<html', '<!doctype')):
            html_content = content
        else:
            # Use shared template for consistent styling
            extra_head = css_styles or ""
            html_content = self._render_html(title, content, extra_head)

        return {
            "type": "html",
            "title": title,
            "content": html_content,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": self._generate_artifact_id("html"),
                "size": len(html_content),
                "has_css": include_css or bool(css_styles),
            },
        }

    def _render_html(
        self,
        title: str,
        body: str,
        extra_head: str = "",
        body_class: str = "",
    ) -> str:
        r"""Render a complete HTML document with shared template and styling.

        Args:
            title (str): The page title and main heading.
            body (str): The main content to display.
            extra_head (str, optional): Additional content for the <head> section.
            body_class (str, optional): CSS class for the body element.

        Returns:
            str: Complete HTML document.
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        h1, h2, h3, h4, h5, h6 {{ 
            color: #2c3e50; 
            margin-top: 0;
        }}
        .container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 800px;
            margin: 0 auto;
        }}
        pre {{ 
            background: #f8f9fa; 
            padding: 1em; 
            border-radius: 6px; 
            overflow-x: auto; 
            border: 1px solid #e1e8ed;
        }}
        code {{ 
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            background: #f1f2f6;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        pre code {{
            background: transparent;
            padding: 0;
        }}
        .mermaid {{ 
            text-align: center; 
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 1em 0;
            padding-left: 1em;
            color: #555;
            background: #f8f9fa;
            padding: 10px 20px;
            border-radius: 0 4px 4px 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
    </style>
    {extra_head}
</head>
<body{f' class="{body_class}"' if body_class else ""}>
    <div class="container">
        <h1>{title}</h1>
        {body}
    </div>
</body>
</html>"""

    def _get_base_styles(self) -> str:
        r"""Get base CSS styles used across all artifacts."""
        return """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }
            h1, h2, h3, h4, h5, h6 { color: #2c3e50; }
            .container {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 800px;
                margin: 0 auto;
            }
        </style>
        """

    def create_svg_artifact(
        self,
        svg_content: str,
        title: str = "SVG Graphic",
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Create an SVG artifact for vector graphics.

        Args:
            svg_content (str): The SVG content (can be just the inner elements
                or complete SVG).
            title (str, optional): Title for the artifact. (default: :obj:`"SVG Graphic"`)
            width (int, optional): Width of the SVG. If not provided, uses SVG's
                viewBox or defaults. (default: :obj:`None`)
            height (int, optional): Height of the SVG. If not provided, uses SVG's
                viewBox or defaults. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing the SVG artifact data.
        """
        # Check if content already has SVG wrapper
        if not svg_content.strip().lower().startswith('<svg'):
            # Wrap in SVG tags with default dimensions
            svg_width = width or 400
            svg_height = height or 300
            svg_full = f"""<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">
    {svg_content}
</svg>"""
        else:
            svg_full = svg_content

        # Use shared template for consistent styling
        html_content = self._render_html(title, svg_full)

        return {
            "type": "svg",
            "title": title,
            "content": html_content,
            "svg_content": svg_full,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": self._generate_artifact_id("svg"),
                "width": width,
                "height": height,
                "size": len(html_content),
            },
        }

    def create_mermaid_flowchart(
        self,
        flowchart_definition: str,
        title: str = "Flowchart",
        direction: str = "TD",
    ) -> Dict[str, Any]:
        r"""Create a Mermaid flowchart artifact.

        Args:
            flowchart_definition (str): The Mermaid flowchart definition.
            title (str, optional): Title for the flowchart. (default: :obj:`"Flowchart"`)
            direction (str, optional): Flow direction (TD, LR, BT, RL).
                (default: :obj:`"TD"`)

        Returns:
            Dict[str, Any]: A dictionary containing the Mermaid flowchart data.
        """
        # Ensure the flowchart starts with proper Mermaid syntax
        if not flowchart_definition.strip().startswith(('flowchart', 'graph')):
            mermaid_content = (
                f"flowchart {direction}\n    {flowchart_definition}"
            )
        else:
            mermaid_content = flowchart_definition

        # Use shared template with Mermaid-specific extras
        extra_head = """
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({ startOnLoad: true });</script>"""

        body_content = f'<div class="mermaid">{mermaid_content}</div>'
        html_content = self._render_html(title, body_content, extra_head)

        return {
            "type": "mermaid",
            "subtype": "flowchart",
            "title": title,
            "content": html_content,
            "mermaid_definition": mermaid_content,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": self._generate_artifact_id("mermaid_flowchart"),
                "direction": direction,
                "size": len(html_content),
            },
        }

    def create_code_artifact(
        self,
        code: str,
        language: str = "python",
        title: str = "Code Snippet",
        show_line_numbers: bool = True,
        theme: str = "github",
    ) -> Dict[str, Any]:
        r"""Create a code artifact with syntax highlighting.

        Args:
            code (str): The source code content.
            language (str, optional): Programming language for syntax highlighting.
                (default: :obj:`"python"`)
            title (str, optional): Title for the code artifact. (default: :obj:`"Code Snippet"`)
            show_line_numbers (bool, optional): Whether to show line numbers.
                (default: :obj:`True`)
            theme (str, optional): Syntax highlighting theme. (default: :obj:`"github"`)

        Returns:
            Dict[str, Any]: A dictionary containing the code artifact data.
        """
        # Use shared template with Prism.js for syntax highlighting
        extra_head = f"""
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
    {"<script src='https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.js'></script>" if show_line_numbers else ""}
    <style>
        .language-label {{
            background: #3498db;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-bottom: 10px;
            display: inline-block;
        }}
    </style>"""

        body_content = f"""
        <div class="language-label">{language.upper()}</div>
        <pre{"" if not show_line_numbers else ' class="line-numbers"'}><code class="language-{language}">{code}</code></pre>"""

        html_content = self._render_html(title, body_content, extra_head)

        return {
            "type": "code",
            "title": title,
            "language": language,
            "content": html_content,
            "code": code,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": self._generate_artifact_id("code"),
                "language": language,
                "line_count": len(code.split('\n')),
                "size": len(code),
                "has_line_numbers": show_line_numbers,
                "theme": theme,
            },
        }

    def create_markdown_artifact(
        self,
        markdown_content: str,
        title: str = "Document",
        include_toc: bool = False,
        theme: str = "github",
    ) -> Dict[str, Any]:
        r"""Create a Markdown document artifact with rendering.

        Args:
            markdown_content (str): The Markdown content.
            title (str, optional): Title for the document. (default: :obj:`"Document"`)
            include_toc (bool, optional): Whether to include a table of contents.
                (default: :obj:`False`)
            theme (str, optional): Styling theme for the document. (default: :obj:`"github"`)

        Returns:
            Dict[str, Any]: A dictionary containing the Markdown artifact data.
        """
        # Use shared template with Marked.js for Markdown rendering
        toc_script = (
            """
        <script>
            // Simple TOC generator
            function generateTOC() {
                const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                if (headings.length === 0) return;
                
                const toc = document.getElementById('table-of-contents');
                const tocList = document.createElement('ul');
                tocList.className = 'toc-list';
                
                headings.forEach((heading, index) => {
                    const id = `heading-${index}`;
                    heading.id = id;
                    
                    const li = document.createElement('li');
                    li.className = `toc-${heading.tagName.toLowerCase()}`;
                    
                    const a = document.createElement('a');
                    a.href = `#${id}`;
                    a.textContent = heading.textContent;
                    a.onclick = (e) => {
                        e.preventDefault();
                        heading.scrollIntoView({ behavior: 'smooth' });
                    };
                    
                    li.appendChild(a);
                    tocList.appendChild(li);
                });
                
                toc.appendChild(tocList);
            }
        </script>
        """
            if include_toc
            else ""
        )

        toc_html = (
            """
        <div id="table-of-contents">
            <h2>📑 Table of Contents</h2>
        </div>
        """
            if include_toc
            else ""
        )

        extra_head = f"""
    <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/9.1.6/marked.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
    <style>
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 2em;
            margin-bottom: 0.5em;
        }}
        h1 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.3em;
        }}
        h2 {{
            border-bottom: 1px solid #ecf0f1;
            padding-bottom: 0.2em;
        }}
        .toc-list {{
            list-style: none;
            padding-left: 0;
        }}
        .toc-list li {{
            margin: 0.25em 0;
        }}
        .toc-h1 {{ padding-left: 0; font-weight: bold; }}
        .toc-h2 {{ padding-left: 1em; }}
        .toc-h3 {{ padding-left: 2em; }}
        .toc-h4 {{ padding-left: 3em; }}
        .toc-h5 {{ padding-left: 4em; }}
        .toc-h6 {{ padding-left: 5em; }}
        .toc-list a {{
            text-decoration: none;
            color: #3498db;
        }}
        .toc-list a:hover {{
            text-decoration: underline;
        }}
        #table-of-contents {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 2em;
            border: 1px solid #e1e8ed;
        }}
        #table-of-contents h2 {{
            margin-top: 0;
            color: #2c3e50;
            border: none;
            padding: 0;
        }}
    </style>
    {toc_script}"""

        body_content = f"""
        {toc_html}
        <div id="markdown-content"></div>
        <script>
            // Configure marked options
            marked.setOptions({{
                highlight: function(code, lang) {{
                    if (Prism.languages[lang]) {{
                        return Prism.highlight(code, Prism.languages[lang], lang);
                    }}
                    return code;
                }},
                breaks: true,
                gfm: true
            }});
            
            // Render markdown
            const markdownContent = `{markdown_content}`;
            document.getElementById('markdown-content').innerHTML = marked.parse(markdownContent);
            
            {"generateTOC();" if include_toc else ""}
        </script>"""

        html_content = self._render_html(title, body_content, extra_head)

        return {
            "type": "markdown",
            "title": title,
            "content": html_content,
            "markdown": markdown_content,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": self._generate_artifact_id("markdown"),
                "word_count": len(markdown_content.split()),
                "line_count": len(markdown_content.split('\n')),
                "size": len(markdown_content),
                "has_toc": include_toc,
                "theme": theme,
            },
        }

    def create_latex_math(
        self,
        latex_expression: str,
        title: str = "Mathematical Expression",
        display_mode: str = "block",
        show_source: bool = False,
    ) -> Dict[str, Any]:
        r"""Create a LaTeX mathematical expression artifact.

        Args:
            latex_expression (str): The LaTeX mathematical expression.
            title (str, optional): Title for the math artifact.
                (default: :obj:`"Mathematical Expression"`)
            display_mode (str, optional): Display mode - "block" for centered equations,
                "inline" for text-style. (default: :obj:`"block"`)
            show_source (bool, optional): Whether to show the LaTeX source code.
                (default: :obj:`False`)

        Returns:
            Dict[str, Any]: A dictionary containing the LaTeX math artifact data.
        """
        # Clean up LaTeX expression - remove extra $$ if present
        clean_latex = latex_expression.strip()
        if clean_latex.startswith('$$') and clean_latex.endswith('$$'):
            clean_latex = clean_latex[2:-2].strip()
        elif clean_latex.startswith('$') and clean_latex.endswith('$'):
            clean_latex = clean_latex[1:-1].strip()

        # Determine math delimiters based on display mode
        if display_mode == "block":
            math_content = f"$$\\displaystyle {clean_latex}$$"
        else:
            math_content = f"$\\{clean_latex}$"

        # Optional source code display
        source_section = (
            f"""
        <div class="latex-source">
            <h3>📝 LaTeX Source</h3>
            <div class="source-code">
                <code>{latex_expression}</code>
                <button onclick="copyToClipboard()" class="copy-btn">📋 Copy</button>
            </div>
        </div>
        """
            if show_source
            else ""
        )

        copy_script = (
            """
        <script>
            function copyToClipboard() {
                const sourceCode = document.querySelector('.source-code code').textContent;
                navigator.clipboard.writeText(sourceCode).then(function() {
                    const btn = document.querySelector('.copy-btn');
                    const originalText = btn.textContent;
                    btn.textContent = '✅ Copied!';
                    setTimeout(() => {
                        btn.textContent = originalText;
                    }, 2000);
                });
            }
        </script>
        """
            if show_source
            else ""
        )

        # Use shared template with MathJax for LaTeX rendering
        extra_head = f"""
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script>
        window.MathJax = {{
            tex: {{
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                processEscapes: true,
                processEnvironments: true,
                tags: 'ams'
            }},
            options: {{
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'],
                ignoreHtmlClass: 'tex2jax_ignore'
            }}
        }};
    </script>
    <style>
        .math-expression {{
            font-size: 1.2em;
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}
        .latex-source {{
            margin-top: 30px;
            text-align: left;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e1e8ed;
        }}
        .latex-source h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .source-code {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        }}
        .copy-btn {{
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }}
        .copy-btn:hover {{
            background: #2980b9;
        }}
        .math-info {{
            margin-top: 20px;
            padding: 15px;
            background: #e3f2fd;
            border-radius: 6px;
            font-size: 14px;
            color: #1976d2;
        }}
    </style>
    {copy_script}"""

        body_content = f"""
        <div class="math-expression">
            {math_content}
        </div>
        {source_section}
        <div class="math-info">
            <strong>💡 Tip:</strong> This mathematical expression is rendered using MathJax with LaTeX syntax.
        </div>"""

        html_content = self._render_html(title, body_content, extra_head)

        return {
            "type": "latex",
            "subtype": "math",
            "title": title,
            "content": html_content,
            "latex_expression": latex_expression,
            "cleaned_latex": clean_latex,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": self._generate_artifact_id("latex"),
                "display_mode": display_mode,
                "show_source": show_source,
                "expression_length": len(clean_latex),
                "size": len(html_content),
            },
        }

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.create_html_artifact),
            FunctionTool(self.create_svg_artifact),
            FunctionTool(self.create_mermaid_flowchart),
            FunctionTool(self.create_code_artifact),
            FunctionTool(self.create_markdown_artifact),
            FunctionTool(self.create_latex_math),
        ]
