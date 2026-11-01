"""
Simple test script for unified_analyzer.js filtering capabilities.
"""

import asyncio
import json
import warnings
from pathlib import Path

from camel.logger import get_logger
from camel.toolkits import HybridBrowserToolkit

# Suppress asyncio warnings
warnings.filterwarnings("ignore", category=ResourceWarning, module="asyncio")

logger = get_logger(__name__)

# Configuration
DEMO_HTML_PATH = Path(__file__).parent / "filtering_demo.html"

# Create browser toolkit
web_toolkit = HybridBrowserToolkit(
    mode="python",  
    headless=False,
    enabled_tools=["browser_open", "browser_close", "browser_visit_page"],
)


def print_analysis_results(analysis_result):
    """Print detailed filtering analysis results."""
    metadata = analysis_result.get('metadata', {})
    filtering_stats = metadata.get('filteringStats', {})
    memory_info = metadata.get('memoryInfo', {})
    
    print(f"\n{'='*60}")
    print(f"CAMEL FILTERING ANALYSIS RESULTS")
    print(f"{'='*60}")
    print(f"URL: {analysis_result.get('url', 'Unknown')}")
    print(f"Timestamp: {metadata.get('timestamp', 'Unknown')}")
    print(f"\nFILTERING STATISTICS:")
    print(f"  Occluded Elements Filtered: {filtering_stats.get('occludedElementsFiltered', 0)}")
    print(f"  No-Info Elements Filtered:  {filtering_stats.get('noInfoElementsFiltered', 0)}")
    print(f"  Total Elements Filtered:    {filtering_stats.get('totalElementsFiltered', 0)}")
    print(f"  Retained Elements:          {metadata.get('elementCount', 0)}")
    
    print(f"\nMEMORY USAGE:")
    print(f"  Memory Utilization: {memory_info.get('memoryUtilization', '0%')}")
    print(f"  Current Refs:       {memory_info.get('currentRefCount', 0)}")
    print(f"  Max Refs:           {memory_info.get('maxRefs', 0)}")
    
    # Show all retained elements with details
    elements = analysis_result.get('elements', {})
    if elements:
        print(f"\nRETAINED ELEMENTS ({len(elements)} total):")
        print(f"{'Ref':<6} {'Role':<12} {'Tag':<8} {'Name':<40}")
        print(f"{'-'*70}")
        
        for ref, element in elements.items():
            role = element.get('role', 'unknown')[:11]
            tag = element.get('tagName', 'unknown')[:7]
            name = element.get('name', '').strip()[:39]
            
            # Add special indicators
            if element.get('disabled'):
                name += " [DISABLED]"
            if element.get('checked'):
                name += " [CHECKED]"
            
            print(f"{ref:<6} {role:<12} {tag:<8} {name:<40}")
    
    print(f"\nELEMENT BREAKDOWN BY ROLE:")
    role_counts = {}
    for element in elements.values():
        role = element.get('role', 'unknown')
        role_counts[role] = role_counts.get(role, 0) + 1
    
    for role, count in sorted(role_counts.items()):
        print(f"  {role:<15}: {count}")
    
    print(f"\n{'='*60}")


async def test_unified_analyzer():
    """Test unified_analyzer.js filtering functionality."""
    if not DEMO_HTML_PATH.exists():
        logger.error(f"Demo HTML file not found at {DEMO_HTML_PATH}")
        return
    
    try:
        # Open browser and load page
        await web_toolkit.browser_open()
        page_url = str(DEMO_HTML_PATH.absolute().as_uri())
        await web_toolkit.browser_visit_page(page_url)
        
        # Get page and load the script
        page = await web_toolkit._require_page()
        js_path = Path(__file__).parent.parent.parent / "camel" / "toolkits" / "hybrid_browser_toolkit_py" / "unified_analyzer.js"
        
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Execute the script
        modified_js = f"""
        window.camelAnalyzer = {js_content.replace('})();', '});')};
        window.camelAnalysisResult = window.camelAnalyzer(false);
        """
        
        await page.add_script_tag(content=modified_js)
        analysis_result = await page.evaluate("window.camelAnalysisResult")
        
        if isinstance(analysis_result, dict):
            logger.info("SUCCESS: unified_analyzer.js executed successfully!")
            print_analysis_results(analysis_result)
            
            # Save detailed results
            with open("unified_analyzer_test_results.json", 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False, default=str)
            logger.info("Results saved to unified_analyzer_test_results.json")
            
        else:
            logger.error(f"Unexpected result: {analysis_result}")
            
    except Exception as e:
        logger.error(f"Test error: {e}")
    finally:
        await web_toolkit.browser_close()


