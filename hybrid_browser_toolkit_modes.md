# HybridBrowserToolkit Operating Modes

The HybridBrowserToolkit offers two primary operating modes for web automation, each optimized for different use cases and interaction patterns. This document provides a comprehensive guide to understanding and using both modes effectively.

## Table of Contents
- [Overview](#overview)
- [Text Mode](#text-mode)
  - [Key Features](#text-mode-key-features)
  - [Basic Usage](#text-mode-basic-usage)
  - [Advanced Text Mode](#advanced-text-mode)
  - [Diff Snapshot Feature](#diff-snapshot-feature)
- [Visual Mode](#visual-mode)
  - [Key Features](#visual-mode-key-features)
  - [Basic Usage](#visual-mode-basic-usage)
  - [AI-Powered Analysis](#ai-powered-analysis)
  - [Screenshot Management](#screenshot-management)
- [Hybrid Approach](#hybrid-approach)
- [Mode Selection Guide](#mode-selection-guide)

## Overview

The HybridBrowserToolkit combines non-visual DOM-based automation with visual screenshot-based capabilities, providing flexibility for various web automation scenarios. Understanding when and how to use each mode is crucial for building efficient automation solutions.

## Text Mode

Text mode provides a DOM-based, non-visual approach to browser automation. This is the default operating mode where the toolkit returns textual snapshots of page elements.

### Text Mode Key Features

- **Automatic Snapshots**: Every action that modifies page state returns a textual snapshot
- **Unique Element IDs**: Elements are identified by `ref` IDs (e.g., `[ref=1]`, `[ref=2]`)
- **Lightweight Operation**: Minimal overhead, suitable for headless execution
- **Smart Diff Detection**: Special handling for dropdown and menu interactions

### Text Mode Basic Usage

#### Standard Text Mode Operation

```python
from camel.toolkits import HybridBrowserToolkit

# Initialize toolkit in default text mode
toolkit = HybridBrowserToolkit(
    headless=True,              # Can run without display
    viewport_limit=False,       # Include all elements, not just visible ones
    default_timeout=30000,      # 30 seconds default timeout
    navigation_timeout=60000    # 60 seconds for page loads
)

# Open browser and get initial snapshot
result = await toolkit.browser_open()
print(result['snapshot'])  # Shows all interactive elements with ref IDs
print(f"Total tabs: {result['total_tabs']}")

# Navigate to a page - automatically returns new snapshot
result = await toolkit.browser_visit_page("https://example.com")
print(result['snapshot'])
# Output example:
# - link "Home" [ref=1]
# - button "Login" [ref=2]
# - textbox "Username" [ref=3]
# - textbox "Password" [ref=4]
# - link "Register" [ref=5]

# Interact with elements
result = await toolkit.browser_click(ref="2")
print(f"Action result: {result['result']}")
print(f"Updated snapshot: {result['snapshot']}")

# Type into input fields
result = await toolkit.browser_type(ref="3", text="user@example.com")
result = await toolkit.browser_type(ref="4", text="password123")

# Submit form
result = await toolkit.browser_enter()  # Simulates pressing Enter
```

#### On-Demand Snapshot Retrieval

```python
# Get snapshot without performing actions
snapshot = await toolkit.browser_get_page_snapshot()
print(snapshot)

# Viewport-limited snapshot (only visible elements)
toolkit_limited = HybridBrowserToolkit(viewport_limit=True)
visible_snapshot = await toolkit_limited.browser_get_page_snapshot()
```

### Advanced Text Mode

#### Full Visual Mode (No Automatic Snapshots)

```python
# Initialize with full_visual_mode to disable automatic snapshots
toolkit = HybridBrowserToolkit(
    full_visual_mode=True  # Actions won't return snapshots
)

# Actions now return minimal information
result = await toolkit.browser_click(ref="1")
print(result)  # {'result': 'Clicked on link "Home"', 'tabs': [...]}

# Must explicitly request snapshots when needed
snapshot = await toolkit.browser_get_page_snapshot()

# Useful for performance-critical operations
async def bulk_operations():
    # Perform multiple actions without snapshot overhead
    await toolkit.browser_click(ref="menu")
    await toolkit.browser_click(ref="submenu-1")
    await toolkit.browser_click(ref="option-3")
    
    # Get snapshot only at the end
    final_snapshot = await toolkit.browser_get_page_snapshot()
    return final_snapshot
```

#### Multiple Input Handling

```python
# Type into multiple fields in one operation
inputs = [
    {'ref': '3', 'text': 'user@example.com'},
    {'ref': '4', 'text': 'password123'},
    {'ref': '5', 'text': 'John Doe'}
]

result = await toolkit.browser_type(inputs=inputs)
print(result['details'])  # Success/error status for each input
```

### Diff Snapshot Feature

The toolkit includes intelligent diff detection for dropdown and menu interactions:

```python
# When typing into a combobox or search field
result = await toolkit.browser_type(ref="search-box", text="laptop")

# Check if dropdown options appeared
if 'diffSnapshot' in result:
    print("New options detected:")
    print(result['diffSnapshot'])
    # Output example:
    # - option "Laptop Computers" [ref=45]
    # - option "Laptop Accessories" [ref=46]
    # - option "Laptop Bags" [ref=47]
    
    # Click on one of the options
    await toolkit.browser_click(ref="45")
else:
    # No dropdown appeared, continue with regular snapshot
    print(result['snapshot'])
```

## Visual Mode

Visual mode enables screenshot-based interaction with visual element recognition. This mode is essential when you need to "see" the page as a human would.

### Visual Mode Key Features

- **Set of Marks (SoM)**: Screenshots with bounding boxes around interactive elements
- **Element Overlays**: Each element is marked with its ref ID
- **AI Integration**: Optional AI-powered image analysis
- **Visual Verification**: Confirm UI states and layouts visually

### Visual Mode Basic Usage

#### Taking SoM Screenshots

```python
# Initialize toolkit for visual operations
toolkit = HybridBrowserToolkit(
    headless=False,    # Often used with display for debugging
    cache_dir="./screenshots",  # Directory for saving screenshots
    screenshot_timeout=10000    # 10 seconds timeout for screenshots
)

# Basic screenshot capture
result = await toolkit.browser_get_som_screenshot()
print(result)
# Output: "Screenshot captured with 23 interactive elements marked 
# (saved to: ./screenshots/example_com_home_123456_som.png)"

# Screenshot with custom analysis
result = await toolkit.browser_get_som_screenshot(
    read_image=True,
    instruction="Identify all buttons related to shopping cart"
)
```

### AI-Powered Analysis

#### Setting Up AI Integration

```python
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# Create AI model for image analysis
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type="gpt-4-vision-preview"
)

# Initialize toolkit with AI model
toolkit = HybridBrowserToolkit(
    web_agent_model=model,
    headless=False
)

# AI-assisted element finding
async def find_element_by_description():
    result = await toolkit.browser_get_som_screenshot(
        read_image=True,
        instruction="Find the blue 'Subscribe' button in the header"
    )
    
    # AI response included in result
    print(result)
    # "Screenshot captured... Agent analysis: The blue 'Subscribe' 
    # button is located at [ref=12] in the top-right header area."
    
    # Click the identified element
    await toolkit.browser_click(ref="12")
```

#### Complex Visual Tasks

```python
# Handle CAPTCHA with human assistance
async def solve_captcha():
    # Capture CAPTCHA image
    await toolkit.browser_get_som_screenshot(
        read_image=False  # Don't use AI for CAPTCHA
    )
    
    print("Please solve the CAPTCHA in the browser window...")
    
    # Wait for human intervention
    result = await toolkit.browser_wait_user(timeout_sec=60)
    
    if "Timeout" not in result['result']:
        # Continue after human solved CAPTCHA
        await toolkit.browser_click(ref="submit-button")

# Visual verification of UI state
async def verify_ui_layout():
    # Take screenshot for layout verification
    result = await toolkit.browser_get_som_screenshot(
        read_image=True,
        instruction="Verify that the login form is centered and all fields are visible"
    )
    
    # AI provides layout analysis
    return "properly centered" in result.lower()
```

### Screenshot Management

#### Organized Screenshot Storage

```python
import os
from datetime import datetime

# Configure toolkit with organized storage
toolkit = HybridBrowserToolkit(
    cache_dir=f"./screenshots/{datetime.now().strftime('%Y%m%d')}",
    session_id="test_session_001"
)

# Screenshots are automatically named and organized
# Format: {page_name}_{timestamp}_som.png

# Custom screenshot handling
async def capture_flow_screenshots(flow_name: str):
    steps = ["login", "dashboard", "profile", "settings"]
    screenshots = []
    
    for step in steps:
        await toolkit.browser_visit_page(f"https://example.com/{step}")
        result = await toolkit.browser_get_som_screenshot()
        
        # Extract file path from result
        if "saved to:" in result:
            file_path = result.split("saved to: ")[1].strip(")")
            screenshots.append({
                'step': step,
                'path': file_path,
                'timestamp': datetime.now()
            })
    
    return screenshots
```

## Hybrid Approach

Combining both modes provides maximum flexibility for complex automation scenarios:

```python
class HybridAutomation:
    def __init__(self):
        self.toolkit = HybridBrowserToolkit(
            headless=False,
            viewport_limit=True,
            web_agent_model=your_model
        )
    
    async def smart_form_filling(self):
        """Use text mode for form filling, visual for verification"""
        
        # Text mode: Navigate and fill form
        await self.toolkit.browser_visit_page("https://forms.example.com")
        
        # Get snapshot to understand form structure
        snapshot = await self.toolkit.browser_get_page_snapshot()
        
        # Fill form fields (text mode is efficient here)
        form_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '555-0123'
        }
        
        for field_ref, value in enumerate(form_data.values(), start=1):
            await self.toolkit.browser_type(ref=str(field_ref), text=value)
        
        # Visual mode: Verify form before submission
        result = await self.toolkit.browser_get_som_screenshot(
            read_image=True,
            instruction="Verify all form fields are filled correctly"
        )
        
        if "correctly filled" in result:
            await self.toolkit.browser_click(ref="submit")
    
    async def dynamic_content_interaction(self):
        """Handle dynamic content with both modes"""
        
        # Start with text mode
        await self.toolkit.browser_visit_page("https://shop.example.com")
        
        # Search triggers dynamic dropdown
        result = await self.toolkit.browser_type(
            ref="search", 
            text="gaming laptop"
        )
        
        # Use diff snapshot if available
        if 'diffSnapshot' in result:
            print("Suggestions:", result['diffSnapshot'])
            await self.toolkit.browser_click(ref="suggestion-1")
        
        # Visual mode for product selection
        result = await self.toolkit.browser_get_som_screenshot(
            read_image=True,
            instruction="Find laptops with RGB keyboards"
        )
        
        # Continue with text mode for checkout
        await self.toolkit.browser_click(ref="add-to-cart")
        await self.toolkit.browser_click(ref="checkout")
```

## Mode Selection Guide

### Quick Decision Matrix

| Use Case | Recommended Mode | Key Method | Example |
|----------|------------------|------------|---------|
| Form automation | Text Mode | `browser_type()` | Login forms, data entry |
| Data extraction | Text Mode | `browser_get_page_snapshot()` | Scraping text content |
| Visual verification | Visual Mode | `browser_get_som_screenshot()` | UI testing, layout checks |
| Element finding | Visual Mode + AI | `browser_get_som_screenshot(read_image=True)` | "Find the red button" |
| CAPTCHA/Manual steps | Visual Mode | `browser_wait_user()` | Human intervention needed |
| Dynamic content | Text Mode with diff | `browser_type()` with diff detection | Autocomplete, dropdowns |
| Complex workflows | Hybrid | Combination of methods | E-commerce, multi-step processes |

### Performance Considerations

```python
# High-performance text mode configuration
toolkit_fast = HybridBrowserToolkit(
    full_visual_mode=True,      # No automatic snapshots
    headless=True,              # No rendering overhead
    short_timeout=5000,         # Fail fast
    viewport_limit=True         # Process less elements
)

# Visual-heavy configuration
toolkit_visual = HybridBrowserToolkit(
    headless=False,             # Need rendering
    screenshot_timeout=30000,   # Allow time for complex pages
    cache_dir="./visual_cache", # Store screenshots
    web_agent_model=ai_model    # Enable AI analysis
)
```

### Best Practices

1. **Start with Text Mode**: It's faster and works for most automation tasks
2. **Use Visual Mode When Needed**: For visual verification, complex UIs, or human-like understanding
3. **Combine Modes**: Use text for navigation/interaction, visual for verification/discovery
4. **Optimize for Performance**: Use `full_visual_mode=True` when you don't need constant snapshots
5. **Handle Dynamic Content**: Leverage diff snapshots for dropdowns and menus

Both modes are designed to work seamlessly together, allowing you to build sophisticated automation solutions that can handle any web interaction scenario.