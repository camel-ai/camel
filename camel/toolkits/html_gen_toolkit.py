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

# Enables postponed evaluation of annotations (for string-based type hints)
from __future__ import annotations

import os
from typing import List, Optional

from camel.logger import get_logger
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import MCPServer

logger = get_logger(__name__)


ONE_PAGE_HTML_PROMPT = """
# Prompt for Generating HTML Presentation Slides

## Objective
Generate the HTML and CSS for a single presentation slide. The slide should be a standalone HTML file, with all CSS embedded in a `<style>` tag in the `<head>`. The dimensions of the slide are fixed at 1280x720 pixels.

---

## General Rules
1.  **Standalone File**: Each output should be a single, complete HTML file.
2.  **Embedded CSS**: All CSS rules must be placed within a `<style>` tag in the HTML `<head>`.
3.  **Fonts**: Import specified fonts from Google Fonts using `@import` at the top of the `<style>` block. The primary fonts to use are 'Lato', 'Open Sans', and 'Roboto Mono'.
4.  **Dimensions**: The main slide container must be exactly `1280px` wide and `720px` high.
5.  **Responsiveness**: The body should center the slide, but the slide itself is fixed-size.
6.  **Content**: The content of the slide (text, images, charts) will be provided in the specific request. You should structure it using the templates below.

---

## Color Palettes

You can choose between two main color palettes depending on the slide's mood.

### 1. Dark Theme (for technical, data-heavy slides)
-   **Background**: Dark blue/charcoal gradients, e.g., `radial-gradient(circle at 50% 50%, #1d2b42, #0f172a)`
-   **Text**: Light grey or off-white, e.g., `#e0e0e0` or `#cbd5e1`.
-   **Headings**: White or a slightly brighter color, e.g., `#ffffff`.
-   **Accent/Highlight**: Bright, saturated colors like cyan, pink, or orange, e.g., `#0ea5e9` (cyan), `#ff8a8a` (pink/red), `#f59e0b` (orange).
-   **Borders/Lines**: Muted blues or greys, e.g., `rgba(71, 85, 105, 0.7)`.

### 2. Light/Corporate Theme (for title, intro, or conclusion slides)
-   **Background**: Deep blue solid color or gradient, e.g., `#1f4e79` or `linear-gradient(135deg, rgba(31, 78, 121, 0.95), rgba(46, 116, 181, 0.85))`.
-   **Text**: White or very light blue/grey, e.g., `#ffffff` or `#d0e0f0`.
-   **Accent/Highlight**: Use subtle background elements or borders with semi-transparent white, e.g., `rgba(255, 255, 255, 0.1)`.

---

## Slide Templates

Use the following templates as a basis for generating slides.

### Template 1: Title Slide

**Use for:** The main title slide of the presentation.
**Key elements:** Large main title, subtitle, author/team name, and a footer with conference/date info.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Slide Title Here</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&family=Open+Sans:wght@400;600&display=swap');
    body { margin: 0; padding: 0; width: 100vw; height: 100vh; display: flex; justify-content: center; align-items: center; background-color: #f0f0f0; font-family: 'Open Sans', sans-serif; }
    .slide { width: 1280px; height: 720px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1); position: relative; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #ffffff; background: #1f4e79; overflow: hidden; }
    .slide::before { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-image: linear-gradient(135deg, rgba(31, 78, 121, 0.95), rgba(46, 116, 181, 0.85)); z-index: 1; }
    .content { position: relative; z-index: 3; text-align: center; padding: 0 60px; }
    h1 { font-family: 'Lato', sans-serif; font-size: 72px; font-weight: 900; margin: 0 0 20px 0; line-height: 1.2; color: #ffffff; text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3); }
    .subtitle { font-family: 'Open Sans', sans-serif; font-size: 24px; font-weight: 400; color: #d0e0f0; margin: 0 0 40px 0; }
    .authors { font-family: 'Lato', sans-serif; font-size: 36px; font-weight: 700; color: #ffffff; margin: 0; }
    footer { position: absolute; bottom: 0; left: 0; width: 100%; padding: 30px 60px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; font-family: 'Open Sans', sans-serif; font-size: 18px; color: #c0d0e0; z-index: 3; }
  </style>
</head>
<body>
  <div class="slide">
    <div class="content">
      <p class="subtitle">Your Subtitle / Conference Name</p>
      <h1>Your Main Title</h1>
      <p class="authors">Author(s) Name(s)</p>
    </div>
    <footer>
      <span>Conference Details | Date</span>
      <span>Slide 1 / N</span>
    </footer>
  </div>
</body>
</html>
```

### Template 2: Content Slide (Bulleted List)

**Use for:** Standard content slides with a title and bullet points.
**Key elements:** Header with a title, main content area, and an unordered list. The layout can be single-column or two-column using a grid.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Slide Title Here</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap');
    body { margin: 0; padding: 0; background-color: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: 'Lato', sans-serif; }
    .slide { width: 1280px; height: 720px; background: #0f172a; color: #e0e0e0; display: flex; flex-direction: column; position: relative; }
    .header { padding: 40px 60px 20px 60px; border-bottom: 1px solid rgba(71, 85, 105, 0.7); }
    .header h1 { font-size: 48px; font-weight: 700; color: #ffffff; margin: 0; }
    .main-content { flex-grow: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 30px 60px; }
    /* Use 'grid-template-columns: 1fr;' for a single column layout */
    .content-section h2 { font-size: 24px; font-weight: 700; color: #94a3b8; margin-bottom: 15px; }
    .content-section ul { list-style: none; padding-left: 20px; margin: 0; }
    .content-section li { font-size: 20px; line-height: 1.6; color: #cbd5e1; margin-bottom: 12px; padding-left: 25px; position: relative; }
    .content-section li::before { content: '•'; position: absolute; left: 0; color: #0ea5e9; font-size: 24px; line-height: 1; }
    .footer { padding: 20px 60px; display: flex; justify-content: flex-end; align-items: center; border-top: 1px solid rgba(71, 85, 105, 0.7); }
    .slide-number { font-size: 18px; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="slide">
    <div class="header"><h1>Slide Title</h1></div>
    <div class="main-content">
      <div class="content-section">
        <h2>Section 1 Title</h2>
        <ul>
          <li>First bullet point. Can contain <strong>highlighted text</strong>.</li>
          <li>Second bullet point.</li>
          <li>Third bullet point.</li>
        </ul>
      </div>
      <div class="content-section">
        <h2>Section 2 Title</h2>
        <ul>
          <li>Another bullet point.</li>
          <li>And another one.</li>
        </ul>
      </div>
    </div>
    <div class="footer"><span class="slide-number">Slide 2 / N</span></div>
  </div>
</body>
</html>
```

### Template 3: Slide with SVG Chart

**Use for:** Displaying simple, stylized charts and graphs.
**Key elements:** Use inline SVG within an HTML structure. Style the SVG elements (path, circle, rect, text) with CSS.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><title>Chart Slide</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&family=Roboto+Mono:wght@400;700&display=swap');
    body { margin: 0; padding: 0; background-color: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: 'Lato', sans-serif; }
    .slide { width: 1280px; height: 720px; background: #0f172a; color: #e0e0e0; display: flex; flex-direction: column; position: relative; padding: 40px 60px; }
    .header { text-align: center; margin-bottom: 40px; }
    h1 { font-size: 48px; color: #fff; }
    .chart-container { flex-grow: 1; display: flex; justify-content: center; align-items: center; }
    .graph-container { width: 800px; height: 400px; position: relative; border-left: 2px solid #64748b; border-bottom: 2px solid #64748b; }
    .graph-label { position: absolute; font-size: 14px; color: #94a3b8; }
    .graph-label.y-axis { top: -20px; left: -10px; }
    .graph-label.x-axis { right: -40px; bottom: -5px; }
    .line-path { fill: none; stroke-width: 4px; }
    .line-path.quadratic { stroke: #ff8a8a; }
    .line-path.linear { stroke: #67e8f9; }
    .legend { display: flex; justify-content: center; gap: 30px; margin-top: 30px; }
    .legend-item { display: flex; align-items: center; font-size: 16px; color: #cbd5e1;}
    .legend-color { width: 20px; height: 20px; margin-right: 10px; }
  </style>
</head>
<body>
<div class="slide">
  <div class="header"><h1>Performance Comparison</h1></div>
  <div class="chart-container">
    <div class="graph-container">
      <span class="graph-label y-axis">Compute Cost</span>
      <span class="graph-label x-axis">Sequence Length</span>
      <svg width="100%" height="100%" viewBox="0 0 800 400" preserveAspectRatio="none">
        <path class="line-path quadratic" d="M 0 390 Q 400 350 800 0"></path>
        <path class="line-path linear" d="M 0 390 L 800 200"></path>
      </svg>
    </div>
  </div>
  <div class="legend">
    <div class="legend-item"><div class="legend-color" style="background-color: #ff8a8a;"></div>Standard Attention (O(n²))</div>
    <div class="legend-item"><div class="legend-color" style="background-color: #67e8f9;"></div>Lightning Attention (O(n))</div>
  </div>
</div>
</body>
</html>
```

### Template 4: Slide with Image

**Use for:** Displaying complex diagrams, photos, or pre-rendered charts as images.
**Key elements:** Use a standard `<img>` tag. The layout can be full-image or split-screen with text. Assume images are located in an `images/` subfolder.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><title>Image Slide</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap');
    body { margin: 0; padding: 0; background-color: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: 'Lato', sans-serif; }
    .slide { width: 1280px; height: 720px; background: #0f172a; color: #e0e0e0; display: flex; flex-direction: column; position: relative; }
    .header { padding: 40px 60px 20px 60px; border-bottom: 1px solid rgba(71, 85, 105, 0.7); }
    .header h1 { font-size: 48px; font-weight: 700; color: #ffffff; margin: 0; }
    .main-content { flex-grow: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 40px 60px; align-items: center; }
    .text-content p { font-size: 22px; line-height: 1.7; color: #cbd5e1; }
    .image-content img { max-width: 100%; border-radius: 8px; box-shadow: 0 5px 25px rgba(0,0,0,0.3); }
    .footer { padding: 20px 60px; text-align: right; border-top: 1px solid rgba(71, 85, 105, 0.7); font-size: 18px; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="slide">
    <div class="header"><h1>Attention Mechanism</h1></div>
    <div class="main-content">
      <div class="text-content">
        <p>The attention mechanism allows the model to focus on relevant parts of the input sequence.</p>
        <p>Our proposed Lightning Attention reduces the computational complexity from quadratic to linear.</p>
      </div>
      <div class="image-content">
        <!-- Use a descriptive file name. Assume it's in the 'images/' folder. -->
        <img src="images/attention_mechanism.png" alt="Diagram of the attention mechanism">
      </div>
    </div>
    <div class="footer">Slide 5 / N</div>
  </div>
</body>
</html>
```

---

## Final Instructions for the LLM
When you receive a request to create a presentation slide, first identify the type of slide (e.g., title, content, chart, image). Then, select the most appropriate template and populate it with the provided content. Pay close attention to the color scheme and styling rules to ensure consistency. Always output the full, final HTML code. 
"""  # noqa: E501

