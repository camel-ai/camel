/**
 * Browser-side JavaScript utilities for the hybrid browser toolkit
 */

/**
 * Get current scroll position and browser metrics
 */
function getCurrentScrollPosition() {
  return {
    x: window.pageXOffset || document.documentElement.scrollLeft || 0,
    y: window.pageYOffset || document.documentElement.scrollTop || 0,
    devicePixelRatio: window.devicePixelRatio || 1,
    zoomLevel: window.outerWidth / window.innerWidth || 1
  };
}

/**
 * Set target="_blank" attribute for anchor elements
 */
function setTargetBlank(element) {
  if (element.tagName.toLowerCase() === 'a') {
    element.setAttribute('target', '_blank');
  }
}

/**
 * Scroll the page by a specified amount
 */
function scrollPage(amount) {
  window.scrollBy(0, amount);
}

/**
 * Check if browser has specific capability
 */
function checkBrowserCapability(capability) {
  switch (capability) {
    case 'devicePixelRatio':
      return window.devicePixelRatio || 1;
    case 'viewport':
      return {
        width: window.innerWidth,
        height: window.innerHeight
      };
    case 'scroll':
      return {
        x: window.pageXOffset || document.documentElement.scrollLeft || 0,
        y: window.pageYOffset || document.documentElement.scrollTop || 0,
        maxX: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
        maxY: Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
      };
    default:
      return null;
  }
}

/**
 * Get document dimensions
 */
function getDocumentDimensions() {
  return {
    scrollWidth: document.documentElement.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
    clientWidth: document.documentElement.clientWidth,
    clientHeight: document.documentElement.clientHeight,
    offsetWidth: document.documentElement.offsetWidth,
    offsetHeight: document.documentElement.offsetHeight
  };
}

/**
 * Wait for element to be visible or interactable
 */
function waitForElement(selector, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    
    function checkElement() {
      const element = document.querySelector(selector);
      if (element && element.offsetParent !== null) {
        resolve(element);
        return;
      }
      
      if (Date.now() - startTime > timeout) {
        reject(new Error(`Element ${selector} not found within timeout`));
        return;
      }
      
      setTimeout(checkElement, 100);
    }
    
    checkElement();
  });
}

/**
 * Get element coordinates relative to viewport
 */
function getElementCoordinates(element) {
  const rect = element.getBoundingClientRect();
  const scroll = getCurrentScrollPosition();
  
  return {
    x: rect.left + scroll.x,
    y: rect.top + scroll.y,
    width: rect.width,
    height: rect.height,
    viewportX: rect.left,
    viewportY: rect.top
  };
}

// Export for use in evaluate() calls
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getCurrentScrollPosition,
    setTargetBlank,
    scrollPage,
    checkBrowserCapability,
    getDocumentDimensions,
    waitForElement,
    getElementCoordinates
  };
}