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
from camel.toolkits.browser_toolkit import AsyncBaseBrowser,AsyncBrowserToolkit  # please ensure the module path is correct

async def test_AsyncBaseBrowser_all_functions():
    # Instantiate the asynchronous browser (adjust the headless parameter as needed)
    browser = AsyncBaseBrowser(headless=False)
    print("Initializing browser...")
    await browser.async_init()
    
    # Test async_visit_page and async_wait_for_load (using GitHub as the test page)
    test_url = "https://github.com/camel-ai/camel"
    print("\nTesting async_visit_page and async_wait_for_load:")
    await browser.async_visit_page(test_url)
    print("Current page URL:", browser.get_url())
    await browser.async_wait_for_load(timeout=10)
    
    print("\nTesting async_click_id:")
    try:
        await browser.page.evaluate("""
        (function(){
            // Define the target button's XPath
            var xpath = "/html/body/div[1]/div[4]/div/main/turbo-frame/div/div/div/div/div[1]/react-partial/div/div/div[2]/div[2]/button";
            // Use document.evaluate to get the node
            var result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
            var button = result.singleNodeValue;
            if(button){
                // Set the __elementId attribute for the button
                button.setAttribute("__elementId", "test_random");
            } else {
                console.log("Target button not found");
            }
        })();
        """)
        # Call async_click_id to click the button
        await browser.async_click_id("test_random")
        print("Click complete")
    except Exception as e:
        print(f"Error occurred during click operation: {e}")
    
    # Test async_click_blank_area
    print("\nTesting async_click_blank_area:")
    try:
        await browser.async_click_blank_area()
        print("Successfully clicked the blank area")
    except Exception as e:
        print("Failed to click the blank area:", e)
    
    # Test async_get_screenshot
    print("\nTesting async_get_screenshot:")
    try:
        screenshot, file_path = await browser.async_get_screenshot(save_image=True)
        print("Screenshot taken successfully, saved at:", file_path)
    except Exception as e:
        print("Screenshot failed:", e)
    
    # Test async_capture_full_page_screenshots
    print("\nTesting async_capture_full_page_screenshots:")
    try:
        full_screenshots = await browser.async_capture_full_page_screenshots(scroll_ratio=0.8)
        print("Full page screenshot file paths:", full_screenshots)
    except Exception as e:
        print("Full page screenshot failed:", e)
    
    # Test async_get_visual_viewport
    print("\nTesting async_get_visual_viewport:")
    try:
        visual_viewport = await browser.async_get_visual_viewport()
        print("Visual viewport information:", visual_viewport)
    except Exception as e:
        print("Failed to get visual viewport:", e)
    
    # Test async_get_interactive_elements
    print("\nTesting async_get_interactive_elements:")
    try:
        interactive_elements = await browser.async_get_interactive_elements()
        print("Interactive elements information:", interactive_elements)
    except Exception as e:
        print("Failed to get interactive elements:", e)
    
    # Test async_get_som_screenshot (screenshot with marked interactive elements)
    print("\nTesting async_get_som_screenshot:")
    try:
        som_screenshot, som_path = await browser.async_get_som_screenshot(save_image=True)
        print("SOM screenshot taken successfully, saved at:", som_path)
    except Exception as e:
        print("Failed to get SOM screenshot:", e)
    
    # Test page scrolling operations
    print("\nTesting page scrolling operations:")
    try:
        await browser.async_scroll_down()
        print("Scrolled down successfully")
        await browser.async_scroll_up()
        print("Scrolled up successfully")
        await browser.async_scroll_to_bottom()
        print("Scrolled to bottom successfully")
        await browser.async_scroll_to_top()
        print("Scrolled to top successfully")
    except Exception as e:
        print("Scrolling operation error:", e)
    
    # Test get_url (non-asynchronous interface, just to retrieve the property)
    print("\nTesting get_url:")
    current_url = browser.get_url()
    print("Current page URL:", current_url)
    
    # Test async_extract_url_content
    print("\nTesting async_extract_url_content:")
    try:
        content = await browser.async_extract_url_content()
        print("Length of page content:", len(content))
    except Exception as e:
        print("Failed to extract page content:", e)
    
    """
    ==========================================================================
    Initializing browser...

    Testing async_visit_page and async_wait_for_load:
    Current page URL: https://github.com/camel-ai/camel

    Testing async_click_id:
    Click complete

    Testing async_click_blank_area:
    Successfully clicked the blank area

    Testing async_get_screenshot:
    Screenshot taken successfully, saved at: tmp/camel_0317152711.png

    Testing async_capture_full_page_screenshots:
    Full page screenshot file paths: ['tmp/camel_0317152711.png', 'tmp/camel_0317152712.png', 'tmp/camel_0317152713.png', 'tmp/camel_0317152713.png', 'tmp/camel_0317152714.png', 'tmp/camel_0317152715.png', 'tmp/camel_0317152715.png', 'tmp/camel_0317152716.png', 'tmp/camel_0317152716.png', 'tmp/camel_0317152717.png', 'tmp/camel_0317152718.png', 'tmp/camel_0317152718.png', 'tmp/camel_0317152719.png', 'tmp/camel_0317152720.png', 'tmp/camel_0317152720.png', 'tmp/camel_0317152721.png', 'tmp/camel_0317152721.png', 'tmp/camel_0317152722.png', 'tmp/camel_0317152723.png', 'tmp/camel_0317152723.png', 'tmp/camel_0317152724.png', 'tmp/camel_0317152724.png']

    Testing async_get_visual_viewport:
    Visual viewport information: {'height': 720, 'width': 1280, 'offsetLeft': 0, 'offsetTop': 0, 'pageLeft': 0, 'pageTop': 11777, 'scale': 1, 'clientWidth': 1280, 'clientHeight': 720, 'scrollWidth': 1280, 'scrollHeight': 12497}

    Testing async_get_interactive_elements:
    Interactive elements information: {....}

    Testing async_get_som_screenshot:
    SOM screenshot taken successfully, saved at: tmp/camel_0317152727.png

    Testing page scrolling operations:
    Scrolled down successfully
    Scrolled up successfully
    Scrolled to bottom successfully
    Scrolled to top successfully

    Testing get_url:
    Current page URL: https://github.com/camel-ai/camel

    Testing async_extract_url_content:
    Length of page content: 460156
    ==========================================================================
    """
    
    
    
    
    # Test async_download_file_id
    # Create a simple test page containing a download link (using a data URI to simulate download content)
    print("\nTesting async_download_file_id:")
    try:
        await browser.async_visit_page("about:blank")
        await browser.async_wait_for_load(timeout=5)
        html = '''
        <html>
          <body>
            <a id="download_link" href="data:text/plain,Hello%20World" download="hello.txt">Download File</a>
          </body>
        </html>
        '''
        await browser.page.set_content(html)
        # Set the __elementId attribute for the download link
        await browser.page.evaluate("document.getElementById('download_link').setAttribute('__elementId', 'test_download');")
        download_result = await browser.async_download_file_id("test_download")
        print("async_download_file_id result:", download_result)
    except Exception as e:
        print("async_download_file_id test error:", e)
    
    """
    ==========================================================================
    Testing async_download_file_id:
    async_download_file_id result: Downloaded file to path 'tmp/hello.txt'.
    ==========================================================================
    """
    
    
    # Test async_fill_input_id
    print("\nTesting async_fill_input_id:")
    try:
        # Navigate to a simple input test page, and use JavaScript to add the __elementId attribute to the first input element on the page
        input_test_page = "https://www.w3schools.com/html/html_forms.asp"
        await browser.async_visit_page(input_test_page)
        await browser.async_wait_for_load(timeout=10)
        await browser.page.evaluate("document.querySelector('input').setAttribute('__elementId', 'test_input');")
        fill_result = await browser.async_fill_input_id("test_input", "Hello World")
        print("Input field fill result:", fill_result)
    except Exception as e:
        print("async_fill_input_id test error:", e)
    
    # Test async_find_text_on_page
    print("\nTesting async_find_text_on_page:")
    try:
        find_result = await browser.async_find_text_on_page("Hello world")
        print("Text search result:", find_result)
    except Exception as e:
        print("Text search failed:", e)
    
    # Test async_back (navigate back to the previous page)
    print("\nTesting async_back:")
    try:
        await browser.async_back()
        print("Successfully navigated back, current page URL:", browser.get_url())
    except Exception as e:
        print("Error navigating back:", e)
    
    # Test async_hover_id
    print("\nTesting async_hover_id:")
    try:
        # Use XPath to locate the target element and set its __elementId attribute to "test_hover"
        locator = browser.page.locator("xpath=//*[@id='main']/div[2]/a[2]")
        await locator.evaluate("el => el.setAttribute('__elementId', 'test_hover')")
        # Call async_hover_id to hover over the element
        hover_result = await browser.async_hover_id("test_hover")
        print("Hover element result:", hover_result)
    except Exception as e:
        print("Hover test error:", e)
    
    # Test async_show_interactive_elements
    print("\nTesting async_show_interactive_elements:")
    try:
        await browser.async_show_interactive_elements()
        print("Interactive elements displayed successfully")
    except Exception as e:
        print("Failed to display interactive elements:", e)
    
    # Test async_get_webpage_content (convert to Markdown format)
    print("\nTesting async_get_webpage_content:")
    try:
        markdown_content = await browser.async_get_webpage_content()
        print("Markdown page content length:", len(markdown_content))
    except Exception as e:
        print("Markdown conversion failed:", e)
        
    # Finally, close the browser and clear the cache
    print("\nClosing browser and clearing cache...")
    await browser.async_close()
    browser.clean_cache()
    print("All tests completed, browser closed, and cache cleared")
    """
    ==========================================================================
    Testing async_fill_input_id:
    Input field fill result: Filled input field 'test_input' with text 'Hello World' and pressed Enter.

    Testing async_find_text_on_page:
    Text search result: Found text 'Hello world' on the page.

    Testing async_back:
    Successfully navigated back, current page URL: https://www.w3schools.com/html/html_forms.asp#gsc.tab=0

    Testing async_hover_id:
    Hover element result: Hovered over element with identifier 'test_hover'.

    Testing async_show_interactive_elements:
    Interactive elements displayed successfully

    Testing async_get_webpage_content:
    Markdown page content length: 66537

    Closing browser and clearing cache...
    All tests completed, browser closed, and cache cleared
    ==========================================================================
    """

async def test_AsyncBrowserToolkit():
    toolkit = AsyncBrowserToolkit(headless=False)

    # Define task parameters
    task_prompt = "Retrieve the current weather information for Beijing."
    start_url = "https://www.accuweather.com/en/cn/beijing/101924/current-weather/101924"
    round_limit = 12

    result = await toolkit.browse_url(task_prompt, start_url, round_limit)
    print("Simulated result:")
    print(result)
    
    """
    ==========================================================================
    The task to retrieve the current weather information for Beijing has been successfully completed. Here is the final weather information obtained:

    - **Temperature**: 4°C
    - **Weather Condition**: Clear
    - **Wind Gusts**: 17 km/h
    - **Humidity**: 28%
    - **Pressure**: 1026 mb
    - **Cloud Cover**: 0%

    This information was retrieved from the AccuWeather website for Beijing, and no further actions are needed.
    ==========================================================================
    """

async def main():
    await test_AsyncBaseBrowser_all_functions()  
    print("\n=========================\n")
    await test_AsyncBrowserToolkit()  

if __name__ == "__main__":
    asyncio.run(main()) 
    
    
