/**
 * Parent-child filtering logic for SOM-labels
 * Filters out child elements that are contained within propagating parent elements
 */

export interface ElementInfo {
  ref: string;
  coordinates?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  role?: string;
  type?: string;
  tagName?: string;
  attributes?: Record<string, any>;
  text?: string;
}

// Elements that propagate bounds to their children
const PROPAGATING_ELEMENTS = [
  { tag: 'a', role: null },
  { tag: 'button', role: null },
  { tag: 'div', role: 'button' },
  { tag: 'div', role: 'combobox' },
  { tag: 'span', role: 'button' },
  { tag: 'span', role: 'combobox' },
  { tag: 'input', role: 'combobox' },
];

const CONTAINMENT_THRESHOLD = 0.99; // 99% containment required

/**
 * Check if element is a propagating element
 */
function isPropagatingElement(element: ElementInfo): boolean {
  const tagName = element.tagName || element.type || '';
  const tag = tagName.toLowerCase();
  const role = element.role || element.attributes?.role || null;
  
  // For generic elements with cursor=pointer, we need to be more selective
  // Only treat them as propagating if they don't have text content
  // (text-containing generics are usually labels, not containers)
  if ((tag === 'generic' || element.type === 'generic') && 
      element.attributes?.['cursor'] === 'pointer') {
    // If element has direct text content, it's likely a label, not a container
    if (element.text && element.text.trim()) {
      return false;
    }
    // If no text, it might be a container
    return true;
  }
  
  for (const pattern of PROPAGATING_ELEMENTS) {
    if (pattern.tag === tag) {
      if (pattern.role === null || pattern.role === role) {
        return true;
      }
    }
  }
  return false;
}

/**
 * Check if child bounds are contained within parent bounds
 */
function isContained(
  childBounds: { x: number; y: number; width: number; height: number },
  parentBounds: { x: number; y: number; width: number; height: number },
  threshold: number
): boolean {
  // Calculate intersection
  const xOverlap = Math.max(0, 
    Math.min(childBounds.x + childBounds.width, parentBounds.x + parentBounds.width) - 
    Math.max(childBounds.x, parentBounds.x)
  );
  const yOverlap = Math.max(0,
    Math.min(childBounds.y + childBounds.height, parentBounds.y + parentBounds.height) - 
    Math.max(childBounds.y, parentBounds.y)
  );
  
  const intersectionArea = xOverlap * yOverlap;
  const childArea = childBounds.width * childBounds.height;
  
  if (childArea === 0) return false;
  
  return (intersectionArea / childArea) >= threshold;
}

/**
 * Check if child element should be filtered out
 */
function shouldFilterChild(childEl: ElementInfo, parentEl: ElementInfo): boolean {
  // Never filter if parent is not a propagating element
  if (!isPropagatingElement(parentEl)) {
    return false;
  }
  
  // Never filter if elements don't have coordinates
  if (!childEl.coordinates || !parentEl.coordinates) {
    return false;
  }
  
  // Check containment
  if (!isContained(childEl.coordinates, parentEl.coordinates, CONTAINMENT_THRESHOLD)) {
    return false;
  }
  
  const childTag = (childEl.tagName || childEl.type || '').toLowerCase();
  const childRole = childEl.role || childEl.attributes?.role || null;
  
  // Exception rules - never filter these:
  
  // 1. Form elements (need individual interaction)
  if (['input', 'select', 'textarea', 'label'].includes(childTag)) {
    return false;
  }
  
  // 2. Child is also a propagating element (might have stopPropagation)
  if (isPropagatingElement(childEl)) {
    return false;
  }
  
  // 3. Has onclick handler
  if (childEl.attributes?.onclick) {
    return false;
  }
  
  // 4. Has meaningful aria-label
  if (childEl.attributes?.['aria-label']?.trim()) {
    return false;
  }
  
  // 5. Has interactive role
  if (['button', 'link', 'checkbox', 'radio', 'tab', 'menuitem'].includes(childRole || '')) {
    return false;
  }
  
  // Default: filter this child
  return true;
}

/**
 * Filter clickable elements based on parent-child relationships
 * @param elements - Map of all elements with their info
 * @param clickableRefs - Set of refs that are clickable
 * @returns Filtered set of element refs and debug info
 */
export function filterParentChildElements(
  elements: Record<string, ElementInfo>,
  clickableRefs: Set<string>
): {
  filteredElements: Set<string>;
  debugInfo: any[];
} {
  const elementRefs = Array.from(clickableRefs);
  const filteredElements = new Set<string>(elementRefs);
  const debugInfo: any[] = [];
  
  console.log(`[Parent-Child Filter] Analyzing ${elementRefs.length} clickable elements`);
  
  // Check each pair of elements for parent-child filtering
  for (let i = 0; i < elementRefs.length; i++) {
    const parentRef = elementRefs[i];
    const parentEl = elements[parentRef];
    
    if (!parentEl?.coordinates) continue;
    
    const isParentPropagating = isPropagatingElement(parentEl);
    
    for (let j = 0; j < elementRefs.length; j++) {
      if (i === j) continue;
      
      const childRef = elementRefs[j];
      const childEl = elements[childRef];
      
      if (!childEl?.coordinates) continue;
      
      // Debug parent-child relationships when enabled
      const DEBUG_PARENT_CHILD = process.env.DEBUG_PARENT_CHILD === 'true';
      if (DEBUG_PARENT_CHILD) {
        const shouldFilter = shouldFilterChild(childEl, parentEl);
        console.log(`\n[Debug] Checking ${parentRef} -> ${childRef}:`);
        console.log(`Parent:`, {
          ref: parentRef, 
          type: parentEl.type || parentEl.tagName, 
          role: parentEl.role,
          coords: parentEl.coordinates,
          isPropagating: isParentPropagating
        });
        console.log(`Child:`, {
          ref: childRef, 
          type: childEl.type || childEl.tagName, 
          role: childEl.role,
          coords: childEl.coordinates
        });
        console.log(`Should filter? ${shouldFilter}`);
      }
      
      if (shouldFilterChild(childEl, parentEl)) {
        filteredElements.delete(childRef);
        
        debugInfo.push({
          type: 'filtered',
          childRef,
          parentRef,
          reason: 'Contained within propagating parent',
          parentType: parentEl.type || parentEl.tagName,
          childType: childEl.type || childEl.tagName,
          parentRole: parentEl.role,
          childRole: childEl.role,
          containment: isContained(childEl.coordinates, parentEl.coordinates, CONTAINMENT_THRESHOLD)
        });
      }
    }
  }
  
  const filteredCount = elementRefs.length - filteredElements.size;
  console.log(`[Parent-Child Filter] Filtered out ${filteredCount} child elements`);
  
  return {
    filteredElements,
    debugInfo
  };
}