VIEWER_HTML_PROMPT = """
# Prompt for Generating an HTML Presentation Viewer

## Objective
Generate a single, standalone HTML file that acts as a viewer for a collection of individual HTML presentation slides. This viewer should load the slides into iframes and provide multiple ways to view them, including a grid, a list, and a fullscreen presentation mode.

---

## General Rules
1.  **Standalone File**: The entire viewer, including HTML, CSS, and JavaScript, must be contained within a single HTML file.
2.  **Dynamic Loading**: The viewer should be configured via a JavaScript array of slide file paths. It will dynamically generate the display for each slide.
3.  **Slide Aspect Ratio**: The slides are designed in a 16:9 aspect ratio (e.g., 1280x720px). The viewer must maintain this aspect ratio when displaying previews.

---

## Required Functionality

1.  **Slide Configuration**: A JavaScript array at the top of the `<script>` tag should define the list of slide files to be loaded.
    ```javascript
    const slideUrls = [
        'slides/slide1.html',
        'slides/slide2.html',
        // ... more slides
    ];
    ```
2.  **Grid View (Default)**:
    -   Display all slides in a responsive grid.
    -   Each slide preview should be a scaled-down version of the actual slide, loaded in an `<iframe>`.
    -   Show a slide number in the top-left corner of each preview.
3.  **List View**:
    -   Display all slides vertically in a single column.
    -   Each slide should be displayed at its full 1280px width.
4.  **Presentation Mode**:
    -   Triggered by a "Play" button or by clicking a slide preview.
    -   Enters fullscreen mode.
    -   Displays one slide at a time, centered on the screen.
    -   Allows navigation between slides using the `ArrowLeft` and `ArrowRight` keyboard keys.
    -   Exits presentation mode when the `Escape` key is pressed.
5.  **Controls**:
    -   A header should contain a title for the presentation.
    -   Controls should include buttons to toggle between "Grid View" and "List View".
    -   A "Play" button to start the presentation from the beginning.

---

## HTML Structure

The body should contain three main parts: a `<header>`, a `div` for the slide previews, and a `div` for the presentation mode overlay.

```html
<body>
    <div class="container">
        <header>
            <h1><!-- Presentation Title --></h1>
            <div class="controls">
                <div class="view-controls">
                    <button id="grid-view-btn" class="active">Grid</button>
                    <button id="list-view-btn">List</button>
                </div>
                <button id="play-btn">Play Presentation</button>
            </div>
        </header>
        <div id="preview-container" class="preview-container">
            <!-- JavaScript will populate this area -->
        </div>
    </div>

    <div id="presentation-mode" class="presentation-mode">
        <iframe id="presentation-slide-frame"></iframe>
        <div class="presentation-nav">
            <button id="prev-slide-btn">&lt;</button>
            <button id="next-slide-btn">&gt;</button>
        </div>
        <div id="presentation-counter"></div>
    </div>

    <script>
        // All JavaScript logic goes here
    </script>
</body>
```

---

## CSS Styling

The embedded CSS should style all components, including:
-   **Layout**: General styles for the header, container, and controls.
-   **Color Scheme**: Use CSS variables for a consistent theme (e.g., dark background, light text, accent color for buttons).
-   **Grid & List Views**:
    -   `.preview-container`: Use `display: grid` and `grid-template-columns: repeat(auto-fill, minmax(480px, 1fr))` for the grid view.
    -   `.preview-container.list-view`: Use `display: flex`, `flex-direction: column` for the list view.
-   **Slide Previews**:
    -   `.slide-preview`: Style the container for each preview (background, border, shadow, etc.).
    -   `.slide-frame-container`: Use the `padding-top: 56.25%` trick to maintain a 16:9 aspect ratio for the iframe container in grid view.
    -   `.slide-frame`: The `<iframe>` itself. Use `transform: scale(...)` to fit the 1280x720 content into the smaller preview container.
-   **Presentation Mode**:
    -   `.presentation-mode`: Style it as a fixed-position overlay with a dark background, initially hidden (`display: none`).
    -   `.presentation-slide`: The iframe inside the presentation mode should be centered and sized appropriately.

---

## JavaScript Logic

The script should handle all the dynamic behavior.

1.  **Initialization**:
    -   Define the `slideUrls` array.
    -   Get references to all necessary DOM elements (`preview-container`, buttons, etc.).
    -   Call a function to dynamically create and append the slide previews to the `#preview-container`.

2.  **Slide Preview Generation**:
    -   Loop through the `slideUrls` array.
    -   For each URL, create the necessary HTML elements (e.g., a `div.slide-preview` containing a numbered `div` and an `iframe`).
    -   Set the `src` of the iframe to the slide URL.
    -   Add an event listener to each preview to enter presentation mode at that specific slide.

3.  **View Switching**:
    -   Add event listeners to the "Grid" and "List" view buttons.
    -   These listeners should add or remove a class (e.g., `.list-view`) on the `#preview-container` and update the active state of the buttons.

4.  **Presentation Mode Logic**:
    -   Create functions `enterPresentation(slideIndex)` and `exitPresentation()`.
    -   `enterPresentation` should:
        -   Show the `#presentation-mode` overlay.
        -   Request fullscreen.
        -   Load the correct slide into the main presentation iframe.
        -   Update the slide counter.
        -   Add keyboard event listeners for navigation.
    -   `exitPresentation` should:
        -   Hide the overlay.
        -   Exit fullscreen.
        -   Remove keyboard event listeners.
    -   Implement `showSlide(slideIndex)` to update the iframe `src` and counter.
    -   The "Play" button should call `enterPresentation(0)`.

---

## Example Snippet for Iframe Scaling (in CSS)

This is a key part of the styling for the grid view previews.

```css
/* In Grid View */
.preview-container .slide-frame-container {
    position: relative;
    padding-top: 56.25%; /* 16:9 Aspect Ratio */
    width: 100%;
    overflow: hidden;
    background: #000;
}

.preview-container .slide-frame {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 1280px; /* Native slide width */
    height: 720px;  /* Native slide height */
    border: none;
    transform-origin: center center;
    /* The scale factor is calculated by JS based on container size, 
       or can be a fixed approximation if previews are fixed size.
       e.g., for a 480px wide container: 480 / 1280 = 0.375 */
    transform: translate(-50%, -50%) scale(0.375);
}
```
You will need JavaScript to dynamically calculate the scale factor for a responsive grid. `const scale = previewContainer.clientWidth / 1280;` is a good starting point. 
"""  # noqa: E501


