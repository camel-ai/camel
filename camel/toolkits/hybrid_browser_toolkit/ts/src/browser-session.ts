import { Page, Browser, BrowserContext, chromium, ConsoleMessage, Frame } from 'playwright';
import { BrowserToolkitConfig, SnapshotResult, SnapshotElement, ActionResult, TabInfo, BrowserAction, DetailedTiming, PageStabilityResult, INTERACTIVE_ROLES, NearestElementInfo } from './types';
import { ConfigLoader, StealthConfig } from './config-loader';

// Constants for loading element detection
// Using word boundary patterns to avoid false positives like "unloading" or "windspinner"
const LOADING_CLASS_PATTERNS = [
  /\bloading\b/i,    // matches "loading", "is-loading", "loading-spinner" but not "unloading"
  /\bloader\b/i,     // matches "loader", "page-loader" but not "preloader" (intentionally excluded)
  /\bspinner\b/i,    // matches "spinner", "loading-spinner" but not "windspinner"
  /\bspin\b/i,       // matches "spin", "spin-animation"
];

// CSS selector for querying loading elements - matches common loading class patterns
const LOADING_ELEMENTS_SELECTOR = [
  '[class*="loading"]:not([class*="unloading"]):not([class*="loaded"])',
  '[class*="loader"]',
  '[class*="spinner"]',
  '[class*="spin"]:not([class*="spinach"])', // avoid false positives
].join(', ');

// Note message for loading state warning
const LOADING_STATE_NOTE = 'Loading-related elements were detected on this page. The page may still be in a loading or transitional state. The current snapshot may not reflect the final state.';

export class HybridBrowserSession {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private contextOwnedByUs: boolean = false;
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

  /**
   * Compatibility wrapper for _snapshotForAI() API
   * Handles both old (string return) and new (object with .full) versions
   */
  private async getSnapshot(page: Page): Promise<string> {
    const result = await (page as any)._snapshotForAI();
    // Version compatibility: if result is object (v1.57.0+), use .full property
    // If result is string (v1.56.x and earlier), return directly
    return typeof result === 'string' ? result : result.full;
  }

  /**
   * Parse frame prefix from ref (e.g., "f1e5" -> { frameIndex: 1, localRef: "e5" })
   * Refs without frame prefix (e.g., "e5") return frameIndex: 0
   */
  private parseFrameRef(ref: string): { frameIndex: number; localRef: string } {
    const frameMatch = ref.match(/^f(\d+)(e.*)$/);
    if (frameMatch) {
      return {
        frameIndex: parseInt(frameMatch[1], 10),
        localRef: frameMatch[2]
      };
    }
    return { frameIndex: 0, localRef: ref };
  }

  /**
   * Try to find element in a specific frame with given selector
   */
  private async tryFindInFrame(
    frame: Frame,
    selector: string
  ): Promise<ReturnType<Frame['locator']> | null> {
    try {
      const element = frame.locator(selector).first();
      if (await element.count() > 0) {
        return element;
      }
    } catch {
      // Frame might be detached or selector invalid
    }
    return null;
  }

  /**
   * Find element across frames with optimized search strategy
   * Search order: 1) Target frame with localRef, 2) All frames with full ref
   */
  private async findElementAcrossFrames(
    page: Page,
    ref: string
  ): Promise<{ locator: ReturnType<Frame['locator']>; frame: Frame } | null> {
    const allFrames = page.frames();
    const { frameIndex, localRef } = this.parseFrameRef(ref);

    // Strategy 1: If ref has frame prefix, try target frame with localRef
    if (frameIndex > 0 && frameIndex < allFrames.length) {
      const targetFrame = allFrames[frameIndex];
      const element = await this.tryFindInFrame(targetFrame, `aria-ref=${localRef}`);
      if (element) {
        return { locator: element, frame: targetFrame };
      }
    }

    // Strategy 2: Search all frames with full ref
    for (const frame of allFrames) {
      const element = await this.tryFindInFrame(frame, `aria-ref=${ref}`);
      if (element) {
        return { locator: element, frame };
      }
    }

    return null;
  }

  /**
   * Get element coordinates from boundingBox
   */
  private async getElementCoordinates(
    element: ReturnType<Frame['locator']>
  ): Promise<{ x: number; y: number; width: number; height: number } | null> {
    const box = await element.boundingBox();
    if (!box) return null;
    return {
      x: Math.round(box.x),
      y: Math.round(box.y),
      width: Math.round(box.width),
      height: Math.round(box.height)
    };
  }

  /**
   * Calculate distance from point to element center
   */
  private distanceToElement(
    x: number,
    y: number,
    coords: { x: number; y: number; width: number; height: number }
  ): number {
    const centerX = coords.x + coords.width / 2;
    const centerY = coords.y + coords.height / 2;
    return Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
  }

  /**
   * Find N nearest interactive elements to a given point
   * Returns elements with clickable center coordinates and aria info
   */
  private findNearestElements(
    elements: Record<string, any>,
    snapshot: string,
    x: number,
    y: number,
    count: number = 5
  ): NearestElementInfo[] {
    // Parse aria-label/name from snapshot text
    const elementNames = this.parseElementNamesFromSnapshot(snapshot);

    const elementsWithDistance: NearestElementInfo[] = [];

    for (const [ref, element] of Object.entries(elements)) {
      if (!element.coordinates) continue;

      const role = element.role || 'unknown';
      if (!INTERACTIVE_ROLES.has(role)) continue;

      const coords = element.coordinates;
      elementsWithDistance.push({
        ref,
        role,
        name: elementNames.get(ref) || '',
        distance: Math.round(this.distanceToElement(x, y, coords)),
        clickableCoord: {
          x: Math.round(coords.x + coords.width / 2),
          y: Math.round(coords.y + coords.height / 2)
        },
        boundingBox: coords
      });
    }

    return elementsWithDistance
      .sort((a, b) => a.distance - b.distance)
      .slice(0, count);
  }

