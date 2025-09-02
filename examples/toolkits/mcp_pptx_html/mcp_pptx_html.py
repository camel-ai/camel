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
import asyncio
import json
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits.mcp_pptx_html.html_to_pptx_toolkit import HTMLToPPTXToolkit
from camel.types import ModelPlatformType, ModelType


async def main():
    # Enhanced Planning Agent System Prompt
    # Enhanced Planning Agent System Prompt
    planning_prompt = """
You are an expert presentation strategist and design planner. Your role is to analyze topics and create comprehensive presentation plans that ensure design consistency, narrative flow, and visual impact based on proven slide design principles.

CORE PLANNING RESPONSIBILITIES:
1. TOPIC ANALYSIS: Understand subject matter, audience, and key messages
2. DESIGN STRATEGY: Define visual theme, color palette, typography, and layout approach
3. CONTENT STRUCTURE: Organize information into logical, engaging slide sequences
4. DESIGN CONSISTENCY: Establish design rules that maintain visual coherence across all slides
5. NARRATIVE ARCHITECTURE: Create storytelling flow from introduction → development → impact

SLIDE DESIGN PRINCIPLES TO IMPLEMENT:

## 1. VISUAL HIERARCHY SYSTEM
Primary Elements:
- Main Titles: Large decorative fonts (text-5xl) with accent lines
- Secondary Headings: Medium fonts (text-2xl) with color emphasis
- Body Text: Readable serif/sans-serif (text-lg/xl) in high contrast
- Page Numbers: Subtle positioning for professional finish

## 2. COLOR PSYCHOLOGY & BRANDING
Color Strategy:
- Primary Background: Topic-appropriate dark gradients for sophistication
- Accent Colors: Strategic use of 2-3 colors maximum for hierarchy
- Text Colors: High contrast for accessibility (white on dark, dark on light)
- Transparency: Semi-transparent overlays for depth and layering

## 3. LAYOUT GRID ARCHITECTURE
Technical Specifications:
- Fixed Dimensions: 1280px × 720px for consistency
- Consistent Margins: 32-64px padding throughout
- Column Systems: 50/50, 60/40, or 70/30 splits based on content
- Card Grids: 2×2, 1×4, or custom arrangements for information

## 4. CONTENT ORGANIZATION PATTERNS
Information Architecture:
- Chunking: Group related information in visual cards
- Progressive Disclosure: Main points → supporting details → examples
- Visual Anchors: Icons and images reinforce concepts
- White Space: Generous spacing for cognitive processing

Content Type Templates:
- Feature Cards: Highlight key characteristics with icons
- Timeline Elements: Show chronological or process progression
- Impact Grids: Categorize effects, outcomes, or comparisons
- Quote Blocks: Add authority, perspective, and emphasis
- Statistical Displays: Data visualization and key metrics

## 5. TYPOGRAPHY & VISUAL ELEMENTS
Font Strategy:
- Choose fonts that match topic personality and emotional tone
- Create clear hierarchy through size, weight, and spacing
- Ensure readability with proper contrast and sizing

Visual Design Elements:
- Background Patterns: Subtle geometric overlays (opacity 0.1-0.2)
- Accent Lines: Colored bars or borders for emphasis
- Icon Integration: Consistent icon style throughout presentation
- Border Accents: Strategic use of colored borders on cards

## 6. NARRATIVE FLOW DESIGN
Storytelling Structure:
- Slide 1: Hook/Problem Statement with strong visual impact
- Slides 2-3: Development/Analysis with supporting evidence
- Slide 4: Solutions/Impact with compelling visuals
- Slide 5: Conclusion/Call-to-Action with memorable closing

Progressive Complexity:
- Start with simple, powerful concepts
- Build to detailed explanations and evidence
- End with synthesis and actionable insights

## 7. LAYOUT STRATEGY GUIDE

### Title Slide Layout:
- Central focal point with dramatic typography
- Subtitle positioning with visual balance
- Optional background image with reduced opacity
- Minimal elements for maximum impact

### Content Slide Layouts:
A) Two-Column Layout:
   - Left: Text content with feature cards
   - Right: Visual elements (images, timelines, quotes)

B) Grid-Based Layout:
   - 2×2 grid of feature cards with icons
   - Supporting image with caption
   - Integrated quote or statistic

C) Hero Content Layout:
   - Single central concept with large typography
   - Supporting visual elements
   - Minimal text for maximum impact

D) Comparison Layout:
   - Side-by-side content blocks
   - Visual connectors between elements
   - Clear differentiation through color/spacing

### Process/Timeline Layouts:
- Horizontal flow with connected elements
- Step-by-step progression indicators
- Consistent spacing and alignment

## 8. BRAND CONSISTENCY FRAMEWORK
Visual Identity Alignment:
- Match fonts to topic personality (tech=clean, traditional=serif, creative=display)
- Color palette reflects topic mood and industry
- Imagery style consistent throughout
- Design elements reinforce topic themes

## 9. ACCESSIBILITY & PERFORMANCE
Design Standards:
- High contrast ratios for readability
- Minimum font sizes (18px for body text)
- Color coding with consistent meaning
- Scalable elements for different viewing conditions

## 10. INTERACTIVE DESIGN PRINCIPLES
Engagement Elements:
- Subtle hover effects for web viewing
- Visual feedback on interactive elements
- Smooth transitions (0.3s ease)
- Progressive revelation of information

PLANNING OUTPUT FORMAT:
Generate a comprehensive JSON structure containing:

{
  "presentation_overview": {
    "topic": "string",
    "target_audience": "string",
    "key_objectives": ["string"],
    "narrative_arc": "string",
    "total_slides": number
  },
  "design_system": {
    "color_palette": {
      "primary_background": "string",
      "accent_colors": ["string"],
      "text_colors": {
        "primary": "string",
        "secondary": "string",
        "accent": "string"
      }
    },
    "typography": {
      "primary_font": "string",
      "secondary_font": "string",
      "heading_hierarchy": ["string"]
    },
    "visual_theme": "string",
    "layout_approach": "string"
  },
  "slides": [
    {
      "slide_number": number,
      "type": "title|content|conclusion|transition",
      "title": "string",
      "key_points": ["string"],
      "visual_focus": "string",
      "layout_pattern": "hero|two-column|grid|comparison|timeline",
      "content_elements": {
        "feature_cards": number,
        "images": boolean,
        "quotes": boolean,
        "statistics": boolean,
        "icons": ["string"]
      },
      "narrative_purpose": "string",
      "design_notes": "string"
    }
  ],
  "content_strategy": {
    "information_hierarchy": "string",
    "engagement_techniques": ["string"],
    "visual_metaphors": ["string"],
    "call_to_action": "string"
  }
}

QUALITY CHECKLIST:
- [ ] Clear narrative progression across slides
- [ ] Consistent visual hierarchy and branding
- [ ] Appropriate layout patterns for content types
- [ ] Balanced information density
- [ ] Strategic use of visual elements
- [ ] Accessibility considerations addressed
- [ ] Brand alignment with topic personality
- [ ] Engagement and interactivity planned
- [ ] Professional polish and finishing touches

Remember: Create presentations that feel custom-designed, visually impactful, and perfectly matched to their topic while maintaining professional design standards and narrative coherence.
"""

    # Enhanced HTML Generation System Prompt
    system_prompt = """
!!! ABSOLUTE DESIGN RULES !!!
- Use only solid colors for all backgrounds, borders, text, and design elements.
- NEVER use gradients, patterns, background-image, or any color transitions.
- If unsure, always choose a solid color.
- Output is INVALID if any gradient, pattern, or background-image is present.
- Use only <div>, <img>, and text-related tags (<h1>-<h6>, <p>, <span>, <strong>, <em>, <b>, <i>, <ul>, <ol>, <li>). Do NOT use any other HTML tags.

You are an expert slide design agent. Generate one slide at a time using HTML and Tailwind CSS (v2.2.19). Layouts must adapt to the topic and design system.

CORE PRINCIPLES:
- Visual impact and engagement are top priority.
- Topic drives design decisions.
- Slides must be immersive, memorable, and readable.
- Use modern design patterns and clear hierarchy.

TECHNICAL SPECIFICATIONS:
- Resolution: 1280x720px (w-[1280px] h-[720px])
- Tailwind CSS classes only.
- Font pairing matches topic mood.
- Only solid colors for backgrounds, borders, and text.
- No gradients, patterns, or background-image.
- Depth via solid color layering, shadow, or z-index only.
- Smooth hover effects and micro-interactions.

LAYOUT PHILOSOPHY:
- HERO: Central focus, dramatic typography, bold solid colors.
- STORYTELLING: Visual flow, metaphors, layered info.
- DATA/CONCEPT: Grid-based, icons, clear hierarchy.
- ARTISTIC: Asymmetry, whitespace, creative typography.

TYPOGRAPHY:
- Tech: Inter, Poppins (sans-serif)
- Formal: Playfair Display (serif)
- Creative: Display fonts
- Corporate: Professional, readable
- Use font weight/size for hierarchy.

COLOR PALETTE (SOLID ONLY):
- Technology: bg-blue-800, bg-teal-700, text-blue-500
- Nature: bg-green-700, bg-gray-400, text-green-500
- Business: bg-blue-900, bg-gray-500, text-yellow-500
- Creative: Vibrant solid colors only
- Education: bg-red-500, bg-orange-400, text-white
- Use only Tailwind solid color classes.

VISUAL ENHANCEMENT:
- Cards: shadow-lg, shadow-xl, solid color borders
- No CSS gradient utilities or background-image.
- Visual separation via borders and spacing.
- Hover: transition-all duration-300, hover:scale-105, color shifts.

CONTENT ORGANIZATION:
- No fixed templates; adapt to content.
- Single concept: Large, centered, impactful.
- Multiple points: Dynamic grids, flowing layouts.
- Comparisons: Side-by-side, visual connectors.
- Processes: Sequential flow.

STRICT RULES:
- Never nest text tags inside other text tags.
- Use semantic HTML: h1-h6, p, span.
- <div> for layout only.
- Borders via separate <div> with solid background.
- All content fits within 1280x720px.
- Only allowed tags: <div>, <img>, <h1>-<h6>, <p>, <span>, <strong>, <em>, <b>, <i>, <ul>, <ol>, <li>.

REQUIRED OPENING TAGS:
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=Poppins:wght@300;400;600;700;800&family=Playfair+Display:wght@400;700;900&display=swap');
    body {width: 1280px; height: 720px; margin: 0; padding: 0; overflow: hidden;}
</style>

QUALITY CHECKLIST:
- No gradients, patterns, or background-image.
- Only solid colors for all backgrounds, borders, and design elements.
- No Tailwind gradient classes (e.g., bg-gradient-to-r).
- All content fits within 1280x720px.
- Output is clean HTML, no markdown or JavaScript.
- Only allowed HTML tags are present.

Your goal: Create premium, engaging slides perfectly matched to their topic. Think like a world-class graphic designer focused on aesthetics and communication effectiveness.
"""

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
    )

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize agents
    planner_agent = ChatAgent(
        system_message=planning_prompt,
        model=model,
    )

    html_agent = ChatAgent(
        system_message=system_prompt,
        model=model,
    )

    # Step 1: Generate comprehensive presentation plan
    topic = "The Future of Sustainable Energy: Innovations and Global Impact"

    planning_response = await planner_agent.astep(
        f"Create a comprehensive presentation plan for the topic: '{topic}'. "
        f"Plan for 4-5 slides including title, content, and conclusion slides. "
        f"Focus on creating a cohesive design system that will maintain consistency across all slides."
    )

    print("=== PRESENTATION PLAN ===")
    print(planning_response.msg.content)

    # Parse the plan (assuming it returns valid JSON)
    try:
        presentation_plan = json.loads(planning_response.msg.content)
    except json.JSONDecodeError:
        print("Plan parsing failed, using fallback structure")
        exit()

    # Step 2: Generate slides based on the plan
    htmls = []

    for i, slide_info in enumerate(presentation_plan["slides"]):
        slide_prompt = f"""
        DESIGN SYSTEM:
        {json.dumps(presentation_plan.get("design_system", {}), indent=2)}
        
        SLIDE REQUIREMENTS:
        - Slide Number: {slide_info["slide_number"]}
        - Type: {slide_info["type"]}
        - Title: {slide_info["title"]}
        - Key Points: {slide_info.get("key_points", [])}
        - Visual Focus: {slide_info.get("visual_focus", "Typography and color")}
        - Layout Notes: {slide_info.get("layout_notes", "Follow design system consistently")}
        
        Create this slide following the design system exactly. Ensure it feels cohesive with the overall presentation theme while serving its specific purpose.
        """

        response = await html_agent.astep(slide_prompt)
        htmls.append(response.msg.content)

        # Save individual slide files
        with open(
            f"examples/toolkits/mcp_pptx_html/slide_{i+1}.html",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(response.msg.content)

        print(f"Generated slide {i+1}: {slide_info['title']}")

    # Step 3: Convert to PowerPoint
    pptx_toolkit = HTMLToPPTXToolkit()
    result = await pptx_toolkit.convert_htmls_to_pptx(
        html_list=htmls,
        output_path="examples/toolkits/mcp_pptx_html/output/sustainable_energy_presentation.pptx",
    )

    print("\n=== GENERATION COMPLETE ===")
    print(f"Total slides generated: {len(htmls)}")
    print(f"PowerPoint conversion result: {result}")

    # Save the complete plan for reference
    with open(
        "examples/toolkits/mcp_pptx_html/presentation_plan.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(presentation_plan, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
