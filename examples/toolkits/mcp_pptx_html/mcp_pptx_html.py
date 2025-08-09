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
    
    # model = ModelFactory.create(
    #     model_platform=ModelPlatformType.OPENAI,
    #     model_type=ModelType.GPT_4_1_MINI,
    # )

    # # Initialize agents
    # planner_agent = ChatAgent(
    #     system_message=planning_prompt,
    #     model=model,
    # )
    
    # html_agent = ChatAgent(
    #     system_message=system_prompt,
    #     model=model,
    # )

    # # Step 1: Generate comprehensive presentation plan
    # topic = "The Future of Sustainable Energy: Innovations and Global Impact"
    
    # planning_response = await planner_agent.astep(
    #     f"Create a comprehensive presentation plan for the topic: '{topic}'. "
    #     f"Plan for 4-5 slides including title, content, and conclusion slides. "
    #     f"Focus on creating a cohesive design system that will maintain consistency across all slides."
    # )
    
    # print("=== PRESENTATION PLAN ===")
    # print(planning_response.msg.content)
    
    # # Parse the plan (assuming it returns valid JSON)
    # try:
    #     presentation_plan = json.loads(planning_response.msg.content)
    # except json.JSONDecodeError:
    #     print("Plan parsing failed, using fallback structure")
    #     exit()

    # # Step 2: Generate slides based on the plan
    # htmls = []
    
    # for i, slide_info in enumerate(presentation_plan["slides"]):
    #     slide_prompt = f"""
    #     DESIGN SYSTEM:
    #     {json.dumps(presentation_plan.get("design_system", {}), indent=2)}
        
    #     SLIDE REQUIREMENTS:
    #     - Slide Number: {slide_info["slide_number"]}
    #     - Type: {slide_info["type"]}
    #     - Title: {slide_info["title"]}
    #     - Key Points: {slide_info.get("key_points", [])}
    #     - Visual Focus: {slide_info.get("visual_focus", "Typography and color")}
    #     - Layout Notes: {slide_info.get("layout_notes", "Follow design system consistently")}
        
    #     Create this slide following the design system exactly. Ensure it feels cohesive with the overall presentation theme while serving its specific purpose.
    #     """
        
    #     response = await html_agent.astep(slide_prompt)
    #     htmls.append(response.msg.content)
        
    #     # Save individual slide files
    #     with open(f"examples/toolkits/mcp_pptx_html/slide_{i+1}.html", "w", encoding="utf-8") as f:
    #         f.write(response.msg.content)
        
    #     print(f"Generated slide {i+1}: {slide_info['title']}")
    htmls=["""<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Merriweather:ital,wght@0,400;0,700&display=swap');
  body {
    width: 1280px;
    height: 720px;
    margin: 0;
    padding: 0;
    overflow: hidden;
    background-color: #0B1D3A;
    font-family: 'Merriweather', serif;
  }
  .font-primary {
    font-family: 'Montserrat', sans-serif;
  }
  .font-secondary {
    font-family: 'Merriweather', serif;
  }
  .hover-scale:hover {
    transform: scale(1.05);
    transition: all 0.3s ease-in-out;
  }
</style>

<div class="w-[1280px] h-[720px] relative overflow-hidden" style="background-color:#0B1D3A;">
  <!-- Overlay solid layering to mimic gradient -->
  <div class="absolute inset-0" style="background-color:#1A2C56; opacity:0.45; z-index:10;"></div>

  <!-- Hero image (left 60%) with border and shadow -->
  <div class="absolute top-[48px] left-[48px] w-[748px] h-[624px] rounded shadow-xl border-6 border-[#E63946] overflow-hidden select-none hover-scale z-20">
    <img src="http://localhost:5000/images/96b19f59-1921-4cfa-94ba-92ae86a8f6e6/Rohit_Sharma_latest_news_and_updates_4.webp" 
         alt="Rohit Sharma Competitive Spirit" 
         class="w-full h-full object-cover" draggable="false" />
  </div>

  <!-- Text content (right 40%) -->
  <div class="absolute top-[48px] right-[48px] w-[444px] h-[624px] flex flex-col justify-center z-30 select-none">
    <h2 class="font-primary text-5xl font-bold text-white mb-8 leading-tight" style="line-height:1.1;">
      Rohit Sharma's <span class="text-[#E63946]">Enduring Legacy</span> &amp;<br> What Lies Ahead
    </h2>
    <ul class="font-secondary text-lg text-[#F4A261] list-disc list-inside space-y-5 max-w-[420px]">
      <li>Continues to inspire on and off-field</li>
      <li>Focused impact in limited overs format</li>
      <li>Mentorship strengthens Indian cricket culture</li>
    </ul>
  </div>

  <!-- Subtle dynamic accent shapes top right -->
  <div class="absolute top-[48px] right-[48px] mt-[680px] w-20 h-20 bg-[#A8DADC] z-15 rotate-12 shadow-lg"></div>
  <div class="absolute top-[96px] right-[96px] mt-[680px] w-12 h-12 bg-[#E63946] z-15 -rotate-6 shadow"></div>
</div>""",
""" <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Merriweather:ital,wght@0,400;0,700&display=swap');
  body {
    width: 1280px;
    height: 720px;
    margin: 0;
    padding: 0;
    overflow: hidden;
    background-color: #0B1D3A;
    font-family: 'Merriweather', serif;
  }
  .font-primary {
    font-family: 'Montserrat', sans-serif;
  }
  .font-secondary {
    font-family: 'Merriweather', serif;
  }
  .timeline-line {
    background-color: #E63946;
    width: 4px;
    border-radius: 2px;
  }
  .timeline-dot {
    background-color: #F4A261;
    width: 24px;
    height: 24px;
    border-radius: 9999px;
    border: 3px solid #E63946;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .timeline-dot i {
    color: #0B1D3A;
    font-size: 14px;
  }
  .timeline-item {
    min-width: 220px;
  }
  .timeline-hover:hover {
    transform: scale(1.05);
    transition: all 0.3s ease-in-out;
  }
</style>

<div class="w-[1280px] h-[720px] relative overflow-hidden" style="background-color:#0B1D3A;">
  <!-- Dark navy overlay for layered effect -->
  <div class="absolute inset-0" style="background-color:#1A2C56; opacity:0.45; z-index:10;"></div>

  <!-- Title area -->
  <div class="absolute top-[48px] left-[48px] right-[48px] z-20">
    <h2 class="font-primary text-5xl font-bold text-white select-none" style="line-height:1.1;">
      BCCI's <span class="text-[#E63946]">Strategic Scheduling</span> &amp; Rohit's Future
    </h2>
  </div>

  <!-- Timeline container -->
  <div class="absolute top-[140px] left-[48px] right-[48px] bottom-[48px] flex justify-center items-center z-20">
    <!-- Vertical timeline line -->
    <div class="timeline-line h-[520px]"></div>

    <!-- Timeline items container -->
    <div class="flex flex-col justify-between h-[520px] ml-8">
      <!-- England Tour -->
      <div class="timeline-item timeline-hover flex items-center space-x-4 cursor-default">
        <div class="timeline-dot">
          <i class="fas fa-cricket-ball"></i>
        </div>
        <div>
          <p class="font-primary text-2xl font-bold text-[#E63946] select-none">England Tour</p>
          <p class="font-secondary text-lg text-[#F4A261] max-w-xs select-none">Key fixtures scheduled before workload management</p>
        </div>
      </div>

      <!-- Series Postponements -->
      <div class="timeline-item timeline-hover flex items-center space-x-4 cursor-default">
        <div class="timeline-dot">
          <i class="fas fa-pause"></i>
        </div>
        <div>
          <p class="font-primary text-2xl font-bold text-[#E63946] select-none">Series Postponements</p>
          <p class="font-secondary text-lg text-[#F4A261] max-w-xs select-none">Comeback delayed due to BCCI workload management</p>
        </div>
      </div>

      <!-- Asia Cup -->
      <div class="timeline-item timeline-hover flex items-center space-x-4 cursor-default">
        <div class="timeline-dot">
          <i class="fas fa-trophy"></i>
        </div>
        <div>
          <p class="font-primary text-2xl font-bold text-[#E63946] select-none">Asia Cup</p>
          <p class="font-secondary text-lg text-[#F4A261] max-w-xs select-none">Focus on limited overs and major tournaments</p>
        </div>
      </div>

      <!-- Australia Tour -->
      <div class="timeline-item timeline-hover flex items-center space-x-4 cursor-default">
        <div class="timeline-dot">
          <i class="fas fa-flag"></i>
        </div>
        <div>
          <p class="font-primary text-2xl font-bold text-[#E63946] select-none">Australia Tour</p>
          <p class="font-secondary text-lg text-[#F4A261] max-w-xs select-none">No fixtures before September 10, 2025</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Accent geometric shapes bottom right -->
  <div class="absolute bottom-[48px] right-[48px] w-20 h-20 bg-[#A8DADC] z-15 rotate-12 shadow-lg"></div>
  <div class="absolute bottom-[96px] right-[96px] w-12 h-12 bg-[#E63946] z-15 -rotate-6 shadow"></div>
</div>
""","""
 <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Merriweather:ital,wght@0,400;0,700&display=swap');
  body {
    width: 1280px;
    height: 720px;
    margin: 0;
    padding: 0;
    overflow: hidden;
    background-color: #0B1D3A;
    font-family: 'Merriweather', serif;
  }
  .font-primary {
    font-family: 'Montserrat', sans-serif;
  }
  .font-secondary {
    font-family: 'Merriweather', serif;
  }
  .card-hover:hover {
    transform: scale(1.05);
    box-shadow: 0 12px 20px rgba(230, 57, 70, 0.5);
    transition: all 0.3s ease-in-out;
  }
</style>

<div class="w-[1280px] h-[720px] relative overflow-hidden" style="background-color:#0B1D3A;">
  <!-- Dark navy overlay for layered solid effect -->
  <div class="absolute inset-0" style="background-color:#1A2C56; opacity:0.45; z-index:10;"></div>

  <!-- Title area top full width -->
  <div class="absolute top-[48px] left-[48px] right-[48px] z-20">
    <h2 class="font-primary text-5xl font-bold text-white select-none" style="line-height:1.1;">
      Mentorship: <span class="text-[#E63946]">Guiding Mumbai's Young Talent</span>
    </h2>
  </div>

  <!-- Main grid container with 2 columns 2 rows and gap -->
  <div class="absolute top-[140px] left-[48px] right-[48px] bottom-[48px] grid grid-cols-4 grid-rows-2 gap-8 z-20">
    
    <!-- Card 1: Yashasvi Jaiswal decision -->
    <div class="col-span-2 row-span-1 bg-[#1A2C56] rounded shadow-xl border-2 border-[#E63946] p-6 flex flex-col card-hover cursor-default">
      <div class="text-[#E63946] text-5xl mb-4 self-center">
        <i class="fas fa-user-check"></i>
      </div>
      <p class="font-secondary text-lg text-[#F4A261] flex-grow select-none">
        Rohit Sharma's intervention influenced <b>Yashasvi Jaiswal's decision to stay with Mumbai</b>
      </p>
    </div>

    <!-- Card 2: Pride of Mumbai Cricket -->
    <div class="col-span-2 row-span-1 bg-[#1A2C56] rounded shadow-xl border-2 border-[#F4A261] p-6 flex flex-col card-hover cursor-default">
      <div class="text-[#F4A261] text-5xl mb-4 self-center">
        <i class="fas fa-shield-alt"></i>
      </div>
      <p class="font-secondary text-lg text-[#F4A261] flex-grow select-none">
        Emphasizes <b>pride</b> of representing Mumbai Cricket
      </p>
    </div>

    <!-- Card 3: Leadership On and Off Field (with Icon) -->
    <div class="col-span-2 row-span-1 bg-[#1A2C56] rounded shadow-xl border-2 border-[#A8DADC] p-6 flex flex-col card-hover cursor-default">
      <div class="text-[#A8DADC] text-5xl mb-4 self-center">
        <i class="fas fa-chess-queen"></i>
      </div>
      <p class="font-secondary text-lg text-[#F4A261] flex-grow select-none">
        Highlights Rohit's <b>leadership</b> both on and off the field
      </p>
    </div>

    <!-- Card 4: Image card with Rohit and young fan -->
    <div class="col-span-2 row-span-1 rounded shadow-xl border-4 border-[#E63946] overflow-hidden select-none">
      <img src="http://localhost:5000/images/96b19f59-1921-4cfa-94ba-92ae86a8f6e6/Rohit_Sharma_latest_news_and_updates_3.jpg" alt="Rohit Sharma with Young Fan" class="w-full h-full object-cover" draggable="false" />
    </div>

  </div>

  <!-- Subtle dynamic accent shapes top right corner -->
  <div class="absolute top-[48px] right-[48px] w-20 h-20 bg-[#A8DADC] z-15 rotate-12 shadow-lg"></div>
  <div class="absolute top-[96px] right-[96px] w-12 h-12 bg-[#E63946] z-15 -rotate-6 shadow"></div>
</div>
""","""
 <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Merriweather:ital,wght@0,400;0,700&display=swap');
  body {
    width: 1280px;
    height: 720px;
    margin: 0;
    padding: 0;
    overflow: hidden;
    background-color: #0B1D3A;
    font-family: 'Merriweather', serif;
  }
  .font-primary {
    font-family: 'Montserrat', sans-serif;
  }
  .font-secondary {
    font-family: 'Merriweather', serif;
  }
</style>
<div class="w-[1280px] h-[720px] relative overflow-hidden" style="background-color:#0B1D3A;">
  <!-- Dark navy overlay to mimic gradient with solid layering -->
  <div class="absolute top-0 left-0 w-full h-full" style="background-color:#1A2C56; opacity:0.45; z-index:10;"></div>

  <!-- Content container with consistent margins -->
  <div class="absolute top-[48px] left-[48px] right-[48px] bottom-[48px] flex flex-row z-20" style="gap: 24px;">
    <!-- Left text column (60%) -->
    <div class="w-[720px] flex flex-col justify-center">
      <h2 class="font-primary text-5xl font-bold text-white mb-6 select-none" style="line-height:1.1;">
        Rohit Sharma's <span class="text-[#E63946]">ODI Comeback</span> with Virat Kohli
      </h2>
      <ul class="font-secondary text-lg text-[#F4A261] list-disc list-inside space-y-4 max-w-[680px]">
        <li>Scheduled return in October 2025 against Australia</li>
        <li>Focus shifted to limited-overs formats after Test retirement</li>
        <li>Emotional return to Australian pitches where Test career ended</li>
      </ul>
    </div>

    <!-- Right image column (40%) -->
    <div class="w-[472px] rounded shadow-xl border-4 border-[#E63946] overflow-hidden select-none" style="min-height: 480px;">
      <img src="http://localhost:5000/images/96b19f59-1921-4cfa-94ba-92ae86a8f6e6/Rohit_Sharma_latest_news_and_updates_2.jpg" alt="Rohit Sharma Comeback" class="w-full h-full object-cover" draggable="false" />
    </div>
  </div>

  <!-- Solid geometric accent shapes bottom left for energetic modern vibe -->
  <div class="absolute bottom-[48px] left-[48px] w-24 h-24 bg-[#A8DADC] z-15 rotate-12 shadow-lg"></div>
  <div class="absolute bottom-[96px] left-[96px] w-16 h-16 bg-[#E63946] z-15 -rotate-6 shadow"></div>
</div>
""","""
 <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Merriweather:ital,wght@0,400;0,700&display=swap');
    body {
      width: 1280px;
      height: 720px;
      margin: 0;
      padding: 0;
      overflow: hidden;
      background-color: #0B1D3A;
      font-family: 'Merriweather', serif;
    }
    .font-primary {
      font-family: 'Montserrat', sans-serif;
    }
    .font-secondary {
      font-family: 'Merriweather', serif;
    }
</style>
<div class="w-[1280px] h-[720px] relative overflow-hidden" style="background-color:#0B1D3A;">
  <!-- Dark navy solid overlay to mimic gradient layering with solid colors -->
  <div class="absolute top-0 left-0 w-full h-full" style="background-color:#1A2C56; opacity:0.4; z-index:10;"></div>

  <!-- Hero image container 60% width left side -->
  <div class="absolute top-[48px] left-[48px] w-[748px] h-[624px] rounded shadow-xl overflow-hidden z-20" style="border: 6px solid #E63946;">
    <img src="http://localhost:5000/images/96b19f59-1921-4cfa-94ba-92ae86a8f6e6/Rohit_Sharma_latest_news_and_updates_1.jpg" 
         alt="Rohit Sharma Celebrating" 
         class="w-full h-full object-cover select-none" draggable="false">
  </div>

  <!-- Text panel 40% width right side -->
  <div class="absolute top-[48px] right-[48px] w-[444px] h-[624px] flex flex-col justify-center z-30">
    <h1 class="font-primary text-5xl font-bold leading-tight text-white mb-8 select-none" style="line-height:1.1;">
      Rohit Sharma:<br>
      <span class="text-[#E63946]">Latest News &amp; Career Updates</span>
    </h1>
    <ul class="font-secondary text-lg text-[#F4A261] list-disc list-inside space-y-4">
      <li>Indian cricket icon's evolving journey</li>
      <li>Comeback, mentorship, and strategic pauses</li>
    </ul>
  </div>

  <!-- Subtle geometric accent shapes bottom right for dynamic energy (solid colored) -->
  <div class="absolute bottom-[48px] right-[48px] w-20 h-20 bg-[#A8DADC] z-15 rotate-12 shadow-lg"></div>
  <div class="absolute bottom-[96px] right-[96px] w-12 h-12 bg-[#E63946] z-15 -rotate-6 shadow"></div>
</div>
"""]
    
    

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