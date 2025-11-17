import {HybridBrowserSession} from './browser-session';
import {ActionResult, BrowserAction, BrowserToolkitConfig, SnapshotResult, TabInfo, VisualMarkResult} from './types';
import {ConfigLoader} from './config-loader';
import {ConsoleMessage} from 'playwright';
import {SomScreenshotInjected} from './som-screenshot-injected';
import {filterClickableByHierarchy} from './snapshot-parser';

export class HybridBrowserToolkit {
  private session: HybridBrowserSession;
  private config: BrowserToolkitConfig;
  private configLoader: ConfigLoader;
  private viewportLimit: boolean;
  private fullVisualMode: boolean;

  constructor(config: BrowserToolkitConfig = {}) {
    this.configLoader = ConfigLoader.fromPythonConfig(config);
    this.config = config; // Store original config for backward compatibility
    this.session = new HybridBrowserSession(config); // Pass original config
    this.viewportLimit = this.configLoader.getWebSocketConfig().viewport_limit;
    this.fullVisualMode = this.configLoader.getWebSocketConfig().fullVisualMode || false;
  }

  async openBrowser(startUrl?: string): Promise<ActionResult> {
    const startTime = Date.now();
    
    try {
      await this.session.ensureBrowser();
      
      // Check if we should skip navigation in CDP keep-current-page mode
      const browserConfig = this.configLoader.getBrowserConfig();
      if (browserConfig.cdpUrl && browserConfig.cdpKeepCurrentPage && !startUrl) {
        // In CDP keep-current-page mode without explicit URL, just ensure browser and return current page
        const snapshotStart = Date.now();
        const snapshot = await this.getSnapshotForAction(this.viewportLimit);
        const snapshotTime = Date.now() - snapshotStart;
        
        const page = await this.session.getCurrentPage();
        const currentUrl = page ? await page.url() : 'unknown';
        
        const totalTime = Date.now() - startTime;
        
        return {
          success: true,
          message: `Browser opened in CDP keep-current-page mode (current page: ${currentUrl})`,
          snapshot,
          timing: {
            total_time_ms: totalTime,
            snapshot_time_ms: snapshotTime,
          },
        };
      }
      
      // For normal mode or CDP with cdpKeepCurrentPage=false: navigate to URL
      if (!browserConfig.cdpUrl || !browserConfig.cdpKeepCurrentPage) {
        const url = startUrl || this.config.defaultStartUrl || 'https://google.com/';
        const result = await this.session.visitPage(url);
        
        const snapshotStart = Date.now();
        const snapshot = await this.getSnapshotForAction(this.viewportLimit);
        const snapshotTime = Date.now() - snapshotStart;
        
        const totalTime = Date.now() - startTime;
        
        return {
          success: true,
          message: result.message,
          snapshot,
          timing: {
            total_time_ms: totalTime,
            page_load_time_ms: result.timing?.page_load_time_ms || 0,
            snapshot_time_ms: snapshotTime,
          },
        };
      }
      
      // Fallback: Just return current page snapshot without any navigation
      const snapshotStart = Date.now();
      const snapshot = await this.getSnapshotForAction(this.viewportLimit);
      const snapshotTime = Date.now() - snapshotStart;
      
      const totalTime = Date.now() - startTime;
      
      return {
        success: true,
        message: `Browser opened without navigation`,
        snapshot,
        timing: {
          total_time_ms: totalTime,
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
    try {
      // Ensure browser is initialized before visiting page
      await this.session.ensureBrowser();
      
      const result = await this.session.visitPage(url);
      
      // Format response for Python layer compatibility
      const response: any = {
        result: result.message,
        snapshot: '',
      };
      
      if (result.success) {
        const snapshotStart = Date.now();
        response.snapshot = await this.getSnapshotForAction(this.viewportLimit);
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
    } catch (error) {
      console.error('[visitPage] Error:', error);
      return {
        result: `Navigation to ${url} failed: ${error}`,
        snapshot: '',
        timing: {
          total_time_ms: 0,
          navigation_time_ms: 0,
          dom_content_loaded_time_ms: 0,
          network_idle_time_ms: 0,
        }
      };
    }
  }

  async getPageSnapshot(viewportLimit: boolean = false): Promise<string> {
    try {
      // Always return real snapshot when explicitly called
      // If viewport limiting is enabled, we need coordinates for filtering
      const snapshotResult = await this.session.getSnapshotForAI(viewportLimit, viewportLimit);
      return snapshotResult.snapshot;
    } catch (error) {
      return `Error capturing snapshot: ${error}`;
    }
  }
  
  // Internal method for getting snapshot in actions (respects fullVisualMode)
  private async getSnapshotForAction(viewportLimit: boolean = false): Promise<string> {
    if (this.fullVisualMode) {
      return 'full visual mode';
    }
    return this.getPageSnapshot(viewportLimit);
  }


  async getSnapshotForAI(): Promise<SnapshotResult> {
    return await this.session.getSnapshotForAI();
  }

  async getSomScreenshot(): Promise<VisualMarkResult & { timing: any }> {
    const startTime = Date.now();
    console.log('[HybridBrowserToolkit] Starting getSomScreenshot...');
    
    try {
      // Get page and snapshot data
      const page = await this.session.getCurrentPage();
      const snapshotResult = await this.session.getSnapshotForAI(true); // Include coordinates
      
      // Parse clickable elements from snapshot text
      const clickableElements = this.parseClickableElements(snapshotResult.snapshot);
      console.log(`[HybridBrowserToolkit] Found ${clickableElements.size} clickable elements`);
      
      // Apply hierarchy-based filtering
      const filteredElements = filterClickableByHierarchy(snapshotResult.snapshot, clickableElements);
      console.log(`[HybridBrowserToolkit] After filtering: ${filteredElements.size} elements remain`);

      // Use injected SOM-screenshot method without export path
      const result = await SomScreenshotInjected.captureOptimized(
        page,
        snapshotResult,
        filteredElements,
        undefined  // No export path - don't generate files
      );
      
      // Add snapshot timing info to result
      result.timing.snapshot_time_ms = snapshotResult.timing.snapshot_time_ms;
      result.timing.coordinate_enrichment_time_ms = snapshotResult.timing.coordinate_enrichment_time_ms;
      
      return result;
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


  /**
   * Parse clickable elements from snapshot text
   */
  private parseClickableElements(snapshotText: string): Set<string> {
    const clickableElements = new Set<string>();
    const lines = snapshotText.split('\n');
    
    for (const line of lines) {
      // Look for lines containing [cursor=pointer] or [active] and extract ref
      if (line.includes('[cursor=pointer]') || line.includes('[active]')) {
        const refMatch = line.match(/\[ref=([^\]]+)\]/);
        if (refMatch) {
          clickableElements.add(refMatch[1]);
        }
      }
    }
    
    return clickableElements;
  }


  private async executeActionWithSnapshot(action: BrowserAction): Promise<any> {
    const result = await this.session.executeAction(action);
    
    const response: any = {
      result: result.message,
      snapshot: '',
    };
    
    if (result.success) {
      if (result.details?.diffSnapshot) {
        response.snapshot = result.details.diffSnapshot;
        
        if (result.timing) {
          result.timing.snapshot_time_ms = 0; // Diff snapshot time is included in action time
        }
      } else {
        // Get full snapshot as usual
        const snapshotStart = Date.now();
        response.snapshot = await this.getPageSnapshot(this.viewportLimit);
        const snapshotTime = Date.now() - snapshotStart;
        
        if (result.timing) {
          result.timing.snapshot_time_ms = snapshotTime;
        }
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
    
    // Include details if present (excluding diffSnapshot as it's already in snapshot)
    if (result.details) {
      const { diffSnapshot, ...otherDetails } = result.details;
      if (Object.keys(otherDetails).length > 0) {
        response.details = otherDetails;
      }
    }
    
    return response;
  }

  async click(ref: string): Promise<any> {
    const action: BrowserAction = { type: 'click', ref };
    return this.executeActionWithSnapshot(action);
  }

  async type(refOrInputs: string | Array<{ ref: string; text: string }>, text?: string): Promise<any> {
    let action: BrowserAction;
    
    if (typeof refOrInputs === 'string') {
      // Single input mode (backward compatibility)
      if (text === undefined) {
        throw new Error('Text parameter is required when ref is a string');
      }
      action = { type: 'type', ref: refOrInputs, text };
    } else {
      // Multiple inputs mode
      action = { type: 'type', inputs: refOrInputs };
    }
    
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

  async batchKeyboardInput(operations: Array<{type: string, keys?: string[], text?: string, delay?: number}>, skipStabilityWait: boolean = true): Promise<any> {
    return this.session.batchKeyboardInput(operations, skipStabilityWait);
  }

  async back(): Promise<ActionResult> {
    const startTime = Date.now();
    
    try {
      const page = await this.session.getCurrentPage();
      
      const navigationStart = Date.now();
      await page.goBack({ waitUntil: 'domcontentloaded' });
      const navigationTime = Date.now() - navigationStart;
      
      const snapshotStart = Date.now();
      const snapshot = await this.getSnapshotForAction(this.viewportLimit);
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
      const snapshot = await this.getSnapshotForAction(this.viewportLimit);
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
        snapshot: await this.getSnapshotForAction(this.viewportLimit),
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
      const snapshot = await this.getSnapshotForAction(this.viewportLimit);
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

