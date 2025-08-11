import { Page, Browser, BrowserContext, chromium, ConsoleMessage } from 'playwright';
import { BrowserToolkitConfig, SnapshotResult, SnapshotElement, ActionResult, TabInfo, BrowserAction, DetailedTiming } from './types';
import { ConfigLoader, StealthConfig } from './config-loader';

export class HybridBrowserSession {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private pages: Map<string, Page> = new Map();
  private consoleLogs: Map<string, ConsoleMessage[]> = new Map();
  private currentTabId: string | null = null;
  private tabCounter = 0;
  private configLoader: ConfigLoader;
  private scrollPosition: { x: number; y: number } = {x: 0, y: 0};
  private hasNavigatedBefore = false; //  Track if we've navigated before
  private logLimit: number; 

  constructor(config: BrowserToolkitConfig = {}) {
    // Use ConfigLoader's fromPythonConfig to handle conversion properly
    this.configLoader = ConfigLoader.fromPythonConfig(config);
    // Load browser configuration for console log limit, default to 1000
    this.logLimit = this.configLoader.getBrowserConfig().consoleLogLimit || 1000;
  }

  private registerNewPage(tabId: string, page: Page): void {
    // Register page and logs with tabId
    this.pages.set(tabId, page);
    this.consoleLogs.set(tabId, []);
    // Set up console log listener for the page
    page.on('console', (msg: ConsoleMessage) => {
      const logs = this.consoleLogs.get(tabId);
      if (logs) {
        logs.push(msg);
        if (logs.length >  this.logLimit) {
          logs.shift();
        }
      }
    });

    // Clean logs on page close
    page.on('close', () => {
      this.consoleLogs.delete(tabId);
    });
  }

  async ensureBrowser(): Promise<void> {  
    if (this.browser) {
      return;
    }

    const browserConfig = this.configLoader.getBrowserConfig();
    const stealthConfig = this.configLoader.getStealthConfig();
    
    // Check if CDP connection is requested
    if (browserConfig.connectOverCdp && browserConfig.cdpUrl) {
      // Connect to existing browser via CDP
      this.browser = await chromium.connectOverCDP(browserConfig.cdpUrl);
      
      // Get existing contexts or create new one
      const contexts = this.browser.contexts();
      if (contexts.length > 0) {
        this.context = contexts[0];
      } else {
        const contextOptions: any = {
          viewport: browserConfig.viewport
        };
        
        // Apply stealth headers if configured
        if (stealthConfig.enabled && stealthConfig.extraHTTPHeaders) {
          contextOptions.extraHTTPHeaders = stealthConfig.extraHTTPHeaders;
        }
        
        this.context = await this.browser.newContext(contextOptions);
      }
      
      // Handle existing pages
      const pages = this.context.pages();
      if (pages.length > 0) {
        // Map existing pages - for CDP, only use pages with about:blank URL
        let availablePageFound = false;
        for (const page of pages) {
          const pageUrl = page.url();
          // In CDP mode, only consider pages with about:blank as available
          if (pageUrl === 'about:blank') {
            const tabId = this.generateTabId();
            this.registerNewPage(tabId, page);
            if (!this.currentTabId) {
              this.currentTabId = tabId;
              availablePageFound = true;
            }
          }
        }
        
        // If no available blank pages found in CDP mode, we cannot create new ones
        if (!availablePageFound) {
          throw new Error('No available blank tabs found in CDP mode. The frontend should have pre-created blank tabs.');
        }
      } else {
        // In CDP mode, newPage is not supported
        throw new Error('No pages available in CDP mode and newPage() is not supported. Ensure the frontend has pre-created blank tabs.');
      }
    } else {
      // Original launch logic
      const launchOptions: any = {
        headless: browserConfig.headless,
      };

      if (stealthConfig.enabled) {
        launchOptions.args = stealthConfig.args || [];
        
        // Apply stealth user agent if configured
        if (stealthConfig.userAgent) {
          launchOptions.userAgent = stealthConfig.userAgent;
        }
      }

      if (browserConfig.userDataDir) {
        this.context = await chromium.launchPersistentContext(
          browserConfig.userDataDir,
          launchOptions
        );
        
        const pages = this.context.pages();
        if (pages.length > 0) {
          const initialTabId = this.generateTabId();
          this.registerNewPage(initialTabId, pages[0]);
          this.currentTabId = initialTabId;
        }
      } else {
        this.browser = await chromium.launch(launchOptions);
        const contextOptions: any = {
          viewport: browserConfig.viewport
        };
        
        // Apply stealth headers if configured
        if (stealthConfig.enabled && stealthConfig.extraHTTPHeaders) {
          contextOptions.extraHTTPHeaders = stealthConfig.extraHTTPHeaders;
        }
        
        this.context = await this.browser.newContext(contextOptions);
        
        const initialPage = await this.context.newPage();
        const initialTabId = this.generateTabId();
        this.registerNewPage(initialTabId, initialPage);
        this.currentTabId = initialTabId;
      }
    }

    // Set timeouts
    for (const page of this.pages.values()) {
      page.setDefaultNavigationTimeout(browserConfig.navigationTimeout);
      page.setDefaultTimeout(browserConfig.navigationTimeout);
    }
  }

