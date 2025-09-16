/**
 * Parse snapshot text to extract parent-child relationships
 */

export interface SnapshotNode {
  ref: string;
  type: string;
  text?: string;
  attributes: Record<string, string>;
  children: string[]; // refs of child elements
  parent?: string; // ref of parent element
}

export function parseSnapshotHierarchy(snapshotText: string): Map<string, SnapshotNode> {
  const nodes = new Map<string, SnapshotNode>();
  const lines = snapshotText.split('\n');
  
  // Stack to track parent elements at each indentation level
  const parentStack: { ref: string; indent: number }[] = [];
  
  for (const line of lines) {
    if (!line.trim()) continue;
    
    const indent = line.length - line.trimStart().length;
    
    // Extract type and optional label
    const headerMatch = line.match(/^\s*(?:-\s*)?'?([a-z0-9_-]+)(?:\s+"((?:[^"\\]|\\.)*)")?/i);
    if (!headerMatch) continue;
    const [, typeRaw, label] = headerMatch;
    const type = (typeRaw || 'unknown');

    const refMatch = line.match(/\[ref=([^\]]+)\]/i);
    if (!refMatch) continue;
    const ref = refMatch[1];

    // Parse bracketed attributes
    const attrs: Record<string, string> = {};
    for (const block of line.matchAll(/\[([^\]]+)\]/g)) {
      const content = block[1];
      if (/^ref=/i.test(content)) continue;
      const attrMatches = content.matchAll(/([a-z0-9_-]+)(?:=(?:"([^"]*)"|'([^']*)'|([^\s\]]+)))?/gi);
      for (const m of attrMatches) {
        const key = m[1].toLowerCase();
        const val = m[2] ?? m[3] ?? m[4] ?? 'true';
        attrs[key] = val;
      }
    }
    
    while (parentStack.length > 0 && parentStack[parentStack.length - 1].indent >= indent) {
      parentStack.pop();
    }
    
    const node: SnapshotNode = {
      ref,
      type: type.toLowerCase(),
      text: label || '',
      attributes: attrs,
      children: [],
      parent: parentStack.length > 0 ? parentStack[parentStack.length - 1].ref : undefined
    };
    
    if (node.parent && nodes.has(node.parent)) {
      nodes.get(node.parent)!.children.push(ref);
    }
    
    nodes.set(ref, node);
    
    parentStack.push({ ref, indent });
  }
  
  return nodes;
}

/**
 * Find clickable elements that should be filtered based on DOM hierarchy
 */