@MCPServer()
class HtmlGenToolkit(BaseToolkit):
    r"""A toolkit for generating HTML content.
    The toolkit uses language models to generate HTML content.
    """

    def __init__(
        self,
        model: Optional[BaseModelBackend] = None,
        timeout: Optional[float] = None,
        workspace: Optional[str] = "./",
    ):
        r"""Initialize the HtmlGenToolkit.

        Args:
            model (Optional[BaseModelBackend]): The model backend to use for
                HTML generation tasks. This model should support generating
                HTML content. If None, a default model will be created using
                ModelFactory. (default: :obj:`None`)
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
            workspace (Optional[str]): The workspace to use for the generation.
                (default: :obj:`.`)
        """
        from camel.agents.chat_agent import ChatAgent

        super().__init__(timeout=timeout)
        self.model = model
        if self.model is None:
            self.model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )
        self.workspace = workspace
        self.onepage_html_agent = ChatAgent(
            model=self.model,
            system_message=ONE_PAGE_HTML_PROMPT,
            max_iteration=1,
        )
        self.viewer_html_agent = ChatAgent(
            model=self.model,
            system_message=VIEWER_HTML_PROMPT,
            max_iteration=1,
        )

    def generate_one_page_html4ppt(self, prompt: str, filename: str) -> str:
        r"""Generates HTML content for one page ppt slide.

        Args:
            prompt (str): The prompt of the html generation,
                the prompt should be the requirement of
                slide, this prompt will be used by anther agent
                to generate the html content.
            filename (str): The filename of the html file.

        Returns:
            str: HTML content for one page ppt slide.
        """
        try:
            response = self.onepage_html_agent.step(
                input_message=prompt,
            )
        except Exception as e:
            logger.error(f"Error generating one page html: {e}")
            return f"Error generating one page html: {e!s}"

        # save to file
        with open(os.path.join(self.workspace, filename), "w") as f:
            f.write(response.msgs[0].content)
        result = (
            f"Content successfully written to file: {filename}"
            f"The content is: {response.msgs[0].content}"
        )
        return result

    def generate_viewer_html4ppt(self, prompt: str, filename: str) -> str:
        r"""Generates HTML content for a viewer for a ppt.

        Args:
            prompt (str): The prompt of the html generation
                the prompt should include the requirement
                of the viewer, this prompt will be used by
                anther agent to generate the html content.
            filename (str): The filename of the viewer html file.

        Returns:
            str: The result of the generation.
        """
        try:
            response = self.viewer_html_agent.step(
                input_message=prompt,
            )
        except Exception as e:
            logger.error(f"Error generating viewer html: {e}")
            return f"Error generating viewer html: {e!s}"

        # save to file
        with open(os.path.join(self.workspace, filename), "w") as f:
            f.write(response.msgs[0].content)
        result = (
            f"Content successfully written to file: {filename}"
            f"The content is: {response.msgs[0].content}"
        )
        return result

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
            functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                functions in the toolkit.
        """
        return [
            FunctionTool(self.generate_one_page_html4ppt),
            FunctionTool(self.generate_viewer_html4ppt),
        ]
