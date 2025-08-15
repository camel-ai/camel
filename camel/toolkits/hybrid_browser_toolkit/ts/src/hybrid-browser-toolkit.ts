import {HybridBrowserSession} from './browser-session';
import {ActionResult, BrowserAction, BrowserToolkitConfig, SnapshotResult, TabInfo, VisualMarkResult} from './types';
import {ConfigLoader} from './config-loader';
import {ConsoleMessage} from 'playwright';

export class HybridBrowserToolkit {
  private session: HybridBrowserSession;
  private config: BrowserToolkitConfig;
  private configLoader: ConfigLoader;
  private viewportLimit: boolean;

  constructor(config: BrowserToolkitConfig = {}) {
    this.configLoader = ConfigLoader.fromPythonConfig(config);
    this.config = config; // Store original config for backward compatibility
    this.session = new HybridBrowserSession(this.configLoader.getBrowserConfig()); // Pass processed config
    this.viewportLimit = this.configLoader.getWebSocketConfig().viewport_limit;
  }

  async openBrowser(startUrl?: string): Promise<ActionResult> {
    const startTime = Date.now();
    
    try {
      await this.session.ensureBrowser();
      
      const url = startUrl || this.config.defaultStartUrl || 'https://google.com/';
      const result = await this.session.visitPage(url);
      
      const snapshotStart = Date.now();
      const snapshot = await this.getPageSnapshot(this.viewportLimit);
      const snapshotTime = Date.now() - snapshotStart;
      
      const totalTime = Date.now() - startTime;
      
      return {
        success: true,
        message: `Browser opened and navigated to ${url}`,
        snapshot,
        timing: {
          total_time_ms: totalTime,
          ...result.timing,
          snapshot_time_ms: snapshotTime,
        },
      };
    } catch (error) {
      const totalTime = Date.now() - startTime;
      return {
        success: false,
        message: `Failed to open browser: ${error}`,
        timing: {
          total_time_ms: totalTime,
        },
      };
    }
  }

