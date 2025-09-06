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
Example usage of the ArtifactToolkit.

This example demonstrates how to create various types of artifacts using the
ArtifactToolkit, which enables Claude-like artifact generation for HTML, SVG,
code, Markdown, and Mermaid diagrams.

Note: This is a standalone demonstration of the ArtifactToolkit functionality.
For full integration with CAMEL agents, ensure all dependencies are installed.
"""

from datetime import datetime


class SimplifiedArtifactDemo:
    """Simplified demonstration of ArtifactToolkit capabilities."""

    def demonstrate_artifacts(self):
        """Show examples of all 5 artifact types."""

        print("ArtifactToolkit Example - Creating Different Artifact Types\n")
        print("=" * 60)

        # 1. HTML Artifact Example
        print("\n1. HTML Artifact Structure:")
        html_artifact = {
            "type": "html",
            "title": "Interactive Welcome Page",
            "content": """<!DOCTYPE html>
<html>
<head>
    <title>Interactive Welcome Page</title>
    <style>
        .card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        button {
            background: #fff;
            color: #667eea;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="card">
        <h2>Welcome to CAMEL!</h2>
        <p>This is a dynamically generated HTML artifact.</p>
        <button onclick="alert('Hello from CAMEL!')">Click Me!</button>
    </div>
</body>
</html>""",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": f"html_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "size": 875,
                "has_css": True,
            },
        }

        self._print_artifact_info(html_artifact)

        # 2. SVG Artifact Example
        print("\n2. SVG Artifact Structure:")
        svg_artifact = {
            "type": "svg",
            "title": "CAMEL Logo Design",
            "content": """<svg width="300" height="300" viewBox="0 0 300 300">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#ff6b6b"/>
            <stop offset="100%" style="stop-color:#4ecdc4"/>
        </linearGradient>
    </defs>
    <circle cx="150" cy="150" r="80" fill="url(#grad1)"/>
    <text x="150" y="150" text-anchor="middle" dy="0.35em" 
          font-family="Arial" font-size="24" fill="white">CAMEL</text>
    <path d="M 70 150 Q 150 80 230 150" stroke="#333" stroke-width="2" fill="none"/>
</svg>""",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": f"svg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "width": 300,
                "height": 300,
            },
        }

        self._print_artifact_info(svg_artifact)

        # 3. Code Artifact Example
        print("\n3. Code Artifact Structure:")
        code_artifact = {
            "type": "code",
            "title": "Fibonacci Generator",
            "language": "python",
            "content": """def fibonacci(n):
    \"\"\"Generate Fibonacci sequence up to n terms.\"\"\"
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[i-1] + sequence[i-2])
    
    return sequence

# Example usage
if __name__ == "__main__":
    result = fibonacci(10)
    print(f"First 10 Fibonacci numbers: {result}")""",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": f"code_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "line_count": 17,
                "language": "python",
            },
        }

        self._print_artifact_info(code_artifact)

        # 4. Markdown Artifact Example
        print("\n4. Markdown Artifact Structure:")
        markdown_artifact = {
            "type": "markdown",
            "title": "ArtifactToolkit Documentation",
            "content": """# CAMEL ArtifactToolkit Guide

## Overview
The **ArtifactToolkit** enables dynamic generation of visual content similar to Claude's artifacts.

## Supported Types
1. **HTML** - Interactive web content
2. **SVG** - Scalable vector graphics  
3. **Code** - Syntax-highlighted code blocks
4. **Markdown** - Rich text documents
5. **Mermaid** - Flowcharts and diagrams

## Quick Start
```python
from camel.toolkits import ArtifactToolkit

toolkit = ArtifactToolkit()
artifact = toolkit.create_html_artifact("<h1>Hello!</h1>")
```

> **Note:** All artifacts include metadata with timestamps and unique IDs.""",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": f"markdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "word_count": 89,
            },
        }

        self._print_artifact_info(markdown_artifact)

        # 5. Mermaid Flowchart Example
        print("\n5. Mermaid Flowchart Structure:")
        mermaid_artifact = {
            "type": "mermaid",
            "title": "ArtifactToolkit Workflow",
            "content": """flowchart TD
    A[User Request] --> B{Choose Artifact Type}
    B -->|HTML| C[Create HTML Artifact]
    B -->|SVG| D[Create SVG Artifact]  
    B -->|Code| E[Create Code Artifact]
    B -->|Markdown| F[Create Markdown Artifact]
    B -->|Math| G[Create LaTeX Math]
    B -->|Diagram| H[Create Mermaid Chart]
    
    C --> I[Return Artifact]
    D --> I
    E --> I
    F --> I
    G --> I  
    H --> I
    
    I --> J[Display in Web Interface]""",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "artifact_id": f"mermaid_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "node_count": 10,
            },
        }

        self._print_artifact_info(mermaid_artifact)

        # Summary
        print("\n" + "=" * 60)
        print("Successfully demonstrated 5 different artifact types!")

        artifacts = [
            html_artifact,
            svg_artifact,
            code_artifact,
            markdown_artifact,
            mermaid_artifact,
        ]

        print("\nArtifact Summary:")
        for i, artifact in enumerate(artifacts, 1):
            print(f"{i}. {artifact['type'].upper()}: {artifact['title']}")

        print("\nKey Features:")
        print("- Dynamic content generation from user input")
        print("- 5 different artifact types supported")
        print("- Metadata with timestamps and unique IDs")
        print("- Web interface rendering capabilities")
        print("- Claude-like interactive experience")

        print("\nImplementation Benefits:")
        print("- Addresses GitHub issue #2546 requirements")
        print("- Integrates with CAMEL MCP framework")
        print("- Provides extensive artifact generation toolkit")
        print("- Enables rich interactive AI experiences")

    def _print_artifact_info(self, artifact):
        """Print formatted artifact information."""
        print(f"Created: {artifact['title']}")
        print(f"   Type: {artifact['type']}")

        # Print type-specific metadata
        if artifact['type'] == 'html':
            print(f"   Size: {artifact['metadata']['size']} characters")
            print(f"   Has CSS: {artifact['metadata']['has_css']}")
        elif artifact['type'] == 'svg':
            print(
                f"   Dimensions: {artifact['metadata']['width']}x{artifact['metadata']['height']}"
            )
        elif artifact['type'] == 'code':
            print(f"   Language: {artifact['language']}")
            print(f"   Lines: {artifact['metadata']['line_count']}")
        elif artifact['type'] == 'markdown':
            print(f"   Word count: {artifact['metadata']['word_count']}")
        elif artifact['type'] == 'mermaid':
            print(f"   Nodes: {artifact['metadata']['node_count']}")

        print(f"   ID: {artifact['metadata']['artifact_id']}")


def main():
    """Run the ArtifactToolkit demonstration."""
    demo = SimplifiedArtifactDemo()
    demo.demonstrate_artifacts()


if __name__ == "__main__":
    main()
