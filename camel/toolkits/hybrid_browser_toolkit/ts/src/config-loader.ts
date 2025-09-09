export interface StealthConfig {
  enabled: boolean;
  args?: string[];
  userAgent?: string;
  extraHTTPHeaders?: Record<string, string>;
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
}

export interface WebSocketConfig {
  browser_log_to_file: boolean;
  session_id?: string;
  viewport_limit: boolean;
  fullVisualMode?: boolean;
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
    extraHTTPHeaders: {}
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
    viewport_limit: false
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
        browserConfig.stealth = { 
          enabled: config.stealth,
          args: getDefaultStealthConfig().args
        };
      } else {
        browserConfig.stealth = config.stealth;
      }
    }
    if (config.defaultStartUrl !== undefined) browserConfig.defaultStartUrl = config.defaultStartUrl;
    if (config.navigationTimeout !== undefined) browserConfig.navigationTimeout = config.navigationTimeout;
    if (config.networkIdleTimeout !== undefined) browserConfig.networkIdleTimeout = config.networkIdleTimeout;
    if (config.screenshotTimeout !== undefined) browserConfig.screenshotTimeout = config.screenshotTimeout;
    if (config.pageStabilityTimeout !== undefined) browserConfig.pageStabilityTimeout = config.pageStabilityTimeout;
    
    if (config.browser_log_to_file !== undefined) wsConfig.browser_log_to_file = config.browser_log_to_file;
    if (config.session_id !== undefined) wsConfig.session_id = config.session_id;
    if (config.viewport_limit !== undefined) wsConfig.viewport_limit = config.viewport_limit;
    if (config.fullVisualMode !== undefined) wsConfig.fullVisualMode = config.fullVisualMode;
    
    // CDP connection options
    if (config.connectOverCdp !== undefined) browserConfig.connectOverCdp = config.connectOverCdp;
    if (config.cdpUrl !== undefined) browserConfig.cdpUrl = config.cdpUrl;
    if (config.cdpKeepCurrentPage !== undefined) browserConfig.cdpKeepCurrentPage = config.cdpKeepCurrentPage;

    return new ConfigLoader(browserConfig, wsConfig);
  }

  // Get stealth configuration for browser launch
  getStealthConfig(): StealthConfig {
    return { ...this.browserConfig.stealth };
  }

}