  private generateTabId(): string {
    const browserConfig = this.configLoader.getBrowserConfig();
    return `${browserConfig.tabIdPrefix}${String(++this.tabCounter).padStart(browserConfig.tabCounterPadding, '0')}`;
  }

  async getCurrentPage(): Promise<Page> {
    if (!this.currentTabId || !this.pages.has(this.currentTabId)) {
      throw new Error('No active page available');
    }
    return this.pages.get(this.currentTabId)!;
  }

  async getCurrentLogs(): Promise<ConsoleMessage[]> {
    if (!this.currentTabId || !this.consoleLogs.has(this.currentTabId)) {
      return [];
    }
    return this.consoleLogs.get(this.currentTabId) || [];
  }

  /**
   * Get current scroll position from the page
   */
  private async getCurrentScrollPosition(): Promise<{ x: number; y: number }> {
    try {
      const page = await this.getCurrentPage();
      const scrollInfo = await page.evaluate(() => {
        return {
          x: window.pageXOffset || document.documentElement.scrollLeft || 0,
          y: window.pageYOffset || document.documentElement.scrollTop || 0,
          devicePixelRatio: window.devicePixelRatio || 1,
          zoomLevel: window.outerWidth / window.innerWidth || 1
        };
      }) as { x: number; y: number; devicePixelRatio: number; zoomLevel: number };
      
      // Store scroll position
      this.scrollPosition = { x: scrollInfo.x, y: scrollInfo.y };
      return this.scrollPosition;
    } catch (error) {
      console.warn('Failed to get scroll position:', error);
      return this.scrollPosition;
    }
  }

  async getSnapshotForAI(includeCoordinates = false, viewportLimit = false): Promise<SnapshotResult & { timing: DetailedTiming }> {
    // Always use native Playwright mapping - this is the correct approach
    return this.getSnapshotForAINative(includeCoordinates, viewportLimit);
  }