export function filterClickableByHierarchy(
  snapshotText: string,
  clickableElements: Set<string>
): Set<string> {
  const hierarchy = parseSnapshotHierarchy(snapshotText);
  const filtered = new Set<string>(clickableElements);
  const debugInfo: any[] = [];
  
  // Debug clickable elements when enabled
  const DEBUG_SNAPSHOT_PARSER = process.env.DEBUG_SNAPSHOT_PARSER === 'true';
  if (DEBUG_SNAPSHOT_PARSER) {
    clickableElements.forEach(ref => {
      const node = hierarchy.get(ref);
      if (node) {
        console.log(`[Debug] ${ref} type: ${node.type}, parent: ${node.parent || 'none'}`);
      } else {
        console.log(`[Debug] ${ref} NOT FOUND in hierarchy!`);
      }
    });
  }
  
  // First pass: identify parent-child relationships where both are clickable
  const parentChildPairs: Array<{parent: string, child: string, parentType: string, childType: string}> = [];
  
  for (const childRef of clickableElements) {
    const childNode = hierarchy.get(childRef);
    if (!childNode || !childNode.parent) continue;
    
    const parentRef = childNode.parent;
    if (clickableElements.has(parentRef)) {
      const parentNode = hierarchy.get(parentRef);
      if (parentNode) {
        parentChildPairs.push({
          parent: parentRef,
          child: childRef,
          parentType: parentNode.type.toLowerCase(),
          childType: childNode.type.toLowerCase()
        });
        
        // Debug specific pairs
        if ((parentRef === 'e296' && childRef === 'e297') ||
            (parentRef === 'e361' && childRef === 'e363') ||
            (parentRef === 'e371' && childRef === 'e373') ||
            (parentRef === 'e344' && childRef === 'e346') ||
            (parentRef === 'e348' && childRef === 'e350')) {
          console.log(`[Debug] Found pair: ${parentRef} (${parentNode.type}) -> ${childRef} (${childNode.type})`);
        }
      }
    }
  }
  
  // Decide which elements to filter based on parent-child relationships
  for (const pair of parentChildPairs) {
    const { parent, child, parentType, childType } = pair;
    
    // Rules for what to filter:
    // 1. link > img: filter img (keep link)
    // 2. button > generic: filter generic (keep button)  
    // 3. generic > button: filter generic (keep button)
    // 4. link > generic: filter generic (keep link)
    // 5. generic > generic: filter child (keep parent)
    // 6. generic > unknown: filter child (keep parent)
    
    if ((parentType === 'link' && childType === 'img') ||
        (parentType === 'button' && childType === 'generic') ||
        (parentType === 'link' && childType === 'generic') ||
        (parentType === 'generic' && childType === 'generic') ||
        (parentType === 'generic' && childType === 'unknown')) {
      // Filter child
      filtered.delete(child);
      console.log(`[Hierarchy Filter] Filtered ${child} (${childType}) - keeping parent ${parent} (${parentType})`);
    } else if (parentType === 'generic' && childType === 'button') {
      // Special case: filter parent generic, keep child button
      filtered.delete(parent);
      console.log(`[Hierarchy Filter] Filtered ${parent} (${parentType}) - keeping child ${child} (${childType})`);
    }
  }
  
  // Original logic for nested hierarchies (keep for deep nesting)
  for (const childRef of clickableElements) {
    if (!filtered.has(childRef)) continue; // Already filtered
    
    const childNode = hierarchy.get(childRef);
    if (!childNode || !childNode.parent) continue;
    
    // Check if any ancestor is a propagating element
    let currentParent: string | undefined = childNode.parent;
    while (currentParent) {
      if (clickableElements.has(currentParent) && filtered.has(currentParent)) {
        const parentNode = hierarchy.get(currentParent);
        if (parentNode) {
          // Check if parent is a propagating element
          const parentType = parentNode.type.toLowerCase();
          const isPropagating = ['button', 'link', 'a'].includes(parentType) ||
            (parentType === 'generic' && parentNode.attributes.cursor === 'pointer' && !parentNode.text);
          
          if (isPropagating) {
            // Filter child elements that should be contained within propagating parents
            const childType = childNode.type.toLowerCase();
            
            // Filter these types of children:
            // 1. Generic elements with cursor=pointer
            // 2. Images within links/buttons
            // 3. Text elements (span, generic without specific role)
            const shouldFilter = 
              (childType === 'generic' && childNode.attributes.cursor === 'pointer') ||
              childType === 'img' ||
              childType === 'span' ||
              (childType === 'generic' && !childNode.attributes.role);
              
            if (shouldFilter) {
              filtered.delete(childRef);
              console.log(`[Hierarchy Filter] Filtered ${childRef} (${childType}) contained in ${currentParent} (${parentType})`);
              break;
            }
          }
        }
      }
      // Move up the hierarchy
      const nextParent = hierarchy.get(currentParent);
      currentParent = nextParent?.parent;
    }
  }
  
  // Additional pass: if a generic parent contains only one button child, filter the parent
  for (const ref of Array.from(filtered)) {
    const node = hierarchy.get(ref);
    if (!node || node.type.toLowerCase() !== 'generic') continue;
    
    // Check if this generic has exactly one clickable child that's a button
    const clickableChildren = node.children.filter(childRef => 
      filtered.has(childRef) && hierarchy.get(childRef)?.type.toLowerCase() === 'button'
    );
    
    if (clickableChildren.length === 1) {
      // This generic wraps a single button - filter it out
      filtered.delete(ref);
      console.log(`[Hierarchy Filter] Filtered ${ref} (generic wrapper around button ${clickableChildren[0]})`);
    }
  }
  
  return filtered;
}