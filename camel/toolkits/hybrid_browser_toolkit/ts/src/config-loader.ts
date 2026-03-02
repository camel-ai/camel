export interface StealthConfig {
  enabled: boolean;
  args?: string[];
  userAgent?: string;
  extraHTTPHeaders?: Record<string, string>;
  initScripts?: string[];  // JS scripts to inject before any page loads
}

export interface BrowserConfig {
  // Browser configuration
  headless: boolean;
  userDataDir?: string;
  stealth: StealthConfig;

  // Default settings
  defaultStartUrl: string;

  // Timeout configurations (in milliseconds)
  defaultTimeout?: number;
  shortTimeout?: number;
  navigationTimeout: number;
  networkIdleTimeout: number;
  screenshotTimeout: number;
  pageStabilityTimeout: number;
  domContentLoadedTimeout: number;
  downloadTimeout: number;
  domStabilityTimeout: number;
  domStabilityThreshold: number;

  // Action timeouts
  popupTimeout: number;
  clickTimeout: number;

  // Tab management
  tabIdPrefix: string;
  tabCounterPadding: number;
  consoleLogLimit: number;

  // Scroll and positioning
  scrollPositionScale: number;
  navigationDelay: number;

  // Page states and URLs
  blankPageUrls: string[];
  dataUrlPrefix: string;

  // Wait states
  domContentLoadedState: string;
  networkIdleState: string;

  // HTML attributes
  targetAttribute: string;
  hrefAttribute: string;
  onclickAttribute: string;

  // Target and navigation values
  blankTarget: string;
  windowOpenString: string;
  javascriptVoidPrefix: string;
  javascriptVoidEmpty: string;
  anchorOnly: string;

  // Action options
  forceClick: boolean;
  fullPageScreenshot: boolean;

  // Keyboard keys
  enterKey: string;

  // Other options
  useNativePlaywrightMapping: boolean;
  viewport: {
    width: number;
    height: number;
  };

  // CDP connection options
  connectOverCdp: boolean;
  cdpUrl?: string;
  cdpKeepCurrentPage: boolean;

  // Download file configuration
  downloadDir?: string;
}

export interface WebSocketConfig {
  browser_log_to_file: boolean;
  session_id?: string;
  viewport_limit: boolean;
  fullVisualMode?: boolean;
  nearestElementsCount: number;  // Number of nearest elements to show for ineffective clicks
}

// Default stealth configuration
function getDefaultStealthConfig(): StealthConfig {
  return {
    enabled: false,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
      '--disable-features=VizDisplayCompositor',
      '--no-first-run',
      '--no-default-browser-check',
      '--no-sandbox',
      '--disable-setuid-sandbox',
    ],
    userAgent: undefined,
    extraHTTPHeaders: {},
    initScripts: []
  };
}