  private async getSnapshotForAINative(includeCoordinates = false, viewportLimit = false): Promise<SnapshotResult & { timing: DetailedTiming }> {
    const startTime = Date.now();
    const page = await this.getCurrentPage();
    
    try {
      //  Use _snapshotForAI() to properly update _lastAriaSnapshot
      const snapshotStart = Date.now();
      const snapshotText = await (page as any)._snapshotForAI();
      const snapshotTime = Date.now() - snapshotStart;
      
      // Extract refs from the snapshot text
      const refPattern = /\[ref=([^\]]+)\]/g;
      const refs: string[] = [];
      let match;
      while ((match = refPattern.exec(snapshotText)) !== null) {
        refs.push(match[1]);
      }
      
      // Get element information including coordinates if needed
      const mappingStart = Date.now();
      const playwrightMapping: Record<string, any> = {};
      
      if (includeCoordinates) {
        // Get coordinates for each ref using aria-ref selector
        for (const ref of refs) {
          try {
            const selector = `aria-ref=${ref}`;
            const element = await page.locator(selector).first();
            const exists = await element.count() > 0;
            
            if (exists) {
              // Get bounding box
              const boundingBox = await element.boundingBox();
              
              if (boundingBox) {
                playwrightMapping[ref] = {
                  ref,
                  coordinates: {
                    x: Math.round(boundingBox.x),
                    y: Math.round(boundingBox.y),
                    width: Math.round(boundingBox.width),
                    height: Math.round(boundingBox.height)
                  }
                };
              }
            }
          } catch (error) {
            // Failed to get coordinates for element
          }
        }
      }
      
      const mappingTime = Date.now() - mappingStart;
      
      // Apply viewport filtering if requested
      let finalElements = playwrightMapping;
      let finalSnapshot = snapshotText;
      
      if (viewportLimit) {
        const viewport = page.viewportSize() || { width: 1280, height: 720 };
        const scrollPos = await this.getCurrentScrollPosition();
        finalElements = this.filterElementsInViewport(playwrightMapping, viewport, scrollPos);
        finalSnapshot = this.rebuildSnapshotText(snapshotText, finalElements);
      }
      
      const totalTime = Date.now() - startTime;
      
      return {
        snapshot: finalSnapshot,
        elements: finalElements,
        metadata: {
          elementCount: Object.keys(finalElements).length,
          url: page.url(),
          timestamp: new Date().toISOString(),
        },
        timing: {
          total_time_ms: totalTime,
          snapshot_time_ms: snapshotTime,
          coordinate_enrichment_time_ms: 0, // Integrated into mapping
          aria_mapping_time_ms: mappingTime,
        },
      };
    } catch (error) {
      console.error('Failed to get AI snapshot with native mapping:', error);
      const totalTime = Date.now() - startTime;
      
      return {
        snapshot: 'Error: Unable to capture page snapshot',
        elements: {},
        metadata: {
          elementCount: 0,
          url: page.url(),
          timestamp: new Date().toISOString(),
        },
        timing: {
          total_time_ms: totalTime,
          snapshot_time_ms: 0,
          coordinate_enrichment_time_ms: 0,
          aria_mapping_time_ms: 0,
        },
      };
    }
  }



  /**
   *  Enhanced click implementation with new tab detection and scroll fix
   */
  private async performClick(page: Page, ref: string): Promise<{ success: boolean; method?: string; error?: string; newTabId?: string }> {
    
    try {
      //  Ensure we have the latest snapshot and mapping
      await (page as any)._snapshotForAI();
      
      //  Use Playwright's aria-ref selector engine
      const selector = `aria-ref=${ref}`;
      
      // Check if element exists
      const element = await page.locator(selector).first();
      const exists = await element.count() > 0;
      
      if (!exists) {
        return { success: false, error: `Element with ref ${ref} not found` };
      }
      
      //  Check element properties
      const browserConfig = this.configLoader.getBrowserConfig();
      const target = await element.getAttribute(browserConfig.targetAttribute);
      const href = await element.getAttribute(browserConfig.hrefAttribute);
      const onclick = await element.getAttribute(browserConfig.onclickAttribute);
      const tagName = await element.evaluate(el => el.tagName.toLowerCase());
      
      // Check if element naturally opens new tab
      const naturallyOpensNewTab = (
        target === browserConfig.blankTarget || 
        (onclick && onclick.includes(browserConfig.windowOpenString)) ||
        (tagName === 'a' && href && (href.includes(`javascript:${browserConfig.windowOpenString}`) || href.includes(browserConfig.blankTarget)))
      );
      
      //  Open ALL links in new tabs
      // Check if this is a navigable link
      const isNavigableLink = tagName === 'a' && href && 
        !href.startsWith(browserConfig.anchorOnly) &&  // Not an anchor link
        !href.startsWith(browserConfig.javascriptVoidPrefix) && // Not a void javascript
        href !== browserConfig.javascriptVoidEmpty && // Not empty javascript
        href !== browserConfig.anchorOnly; // Not just #
      
      const shouldOpenNewTab = naturallyOpensNewTab || isNavigableLink;
      
      
      if (shouldOpenNewTab) {
        //  Handle new tab opening
        
        // If it's a link that doesn't naturally open in new tab, force it
        if (isNavigableLink && !naturallyOpensNewTab) {
          await element.evaluate((el, blankTarget) => {
            if (el.tagName.toLowerCase() === 'a') {
              el.setAttribute('target', blankTarget);
            }
          }, browserConfig.blankTarget);
        }
        
        // Set up popup listener before clicking
        const popupPromise = page.context().waitForEvent('page', { timeout: browserConfig.popupTimeout });
        
        // Click with force to avoid scrolling issues
        await element.click({ force: browserConfig.forceClick });
        
        try {
          // Wait for new page to open
          const newPage = await popupPromise;
          
          // Generate tab ID for the new page
          const newTabId = this.generateTabId();
          this.registerNewPage(newTabId, newPage);
          
          // Set up page properties
          const browserConfig = this.configLoader.getBrowserConfig();
          newPage.setDefaultNavigationTimeout(browserConfig.navigationTimeout);
          newPage.setDefaultTimeout(browserConfig.navigationTimeout);
          
          
          //  Automatically switch to the new tab
          this.currentTabId = newTabId;
          await newPage.bringToFront();
          
          // Wait for new page to be ready
          await newPage.waitForLoadState('domcontentloaded', { timeout: browserConfig.popupTimeout }).catch(() => {});
          
          return { success: true, method: 'playwright-aria-ref-newtab', newTabId };
        } catch (popupError) {
          return { success: true, method: 'playwright-aria-ref' };
        }
      } else {
        //  Add options to prevent scrolling issues
        try {
          // First try normal click
          const browserConfig = this.configLoader.getBrowserConfig();
          await element.click({ timeout: browserConfig.clickTimeout });
        } catch (clickError) {
          // If normal click fails due to scrolling, try force click
          await element.click({ force: browserConfig.forceClick });
        }
        
        return { success: true, method: 'playwright-aria-ref' };
      }
      
    } catch (error) {
      console.error('[performClick] Exception during click for ref: %s', ref, error);
      return { success: false, error: `Click failed with exception: ${error}` };
    }
  }

  /**
   *  Simplified type implementation using Playwright's aria-ref selector
   */
  private async performType(page: Page, ref: string, text: string): Promise<{ success: boolean; error?: string }> {
    try {
      // Ensure we have the latest snapshot
      await (page as any)._snapshotForAI();
      
      // Use Playwright's aria-ref selector
      const selector = `aria-ref=${ref}`;
      const element = await page.locator(selector).first();
      
      const exists = await element.count() > 0;
      if (!exists) {
        return { success: false, error: `Element with ref ${ref} not found` };
      }
      
      // Type text using Playwright's built-in fill method
      await element.fill(text);
      
      return { success: true };
    } catch (error) {
      return { success: false, error: `Type failed: ${error}` };
    }
  }

  /**
   *  Simplified select implementation using Playwright's aria-ref selector
   */
  private async performSelect(page: Page, ref: string, value: string): Promise<{ success: boolean; error?: string }> {
    try {
      // Ensure we have the latest snapshot
      await (page as any)._snapshotForAI();
      
      // Use Playwright's aria-ref selector
      const selector = `aria-ref=${ref}`;
      const element = await page.locator(selector).first();
      
      const exists = await element.count() > 0;
      if (!exists) {
        return { success: false, error: `Element with ref ${ref} not found` };
      }
      
      // Select value using Playwright's built-in selectOption method
      await element.selectOption(value);
      
      return { success: true };
    } catch (error) {
      return { success: false, error: `Select failed: ${error}` };
    }
  }

  /**
   *  Simplified mouse control implementation
   */
  private async performMouseControl(page: Page, control: string, x: number, y: number): Promise<{ success: boolean; error?: string }> {
    try {
      const viewport = page.viewportSize();
      if (!viewport) {
        return { success: false, error: 'Viewport size not available from page.' };
      }
      if (x < 0 || y < 0 || x > viewport.width || y > viewport.height) {
        return { success: false, error: `Invalid coordinates, outside viewport bounds: (${x}, ${y})` };
      }
      switch (control) {
        case 'click': {
          await page.mouse.click(x, y);
          break;
        }
        case 'right_click': {
          await page.mouse.click(x, y, { button: 'right' });
          break;
        }
        case 'dblclick': {
          await page.mouse.dblclick(x, y);
          break;
        }
        default:
          return { success: false, error: `Invalid control action: ${control}` };
      }
      
      return { success: true };
    } catch (error) {
      return { success: false, error: `Mouse action failed: ${error}` };
    }
  }

  /**
   *  Enhanced mouse drag and drop implementation using ref IDs
   */
  private async performMouseDrag(page: Page, fromRef: string, toRef: string): Promise<{ success: boolean; error?: string }> {
    try {
      // Ensure we have the latest snapshot
      await (page as any)._snapshotForAI();
      
      // Get elements using Playwright's aria-ref selector
      const fromSelector = `aria-ref=${fromRef}`;
      const toSelector = `aria-ref=${toRef}`;
      
      const fromElement = await page.locator(fromSelector).first();
      const toElement = await page.locator(toSelector).first();
      
      // Check if elements exist
      const fromExists = await fromElement.count() > 0;
      const toExists = await toElement.count() > 0;
      
      if (!fromExists) {
        return { success: false, error: `Source element with ref ${fromRef} not found` };
      }
      
      if (!toExists) {
        return { success: false, error: `Target element with ref ${toRef} not found` };
      }
      
      // Get the center coordinates of both elements
      const fromBox = await fromElement.boundingBox();
      const toBox = await toElement.boundingBox();
      
      if (!fromBox) {
        return { success: false, error: `Could not get bounding box for source element with ref ${fromRef}` };
      }
      
      if (!toBox) {
        return { success: false, error: `Could not get bounding box for target element with ref ${toRef}` };
      }
      
      const fromX = fromBox.x + fromBox.width / 2;
      const fromY = fromBox.y + fromBox.height / 2;
      const toX = toBox.x + toBox.width / 2;
      const toY = toBox.y + toBox.height / 2;

      // Perform the drag operation
      await page.mouse.move(fromX, fromY);
      await page.mouse.down();
      // Destination coordinates
      await page.mouse.move(toX, toY);
      await page.mouse.up();

      return { success: true };
    } catch (error) {
      return { success: false, error: `Mouse drag action failed: ${error}` };
    }
  }

  async executeAction(action: BrowserAction): Promise<ActionResult> {
    const startTime = Date.now();
    const page = await this.getCurrentPage();
    
    let elementSearchTime = 0;
    let actionExecutionTime = 0;
    let stabilityWaitTime = 0;
    
    try {
      const elementSearchStart = Date.now();
      
      //  No need to pre-fetch snapshot - each action method handles this
      
      let newTabId: string | undefined;
      
      switch (action.type) {
        case 'click': {
          elementSearchTime = Date.now() - elementSearchStart;
          const clickStart = Date.now();
          
          //  Use simplified click logic
          const clickResult = await this.performClick(page, action.ref);
          
          if (!clickResult.success) {
            throw new Error(`Click failed: ${clickResult.error}`);
          }
          
          //  Capture new tab ID if present
          newTabId = clickResult.newTabId;
          
          actionExecutionTime = Date.now() - clickStart;
          break;
        }
          
        case 'type': {
          elementSearchTime = Date.now() - elementSearchStart;
          const typeStart = Date.now();

          const typeResult = await this.performType(page, action.ref, action.text);
          
          if (!typeResult.success) {
            throw new Error(`Type failed: ${typeResult.error}`);
          }
          
          actionExecutionTime = Date.now() - typeStart;
          break;
        }
          
        case 'select': {
          elementSearchTime = Date.now() - elementSearchStart;
          const selectStart = Date.now();
          
          const selectResult = await this.performSelect(page, action.ref, action.value);

          if (!selectResult.success) {
            throw new Error(`Select failed: ${selectResult.error}`);
          }
          
          actionExecutionTime = Date.now() - selectStart;
          break;
        }
          
        case 'scroll': {
          elementSearchTime = Date.now() - elementSearchStart;
          const scrollStart = Date.now();
          const scrollAmount = action.direction === 'up' ? -action.amount : action.amount;
          await page.evaluate((amount: number) => {
            window.scrollBy(0, amount);
          }, scrollAmount);
          // Update scroll position tracking
          await this.getCurrentScrollPosition();
          actionExecutionTime = Date.now() - scrollStart;
          break;
        }
          
        case 'enter': {
          elementSearchTime = Date.now() - elementSearchStart;
          const enterStart = Date.now();
          const browserConfig = this.configLoader.getBrowserConfig();
          await page.keyboard.press(browserConfig.enterKey);
          actionExecutionTime = Date.now() - enterStart;
          break;
        }

        case 'mouse_control': {
          elementSearchTime = Date.now() - elementSearchStart;
          const mouseControlStart = Date.now();
          const mouseControlResult = await this.performMouseControl(page, action.control, action.x, action.y);

          if (!mouseControlResult.success) {
            throw new Error(`Action failed: ${mouseControlResult.error}`);
          }
          actionExecutionTime = Date.now() - mouseControlStart;
          break;
        }

        case 'mouse_drag': {
          elementSearchTime = Date.now() - elementSearchStart;
          const mouseDragStart = Date.now();
          const mouseDragResult = await this.performMouseDrag(page, action.from_ref, action.to_ref);

          if (!mouseDragResult.success) {
            throw new Error(`Action failed: ${mouseDragResult.error}`);
          }
          actionExecutionTime = Date.now() - mouseDragStart;
          break;
        }

        case 'press_key': {
          elementSearchTime = Date.now() - elementSearchStart;
          const keyPressStart = Date.now();
          // concatenate keys with '+' for key combinations
          const keys = action.keys.join('+');
          await page.keyboard.press(keys);
          actionExecutionTime = Date.now() - keyPressStart;
          break;
        }
          
        default:
          throw new Error(`Unknown action type: ${(action as any).type}`);
      }

      // Wait for stability after action
      const stabilityStart = Date.now();
      const stabilityResult = await this.waitForPageStability(page);
      stabilityWaitTime = Date.now() - stabilityStart;
      
      const totalTime = Date.now() - startTime;
      
      return {
        success: true,
        message: `Action ${action.type} executed successfully`,
        timing: {
          total_time_ms: totalTime,
          element_search_time_ms: elementSearchTime,
          action_execution_time_ms: actionExecutionTime,
          stability_wait_time_ms: stabilityWaitTime,
          dom_content_loaded_time_ms: stabilityResult.domContentLoadedTime,
          network_idle_time_ms: stabilityResult.networkIdleTime,
        },
        ...(newTabId && { newTabId }), //  Include new tab ID if present
      };
    } catch (error) {
      const totalTime = Date.now() - startTime;
      return {
        success: false,
        message: `Action ${action.type} failed: ${error}`,
        timing: {
          total_time_ms: totalTime,
          element_search_time_ms: elementSearchTime,
          action_execution_time_ms: actionExecutionTime,
          stability_wait_time_ms: stabilityWaitTime,
        },
      };
    }
  }

  private async waitForPageStability(page: Page): Promise<{ domContentLoadedTime: number; networkIdleTime: number }> {
    let domContentLoadedTime = 0;
    let networkIdleTime = 0;
    
    try {
      const domStart = Date.now();
      const browserConfig = this.configLoader.getBrowserConfig();
      await page.waitForLoadState(browserConfig.domContentLoadedState as any, { timeout: browserConfig.pageStabilityTimeout });
      domContentLoadedTime = Date.now() - domStart;
      
      const networkStart = Date.now();
      await page.waitForLoadState(browserConfig.networkIdleState as any, { timeout: browserConfig.networkIdleTimeout });
      networkIdleTime = Date.now() - networkStart;
    } catch (error) {
      // Continue even if stability wait fails
    }
    
    return { domContentLoadedTime, networkIdleTime };
  }

  async visitPage(url: string): Promise<ActionResult & { newTabId?: string }> {
    const startTime = Date.now();
    
    try {
      // Get current page to check if it's blank
      const currentPage = await this.getCurrentPage();
      const currentUrl = currentPage.url();
      
      //  Check if current page is blank or if this is the first navigation
      const browserConfig = this.configLoader.getBrowserConfig();
      const isBlankPage = (
        browserConfig.blankPageUrls.includes(currentUrl) ||
        currentUrl === browserConfig.defaultStartUrl ||
        currentUrl.startsWith(browserConfig.dataUrlPrefix) // data URLs are often used for blank pages
      );
      
      const shouldUseCurrentTab = isBlankPage || !this.hasNavigatedBefore;
      
      
      if (shouldUseCurrentTab) {
        // Navigate in current tab if it's blank
        
        const navigationStart = Date.now();
        const browserConfig = this.configLoader.getBrowserConfig();
        await currentPage.goto(url, { 
          timeout: browserConfig.navigationTimeout,
          waitUntil: browserConfig.domContentLoadedState as any
        });
        
        // Reset scroll position after navigation
        this.scrollPosition = { x: 0, y: 0 };
        
        //  Mark that we've navigated
        this.hasNavigatedBefore = true;
        
        const navigationTime = Date.now() - navigationStart;
        const stabilityResult = await this.waitForPageStability(currentPage);
        const totalTime = Date.now() - startTime;
        
        return {
          success: true,
          message: `Navigated to ${url}`,
          timing: {
            total_time_ms: totalTime,
            navigation_time_ms: navigationTime,
            dom_content_loaded_time_ms: stabilityResult.domContentLoadedTime,
            network_idle_time_ms: stabilityResult.networkIdleTime,
          },
        };
      } else {
        //  Open in new tab if current page has content
        if (!this.context) {
          throw new Error('Browser context not initialized');
        }
        
        const navigationStart = Date.now();
        
        // In CDP mode, find an available blank tab instead of creating new page
        let newPage: Page | null = null;
        let newTabId: string | null = null;
        
        const browserConfig = this.configLoader.getBrowserConfig();
        if (browserConfig.connectOverCdp) {
          // CDP mode: find an available blank tab
          const allPages = this.context.pages();
          for (const page of allPages) {
            const pageUrl = page.url();
            // Check if this page is not already tracked and is blank
            const isTracked = Array.from(this.pages.values()).includes(page);
            if (!isTracked && pageUrl === 'about:blank') {
              newPage = page;
              newTabId = this.generateTabId();
              this.registerNewPage(newTabId, newPage);
              break;
            }
          }
          
          if (!newPage || !newTabId) {
            throw new Error('No available blank tabs in CDP mode. Frontend should create more blank tabs when half are used.');
          }
        } else {
          // Non-CDP mode: create new page as usual
          newPage = await this.context.newPage();
          newTabId = this.generateTabId();
          this.registerNewPage(newTabId, newPage);
        }
        
        // Set up page properties
        newPage.setDefaultNavigationTimeout(browserConfig.navigationTimeout);
        newPage.setDefaultTimeout(browserConfig.navigationTimeout);
        
        // Navigate to the URL
        await newPage.goto(url, { 
          timeout: browserConfig.navigationTimeout,
          waitUntil: browserConfig.domContentLoadedState as any
        });
        
        //  Automatically switch to the new tab
        this.currentTabId = newTabId;
        await newPage.bringToFront();
        
        // Reset scroll position for the new page
        this.scrollPosition = { x: 0, y: 0 };
        
        //  Mark that we've navigated
        this.hasNavigatedBefore = true;
        
        const navigationTime = Date.now() - navigationStart;
        const stabilityResult = await this.waitForPageStability(newPage);
        const totalTime = Date.now() - startTime;
        
        return {
          success: true,
          message: `Opened ${url} in new tab`,
          newTabId: newTabId, //  Include the new tab ID
          timing: {
            total_time_ms: totalTime,
            navigation_time_ms: navigationTime,
            dom_content_loaded_time_ms: stabilityResult.domContentLoadedTime,
            network_idle_time_ms: stabilityResult.networkIdleTime,
          },
        };
      }
    } catch (error) {
      const totalTime = Date.now() - startTime;
      return {
        success: false,
        message: `Navigation to ${url} failed: ${error}`,
        timing: {
          total_time_ms: totalTime,
          navigation_time_ms: 0,
          dom_content_loaded_time_ms: 0,
          network_idle_time_ms: 0,
        },
      };
    }
  }

  async switchToTab(tabId: string): Promise<boolean> {
    if (!this.pages.has(tabId)) {
      return false;
    }
    
    const page = this.pages.get(tabId)!;
    
    if (page.isClosed()) {
      this.pages.delete(tabId);
      return false;
    }
    
    try {
      console.log(`Switching to tab ${tabId}`);
      
      // Update internal state first
      this.currentTabId = tabId;
      
      // Try to activate the tab using a gentler approach
      // Instead of bringToFront, we'll use a combination of methods
      try {
        // Method 1: Evaluate focus in the page context
        await page.evaluate(() => {
          // Focus the window
          window.focus();
          // Dispatch a focus event
          window.dispatchEvent(new Event('focus'));
        }).catch(() => {});
        
        // Method 2: For non-headless mode, schedule bringToFront asynchronously
        // This prevents WebSocket disruption by not blocking the current operation
        if (!this.configLoader.getBrowserConfig().headless) {
          // Use Promise to handle async operation without await
          Promise.resolve().then(async () => {
            // Small delay to ensure WebSocket message is processed
            const browserConfig = this.configLoader.getBrowserConfig();
            await new Promise(resolve => setTimeout(resolve, browserConfig.navigationDelay));
            try {
              await page.bringToFront();
            } catch (e) {
              // Silently ignore - tab switching still works internally
              console.debug(`bringToFront failed for ${tabId}, but tab is switched internally`);
            }
          });
        }
      } catch (error) {
        // Log but don't fail - internal state is still updated
        console.warn(`Tab focus warning for ${tabId}:`, error);
      }
      
      console.log(`Successfully switched to tab ${tabId}`);
      return true;
    } catch (error) {
      console.error(`Error switching to tab ${tabId}:`, error);
      return false;
    }
  }

  async closeTab(tabId: string): Promise<boolean> {
    if (!this.pages.has(tabId)) {
      return false;
    }
    
    const page = this.pages.get(tabId)!;
    
    if (!page.isClosed()) {
      await page.close();
    }
    
    this.pages.delete(tabId);
    
    if (tabId === this.currentTabId) {
      const remainingTabs = Array.from(this.pages.keys());
      if (remainingTabs.length > 0) {
        this.currentTabId = remainingTabs[0];
      } else {
        this.currentTabId = null;
      }
    }
    
    return true;
  }

  async getTabInfo(): Promise<TabInfo[]> {
    const tabInfo: TabInfo[] = [];
    
    for (const [tabId, page] of this.pages) {
      if (!page.isClosed()) {
        try {
          const title = await page.title();
          const url = page.url();
          
          tabInfo.push({
            tab_id: tabId,
            title,
            url,
            is_current: tabId === this.currentTabId,
          });
        } catch (error) {
          // Skip tabs that can't be accessed
        }
      }
    }
    
    return tabInfo;
  }

  async takeScreenshot(): Promise<{ buffer: Buffer; timing: { screenshot_time_ms: number } }> {
    const startTime = Date.now();
    const page = await this.getCurrentPage();
    
    const browserConfig = this.configLoader.getBrowserConfig();
    const buffer = await page.screenshot({ 
      timeout: browserConfig.screenshotTimeout,
      fullPage: browserConfig.fullPageScreenshot
    });
    
    const screenshotTime = Date.now() - startTime;
    
    return {
      buffer,
      timing: {
        screenshot_time_ms: screenshotTime,
      },
    };
  }

  async close(): Promise<void> {
    const browserConfig = this.configLoader.getBrowserConfig();
    
    for (const page of this.pages.values()) {
      if (!page.isClosed()) {
        await page.close();
      }
    }
    
    this.pages.clear();
    this.currentTabId = null;
    
    if (this.context) {
      await this.context.close();
      this.context = null;
    }
    
    if (this.browser) {
      if (browserConfig.connectOverCdp) {
        // For CDP connections, just disconnect without closing the browser
        await this.browser.close();
      } else {
        // For launched browsers, close completely
        await this.browser.close();
      }
      this.browser = null;
    }
  }

  private filterElementsInViewport(
    elements: Record<string, SnapshotElement>, 
    viewport: { width: number, height: number }, 
    scrollPos: { x: number, y: number }
  ): Record<string, SnapshotElement> {
    const filtered: Record<string, SnapshotElement> = {};
    
    
    // Apply viewport filtering with scroll position adjustment
    const browserConfig = this.configLoader.getBrowserConfig();
    const adjustedScrollPos = {
      x: scrollPos.x * browserConfig.scrollPositionScale,
      y: scrollPos.y * browserConfig.scrollPositionScale
    };
    
    for (const [ref, element] of Object.entries(elements)) {
      // If element has no coordinates, include it (fallback)
      if (!element.coordinates) {
        filtered[ref] = element;
        continue;
      }
      
      const { x, y, width, height } = element.coordinates;
      
      // Calculate viewport bounds using adjusted scroll position
      const viewportLeft = adjustedScrollPos.x;
      const viewportTop = adjustedScrollPos.y;
      const viewportRight = adjustedScrollPos.x + viewport.width;
      const viewportBottom = adjustedScrollPos.y + viewport.height;
      
      // Check if element is visible in current viewport
      // Element is visible if it overlaps with viewport bounds
      const isVisible = (
        x < viewportRight &&              // Left edge is before viewport right
        y < viewportBottom &&             // Top edge is before viewport bottom  
        x + width > viewportLeft &&       // Right edge is after viewport left
        y + height > viewportTop          // Bottom edge is after viewport top
      );
      
      if (isVisible) {
        filtered[ref] = element;
      }
    }
    
    return filtered;
  }

  private rebuildSnapshotText(originalSnapshot: string, filteredElements: Record<string, SnapshotElement>): string {
    const lines = originalSnapshot.split('\n');
    const filteredLines: string[] = [];
    
    for (const line of lines) {
      const refMatch = line.match(/\[ref=([^\]]+)\]/);
      
      if (refMatch) {
        const ref = refMatch[1];
        // Only include lines for elements that passed viewport filtering
        if (filteredElements[ref]) {
          filteredLines.push(line);
        }
      } else {
        // Include non-element lines (headers, etc.)
        filteredLines.push(line);
      }
    }
    
    return filteredLines.join('\n');
  }

}