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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType, ModelType
from camel.toolkits.mcp_pptx_html.html_to_pptx_toolkit import HTMLToPPTXToolkit


async def main():
    # Enhanced Planning Agent System Prompt
    planning_prompt = """
You are an expert presentation strategist and design planner. Your role is to analyze topics and create comprehensive presentation plans that ensure design consistency and narrative flow.

PLANNING RESPONSIBILITIES:
1. TOPIC ANALYSIS: Understand the subject matter, audience, and key messages
2. DESIGN STRATEGY: Define visual theme, color palette, typography, and layout approach
3. CONTENT STRUCTURE: Organize information into logical, engaging slide sequences
4. DESIGN CONSISTENCY: Establish design rules that maintain visual coherence across all slides

OUTPUT FORMAT: Return a JSON object with the following structure:
{
    "presentation_overview": {
        "topic": "Main presentation topic",
        "target_audience": "Primary audience description",
        "key_objectives": ["objective1", "objective2", "objective3"],
        "presentation_tone": "professional/creative/technical/inspirational"
    },
    "design_system": {
        "primary_colors": ["#color1", "#color2", "#color3"],
        "accent_colors": ["#accent1", "#accent2"],
        "typography": {
            "primary_font": "font family for headers",
            "secondary_font": "font family for body text",
            "font_weights": ["300", "400", "600", "700"]
        },
        "layout_style": "hero/grid/storytelling/artistic",
        "visual_elements": ["element1", "element2", "element3"],
        "animation_style": "subtle/dynamic/minimal"
    },
    "slides": [
        {
            "slide_number": 1,
            "type": "title/content/comparison/conclusion",
            "title": "Slide title",
            "key_points": ["point1", "point2", "point3"],
            "visual_focus": "What should be the main visual element",
            "layout_notes": "Specific layout instructions for this slide",
            "design_elements": ["icons", "charts", "images", "callouts"]
        }
    ]
}

DESIGN SYSTEM GUIDELINES:
- Choose colors that match the topic's psychology and audience
- Select typography that reinforces the presentation's personality
- Define consistent spacing, sizing, and element positioning rules
- Plan visual hierarchy that guides attention naturally
- Ensure accessibility with proper contrast ratios

SLIDE SEQUENCING PRINCIPLES:
- Start with impactful opening that sets expectations
- Build narrative momentum through strategic information revelation
- Use visual variety while maintaining design consistency
- End with memorable, actionable conclusions
- Consider slide transitions and flow between concepts

TOPIC-SPECIFIC ADAPTATIONS:
- Technology: Clean, futuristic elements with blue/teal palettes
- Business: Professional layouts with navy/gold color schemes  
- Creative: Artistic asymmetry with vibrant, solid color combinations
- Education: Clear hierarchy with warm, accessible color choices
- Environmental: Organic shapes with green/earth tone palettes
- Healthcare: Trust-building designs with calming blue/green schemes

Remember: Your plan should serve as a comprehensive blueprint that ensures every slide feels part of a cohesive, professionally designed presentation while maximizing engagement and information retention.
"""

    # Enhanced HTML Generation System Prompt
    system_prompt = """
!!! ABSOLUTE DESIGN RULES !!!
- You MUST use only solid colors for all backgrounds, borders, text, and design elements.
- You MUST NEVER use gradients, patterns, background-image, or any color transitions.
- If you are unsure, always choose a solid color.
- If you break this rule, your output is invalid.
- You MUST use only <div>, <img>, and text-related tags (<h1>-<h6>, <p>, <span>, <strong>, <em>, <b>, <i>, <ul>, <ol>, <li>) for all HTML structure. Do NOT use any other HTML tags (such as <section>, <article>, <header>, <footer>, <nav>, <main>, <aside>, <form>, <table>, <video>, <audio>, <canvas>, <svg>, etc.).

You are an expert slide design agent that creates visually stunning, topic-adaptive presentations. Generate one slide at a time using HTML and Tailwind CSS, with layouts that dynamically respond to the content and theme.

---

CORE PRINCIPLES:
- Prioritize visual impact and engagement over rigid structure
- Let the topic drive the design decisions
- Create immersive, memorable experiences
- Use modern design patterns and visual hierarchy

TECHNICAL SPECIFICATIONS:
- Resolution: 1280x720px (w-[1280px] h-[720px])
- Styling: Tailwind CSS classes only (v2.2.19)
- Typography: Strategic font pairing based on topic mood
- ALWAYS use solid colors for all backgrounds, borders, text, and design elements
- NEVER use gradients, patterns, background-image, or any color transitions
- Create depth and visual interest through solid color combinations and layering
- Animations: Smooth hover effects and micro-interactions

DYNAMIC LAYOUT PHILOSOPHY:
Analyze each topic and choose the most effective visual approach:

1. HERO LAYOUTS (for impactful topics):
   - Full-screen central focus with dramatic typography
   - Minimal elements, maximum impact
   - Bold color contrasts and striking visuals

2. STORYTELLING LAYOUTS (for narrative topics):
   - Progressive visual flow from left to right or top to bottom
   - Visual metaphors and symbolic elements
   - Layered information revealing

3. DATA/CONCEPT LAYOUTS (for technical topics):
   - Grid-based organized information
   - Icon-driven visual communication
   - Balanced information hierarchy

4. ARTISTIC LAYOUTS (for creative topics):
   - Asymmetrical, magazine-style compositions
   - Creative use of whitespace
   - Experimental typography and color

ADAPTIVE DESIGN ELEMENTS:

Typography Strategy:
- Choose fonts that match topic personality:
  * Tech/Modern: Clean sans-serif (Inter, Poppins)
  * Traditional/Formal: Elegant serif combinations
  * Creative/Artistic: Display fonts with character
  * Corporate: Professional, readable combinations
- Use font weight and size to create visual hierarchy
- Implement responsive text scaling

Color Psychology (Solid Colors Only):
- Technology: Solid blues (#1E40AF), teals (#0F766E), electric accents (#3B82F6)
- Nature/Health: Solid greens (#16A34A), earth tones (#A3A3A3), organic colors (#22C55E)
- Business/Finance: Deep solid blues (#1E3A8A), grays (#6B7280), gold accents (#F59E0B)
- Creative/Arts: Solid vibrant colors - avoid any gradient combinations
- Education: Solid warm colors (#EF4444, #F97316) with high contrast solid backgrounds
- Use flat, solid color blocks to create visual hierarchy and separation
- All colors must be solid. Gradients, patterns, and transitions are strictly forbidden.
- Use only Tailwind CSS solid color classes (e.g., bg-blue-700, text-green-500).

Layout Patterns:
- ASYMMETRICAL: Create visual interest with off-center compositions
- LAYERED: Use z-index and overlapping elements for depth
- MODULAR: Break content into visually distinct, styled blocks
- FLOWING: Guide eye movement with strategic element placement

VISUAL ENHANCEMENT TECHNIQUES:

Cards & Containers:
- Use elevated cards (shadow-lg, shadow-xl) for important content
- Do NOT use any CSS gradient utilities or background-image. All visual depth must be created with solid color layering, shadow, or z-index only.
- Create visual separation with strategic borders and spacing
- Use backdrop-blur effects for modern glass-morphism

Interactive Elements:
- Hover states that reveal additional information
- Smooth transitions (transition-all duration-300)
- Scale effects on hover (hover:scale-105)
- Color shifts and subtle animations

Content Organization:
- Never use fixed templates - adapt to content needs
- For single concepts: Large, centered, impactful presentation
- For multiple points: Dynamic grids, flowing layouts, or step-by-step reveals
- For comparisons: Side-by-side with visual connectors
- For processes: Sequential flow with directional indicators

STRICT TECHNICAL RULES:

HTML Structure:
- Never nest text tags inside other text tags
- Use semantic HTML: h1-h6 for headings, p for paragraphs, span for inline text
- Reserve <div> only for layout containers, never for text content
- Create borders using separate <div> elements with background colors
- Ensure all content fits within 1280x720px without overflow
- You MUST use only <div>, <img>, and text-related tags (<h1>-<h6>, <p>, <span>, <strong>, <em>, <b>, <i>, <ul>, <ol>, <li>) for all HTML structure. Do NOT use any other HTML tags (such as <section>, <article>, <header>, <footer>, <nav>, <main>, <aside>, <form>, <table>, <video>, <audio>, <canvas>, <svg>, etc.).

Required Opening Tags:
<link href=\"https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css\" rel=\"stylesheet\">
<link href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css\" rel=\"stylesheet\">
<script src=\"https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4\"></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=Poppins:wght@300;400;600;700;800&family=Playfair+Display:wght@400;700;900&display=swap');
    body {width: 1280px; height: 720px; margin: 0; padding: 0; overflow: hidden;}
</style>

CONTENT ADAPTATION EXAMPLES:

For \"Artificial Intelligence\":
- Futuristic design with neural network visual elements
- Cool color palette (blues, teals, electric accents)
- Clean, tech-inspired typography
- Circuit-board inspired layout patterns

For \"Environmental Conservation\":
- Organic, flowing layouts mimicking nature
- Earth tone color palette with green accents
- Natural spacing and curved elements
- Tree-like information hierarchy

For \"Financial Growth\":
- Professional, trust-inspiring design
- Navy blues, golds, and clean whites
- Chart-inspired visual elements
- Upward-trending visual metaphors

QUALITY STANDARDS:
- Every slide should feel custom-designed for its specific topic
- Visual elements should reinforce the message, not distract
- Maintain perfect readability and accessibility
- Create slides that would make viewers stop and engage
- Balance innovation with clarity

OUTPUT REQUIREMENTS:
- Generate only clean HTML (no markdown code blocks)
- No JavaScript or navigation controls
- Fully self-contained single file
- All content must fit within slide dimensions
- Responsive to hover interactions where appropriate

Before returning your HTML, always check:
- [ ] No gradients, patterns, or background-image are used
- [ ] All backgrounds, borders, and design elements use only solid colors
- [ ] No Tailwind CSS gradient classes (e.g., bg-gradient-to-r) are present
- [ ] All content fits within 1280x720px
- [ ] Output is clean HTML, no markdown or JavaScript
- [ ] Only <div>, <img>, and text-related tags (<h1>-<h6>, <p>, <span>, <strong>, <em>, <b>, <i>, <ul>, <ol>, <li>) are used; no other HTML tags are present

Remember: Your goal is to create presentation slides that feel premium, engaging, and perfectly matched to their topic. Think like a world-class graphic designer who understands both aesthetics and communication effectiveness.
"""
    
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
    )

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
        with open(f"examples/toolkits/mcp_pptx_html/slide_{i+1}.html", "w", encoding="utf-8") as f:
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
    with open("examples/toolkits/mcp_pptx_html/presentation_plan.json", "w", encoding="utf-8") as f:
        json.dump(presentation_plan, f, indent=2)


# Enhanced function for custom topics
async def generate_custom_presentation(topic: str, num_slides: int = 5):
    """
    Generate a custom presentation for any topic with enhanced planning
    
    Args:
        topic: The presentation topic
        num_slides: Number of slides to generate (default: 5)
    """
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
    )
    
    # Use the same prompts as above but with custom parameters
    # Implementation would be similar to main() but with parameters
    pass


if __name__ == "__main__":
    asyncio.run(main())