if __name__ == "__main__":
    # Simple execution with basic error suppression
    try:
        asyncio.run(test_unified_analyzer())
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise

"""
============================================================
CAMEL FILTERING ANALYSIS RESULTS
============================================================
URL: file:///E:/EnjoyAI/camel/examples/toolkits/filtering_demo.html
Timestamp: 2025-09-16T15:39:07.466Z

FILTERING STATISTICS:
  Occluded Elements Filtered: 4
  No-Info Elements Filtered:  34
  Total Elements Filtered:    38
  Retained Elements:          61

MEMORY USAGE:
  Memory Utilization: 3.4%
  Current Refs:       67
  Max Refs:           2000

RETAINED ELEMENTS (61 total):
Ref    Role         Tag      Name
----------------------------------------------------------------------
e2     generic      div
e3     heading      h1       CAMEL Filtering Test - Extended Demo
e4     generic      p        Comprehensive test for occlusion filter
e5     generic      div      1. Occlusion Filtering Test

e6     generic      div      1. Occlusion Filtering Test
e7     generic      p        Elements hidden behind other elements s
e8     generic      div      Hidden Button 1
                Red Ove
e9     generic      div      Red Overlay
e10    generic      div      Purple Cover
e11    button       button   Visible Button
e12    generic      p        Expected: 2 buttons should be filtered
e14    generic      div
e15    generic      div      2. No-Information Label Filtering Test
e16    generic      p        Interactive elements without meaningful
e17    heading      h4       Empty Elements (should be filtered):
e18    generic      div
e19    heading      h4       Symbol-only Elements (should be filtere
e20    generic      p        Expected: All 16 empty/symbol elements
e22    generic      div      3. Valid Elements Test (should NOT be f
e23    generic      div      3. Valid Elements Test (should NOT be f
e24    generic      p        Elements with clear functionality and m
e25    generic      div      Search
                Submit Form

e26    button       button   Search
e27    button       button   Submit Form
e28    button       button   Login
e29    button       button   Cancel
e30    button       button   Delete Item
e31    textbox      input
e32    textbox      input
e33    textbox      input
e34    select       select
e35    select       select
e36    link         a        Home
e37    link         a        About Us
e38    link         a        Contact
e39    generic      p        Expected: All 16 elements above should
e41    generic      div      4. Complex Layout Test
            Mixe
e42    generic      div      4. Complex Layout Test
e43    generic      p        Mixed content with various interactive
e44    generic      div      User Profile


e45    generic      div      User Profile


e46    generic      div      User Profile
e47    textbox      input
e48    textbox      input
e49    button       button   Update Profile
e50    generic      div      Settings


e51    generic      div      Settings
e53    checkbox     input     [CHECKED]
e55    checkbox     input
e56    button       button   Save Settings
e57    generic      div
e58    generic      div      5. Expected Results Summary
e59    list         ul
e60    listitem     li       Occluded Filtered: 2 elements (Hidden B
e61    generic      strong   Occluded Filtered:
e62    listitem     li       No-Info Filtered: 16 elements (6 empty
e63    generic      strong   No-Info Filtered:
e64    listitem     li       Total Filtered: 18 elements
e65    generic      strong   Total Filtered:
e66    listitem     li       Preserved Elements: ~20+ meaningful int
e67    generic      strong   Preserved Elements:

ELEMENT BREAKDOWN BY ROLE:
  button         : 8
  checkbox       : 2
  generic        : 33
  heading        : 3
  link           : 3
  list           : 1
  listitem       : 4
  select         : 2
  textbox        : 5

============================================================
"""