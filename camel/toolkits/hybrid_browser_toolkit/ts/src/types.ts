export interface SnapshotElement {
  ref: string;
  role: string;
  name: string;
  coordinates?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  disabled?: boolean;
  checked?: boolean;
  expanded?: boolean;
  tagName?: string;
  [key: string]: any;
}


export interface SnapshotResult {
  snapshot: string;
  elements: Record<string, SnapshotElement>;
  metadata: {
    elementCount: number;
    url: string;
    timestamp: string;
  };
}

export interface DetailedTiming {
  total_time_ms: number;
  navigation_time_ms?: number;
  page_load_time_ms?: number;
  stability_wait_time_ms?: number;
  dom_content_loaded_time_ms?: number;
  network_idle_time_ms?: number;
  snapshot_time_ms?: number;
  element_search_time_ms?: number;
  action_execution_time_ms?: number;
  screenshot_time_ms?: number;
  coordinate_enrichment_time_ms?: number;
  visual_marking_time_ms?: number;
  aria_mapping_time_ms?: number;
}

export interface ActionResult {
  success: boolean;
  message: string;
  snapshot?: string;
  details?: Record<string, any>;
  timing?: DetailedTiming;
  newTabId?: string;  // ID of newly opened tab if click opened a new tab
}

export interface TabInfo {
  tab_id: string;
  title: string;
  url: string;
  is_current: boolean;
}

import { StealthConfig } from './config-loader';

export interface BrowserToolkitConfig {
  headless?: boolean;
  userDataDir?: string;
  stealth?: boolean | StealthConfig; // Support both legacy boolean and new object format
  defaultStartUrl?: string;
  navigationTimeout?: number;
  networkIdleTimeout?: number;
  screenshotTimeout?: number;
  pageStabilityTimeout?: number;
  useNativePlaywrightMapping?: boolean; // New option to control mapping implementation
  connectOverCdp?: boolean; // Whether to connect to existing browser via CDP
  cdpUrl?: string; // WebSocket endpoint URL for CDP connection
  cdpKeepCurrentPage?: boolean; // When true, CDP mode will keep the current page instead of creating new one
}

export interface ClickAction {
  type: 'click';
  ref: string;
}

export interface TypeAction {
  type: 'type';
  ref?: string;  // Optional for backward compatibility
  text?: string; // Optional for backward compatibility
  inputs?: Array<{ ref: string; text: string }>; // New field for multiple inputs
}

export interface SelectAction {
  type: 'select';
  ref: string;
  value: string;
}

export interface ScrollAction {
  type: 'scroll';
  direction: 'up' | 'down';
  amount: number;
}

export interface EnterAction {
  type: 'enter';
}

export interface MouseAction {
  type: 'mouse_control';
  control: 'click' | 'right_click' | 'dblclick';
  x: number; 
  y: number; 
}

export interface MouseDragAction {
  type: 'mouse_drag';
  from_ref: string;
  to_ref: string;
}

export interface PressKeyAction {
  type: 'press_key';
  keys: string[];
}

export type BrowserAction = ClickAction | TypeAction | SelectAction | ScrollAction | EnterAction | MouseAction | MouseDragAction | PressKeyAction;

export interface VisualMarkResult {
  text: string;
  images: string[];
}

