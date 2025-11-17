const WebSocket = require('ws');
const { HybridBrowserToolkit } = require('./dist/index.js');

class WebSocketBrowserServer {
  constructor() {
    this.toolkit = null;
    this.port = 0; // Let the OS assign a free port
    this.server = null;
  }

  async start() {
    return new Promise((resolve, reject) => {
      this.server = new WebSocket.Server({ 
        port: this.port,
        maxPayload: 50 * 1024 * 1024 // 50MB limit instead of default 1MB
      }, () => {
        this.port = this.server.address().port;
        console.log(`WebSocket server started on port ${this.port}`);
        resolve(this.port);
      });

      this.server.on('connection', (ws) => {
        console.log('Client connected');
        
        ws.on('message', async (message) => {
          try {
            const data = JSON.parse(message.toString());
            const { id, command, params } = data;
            
            console.log(`Received command: ${command} with id: ${id}`);
            
            const result = await this.handleCommand(command, params);
            
            const response = {
              id,
              success: true,
              result
            };
            
            ws.send(JSON.stringify(response));
          } catch (error) {
            console.error('Error handling command:', error);
            
            const errorResponse = {
              id: data?.id || 'unknown',
              success: false,
              error: error.message,
              stack: error.stack
            };
            
            ws.send(JSON.stringify(errorResponse));
          }
        });

        ws.on('close', (code, reason) => {
          console.log('Client disconnected, code:', code, 'reason:', reason?.toString());
          // Clean up resources when client disconnects
          if (this.toolkit) {
            this.toolkit.closeBrowser().catch(err => {
              console.error('Error closing browser on disconnect:', err);
            });
          }
        });

        ws.on('error', (error) => {
          console.error('WebSocket error:', error);
        });
      });

      this.server.on('error', (error) => {
        console.error('Server error:', error);
        reject(error);
      });
    });
  }