  /**
   * Parse element names/labels from snapshot text
   */
  private parseElementNamesFromSnapshot(snapshot: string): Map<string, string> {
    const elementNames = new Map<string, string>();
    for (const line of snapshot.split('\n')) {
      const refMatch = line.match(/\[ref=([^\]]+)\]/);
      if (refMatch) {
        const nameMatch = line.match(/-\s+\w+\s+"([^"]+)"/);
        if (nameMatch) {
          elementNames.set(refMatch[1], nameMatch[1]);
        }
      }
    }
    return elementNames;
  }

  /**
   * Format nearest elements as readable text for LLM
   */
  private formatNearestElementsMessage(
    clickX: number,
    clickY: number,
    nearestElements: NearestElementInfo[]
  ): string {
    const lines: string[] = [
      `Click at (${clickX}, ${clickY}) may be ineffective - page content unchanged.`,
      `Nearest interactive elements:`
    ];

    for (let i = 0; i < nearestElements.length; i++) {
      const el = nearestElements[i];
      const nameStr = el.name ? ` "${el.name}"` : '';
      const box = el.boundingBox;
      lines.push(
        `  ${i + 1}. [${el.role}]${nameStr} - click at (${el.clickableCoord.x}, ${el.clickableCoord.y}), ` +
        `area: (${box.x}, ${box.y}) to (${box.x + box.width}, ${box.y + box.height})`
      );
    }

    return lines.join('\n');
  }

  /**
   * Check if a point is within a canvas element
   */
  private async isPointOnCanvas(page: Page, x: number, y: number): Promise<boolean> {
    return await page.evaluate(({ x, y }) => {
      const element = document.elementFromPoint(x, y);
      if (!element) return false;
      // Check if element is canvas or inside canvas
      return element.tagName.toUpperCase() === 'CANVAS' ||
             element.closest('canvas') !== null;
    }, { x, y });
  }

  /**
   * Compare two snapshots to detect if page changed
   * Returns true if snapshots are meaningfully different
   */
  private snapshotsAreDifferent(before: string, after: string): boolean {
    // Normalize whitespace and compare
    const normalize = (s: string) => s.replace(/\s+/g, ' ').trim();
    return normalize(before) !== normalize(after);
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

    // Check if CDP URL is provided
    if (browserConfig.cdpUrl) {
      // Connect to existing browser via CDP
      this.browser = await chromium.connectOverCDP(browserConfig.cdpUrl);

      // Get existing contexts or create new one
      const contexts = this.browser.contexts();
      if (contexts.length > 0) {
        this.context = contexts[0];
        this.contextOwnedByUs = false;

        // Apply stealth headers to existing context if configured
        // Note: userAgent cannot be changed on an existing context
        if (stealthConfig.enabled) {
          if (stealthConfig.extraHTTPHeaders) {
            await this.context.setExtraHTTPHeaders(stealthConfig.extraHTTPHeaders);
          }
          if (stealthConfig.userAgent) {
            console.warn('[HybridBrowserSession] Cannot apply userAgent to existing context. Consider creating a new context if userAgent customization is required.');
          }
        }
      } else {
        const contextOptions: any = {
          viewport: browserConfig.viewport
        };

        // Apply stealth headers and UA if configured
        if (stealthConfig.enabled) {
          if (stealthConfig.extraHTTPHeaders) {
            contextOptions.extraHTTPHeaders = stealthConfig.extraHTTPHeaders;
          }
          if (stealthConfig.userAgent) {
            contextOptions.userAgent = stealthConfig.userAgent;
          }
        }

        this.context = await this.browser.newContext(contextOptions);
        this.contextOwnedByUs = true;
        this.browser = this.context.browser();
      }

      const pages = this.context.pages();
      console.log(`[CDP] cdpKeepCurrentPage: ${browserConfig.cdpKeepCurrentPage}, pages count: ${pages.length}`);
      if (browserConfig.cdpKeepCurrentPage) {
        // Use existing page without creating new ones
        if (pages.length > 0) {
          // Find first non-closed page
          let validPage: Page | null = null;
          for (const page of pages) {
            if (!page.isClosed()) {
              validPage = page;
              break;
            }
          }

          if (validPage) {
            const tabId = this.generateTabId();
            this.registerNewPage(tabId, validPage);
            this.currentTabId = tabId;
            console.log(`[CDP] cdpKeepCurrentPage mode: using existing page as initial tab: ${tabId}, URL: ${validPage.url()}`);
          } else {
            throw new Error('No active pages available in CDP mode with cdpKeepCurrentPage=true (all pages are closed)');
          }
        } else {
          throw new Error('No pages available in CDP mode with cdpKeepCurrentPage=true');
        }
      } else {
        // Look for blank pages or create new ones
        if (pages.length > 0) {
          // Find one available blank page
          let availablePageFound = false;
          for (const page of pages) {
            const pageUrl = page.url();
            if (this.isBlankPageUrl(pageUrl)) {
              const tabId = this.generateTabId();
              this.registerNewPage(tabId, page);
              this.currentTabId = tabId;
              availablePageFound = true;
              console.log(`[CDP] Registered blank page as initial tab: ${tabId}, URL: ${pageUrl}`);
              break;
            }
          }

          if (!availablePageFound) {
            console.log('[CDP] No blank pages found, creating new page');
            const newPage = await this.context.newPage();
            const tabId = this.generateTabId();
            this.registerNewPage(tabId, newPage);
            this.currentTabId = tabId;
          }
        } else {
          console.log('[CDP] No existing pages, creating initial page');
          const newPage = await this.context.newPage();
          const tabId = this.generateTabId();
          this.registerNewPage(tabId, newPage);
          this.currentTabId = tabId;
        }
      }
    } else {
      // Original launch logic
      const launchOptions: any = {
        headless: browserConfig.headless,
      };

      if (stealthConfig.enabled) {
        launchOptions.args = stealthConfig.args || [];

        // Apply stealth user agent/headers if configured
        if (stealthConfig.userAgent) {
          launchOptions.userAgent = stealthConfig.userAgent;
        }
        if (stealthConfig.extraHTTPHeaders) {
          launchOptions.extraHTTPHeaders = stealthConfig.extraHTTPHeaders;
        }
      }

      if (browserConfig.userDataDir) {
        // Ensure viewport is honored in persistent context
        launchOptions.viewport = browserConfig.viewport;
        this.context = await chromium.launchPersistentContext(
          browserConfig.userDataDir,
          launchOptions
        );
        this.contextOwnedByUs = true;
        this.browser = this.context.browser();
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

        // Apply stealth headers and UA if configured
        if (stealthConfig.enabled) {
          if (stealthConfig.extraHTTPHeaders) {
            contextOptions.extraHTTPHeaders = stealthConfig.extraHTTPHeaders;
          }
          if (stealthConfig.userAgent) {
            contextOptions.userAgent = stealthConfig.userAgent;
          }
        }

        this.context = await this.browser.newContext(contextOptions);
        this.contextOwnedByUs = true;

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

  private isBlankPageUrl(url: string): boolean {
    // Unified blank page detection logic used across the codebase
    const browserConfig = this.configLoader.getBrowserConfig();
    return (
      // Standard about:blank variations (prefix match for query params)
      url === 'about:blank' ||
      url.startsWith('about:blank?') ||
      // Configured blank page URLs (exact match for compatibility)
      browserConfig.blankPageUrls.includes(url) ||
      // Empty URL
      url === '' ||
      // Data URLs (often used for blank pages)
      url.startsWith(browserConfig.dataUrlPrefix || 'data:')
    );
  }

  async getCurrentPage(): Promise<Page> {
    if (!this.currentTabId || !this.pages.has(this.currentTabId)) {
      const browserConfig = this.configLoader.getBrowserConfig();

      // In CDP keep-current-page mode, find existing page
      if (browserConfig.cdpKeepCurrentPage && browserConfig.cdpUrl && this.context) {
        const allPages = this.context.pages();
        console.log(`[getCurrentPage] cdpKeepCurrentPage mode: Looking for existing page, found ${allPages.length} pages`);

        if (allPages.length > 0) {
          // Try to find a page that's not already tracked
          for (const page of allPages) {
            const isTracked = Array.from(this.pages.values()).includes(page);
            if (!isTracked && !page.isClosed()) {
              const tabId = this.generateTabId();
              this.registerNewPage(tabId, page);
              this.currentTabId = tabId;
              console.log(`[getCurrentPage] cdpKeepCurrentPage mode: Found and registered untracked page: ${tabId}`);
              return page;
            }
          }

          // If all pages are tracked, use the first available one
          const firstPage = allPages[0];
          if (!firstPage.isClosed()) {
            // Find the tab ID for this page
            for (const [tabId, page] of this.pages.entries()) {
              if (page === firstPage) {
                this.currentTabId = tabId;
                console.log(`[getCurrentPage] cdpKeepCurrentPage mode: Using existing tracked page: ${tabId}`);
                return page;
              }
            }
          }
        }

        throw new Error('No active page available in CDP mode with cdpKeepCurrentPage=true');
      }

      // Normal mode: create new page
      if (this.context) {
        console.log('[getCurrentPage] No active page, creating new page');
        const newPage = await this.context.newPage();
        const tabId = this.generateTabId();
        this.registerNewPage(tabId, newPage);
        this.currentTabId = tabId;

        newPage.setDefaultNavigationTimeout(browserConfig.navigationTimeout);
        newPage.setDefaultTimeout(browserConfig.navigationTimeout);

        return newPage;
      }
      throw new Error('No browser context available');
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


  private buildSnapshotIndex(snapshotText: string): Map<string, string|undefined> {
    // Get ref to role mapping from snapshot text
    const index = new Map<string, string|undefined>();
    const refRe = /\[ref=([^\]]+)\]/i;
    for (const line of snapshotText.split('\n')) {
      const m = line.match(refRe);
      if (!m) continue;
      const ref = m[1];
      const roleMatch = line.match(/^\s*-?\s*([a-z0-9_-]+)/i);
      const role = roleMatch ? roleMatch[1].toLowerCase() : undefined;
      index.set(ref, role);
    }
    return index;
  }


  private filterElementsInViewport(
    elements: Record<string, SnapshotElement>,
    viewport: { width: number, height: number },
    scrollPos: { x: number, y: number }
  ): Record<string, SnapshotElement> {
    const filtered: Record<string, SnapshotElement> = {};
    // Apply viewport filtering
    // boundingBox() returns viewport-relative coordinates, so we don't need to add scroll offsets
    const viewportLeft = 0;
    const viewportTop = 0;
    const viewportRight = viewport.width;
    const viewportBottom = viewport.height;

    for (const [ref, element] of Object.entries(elements)) {
      // If element has no coordinates, include it (fallback)
      if (!element.coordinates) {
        filtered[ref] = element;
        continue;
      }

      const { x, y, width, height } = element.coordinates;

      // Check if element is visible in current viewport
      // Element is visible if it overlaps with viewport bounds
      // Since boundingBox() coords are viewport-relative, we compare directly
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


  private filterSnapshotLines(
    lines: string[],
    viewportRefs: Set<string>,
    tabSize: number = 2
  ): string[] {
    // Filter snapshot lines to include only those in viewportRefs
    // and their context
    const levelStack: number[] = [];
    const filteredLines: string[] = [];
    for (const line of lines) {
      const refMatch = line.match(/\[ref=([^\]]+)\]/);
      const indentMatch = line.match(/^(\s*)/);
      const level = indentMatch ? indentMatch[1].length / tabSize : 0;
      const prevLevel = levelStack[levelStack.length - 1] ?? 0;
      const levelDiff = level - prevLevel;
      // Pop stack when going up to the parent level
      if (levelDiff <= 0) {
        while (
          levelStack.length > 0 &&
          levelStack[levelStack.length - 1] >= level
        ) {
          levelStack.pop();
        }
      }
      // Line has a ref
      if (refMatch && viewportRefs.has(refMatch[1])) {
        levelStack.push(level);
        filteredLines.push(line);
        continue;
      }
      // Line without ref - include if it's a header or direct child of tracked element
      if (!refMatch && (levelDiff === 0 || levelDiff === 1)) {
        filteredLines.push(line);
      }
    }
    return filteredLines;
  }

  private rebuildSnapshotText(
    originalSnapshot: string,
    filteredElements: Record<string, SnapshotElement>): string {
    const lines = originalSnapshot.split('\n');
    const filteredLines = this.filterSnapshotLines(lines, new Set(Object.keys(filteredElements)));
    const filteredContent = filteredLines.join('\n');
    return filteredContent;
  }


  private async getSnapshotForAINative(includeCoordinates = false, viewportLimit = false): Promise<SnapshotResult & { timing: DetailedTiming }> {
    const startTime = Date.now();
    const page = await this.getCurrentPage();

    try {
      //  Use _snapshotForAI() to properly update _lastAriaSnapshot
      const snapshotStart = Date.now();
      const snapshotText = await this.getSnapshot(page);
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

      // Parse element info in a single pass
      const snapshotIndex = this.buildSnapshotIndex(snapshotText);
      for (const ref of refs) {
        const role = snapshotIndex.get(ref) || undefined;
        playwrightMapping[ref] = {
          ref,
          role: role || 'unknown',
        };
      }

      if (includeCoordinates) {
        // Enrich elements with coordinates using parallel processing
        // Process in batches to avoid overwhelming the browser
        const BATCH_SIZE = 10;
        for (let i = 0; i < refs.length; i += BATCH_SIZE) {
          const batch = refs.slice(i, i + BATCH_SIZE);
          await Promise.all(batch.map(async (ref) => {
            const result = await this.findElementAcrossFrames(page, ref);
            if (result) {
              const coords = await this.getElementCoordinates(result.locator);
              if (coords) {
                const { frameIndex } = this.parseFrameRef(ref);
                playwrightMapping[ref] = {
                  ...playwrightMapping[ref],
                  coordinates: coords,
                  frameIndex,
                  frameUrl: frameIndex > 0 ? result.frame.url() : undefined
                };
              }
            }
          }));
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
  private async performClick(page: Page, ref: string): Promise<{ success: boolean; method?: string; error?: string; newTabId?: string; diffSnapshot?: string; dialogMessage?: string }> {
    // Track dialog (alert/confirm/prompt) that may appear during click
    let dialogMessage: string | undefined;

    const dialogHandler = (dialog: any) => {
      dialogMessage = dialog.message();
      // Auto-accept the dialog to prevent blocking
      dialog.accept().catch(() => {});
    };

    // Set up dialog handler before clicking
    page.on('dialog', dialogHandler);

    try {
      //  Ensure we have the latest snapshot and mapping
      await this.getSnapshot(page);

      //  Use findElementAcrossFrames to support elements inside iframes
      const result = await this.findElementAcrossFrames(page, ref);

      if (!result) {
        page.off('dialog', dialogHandler);
        return { success: false, error: `Element with ref ${ref} not found in any frame` };
      }

      const element = result.locator;
      const role = await element.getAttribute('role');
      const elementTagName = await element.evaluate(el => el.tagName.toLowerCase());
      const isCombobox = role === 'combobox' || elementTagName === 'combobox';
      const isTextbox = role === 'textbox' || elementTagName === 'input' || elementTagName === 'textarea';
      const shouldCheckDiff = isCombobox || isTextbox;

      let snapshotBefore: string | null = null;
      let comboboxAriaLabel: string | null = null;
      if (shouldCheckDiff) {
        snapshotBefore = await this.getSnapshot(page);
        // Capture aria-label for combobox to find it again after click (ref may change)
        if (isCombobox) {
          comboboxAriaLabel = await element.getAttribute('aria-label');
          if (!comboboxAriaLabel) {
            // Try to get accessible name from aria-labelledby or inner text
            comboboxAriaLabel = await element.evaluate(el => {
              const labelledBy = el.getAttribute('aria-labelledby');
              if (labelledBy) {
                const labelEl = document.getElementById(labelledBy);
                if (labelEl) return labelEl.textContent?.trim() || null;
              }
              return el.textContent?.trim() || null;
            });
          }
        }
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

      // Only open new tab if element naturally opens one (has target="_blank" or window.open)
      // Do NOT force all links to open in new tabs
      if (naturallyOpensNewTab) {
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

          page.off('dialog', dialogHandler);
          return { success: true, method: 'playwright-aria-ref-newtab', newTabId, dialogMessage };
        } catch (popupError) {
          // Popup didn't open within timeout - this is expected for elements that
          // look like they might open popups but don't (e.g., JS intercepted the click)
          // The click still executed successfully
          page.off('dialog', dialogHandler);
          return { success: true, method: 'playwright-aria-ref', dialogMessage };
        }
      } else {
        //  Add options to prevent scrolling issues
        const browserConfig = this.configLoader.getBrowserConfig();
        await element.click({ force: browserConfig.forceClick });

        if (shouldCheckDiff && snapshotBefore) {
          await page.waitForTimeout(300);
          const snapshotAfter = await this.getSnapshot(page);
          let diffSnapshot = this.getSnapshotDiff(snapshotBefore, snapshotAfter, ['option', 'menuitem']);

          // For combobox, find the new ref based on aria-label and prepend to diffSnapshot
          if (isCombobox && comboboxAriaLabel) {
            const newComboboxRef = this.findComboboxRefByAriaLabel(snapshotAfter, comboboxAriaLabel);
            if (newComboboxRef) {
              // Find the full line for this combobox in the snapshot
              const comboboxLine = this.findSnapshotLineByRef(snapshotAfter, newComboboxRef);
              if (comboboxLine) {
                diffSnapshot = comboboxLine + (diffSnapshot ? '\n' + diffSnapshot : '');
              }
            }
          }

          if (diffSnapshot && diffSnapshot.trim() !== '') {
            page.off('dialog', dialogHandler);
            return { success: true, method: 'playwright-aria-ref', diffSnapshot, dialogMessage };
          }
        }

        page.off('dialog', dialogHandler);
        return { success: true, method: 'playwright-aria-ref', dialogMessage };
      }

    } catch (error) {
      page.off('dialog', dialogHandler);
      console.error('[performClick] Exception during click for ref: %s', ref, error);
      return { success: false, error: `Click failed with exception: ${error}`, dialogMessage };
    }
  }

  /**
   * Extract diff between two snapshots, returning only new elements of specified types
   */
  private getSnapshotDiff(snapshotBefore: string, snapshotAfter: string, targetRoles: string[]): string {
    const refsBefore = new Set<string>();
    const refPattern = /\[ref=([^\]]+)\]/g;
    let match;
    while ((match = refPattern.exec(snapshotBefore)) !== null) {
      refsBefore.add(match[1]);
    }

    const lines = snapshotAfter.split('\n');
    const newElements: string[] = [];

    for (const line of lines) {
      const refMatch = line.match(/\[ref=([^\]]+)\]/);
      if (refMatch && !refsBefore.has(refMatch[1])) {
        const hasTargetRole = targetRoles.some(role => {
          const rolePattern = new RegExp(`\\b${role}\\b`, 'i');
          return rolePattern.test(line);
        });

        if (hasTargetRole) {
          newElements.push(line.trim());
        }
      }
    }

    if (newElements.length > 0) {
      return newElements.join('\n');
    } else {
      return '';
    }
  }

  /**
   * Find a combobox ref in the snapshot by its aria-label or expanded state
   */
  private findComboboxRefByAriaLabel(snapshot: string, ariaLabel: string): string | null {
    const lines = snapshot.split('\n');
    // Escape special regex characters in ariaLabel
    const escapedLabel = ariaLabel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    // First, try to find by aria-label
    for (const line of lines) {
      const isCombobox = /\bcombobox\b/i.test(line);
      const hasLabel = new RegExp(`["']${escapedLabel}["']`, 'i').test(line) ||
                       line.includes(ariaLabel);

      if (isCombobox && hasLabel) {
        const refMatch = line.match(/\[ref=([^\]]+)\]/);
        if (refMatch) {
          return refMatch[1];
        }
      }
    }

    // Fallback: find the expanded combobox (since we just clicked it)
    for (const line of lines) {
      const isCombobox = /\bcombobox\b/i.test(line);
      const isExpanded = /\[expanded\]/i.test(line);

      if (isCombobox && isExpanded) {
        const refMatch = line.match(/\[ref=([^\]]+)\]/);
        if (refMatch) {
          return refMatch[1];
        }
      }
    }

    return null;
  }

  /**
   * Find the full snapshot line for a given ref
   */
  private findSnapshotLineByRef(snapshot: string, ref: string): string | null {
    const lines = snapshot.split('\n');
    for (const line of lines) {
      if (line.includes(`[ref=${ref}]`)) {
        return line.trim();
      }
    }
    return null;
  }

  /**
   *  Simplified type implementation using Playwright's aria-ref selector
   *  Supports both single and multiple input operations
   */
  private async performType(page: Page, ref: string | undefined, text: string | undefined, inputs?: Array<{ ref: string; text: string }>): Promise<{ success: boolean; error?: string; details?: Record<string, any>; diffSnapshot?: string }> {
    try {
      // Ensure we have the latest snapshot
      await this.getSnapshot(page);

      // Handle multiple inputs if provided
      if (inputs && inputs.length > 0) {
        const results: Record<string, { success: boolean; error?: string }> = {};

        for (const input of inputs) {
          const singleResult = await this.performType(page, input.ref, input.text);
          results[input.ref] = {
            success: singleResult.success,
            error: singleResult.error
          };
        }

        // Check if all inputs were successful
        const allSuccess = Object.values(results).every(r => r.success);
        const errors = Object.entries(results)
          .filter(([_, r]) => !r.success)
          .map(([ref, r]) => `${ref}: ${r.error}`)
          .join('; ');

        return {
          success: allSuccess,
          error: allSuccess ? undefined : `Some inputs failed: ${errors}`,
          details: results
        };
      }

      // Handle single input (backward compatibility)
      if (ref && text !== undefined) {
        //  Use findElementAcrossFrames to support elements inside iframes
        const result = await this.findElementAcrossFrames(page, ref);

        if (!result) {
          return { success: false, error: `Element with ref ${ref} not found in any frame` };
        }

        const element = result.locator;

        // Get element attributes to check if it's readonly or a special input type
        let originalPlaceholder: string | null = null;
        let isReadonly = false;
        let elementType: string | null = null;
        let isCombobox = false;
        let isTextbox = false;
        let shouldCheckDiff = false;

        try {
          // Get element info in one evaluation to minimize interactions
          const elementInfo = await element.evaluate((el: any) => {
            return {
              placeholder: el.placeholder || null,
              readonly: el.readOnly || el.hasAttribute('readonly'),
              type: el.type || null,
              tagName: el.tagName.toLowerCase(),
              disabled: el.disabled || false,
              role: el.getAttribute('role'),
              ariaHaspopup: el.getAttribute('aria-haspopup')
            };
          });

          originalPlaceholder = elementInfo.placeholder;
          isReadonly = elementInfo.readonly;
          elementType = elementInfo.type;
          isCombobox = elementInfo.role === 'combobox' ||
                       elementInfo.tagName === 'combobox' ||
                       elementInfo.ariaHaspopup === 'listbox';
          isTextbox = elementInfo.role === 'textbox' ||
                      elementInfo.tagName === 'input' ||
                      elementInfo.tagName === 'textarea';
          shouldCheckDiff = isCombobox || isTextbox;

        } catch (e) {
          console.log(`Warning: Failed to get element attributes: ${e}`);
        }

        // Get snapshot before action to record existing elements
        const snapshotBefore = await this.getSnapshot(page);
        const existingRefs = new Set<string>();
        const refPattern = /\[ref=([^\]]+)\]/g;
        let match;
        while ((match = refPattern.exec(snapshotBefore)) !== null) {
          existingRefs.add(match[1]);
        }
        console.log(`Found ${existingRefs.size} total elements before action`);

        // If element is readonly or a date/time input, skip fill attempt and go directly to click
        if (isReadonly || ['date', 'datetime-local', 'time'].includes(elementType || '')) {
          console.log(`Element ref=${ref} is readonly or date/time input, skipping direct fill attempt`);

          // Click with force option to avoid scrolling
          try {
            await element.click({ force: true });
            console.log(`Clicked readonly/special element ref=${ref} to trigger dynamic content`);
            // Wait for potential dynamic content to appear
            await page.waitForTimeout(500);
          } catch (clickError) {
            console.log(`Warning: Failed to click element: ${clickError}`);
          }
        } else {
          // Try to fill the element, with fallback to click-then-fill strategy
          let alreadyClicked = false;
          try {
            let fillSuccess = false;

            try {
              // Strategy 1: Try to fill directly without clicking (for modern inputs like Google Flights combobox)
              await element.fill(text, { timeout: 3000, force: true });
              fillSuccess = true;
              console.log(`Filled element ref=${ref} directly without clicking`);
            } catch (directFillError) {
              // Strategy 2: Click first, then fill (for traditional inputs that need activation)
              console.log(`Direct fill failed for ref=${ref}, trying click-then-fill strategy`);
              try {
                await element.click({ force: true });
                alreadyClicked = true;
                console.log(`Clicked element ref=${ref} before typing`);
              } catch (clickError) {
                console.log(`Warning: Failed to click element before typing: ${clickError}`);
              }

              try {
                await element.fill(text, { timeout: 3000, force: true });
                fillSuccess = true;
                console.log(`Filled element ref=${ref} after clicking`);
              } catch (secondFillError) {
                // Will be handled by outer catch block below
                throw secondFillError;
              }
            }

            if (fillSuccess) {
              // If this element might show dropdown, wait and check for new elements
              if (shouldCheckDiff) {
                await page.waitForTimeout(300);
                const snapshotAfter = await this.getSnapshot(page);
                const diffSnapshot = this.getSnapshotDiff(snapshotBefore, snapshotAfter, ['option', 'menuitem']);

                if (diffSnapshot && diffSnapshot.trim() !== '') {
                  return { success: true, diffSnapshot };
                }
              }

              return { success: true };
            }
          } catch (fillError: any) {
            // Log the error for debugging
            console.log(`Fill error for ref ${ref}: ${fillError.message}`);

            // Check for various error messages that indicate the element is not fillable
            const errorMessage = fillError.message.toLowerCase();
            if (errorMessage.includes('not an <input>') ||
              errorMessage.includes('not have a role allowing') ||
              errorMessage.includes('element is not') ||
              errorMessage.includes('cannot type') ||
              errorMessage.includes('readonly') ||
              errorMessage.includes('not editable') ||
              errorMessage.includes('timeout') ||
              errorMessage.includes('timeouterror')) {

            // Click the element again to trigger dynamic content (like date pickers), but only if we haven't clicked yet
            if (!alreadyClicked) {
              try {
                await element.click({ force: true });
                console.log(`Clicked element ref=${ref} to trigger dynamic content`);
                // Wait for potential dynamic content to appear
                await page.waitForTimeout(500);
              } catch (clickError) {
                console.log(`Warning: Failed to click element to trigger dynamic content: ${clickError}`);
              }
            } else {
              // We already clicked during the click-then-fill strategy
              await page.waitForTimeout(500);
            }

            // Step 1: Try to find input elements within the clicked element
            const inputSelector = `input:visible, textarea:visible, [contenteditable="true"]:visible, [role="textbox"]:visible`;
            const inputElement = await element.locator(inputSelector).first();

            const inputExists = await inputElement.count() > 0;
            if (inputExists) {
              console.log(`Found input element within ref ${ref}, attempting to fill`);
              try {
                await inputElement.fill(text, { force: true });

                // If element might show dropdown, check for new elements
                if (shouldCheckDiff) {
                  await page.waitForTimeout(300);
                  const snapshotFinal = await this.getSnapshot(page);
                  const diffSnapshot = this.getSnapshotDiff(snapshotBefore, snapshotFinal, ['option', 'menuitem']);

                  if (diffSnapshot && diffSnapshot.trim() !== '') {
                    return { success: true, diffSnapshot };
                  }
                }

                return { success: true };
              } catch (innerError) {
                console.log(`Failed to fill child element: ${innerError}`);
              }
            }

            // Step 2: Look for new elements that appeared after the action
            console.log(`Looking for new elements that appeared after action...`);

            // Get snapshot after action to find new elements
            const snapshotAfter = await this.getSnapshot(page);
            const newRefs = new Set<string>();
            const afterRefPattern = /\[ref=([^\]]+)\]/g;
            let afterMatch;
            while ((afterMatch = afterRefPattern.exec(snapshotAfter)) !== null) {
              const refId = afterMatch[1];
              if (!existingRefs.has(refId)) {
                newRefs.add(refId);
              }
            }

            console.log(`Found ${newRefs.size} new elements after action`);

            // If we have a placeholder, try to find new input elements with that placeholder
            if (originalPlaceholder && newRefs.size > 0) {
              console.log(`Looking for new input elements with placeholder: ${originalPlaceholder}`);

              // Try each new ref to see if it's an input with our placeholder
              for (const newRef of newRefs) {
                try {
                  const newElement = await page.locator(`aria-ref=${newRef}`).first();
                  const tagName = await newElement.evaluate(el => el.tagName.toLowerCase()).catch(() => null);

                  if (tagName === 'input' || tagName === 'textarea') {
                    const placeholder = await newElement.getAttribute('placeholder').catch(() => null);
                    if (placeholder === originalPlaceholder) {
                      console.log(`Found new input element with matching placeholder: ref=${newRef}`);

                      // Check if it's visible and fillable
                      const elementInfo = await newElement.evaluate((el: any) => {
                        return {
                          tagName: el.tagName,
                          id: el.id,
                          className: el.className,
                          placeholder: el.placeholder,
                          isVisible: el.offsetParent !== null,
                          isReadonly: el.readOnly || el.getAttribute('readonly') !== null
                        };
                      });
                      console.log(`New element details:`, JSON.stringify(elementInfo));

                      // Try to fill it with force to avoid scrolling
                      await newElement.fill(text, { force: true });

                      // If element might show dropdown, check for new elements
                      if (shouldCheckDiff) {
                        await page.waitForTimeout(300);
                        const snapshotFinal = await this.getSnapshot(page);
                        const diffSnapshot = this.getSnapshotDiff(snapshotBefore, snapshotFinal, ['option', 'menuitem']);

                        if (diffSnapshot && diffSnapshot.trim() !== '') {
                          return { success: true, diffSnapshot };
                        }
                      }

                      return { success: true };
                    }
                  }
                } catch (e) {
                  // Ignore errors for non-input elements
                }
              }
            }

            console.log(`No suitable input element found for ref ${ref}`);
            }
            // Re-throw the original error if we couldn't find an input element
            throw fillError;
          }
        }

        // If we skipped the fill attempt (readonly elements), look for new elements directly
        if (isReadonly || ['date', 'datetime-local', 'time'].includes(elementType || '')) {
          // Look for new elements that appeared after clicking
          console.log(`Looking for new elements that appeared after clicking readonly element...`);

          // Get snapshot after action to find new elements
          const snapshotAfter = await this.getSnapshot(page);
          const newRefs = new Set<string>();
          const afterRefPattern = /\[ref=([^\]]+)\]/g;
          let afterMatch;
          while ((afterMatch = afterRefPattern.exec(snapshotAfter)) !== null) {
            const refId = afterMatch[1];
            if (!existingRefs.has(refId)) {
              newRefs.add(refId);
            }
          }

          console.log(`Found ${newRefs.size} new elements after clicking readonly element`);

          // If we have a placeholder, try to find new input elements with that placeholder
          if (originalPlaceholder && newRefs.size > 0) {
            console.log(`Looking for new input elements with placeholder: ${originalPlaceholder}`);

            // Try each new ref to see if it's an input with our placeholder
            for (const newRef of newRefs) {
              try {
                const newElement = await page.locator(`aria-ref=${newRef}`).first();
                const tagName = await newElement.evaluate(el => el.tagName.toLowerCase()).catch(() => null);

                if (tagName === 'input' || tagName === 'textarea') {
                  const placeholder = await newElement.getAttribute('placeholder').catch(() => null);
                  if (placeholder === originalPlaceholder) {
                    console.log(`Found new input element with matching placeholder: ref=${newRef}`);

                    // Check if it's visible and fillable
                    const elementInfo = await newElement.evaluate((el: any) => {
                      return {
                        tagName: el.tagName,
                        id: el.id,
                        className: el.className,
                        placeholder: el.placeholder,
                        isVisible: el.offsetParent !== null,
                        isReadonly: el.readOnly || el.getAttribute('readonly') !== null
                      };
                    });
                    console.log(`New element details:`, JSON.stringify(elementInfo));

                    // Try to fill it with force to avoid scrolling
                    await newElement.fill(text, { force: true });

                    // If element might show dropdown, check for new elements
                    if (shouldCheckDiff) {
                      await page.waitForTimeout(300);
                      const snapshotFinal = await this.getSnapshot(page);
                      const diffSnapshot = this.getSnapshotDiff(snapshotBefore, snapshotFinal, ['option', 'menuitem']);

                      if (diffSnapshot && diffSnapshot.trim() !== '') {
                        return { success: true, diffSnapshot };
                      }
                    }

                    return { success: true };
                  }
                }
              } catch (e) {
                // Ignore errors for non-input elements
              }
            }
          }

          console.log(`No suitable input element found for readonly ref ${ref}`);
          return { success: false, error: `Element ref=${ref} is readonly and no suitable input was found` };
        }
      }

      return { success: false, error: 'No valid input provided' };
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
      await this.getSnapshot(page);

      //  Use findElementAcrossFrames to support elements inside iframes
      const result = await this.findElementAcrossFrames(page, ref);

      if (!result) {
        return { success: false, error: `Element with ref ${ref} not found in any frame` };
      }

      const element = result.locator;

      // Select value using Playwright's built-in selectOption method
      await element.selectOption(value);

      return { success: true };
    } catch (error) {
      return { success: false, error: `Select failed: ${error}` };
    }
  }

  /**
   *  Show highlight animation at given coordinates
   */
  private async showClickHighlight(page: Page, x: number, y: number): Promise<void> {
    await page.evaluate(({ x, y }) => {
      // Create highlight element
      const highlight = document.createElement('div');
      highlight.id = 'claude-click-highlight-' + Date.now();
      highlight.style.cssText = `
        position: fixed;
        left: ${x}px;
        top: ${y}px;
        width: 20px;
        height: 20px;
        margin-left: -10px;
        margin-top: -10px;
        border-radius: 50%;
        background: rgba(59, 130, 246, 0.5);
        border: 2px solid rgba(59, 130, 246, 0.8);
        pointer-events: none;
        z-index: 2147483647;
        animation: claude-highlight-pulse 0.6s ease-out forwards;
      `;

      // Add keyframes if not already present
      if (!document.getElementById('claude-highlight-styles')) {
        const style = document.createElement('style');
        style.id = 'claude-highlight-styles';
        style.textContent = `
          @keyframes claude-highlight-pulse {
            0% {
              transform: scale(1);
              opacity: 1;
            }
            50% {
              transform: scale(2);
              opacity: 0.7;
            }
            100% {
              transform: scale(2.5);
              opacity: 0;
            }
          }
        `;
        document.head.appendChild(style);
      }

      document.body.appendChild(highlight);

      // Remove after animation
      setTimeout(() => {
        highlight.remove();
      }, 600);
    }, { x, y });
  }

  /**
   *  Mouse control implementation with ineffective click detection
   *  For full visual mode: detects when click has no effect and suggests nearest elements
   */
  private async performMouseControl(
    page: Page,
    control: string,
    x: number,
    y: number
  ): Promise<{
    success: boolean;
    error?: string;
    resultMessage?: string;  // Custom result message for ineffective clicks
  }> {
    try {
      const viewport = page.viewportSize();
      if (!viewport) {
        return { success: false, error: 'Viewport size not available from page.' };
      }
      if (x < 0 || y < 0 || x > viewport.width || y > viewport.height) {
        return { success: false, error: `Invalid coordinates, outside viewport bounds: (${x}, ${y})` };
      }

      // Check if clicking on canvas element
      const isOnCanvas = await this.isPointOnCanvas(page, x, y);

      // Get snapshot before click (with coordinates for nearest element calculation)
      let snapshotBefore: string | null = null;
      let elementsWithCoords: Record<string, any> | null = null;

      if (!isOnCanvas && control === 'click') {
        const snapshotResult = await this.getSnapshotForAINative(true, false);
        snapshotBefore = snapshotResult.snapshot;
        elementsWithCoords = snapshotResult.elements;
      }

      // Show highlight animation at click position
      await this.showClickHighlight(page, x, y);

      // Perform the click action
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

      // For non-canvas clicks, check if the click had any effect
      if (!isOnCanvas && control === 'click' && snapshotBefore && elementsWithCoords) {
        // Wait a moment for any UI changes
        await page.waitForTimeout(100);

        // Get snapshot after click
        const snapshotAfter = await this.getSnapshot(page);

        // Check if snapshot changed
        if (!this.snapshotsAreDifferent(snapshotBefore, snapshotAfter)) {
          // Click had no effect - find nearest interactive elements and format message
          const nearestCount = this.configLoader.getWebSocketConfig().nearestElementsCount;
          const nearestElements = this.findNearestElements(elementsWithCoords, snapshotBefore, x, y, nearestCount);
          const resultMessage = this.formatNearestElementsMessage(x, y, nearestElements);

          return { success: true, resultMessage };
        }
      }

      return { success: true };
    } catch (error) {
      return { success: false, error: `Mouse action failed: ${error}` };
    }
  }

  /**
   *  Mouse drag and drop implementation supporting both ref and pixel modes
   */
  private async performMouseDrag(
    page: Page,
    action: { from_ref?: string; to_ref?: string; from_x?: number; from_y?: number; to_x?: number; to_y?: number }
  ): Promise<{ success: boolean; error?: string }> {
    try {
      let fromX: number, fromY: number, toX: number, toY: number;

      // Pixel mode: use coordinates directly
      if (action.from_x !== undefined && action.from_y !== undefined &&
          action.to_x !== undefined && action.to_y !== undefined) {
        fromX = action.from_x;
        fromY = action.from_y;
        toX = action.to_x;
        toY = action.to_y;

        // Show highlight at start and end positions for pixel mode
        await this.showClickHighlight(page, fromX, fromY);
        await this.showClickHighlight(page, toX, toY);
      }
      // Ref mode: get coordinates from elements (supports iframes)
      else if (action.from_ref && action.to_ref) {
        await this.getSnapshot(page);

        //  Use findElementAcrossFrames to support elements inside iframes
        const fromResult = await this.findElementAcrossFrames(page, action.from_ref);
        const toResult = await this.findElementAcrossFrames(page, action.to_ref);

        if (!fromResult) {
          return { success: false, error: `Source element with ref ${action.from_ref} not found in any frame` };
        }
        if (!toResult) {
          return { success: false, error: `Target element with ref ${action.to_ref} not found in any frame` };
        }

        const fromBox = await fromResult.locator.boundingBox();
        const toBox = await toResult.locator.boundingBox();

        if (!fromBox) {
          return { success: false, error: `Could not get bounding box for source element` };
        }
        if (!toBox) {
          return { success: false, error: `Could not get bounding box for target element` };
        }

        fromX = fromBox.x + fromBox.width / 2;
        fromY = fromBox.y + fromBox.height / 2;
        toX = toBox.x + toBox.width / 2;
        toY = toBox.y + toBox.height / 2;
      } else {
        return { success: false, error: 'Must provide either (from_ref, to_ref) or (from_x, from_y, to_x, to_y)' };
      }

      // Perform the drag operation
      await page.mouse.move(fromX, fromY);
      await page.mouse.down();
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
      let customMessage: string | undefined;
      let actionDetails: Record<string, any> | undefined;

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

          // Capture diff snapshot and dialog message if present
          if (clickResult.diffSnapshot || clickResult.dialogMessage) {
            actionDetails = {
              ...(clickResult.diffSnapshot && { diffSnapshot: clickResult.diffSnapshot }),
              ...(clickResult.dialogMessage && { dialogMessage: clickResult.dialogMessage })
            };
          }

          actionExecutionTime = Date.now() - clickStart;
          break;
        }

        case 'type': {
          elementSearchTime = Date.now() - elementSearchStart;
          const typeStart = Date.now();

          const typeResult = await this.performType(page, action.ref, action.text, action.inputs);

          if (!typeResult.success) {
            throw new Error(`Type failed: ${typeResult.error}`);
          }

          // Set custom message and details if multiple inputs were used
          if (typeResult.details) {
            const successCount = Object.values(typeResult.details).filter((r: any) => r.success).length;
            const totalCount = Object.keys(typeResult.details).length;
            customMessage = `Typed text into ${successCount}/${totalCount} elements`;
            actionDetails = typeResult.details;
          }

          // Capture diff snapshot if present
          if (typeResult.diffSnapshot) {
            if (!actionDetails) {
              actionDetails = {};
            }
            actionDetails.diffSnapshot = typeResult.diffSnapshot;
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

          // Use custom result message if click was ineffective
          if (mouseControlResult.resultMessage) {
            customMessage = mouseControlResult.resultMessage;
          }

          actionExecutionTime = Date.now() - mouseControlStart;
          break;
        }

        case 'mouse_drag': {
          elementSearchTime = Date.now() - elementSearchStart;
          const mouseDragStart = Date.now();
          const mouseDragResult = await this.performMouseDrag(page, action);

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
        message: customMessage || `Action ${action.type} executed successfully`,
        timing: {
          total_time_ms: totalTime,
          element_search_time_ms: elementSearchTime,
          action_execution_time_ms: actionExecutionTime,
          stability_wait_time_ms: stabilityWaitTime,
          dom_content_loaded_time_ms: stabilityResult.domContentLoadedTime,
          network_idle_time_ms: stabilityResult.networkIdleTime,
          dom_stability_time_ms: stabilityResult.domStabilityTime,
        },
        note: stabilityResult.note,
        ...(newTabId && { newTabId }),
        ...(actionDetails && { details: actionDetails }),
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

  /**
   * Wait for DOM to stop changing for a specified duration
   * @param page - The Playwright page instance
   * @param maxWaitTime - Maximum time to wait for stability in ms (uses config value)
   * @returns Object indicating if loading elements were detected
   */
  private async waitForDOMStability(page: Page, maxWaitTime: number): Promise<{ hasLoadingElements: boolean }> {
    const browserConfig = this.configLoader.getBrowserConfig();
    const stabilityThreshold = browserConfig.domStabilityThreshold;
    let hasLoadingElements = false;

    // Pass the selector as a parameter to avoid closure issues
    const loadingSelector = LOADING_ELEMENTS_SELECTOR;

    try {
      // Monitor DOM changes and loading elements
      await page.evaluate((selector: string) => {
        // Word boundary regex patterns for accurate loading class detection
        const loadingPatterns = [
          /\bloading\b/i,
          /\bloader\b/i,
          /\bspinner\b/i,
          /\bspin\b/i,
        ];

        // Helper function to check if className contains loading indicators using word boundaries
        const hasLoadingClass = (className: string): boolean => {
          return loadingPatterns.some(pattern => pattern.test(className));
        };

        // Helper function to check if any loading elements exist in the DOM
        const checkForLoadingElements = (): boolean => {
          const loadingElements = document.querySelectorAll(selector);
          // Double-check with regex patterns to reduce false positives
          for (const el of Array.from(loadingElements)) {
            const cls = el.getAttribute('class') || '';
            if (hasLoadingClass(cls)) {
              return true;
            }
          }
          return false;
        };

        (window as any).__domStabilityCheck = {
          changeCount: 0,
          lastChange: Date.now(),
          hasLoadingElements: checkForLoadingElements()
        };

        const observer = new MutationObserver((mutations: MutationRecord[]) => {
          const check = (window as any).__domStabilityCheck;
          check.changeCount++;
          check.lastChange = Date.now();

          let loadingAdded = false;
          let loadingRemoved = false;

          for (const mutation of mutations) {
            // Check if class attribute changed to add/remove loading
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
              const target = mutation.target as Element;
              const oldValue = mutation.oldValue || '';
              const newValue = target.getAttribute('class') || '';

              const hadLoading = hasLoadingClass(oldValue);
              const hasLoading = hasLoadingClass(newValue);

              if (!hadLoading && hasLoading) {
                loadingAdded = true;
              } else if (hadLoading && !hasLoading) {
                loadingRemoved = true;
              }
            }

            // Check added/removed nodes for loading elements
            if (mutation.type === 'childList') {
              for (const node of Array.from(mutation.addedNodes)) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                  const el = node as Element;
                  const cls = el.getAttribute('class') || '';
                  if (hasLoadingClass(cls)) {
                    loadingAdded = true;
                    break;
                  }
                  // Check descendants
                  const descendants = el.querySelectorAll(selector);
                  for (const desc of Array.from(descendants)) {
                    if (hasLoadingClass(desc.getAttribute('class') || '')) {
                      loadingAdded = true;
                      break;
                    }
                  }
                }
              }

              for (const node of Array.from(mutation.removedNodes)) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                  const el = node as Element;
                  const cls = el.getAttribute('class') || '';
                  if (hasLoadingClass(cls)) {
                    loadingRemoved = true;
                    break;
                  }
                  const descendants = el.querySelectorAll(selector);
                  for (const desc of Array.from(descendants)) {
                    if (hasLoadingClass(desc.getAttribute('class') || '')) {
                      loadingRemoved = true;
                      break;
                    }
                  }
                }
              }
            }
          }

          if (loadingAdded) {
            check.hasLoadingElements = true;
          }

          if (loadingRemoved) {
            check.hasLoadingElements = checkForLoadingElements();
          }
        });

        observer.observe(document.body, {
          childList: true,
          subtree: true,
          attributes: true,
          attributeOldValue: true,
          characterData: true
        });

        (window as any).__domStabilityObserver = observer;
      }, loadingSelector);

      // Wait until no changes for stabilityThreshold, or timeout
      await page.waitForFunction(
        (threshold: number) => {
          const check = (window as any).__domStabilityCheck;
          if (!check) return true;
          return (Date.now() - check.lastChange) > threshold;
        },
        stabilityThreshold,
        { timeout: Math.max(0, maxWaitTime) }
      ).catch(() => {});

      // Get final loading state
      hasLoadingElements = await page.evaluate(() => {
        const check = (window as any).__domStabilityCheck;
        return check ? check.hasLoadingElements : false;
      });
    } finally {
      // Cleanup observer
      await page.evaluate(() => {
        const observer = (window as any).__domStabilityObserver;
        if (observer) observer.disconnect();
        delete (window as any).__domStabilityObserver;
        delete (window as any).__domStabilityCheck;
      }).catch(() => {});
    }

    return { hasLoadingElements };
  }

  async waitForPageStability(page: Page): Promise<PageStabilityResult> {
    const defaultResult: PageStabilityResult = {
      domContentLoadedTime: 0,
      networkIdleTime: 0,
      domStabilityTime: 0,
      hasLoadingElements: false,
      note: ''
    };

    try {
      const browserConfig = this.configLoader.getBrowserConfig();

      const maxTimeout = Math.max(
        browserConfig.domContentLoadedTimeout,
        browserConfig.networkIdleTimeout,
        browserConfig.domStabilityTimeout
      );

      // Track timeout for cleanup
      let timeoutId: ReturnType<typeof setTimeout> | null = null;

      const start = Date.now();
      await page.waitForLoadState(browserConfig.domContentLoadedState as any, {
        timeout: browserConfig.domContentLoadedTimeout
      });
      const domContentLoadedTime = Date.now() - start;

      const networkIdlePromise = (async () => {
        const startTime = Date.now();
        await page.waitForLoadState(browserConfig.networkIdleState as any, {
          timeout: browserConfig.networkIdleTimeout
        });
        return Date.now() - startTime;
      })();

      const domStabilityPromise = (async () => {
        const startTime = Date.now();
        const result = await this.waitForDOMStability(page, browserConfig.domStabilityTimeout);
        return {
          time: Date.now() - startTime,
          hasLoadingElements: result.hasLoadingElements
        };
      })();

      // Create timeout promise with cleanup capability
      const timeoutPromise = new Promise<never>((_, reject) => {
        timeoutId = setTimeout(() => reject(new Error('max timeout')), maxTimeout);
      });

      try {
        const [networkIdleTime, domStabilityResult] = await Promise.race([
          Promise.all([networkIdlePromise, domStabilityPromise]),
          timeoutPromise
        ]);

        return {
          domContentLoadedTime,
          networkIdleTime,
          domStabilityTime: domStabilityResult.time,
          hasLoadingElements: domStabilityResult.hasLoadingElements,
          note: domStabilityResult.hasLoadingElements ? LOADING_STATE_NOTE : ''
        };
      } finally {
        // Clean up timeout to prevent memory leak
        if (timeoutId !== null) {
          clearTimeout(timeoutId);
        }
      }
    } catch (error) {
      return defaultResult;
    }
  }

  async visitPage(url: string): Promise<ActionResult & { newTabId?: string }> {
    const startTime = Date.now();

    try {
      // Get current page to check if it's blank
      let currentPage: Page;
      let currentUrl: string;

      try {
        currentPage = await this.getCurrentPage();
        currentUrl = currentPage.url();
      } catch (error: any) {
        // If no active page is available, getCurrentPage() will create one in CDP mode
        console.log('[visitPage] Failed to get current page:', error);
        throw new Error(`No active page available: ${error?.message || error}`);
      }

      //  Check if current page is blank or if this is the first navigation
      const browserConfig = this.configLoader.getBrowserConfig();

      // Use unified blank page detection
      const isBlankPage = this.isBlankPageUrl(currentUrl) || currentUrl === browserConfig.defaultStartUrl;

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
            dom_stability_time_ms: stabilityResult.domStabilityTime,
          },
          note: stabilityResult.note,
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
        if (browserConfig.cdpUrl) {
          // CDP mode: find an available blank tab
          const allPages = this.context.pages();
          for (const page of allPages) {
            const pageUrl = page.url();
            // Check if this page is not already tracked and is blank
            const isTracked = Array.from(this.pages.values()).includes(page);
            if (!isTracked && this.isBlankPageUrl(pageUrl)) {
              newPage = page;
              newTabId = this.generateTabId();
              this.registerNewPage(newTabId, newPage);
              break;
            }
          }

          if (!newPage || !newTabId) {
            console.log('[CDP] No available blank tabs, creating new page');
            newPage = await this.context.newPage();
            newTabId = this.generateTabId();
            this.registerNewPage(newTabId, newPage);
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
          newTabId: newTabId,
          timing: {
            total_time_ms: totalTime,
            navigation_time_ms: navigationTime,
            dom_content_loaded_time_ms: stabilityResult.domContentLoadedTime,
            network_idle_time_ms: stabilityResult.networkIdleTime,
            dom_stability_time_ms: stabilityResult.domStabilityTime,
          },
          note: stabilityResult.note,
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
          dom_stability_time_ms: 0,
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

  async batchKeyboardInput(operations: Array<{type: string, keys?: string[], text?: string, delay?: number}>, skipStabilityWait: boolean = false): Promise<any> {
    const startTime = Date.now();
    const page = await this.getCurrentPage();

    try {
      const maxOperations = 100; // Prevent excessive number of operations per batch
      if (!Array.isArray(operations) || operations.length > maxOperations) {
        throw new Error(`Too many operations in batch (max ${maxOperations} allowed)`);
      }

      const executionStart = Date.now();

      for (const op of operations) {
        switch (op.type) {
          case 'press':
            if (op.keys) {
              const keys = op.keys.join('+');
              await page.keyboard.press(keys);
            }
            break;
          case 'type':
            if (op.text) {
              // Limit delay to prevent resource exhaustion attacks
              const maxTypeDelay = 1000; // 1 second per character max
              let delayValue = Number(op.delay);
              if (!isFinite(delayValue) || delayValue < 0) delayValue = 0;
              const safeTypeDelay = Math.min(delayValue, maxTypeDelay);
              await page.keyboard.type(op.text, { delay: safeTypeDelay });
            }
            break;
          case 'wait':
            // Only apply wait if op.delay is a non-negative finite number
            // Limit to prevent resource exhaustion (CodeQL js/resource-exhaustion)
            {
              const MAX_WAIT_DELAY = 10000; // 10 seconds maximum
              let delayValue = Number(op.delay);
              if (!isFinite(delayValue) || delayValue < 0) {
                delayValue = 0;
              }
              // Clamp delay to safe range [0, MAX_WAIT_DELAY]
              const safeDelay = delayValue > MAX_WAIT_DELAY ? MAX_WAIT_DELAY : delayValue;
              // lgtm[js/resource-exhaustion]
              // Safe: delay is clamped to MAX_WAIT_DELAY (10 seconds)
              await new Promise(resolve => setTimeout(resolve, safeDelay));
            }
            break;
        }
      }

      const executionTime = Date.now() - executionStart;
      let stabilityTime = 0;
      let stabilityResult = { domContentLoadedTime: 0, networkIdleTime: 0 };

      if (!skipStabilityWait) {
        const stabilityStart = Date.now();

        try {
          const browserConfig = this.configLoader.getBrowserConfig();
          await page.waitForLoadState(browserConfig.domContentLoadedState as any, { timeout: browserConfig.domContentLoadedTimeout });
          stabilityResult.domContentLoadedTime = Date.now() - stabilityStart;
        } catch (error) {
        }

        await new Promise(resolve => setTimeout(resolve, 50));
        stabilityTime = Date.now() - stabilityStart;
      } else {
        await new Promise(resolve => setTimeout(resolve, 50));
        stabilityTime = 50;
      }

      const totalTime = Date.now() - startTime;

      return {
        success: true,
        message: `Batch keyboard input completed (${operations.length} operations)`,
        timing: {
          total_time_ms: totalTime,
          execution_time_ms: executionTime,
          stability_wait_time_ms: stabilityTime,
          operations_count: operations.length,
          skipped_stability: skipStabilityWait,
        },
      };
    } catch (error) {
      const totalTime = Date.now() - startTime;
      return {
        success: false,
        message: `Batch keyboard input failed: ${error}`,
        timing: {
          total_time_ms: totalTime,
        },
      };
    }
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

  async takeScreenshot(): Promise<{
    buffer: Buffer;
    timing: { screenshot_time_ms: number };
    viewport: { width: number; height: number };
  }> {
    const startTime = Date.now();
    const page = await this.getCurrentPage();

    const browserConfig = this.configLoader.getBrowserConfig();
    const buffer = await page.screenshot({
      timeout: browserConfig.screenshotTimeout,
      fullPage: browserConfig.fullPageScreenshot
    });

    const viewport = page.viewportSize() || browserConfig.viewport;
    const screenshotTime = Date.now() - startTime;

    return {
      buffer,
      timing: {
        screenshot_time_ms: screenshotTime,
      },
      viewport,
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

    // Handle context cleanup separately for CDP mode
    if (!browserConfig.cdpUrl && this.context && this.contextOwnedByUs) {
      // For non-CDP mode, close context here
      await this.context.close();
      this.context = null;
      this.contextOwnedByUs = false;
    }

    if (this.browser) {
      if (browserConfig.cdpUrl) {
        // In CDP mode: tear down only our context, then disconnect
        if (this.context && this.contextOwnedByUs) {
          await this.context.close().catch(() => {});
          this.context = null;
          this.contextOwnedByUs = false;
        }
        await this.browser.close(); // disconnect
      } else {
        // Local launch: close everything
        await this.browser.close();
      }
      this.browser = null;
    }
  }
}