// Enhanced stealth configuration that patches common fingerprint leaks
function getEnhancedStealthConfig(): StealthConfig {
  // A realistic Chrome UA (no "HeadlessChrome")
  const realUserAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

  const stealthInitScript = `
    // === Stealth Init Script ===

    // 1. Override navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
      get: () => undefined,
      configurable: true
    });

    // 2. Fake plugins array (Chrome typically has 5 default plugins)
    Object.defineProperty(navigator, 'plugins', {
      get: () => {
        const pluginData = [
          { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
          { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
          { name: 'Chromium PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
          { name: 'Chromium PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
          { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        ];
        const plugins = Object.create(PluginArray.prototype);
        for (let i = 0; i < pluginData.length; i++) {
          const p = Object.create(Plugin.prototype);
          Object.defineProperties(p, {
            name: { value: pluginData[i].name, enumerable: true },
            filename: { value: pluginData[i].filename, enumerable: true },
            description: { value: pluginData[i].description, enumerable: true },
            length: { value: 0, enumerable: true },
          });
          Object.defineProperty(plugins, i, { value: p, enumerable: true });
        }
        Object.defineProperty(plugins, 'length', { value: pluginData.length, enumerable: true });
        plugins.item = (index) => plugins[index] || null;
        plugins.namedItem = (name) => Array.from({length: pluginData.length}, (_, i) => plugins[i]).find(p => p.name === name) || null;
        plugins.refresh = () => {};
        return plugins;
      },
      configurable: true
    });

    // 3. Fake window.chrome object
    if (!window.chrome) {
      window.chrome = {};
    }
    if (!window.chrome.runtime) {
      window.chrome.runtime = {
        connect: function() {},
        sendMessage: function() {},
        onMessage: { addListener: function() {}, removeListener: function() {} },
        id: undefined
      };
    }
    if (!window.chrome.loadTimes) {
      window.chrome.loadTimes = function() {
        return {
          commitLoadTime: Date.now() / 1000,
          connectionInfo: 'http/1.1',
          finishDocumentLoadTime: Date.now() / 1000 + 0.1,
          finishLoadTime: Date.now() / 1000 + 0.2,
          firstPaintAfterLoadTime: 0,
          firstPaintTime: Date.now() / 1000 + 0.05,
          navigationType: 'Other',
          npnNegotiatedProtocol: 'unknown',
          requestTime: Date.now() / 1000 - 0.5,
          startLoadTime: Date.now() / 1000 - 0.4,
          wasAlternateProtocolAvailable: false,
          wasFetchedViaSpdy: false,
          wasNpnNegotiated: false,
        };
      };
    }
    if (!window.chrome.csi) {
      window.chrome.csi = function() {
        return {
          onloadT: Date.now(),
          startE: Date.now() - 500,
          pageT: 500,
          tran: 15,
        };
      };
    }
    if (!window.chrome.app) {
      window.chrome.app = {
        isInstalled: false,
        InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
        RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
        getDetails: function() { return null; },
        getIsInstalled: function() { return false; },
      };
    }

    // 4. Fix Permissions API (headless returns 'prompt' for notifications, real Chrome returns 'denied')
    const originalQuery = window.navigator.permissions.query.bind(window.navigator.permissions);
    window.navigator.permissions.query = (parameters) => {
      if (parameters.name === 'notifications') {
        return Promise.resolve({ state: Notification.permission, onchange: null });
      }
      return originalQuery(parameters);
    };

    // 5. Fake languages (add more variety)
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en', 'zh-CN', 'zh'],
      configurable: true
    });

    // 6. Fake MediaDevices
    if (!navigator.mediaDevices) {
      Object.defineProperty(navigator, 'mediaDevices', {
        get: () => ({
          enumerateDevices: () => Promise.resolve([
            { deviceId: '', groupId: '', kind: 'audioinput', label: '' },
            { deviceId: '', groupId: '', kind: 'videoinput', label: '' },
            { deviceId: '', groupId: '', kind: 'audiooutput', label: '' },
          ]),
          getUserMedia: () => Promise.reject(new DOMException('Not allowed', 'NotAllowedError')),
          getSupportedConstraints: () => ({
            aspectRatio: true, autoGainControl: true, brightness: true,
            channelCount: true, colorTemperature: true, contrast: true,
            deviceId: true, echoCancellation: true, exposureCompensation: true,
            exposureMode: true, facingMode: true, focusDistance: true,
            focusMode: true, frameRate: true, groupId: true, height: true,
            iso: true, latency: true, noiseSuppression: true, pan: true,
            pointsOfInterest: true, resizeMode: true, sampleRate: true,
            sampleSize: true, saturation: true, sharpness: true, tilt: true,
            torch: true, whiteBalanceMode: true, width: true, zoom: true,
          }),
        }),
        configurable: true
      });
    }

    // 7. Override WebGL renderer to hide SwiftShader
    const getParameterProto = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
      // UNMASKED_VENDOR_WEBGL
      if (parameter === 0x9245) return 'Google Inc. (Apple)';
      // UNMASKED_RENDERER_WEBGL
      if (parameter === 0x9246) return 'ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)';
      return getParameterProto.call(this, parameter);
    };
    // Same for WebGL2
    if (typeof WebGL2RenderingContext !== 'undefined') {
      const getParameterProto2 = WebGL2RenderingContext.prototype.getParameter;
      WebGL2RenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 0x9245) return 'Google Inc. (Apple)';
        if (parameter === 0x9246) return 'ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)';
        return getParameterProto2.call(this, parameter);
      };
    }

    // 8. Fake deviceMemory
    Object.defineProperty(navigator, 'deviceMemory', {
      get: () => 8,
      configurable: true
    });

    // 9. Fake hardwareConcurrency (if too low)
    if (navigator.hardwareConcurrency < 4) {
      Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
        configurable: true
      });
    }

    // 10. Prevent toString detection of overridden functions
    const nativeToString = Function.prototype.toString;
    const customFunctions = new Set();
    const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
    // Nothing more needed - the above overrides use defineProperty which is hard to detect
  `;

  return {
    enabled: true,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
      '--disable-features=VizDisplayCompositor',
      '--no-first-run',
      '--no-default-browser-check',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-infobars',
      '--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows',
      '--disable-renderer-backgrounding',
      '--disable-component-update',
      '--disable-hang-monitor',
      '--disable-prompt-on-repost',
      '--disable-sync',
      '--metrics-recording-only',
      '--disable-default-apps',
      '--mute-audio',
      '--disable-extensions',
      '--lang=en-US,en',
    ],
    userAgent: realUserAgent,
    extraHTTPHeaders: {
      'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
      'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"macOS"',
    },
    initScripts: [stealthInitScript]
  };
}