  async closeBrowser(): Promise<ActionResult> {
    try {
      await this.session.close();
      return {
        success: true,
        message: 'Browser closed successfully',
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to close browser: ${error}`,
      };
    }
  }

  async visitPage(url: string): Promise<any> {
    const result = await this.session.visitPage(url);
    
    // Format response for Python layer compatibility
    const response: any = {
      result: result.message,
      snapshot: '',
    };
    
    if (result.success) {
      const snapshotStart = Date.now();
      response.snapshot = await this.getPageSnapshot(this.viewportLimit);
      const snapshotTime = Date.now() - snapshotStart;
      
      if (result.timing) {
        result.timing.snapshot_time_ms = snapshotTime;
      }
    }
    
    // Include timing if available
    if (result.timing) {
      response.timing = result.timing;
    }
    
    // Include newTabId if present
    if (result.newTabId) {
      response.newTabId = result.newTabId;
    }
    
    return response;
  }

  async getPageSnapshot(viewportLimit: boolean = false): Promise<string> {
    try {
      // If viewport limiting is enabled, we need coordinates for filtering
      const snapshotResult = await this.session.getSnapshotForAI(viewportLimit, viewportLimit);
      return snapshotResult.snapshot;
    } catch (error) {
      return `Error capturing snapshot: ${error}`;
    }
  }


  async getSnapshotForAI(): Promise<SnapshotResult> {
    return await this.session.getSnapshotForAI();
  }

  async getSomScreenshot(): Promise<VisualMarkResult & { timing: any }> {
    const startTime = Date.now();
    
    try {
      const screenshotResult = await this.session.takeScreenshot();
      const snapshotResult = await this.session.getSnapshotForAI(true); // Include coordinates for SOM_mark
      
      // Add visual marks using improved method
      const markingStart = Date.now();
      const markedImageBuffer = await this.addVisualMarksOptimized(screenshotResult.buffer, snapshotResult);
      const markingTime = Date.now() - markingStart;
      
      const base64Image = markedImageBuffer.toString('base64');
      const dataUrl = `data:image/png;base64,${base64Image}`;
      
      const totalTime = Date.now() - startTime;
      
      // Count elements with coordinates
      const elementsWithCoords = Object.values(snapshotResult.elements).filter(el => el.coordinates).length;
      
      return {
        text: `Visual webpage screenshot captured with ${Object.keys(snapshotResult.elements).length} interactive elements (${elementsWithCoords} marked visually)`,
        images: [dataUrl],
        timing: {
          total_time_ms: totalTime,
          screenshot_time_ms: screenshotResult.timing.screenshot_time_ms,
          snapshot_time_ms: snapshotResult.timing.snapshot_time_ms,
          coordinate_enrichment_time_ms: snapshotResult.timing.coordinate_enrichment_time_ms,
          visual_marking_time_ms: markingTime,
        },
      };
    } catch (error) {
      const totalTime = Date.now() - startTime;
      return {
        text: `Error capturing screenshot: ${error}`,
        images: [],
        timing: {
          total_time_ms: totalTime,
          screenshot_time_ms: 0,
          snapshot_time_ms: 0,
          coordinate_enrichment_time_ms: 0,
          visual_marking_time_ms: 0,
        },
      };
    }
  }

  private async addVisualMarksOptimized(screenshotBuffer: Buffer, snapshotResult: SnapshotResult): Promise<Buffer> {
    try {
      
      // Check if we have any elements with coordinates
      const elementsWithCoords = Object.entries(snapshotResult.elements)
        .filter(([ref, element]) => element.coordinates);
      
      if (elementsWithCoords.length === 0) {
        return screenshotBuffer;
      }
      
      // Parse clickable elements from snapshot text
      const clickableElements = this.parseClickableElements(snapshotResult.snapshot);
      
      // Use sharp for image processing
      const sharp = require('sharp');
      const page = await this.session.getCurrentPage();
      const viewport = page.viewportSize() || { width: 1280, height: 720 };
      
      // Filter elements visible in viewport
      const visibleElements = elementsWithCoords.filter(([ref, element]) => {
        const coords = element.coordinates!;
        return coords.x < viewport.width && 
               coords.y < viewport.height && 
               coords.x + coords.width > 0 && 
               coords.y + coords.height > 0;
      });
      
      // Remove overlapped elements (only keep topmost)
      const nonOverlappedElements = this.removeOverlappedElements(visibleElements);
      
      // Create SVG overlay with all the marks
      const marks = nonOverlappedElements.map(([ref, element]) => {
        const coords = element.coordinates!;
        const isClickable = clickableElements.has(ref);
        
        // Use original coordinates for elements within viewport
        // Clamp only to prevent marks from extending beyond screenshot bounds
        const x = Math.max(0, coords.x);
        const y = Math.max(0, coords.y);
        const maxWidth = viewport.width - x;
        const maxHeight = viewport.height - y;
        const width = Math.min(coords.width, maxWidth);
        const height = Math.min(coords.height, maxHeight);
        
        // Position text to be visible even if element is partially cut off
        const textX = Math.max(2, Math.min(x + 2, viewport.width - 40));
        const textY = Math.max(14, Math.min(y + 14, viewport.height - 4));
        
        // Different colors for clickable vs non-clickable elements
        const colors = isClickable ? {
          fill: 'rgba(0, 150, 255, 0.15)',  // Blue for clickable
          stroke: '#0096FF',
          textFill: '#0096FF'
        } : {
          fill: 'rgba(255, 107, 107, 0.1)',  // Red for non-clickable
          stroke: '#FF6B6B', 
          textFill: '#FF6B6B'
        };
        
        return `
          <rect x="${x}" y="${y}" width="${width}" height="${height}" 
                fill="${colors.fill}" stroke="${colors.stroke}" stroke-width="2" rx="2"/>
          <text x="${textX}" y="${textY}" font-family="Arial, sans-serif" 
                font-size="12" fill="${colors.textFill}" font-weight="bold">${ref}</text>
        `;
      }).join('');
      
      const svgOverlay = `
        <svg width="${viewport.width}" height="${viewport.height}" xmlns="http://www.w3.org/2000/svg">
          ${marks}
        </svg>
      `;
      
      // Composite the overlay onto the screenshot
      const markedImageBuffer = await sharp(screenshotBuffer)
        .composite([{
          input: Buffer.from(svgOverlay),
          top: 0,
          left: 0
        }])
        .png()
        .toBuffer();
      
      return markedImageBuffer;
      
    } catch (error) {
      // Error adding visual marks, falling back to original screenshot
      // Return original screenshot if marking fails
      return screenshotBuffer;
    }
  }

  /**
   * Parse clickable elements from snapshot text
   */
  private parseClickableElements(snapshotText: string): Set<string> {
    const clickableElements = new Set<string>();
    const lines = snapshotText.split('\n');
    
    for (const line of lines) {
      // Look for lines containing [cursor=pointer] and extract ref
      if (line.includes('[cursor=pointer]')) {
        const refMatch = line.match(/\[ref=([^\]]+)\]/);
        if (refMatch) {
          clickableElements.add(refMatch[1]);
        }
      }
    }
    
    return clickableElements;
  }

  /**
   * Remove overlapped elements, keeping only the topmost (last in DOM order)
   */
  private removeOverlappedElements(elements: Array<[string, any]>): Array<[string, any]> {
    const result: Array<[string, any]> = [];
    
    for (let i = 0; i < elements.length; i++) {
      const [refA, elementA] = elements[i];
      const coordsA = elementA.coordinates!;
      let isOverlapped = false;
      
      // Check if this element is completely overlapped by any later element
      for (let j = i + 1; j < elements.length; j++) {
        const [refB, elementB] = elements[j];
        const coordsB = elementB.coordinates!;
        
        // Check if element A is completely covered by element B
        if (this.isCompletelyOverlapped(coordsA, coordsB)) {
          isOverlapped = true;
          break;
        }
      }
      
      if (!isOverlapped) {
        result.push(elements[i]);
      }
    }
    
    return result;
  }

  /**
   * Check if element A is completely overlapped by element B
   */
  private isCompletelyOverlapped(
    coordsA: { x: number; y: number; width: number; height: number },
    coordsB: { x: number; y: number; width: number; height: number }
  ): boolean {
    // A is completely overlapped by B if:
    // B's left edge is <= A's left edge AND
    // B's top edge is <= A's top edge AND  
    // B's right edge is >= A's right edge AND
    // B's bottom edge is >= A's bottom edge
    return (
      coordsB.x <= coordsA.x &&
      coordsB.y <= coordsA.y &&
      coordsB.x + coordsB.width >= coordsA.x + coordsA.width &&
      coordsB.y + coordsB.height >= coordsA.y + coordsA.height
    );
  }

  private async executeActionWithSnapshot(action: BrowserAction): Promise<any> {
    const result = await this.session.executeAction(action);
    
    // Format response for Python layer compatibility
    const response: any = {
      result: result.message,
      snapshot: '',
    };
    
    if (result.success) {
      const snapshotStart = Date.now();
      response.snapshot = await this.getPageSnapshot(this.viewportLimit);
      const snapshotTime = Date.now() - snapshotStart;
      
      if (result.timing) {
        result.timing.snapshot_time_ms = snapshotTime;
      }
    }
    
    // Include timing if available
    if (result.timing) {
      response.timing = result.timing;
    }
    
    // Include newTabId if present
    if (result.newTabId) {
      response.newTabId = result.newTabId;
    }
    
    return response;
  }

  async click(ref: string): Promise<any> {
    const action: BrowserAction = { type: 'click', ref };
    return this.executeActionWithSnapshot(action);
  }

  async type(ref: string, text: string): Promise<any> {
    const action: BrowserAction = { type: 'type', ref, text };
    return this.executeActionWithSnapshot(action);
  }

  async select(ref: string, value: string): Promise<any> {
    const action: BrowserAction = { type: 'select', ref, value };
    return this.executeActionWithSnapshot(action);
  }

  async scroll(direction: 'up' | 'down', amount: number): Promise<any> {
    const action: BrowserAction = { type: 'scroll', direction, amount };
    return this.executeActionWithSnapshot(action);
  }

  async enter(): Promise<any> {
    const action: BrowserAction = { type: 'enter' };
    return this.executeActionWithSnapshot(action);
  }

  async mouseControl(control: 'click' | 'right_click'| 'dblclick', x: number, y: number): Promise<any> {
    const action: BrowserAction = { type: 'mouse_control', control, x, y };
    return this.executeActionWithSnapshot(action);
  }

  async mouseDrag(from_ref: string, to_ref: string): Promise<any> {
    const action: BrowserAction = { type: 'mouse_drag', from_ref, to_ref };
    return this.executeActionWithSnapshot(action);
  }

  async pressKeys(keys: string[]): Promise<any> {
    const action: BrowserAction = { type: 'press_key', keys};
    return this.executeActionWithSnapshot(action);
  }

  async back(): Promise<ActionResult> {
    const startTime = Date.now();
    
    try {
      const page = await this.session.getCurrentPage();
      
      const navigationStart = Date.now();
      await page.goBack({ waitUntil: 'domcontentloaded' });
      const navigationTime = Date.now() - navigationStart;
      
      const snapshotStart = Date.now();
      const snapshot = await this.getPageSnapshot(this.viewportLimit);
      const snapshotTime = Date.now() - snapshotStart;
      
      const totalTime = Date.now() - startTime;
      
      return {
        success: true,
        message: 'Navigated back successfully',
        snapshot,
        timing: {
          total_time_ms: totalTime,
          navigation_time_ms: navigationTime,
          snapshot_time_ms: snapshotTime,
        },
      };
    } catch (error) {
      const totalTime = Date.now() - startTime;
      return {
        success: false,
        message: `Back navigation failed: ${error}`,
        timing: {
          total_time_ms: totalTime,
          navigation_time_ms: 0,
          snapshot_time_ms: 0,
        },
      };
    }
  }

  async forward(): Promise<ActionResult> {
    const startTime = Date.now();
    
    try {
      const page = await this.session.getCurrentPage();
      
      const navigationStart = Date.now();
      await page.goForward({ waitUntil: 'domcontentloaded' });
      const navigationTime = Date.now() - navigationStart;
      
      const snapshotStart = Date.now();
      const snapshot = await this.getPageSnapshot(this.viewportLimit);
      const snapshotTime = Date.now() - snapshotStart;
      
      const totalTime = Date.now() - startTime;
      
      return {
        success: true,
        message: 'Navigated forward successfully',
        snapshot,
        timing: {
          total_time_ms: totalTime,
          navigation_time_ms: navigationTime,
          snapshot_time_ms: snapshotTime,
        },
      };
    } catch (error) {
      const totalTime = Date.now() - startTime;
      return {
        success: false,
        message: `Forward navigation failed: ${error}`,
        timing: {
          total_time_ms: totalTime,
          navigation_time_ms: 0,
          snapshot_time_ms: 0,
        },
      };
    }
  }


  async switchTab(tabId: string): Promise<any> {
    const startTime = Date.now();
    
    try {
      const success = await this.session.switchToTab(tabId);
      
      if (success) {
        const snapshotStart = Date.now();
        const snapshot = await this.getPageSnapshot(this.viewportLimit);
        const snapshotTime = Date.now() - snapshotStart;
        
        const totalTime = Date.now() - startTime;
        
        return {
          result: `Switched to tab ${tabId}`,
          snapshot: snapshot,
          timing: {
            total_time_ms: totalTime,
            snapshot_time_ms: snapshotTime,
          },
        };
      } else {
        return {
          result: `Failed to switch to tab ${tabId}`,
          snapshot: '',
        };
      }
    } catch (error) {
      return {
        result: `Error switching tab: ${error}`,
        snapshot: '',
      };
    }
  }

  async closeTab(tabId: string): Promise<ActionResult> {
    const success = await this.session.closeTab(tabId);
    
    if (success) {
      return {
        success: true,
        message: `Closed tab ${tabId}`,
        snapshot: await this.getPageSnapshot(this.viewportLimit),
      };
    } else {
      return {
        success: false,
        message: `Failed to close tab ${tabId}`,
      };
    }
  }

  async getTabInfo(): Promise<TabInfo[]> {
    return await this.session.getTabInfo();
  }

  async getConsoleView(): Promise<any> {
    const currentLogs = await this.session.getCurrentLogs();
    // Format logs
    return currentLogs.map(item => ({
      type: item.type(),
      text: item.text(),
    }));
  }

  async consoleExecute(code: string): Promise<any> {
    const startTime = Date.now();
    try {
      const page = await this.session.getCurrentPage();
      
      // Wrap the code to capture console.log output
      const wrappedCode = `
        (function() {
          const _logs = [];
          const originalLog = console.log;
          console.log = function(...args) {
            _logs.push(args.map(arg => {
              try {
                return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
              } catch (e) {
                return String(arg);
              }
            }).join(' '));
            originalLog.apply(console, args);
          };
          
          let result;
          try {
            result = eval(${JSON.stringify(code)});
          } catch (e) {
            try {
              result = (function() { ${code} })();
            } catch (error) {
              console.log = originalLog;
              throw error;
            }
          }
          
          console.log = originalLog;
          return { result, logs: _logs };
        })()
      `;
      
      const evalResult = await page.evaluate(wrappedCode) as { result: any; logs: string[] };
      const { result, logs } = evalResult;

      const snapshotStart = Date.now();
      const snapshot = await this.getPageSnapshot(this.viewportLimit);
      const snapshotTime = Date.now() - snapshotStart;
      const totalTime = Date.now() - startTime;

      // Properly serialize the result
      let resultStr: string;
      try {
        resultStr = JSON.stringify(result, null, 2);
      } catch (e) {
        // Fallback for non-serializable values
        resultStr = String(result);
      }

      return {
        result: `Console execution result: ${resultStr}`,
        console_output: logs,
        snapshot: snapshot,
        timing: {
          total_time_ms: totalTime,
          snapshot_time_ms: snapshotTime,
        },
      };
      
    } catch (error) {
      const totalTime = Date.now() - startTime;
      return {
        result: `Console execution failed: ${error}`,
        console_output: [],
        snapshot: '',
        timing: {
          total_time_ms: totalTime,
          snapshot_time_ms: 0,
        },
      };
    }
  }

}