  async handleCommand(command, params) {
    switch (command) {
      case 'init':
        console.log('Initializing toolkit with params:', JSON.stringify(params, null, 2));
        
        // Check if CDP is available first
        let useCdp = false;
        let cdpUrl = params.cdpUrl || 'http://localhost:9222';
        
        // Extract base URL and port for validation
        const baseUrl = cdpUrl.includes('/devtools/') ? cdpUrl.split('/devtools/')[0] : cdpUrl;
        
        try {
          // Test if Chrome debug port is accessible and get page URL
          const response = await fetch(`${baseUrl}/json`);
          if (response.ok) {
            const pages = await response.json();
            if (pages && pages.length > 0) {
              // If user provided a specific page URL, use it; otherwise use first available
              if (cdpUrl.includes('/devtools/page/') || cdpUrl.includes('/devtools/browser/')) {
                useCdp = true;
                console.log(`Using provided CDP URL: ${cdpUrl}`);
              } else {
                // Use the first available page
                const firstPage = pages[0];
                const pageUrl = firstPage.devtoolsFrontendUrl;
                const pageId = pageUrl.match(/ws=localhost:\d+(.*)$/)?.[1];
                
                if (pageId) {
                  useCdp = true;
                  cdpUrl = `${baseUrl}${pageId}`;
                  console.log(`Chrome debug port detected, using CDP connection to: ${pageId}`);
                }
              }
            }
          }
        } catch (error) {
          console.log('Chrome debug port not accessible, will start new browser instance');
        }
        
        const config = {
          connectOverCdp: useCdp,
          cdpUrl: useCdp ? cdpUrl : undefined,
          headless: false,
          ...params
        };
        
        console.log('Final config:', JSON.stringify(config, null, 2));
        this.toolkit = new HybridBrowserToolkit(config);
        return { message: 'Toolkit initialized with CDP connection' };

      case 'open_browser':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.openBrowser(params.startUrl);

      case 'close_browser':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.closeBrowser();

      case 'visit_page':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.visitPage(params.url);

      case 'get_page_snapshot':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.getPageSnapshot(params.viewport_limit);

      case 'get_snapshot_for_ai': {
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        // Support includeCoordinates and viewportLimit parameters
        const includeCoordinates = Boolean(params.includeCoordinates);
        const viewportLimit = Boolean(params.viewportLimit);
        return await this.toolkit.session.getSnapshotForAI(includeCoordinates, viewportLimit);
      }

      case 'get_som_screenshot': {
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        console.log('Starting screenshot...');
        const startTime = Date.now();
        const result = await this.toolkit.getSomScreenshot();
        const endTime = Date.now();
        console.log(`Screenshot completed in ${endTime - startTime}ms`);
        return result;
      }
      case 'click':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.click(params.ref);

      case 'type':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        // Handle both single input and multiple inputs
        if (params.inputs) {
          // Multiple inputs mode - pass inputs array directly
          return await this.toolkit.type(params.inputs);
        } else {
          // Single input mode - pass ref and text
          return await this.toolkit.type(params.ref, params.text);
        }

      case 'select':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.select(params.ref, params.value);

      case 'scroll':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.scroll(params.direction, params.amount);

      case 'enter':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.enter();
      
      case 'mouse_control':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.mouseControl(params.control, params.x, params.y);

      case 'mouse_drag':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.mouseDrag(params.from_ref, params.to_ref);

      case 'press_key':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.pressKeys(params.keys);

      case 'batch_keyboard_input':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        const skipStabilityWait = params.skipStabilityWait !== undefined ? params.skipStabilityWait : true;
        return await this.toolkit.batchKeyboardInput(params.operations, skipStabilityWait);

      case 'back':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.back();

      case 'forward':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.forward();

      case 'switch_tab':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.switchTab(params.tabId);

      case 'close_tab':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.closeTab(params.tabId);

      case 'get_tab_info':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.getTabInfo();

      case 'console_view':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.getConsoleView();

      case 'console_exec':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.consoleExecute(params.code);

      case 'wait_user':
        if (!this.toolkit) throw new Error('Toolkit not initialized');
        return await this.toolkit.waitUser(params.timeout);

      case 'shutdown': {
        console.log('Shutting down server...');
        
        // Close browser first
        if (this.toolkit) {
          try {
            await this.toolkit.closeBrowser();
          } catch (error) {
            console.error('Error closing browser:', error);
          }
        }
        
        // Return response immediately
        const shutdownResponse = { message: 'Server shutting down' };
        
        // Schedule server shutdown after a short delay to ensure response is sent
        setTimeout(() => {
          // Close the WebSocket server properly
          if (this.server) {
            this.server.close((err) => {
              if (err) {
                console.error('Error closing server:', err);
              } else {
                console.log('WebSocket server closed successfully');
              }
              console.log('Exiting process...');
              process.exit(0);
            });
            
            // Fallback timeout in case server close hangs
            setTimeout(() => {
              console.log('Server close timeout, forcing exit...');
              process.exit(0);
            }, 5000); // 5 second fallback
          } else {
            console.log('No server to close, exiting...');
            process.exit(0);
          }
        }, 100);  // Delay to ensure response is sent
        
        return shutdownResponse;
      }

      default:
        throw new Error(`Unknown command: ${command}`);
    }
  }

  async stop() {
    if (this.server) {
      this.server.close();
      console.log('WebSocket server stopped');
    }
  }
}

// Start server if this file is run directly
if (require.main === module) {
  const server = new WebSocketBrowserServer();
  
  server.start().then((port) => {
    // Output the port so the Python client can connect
    console.log(`SERVER_READY:${port}`);
  }).catch((error) => {
    console.error('Failed to start server:', error);
    process.exit(1);
  });

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.log('Received SIGINT, shutting down gracefully...');
    await server.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.log('Received SIGTERM, shutting down gracefully...');
    await server.stop();
    process.exit(0);
  });
}

module.exports = WebSocketBrowserServer;