// Default configuration helper function
function getDefaultBrowserConfig(): BrowserConfig {
  return {
    headless: true,
    stealth: getDefaultStealthConfig(),
    defaultStartUrl: 'https://google.com/',
    navigationTimeout: 30000,
    networkIdleTimeout: 5000,
    screenshotTimeout: 15000,
    pageStabilityTimeout: 1500,
    domContentLoadedTimeout: 5000,
    downloadTimeout: 30000,
    domStabilityTimeout: 5000,
    domStabilityThreshold: 200,       // Consider DOM stable if no changes for 200ms
    popupTimeout: 5000,
    clickTimeout: 3000,
    tabIdPrefix: 'tab-',
    tabCounterPadding: 3,
    consoleLogLimit: 1000,
    scrollPositionScale: 0.1,
    navigationDelay: 100,
    blankPageUrls: ['chrome://newtab/', 'edge://newtab/', 'chrome://new-tab-page/'],
    dataUrlPrefix: 'data:',
    domContentLoadedState: 'domcontentloaded',
    networkIdleState: 'networkidle',
    targetAttribute: 'target',
    hrefAttribute: 'href',
    onclickAttribute: 'onclick',
    blankTarget: '_blank',
    windowOpenString: 'window.open',
    javascriptVoidPrefix: 'javascript:void',
    javascriptVoidEmpty: 'javascript:;',
    anchorOnly: '#',
    forceClick: true,
    fullPageScreenshot: false,
    enterKey: 'Enter',
    useNativePlaywrightMapping: true,
    viewport: {
      width: 1280,
      height: 720
    },
    connectOverCdp: false,
    cdpUrl: undefined,
    cdpKeepCurrentPage: false
  };
}

function getDefaultWebSocketConfig(): WebSocketConfig {
  return {
    browser_log_to_file: false,
    viewport_limit: false,
    nearestElementsCount: 5  // Default number of nearest elements for ineffective click detection
  };
}

export class ConfigLoader {
  private browserConfig: BrowserConfig;
  private wsConfig: WebSocketConfig;

  constructor(
    browserConfig: Partial<BrowserConfig> = {},
    wsConfig: Partial<WebSocketConfig> = {}
  ) {
    const defaultConfig = getDefaultBrowserConfig();
    this.browserConfig = {
      ...defaultConfig,
      ...browserConfig,
      stealth: {
        ...defaultConfig.stealth,
        ...(browserConfig.stealth || {})
      }
    };

    this.wsConfig = {
      ...getDefaultWebSocketConfig(),
      ...wsConfig
    };
  }

  getBrowserConfig(): BrowserConfig {
    return { ...this.browserConfig };
  }

  getWebSocketConfig(): WebSocketConfig {
    return { ...this.wsConfig };
  }




  // Merge from Python config format
  static fromPythonConfig(config: any): ConfigLoader {
    const browserConfig: Partial<BrowserConfig> = {};
    const wsConfig: Partial<WebSocketConfig> = {};

    // Map Python config to TypeScript config
    if (config.headless !== undefined) browserConfig.headless = config.headless;
    if (config.userDataDir !== undefined) browserConfig.userDataDir = config.userDataDir;
    if (config.stealth !== undefined) {
      // Handle both boolean and object formats for backward compatibility
      if (typeof config.stealth === 'boolean') {
        if (config.stealth) {
          // Use enhanced stealth config with full anti-detection
          browserConfig.stealth = getEnhancedStealthConfig();
        } else {
          browserConfig.stealth = getDefaultStealthConfig();
        }
      } else {
        browserConfig.stealth = config.stealth;
      }
    }
    if (config.defaultStartUrl !== undefined) browserConfig.defaultStartUrl = config.defaultStartUrl;
    if (config.navigationTimeout !== undefined) browserConfig.navigationTimeout = config.navigationTimeout;
    if (config.networkIdleTimeout !== undefined) browserConfig.networkIdleTimeout = config.networkIdleTimeout;
    if (config.screenshotTimeout !== undefined) browserConfig.screenshotTimeout = config.screenshotTimeout;
    if (config.pageStabilityTimeout !== undefined) browserConfig.pageStabilityTimeout = config.pageStabilityTimeout;
    if (config.domStabilityThreshold !== undefined) browserConfig.domStabilityThreshold = config.domStabilityThreshold;
    if (config.domStabilityTimeout !== undefined) browserConfig.domStabilityTimeout = config.domStabilityTimeout;

    if (config.browser_log_to_file !== undefined) wsConfig.browser_log_to_file = config.browser_log_to_file;
    if (config.session_id !== undefined) wsConfig.session_id = config.session_id;
    if (config.viewport_limit !== undefined) wsConfig.viewport_limit = config.viewport_limit;
    if (config.fullVisualMode !== undefined) wsConfig.fullVisualMode = config.fullVisualMode;
    if (config.nearestElementsCount !== undefined) wsConfig.nearestElementsCount = config.nearestElementsCount;

    // CDP connection options
    if (config.connectOverCdp !== undefined) browserConfig.connectOverCdp = config.connectOverCdp;
    if (config.cdpUrl !== undefined) browserConfig.cdpUrl = config.cdpUrl;
    if (config.cdpKeepCurrentPage !== undefined) browserConfig.cdpKeepCurrentPage = config.cdpKeepCurrentPage;
    if (config.downloadDir !== undefined) browserConfig.downloadDir = config.downloadDir;
    if (config.downloadTimeout !== undefined) browserConfig.downloadTimeout = config.downloadTimeout;

    return new ConfigLoader(browserConfig, wsConfig);
  }

  // Get stealth configuration for browser launch
  getStealthConfig(): StealthConfig {
    return { ...this.browserConfig.stealth };
  }

}
