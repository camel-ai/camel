(() => {
    // Unified analyzer that combines visual and structural analysis
    // Preserves complete snapshot.js logic while adding visual coordinate information

    // Memory management constants and configuration
    const MAX_REFS = 2000; // Maximum number of refs to keep in memory
    const MAX_UNUSED_AGE_MS = 90000; // Remove refs unused for more than xx seconds
    const CLEANUP_THRESHOLD = 0.8; // Start aggressive cleanup when 80% of max refs reached

    // Persistent ref management across page analysis calls with memory leak prevention
    let refCounter = window.__camelRefCounter || 1;
    let elementRefMap = window.__camelElementRefMap || new WeakMap();
    let refElementMap = window.__camelRefElementMap || new Map();
    let elementSignatureMap = window.__camelElementSignatureMap || new Map();
    
    // LRU tracking for ref access times
    let refAccessTimes = window.__camelRefAccessTimes || new Map();
    let lastNavigationUrl = window.__camelLastNavigationUrl || window.location.href;

    // Initialize navigation event listeners for automatic cleanup
    if (!window.__camelNavigationListenersInitialized) {
        window.__camelNavigationListenersInitialized = true;
        
        // Listen for page navigation events
        window.addEventListener('beforeunload', clearAllRefs);
        window.addEventListener('pagehide', clearAllRefs);
        
        // Listen for pushState/replaceState navigation (SPA navigation)
        const originalPushState = history.pushState;
        const originalReplaceState = history.replaceState;
        
        history.pushState = function(...args) {
            clearAllRefs();
            return originalPushState.apply(this, args);
        };
        
        history.replaceState = function(...args) {
            clearAllRefs();
            return originalReplaceState.apply(this, args);
        };
        
        // Listen for popstate (back/forward navigation)
        window.addEventListener('popstate', clearAllRefs);
        
        // Check for URL changes periodically (fallback for other navigation types)
        setInterval(() => {
            if (window.location.href !== lastNavigationUrl) {
                clearAllRefs();
                lastNavigationUrl = window.location.href;
                window.__camelLastNavigationUrl = lastNavigationUrl;
            }
        }, 1000);
    }

    function generateRef() {
        const ref = `e${refCounter++}`;
        // Persist counter globally
        window.__camelRefCounter = refCounter;
        return ref;
    }

    // Clear all refs and reset memory state
    function clearAllRefs() {
        try {
            // Clear all DOM aria-ref attributes
            document.querySelectorAll('[aria-ref]').forEach(element => {
                element.removeAttribute('aria-ref');
            });
            
            // Clear all maps and reset counters
            elementRefMap.clear();
            refElementMap.clear();
            elementSignatureMap.clear();
            refAccessTimes.clear();
            
            // Reset global state
            window.__camelElementRefMap = elementRefMap;
            window.__camelRefElementMap = refElementMap;
            window.__camelElementSignatureMap = elementSignatureMap;
            window.__camelRefAccessTimes = refAccessTimes;
            
            // Clear cached analysis results
            delete window.__camelLastAnalysisResult;
            delete window.__camelLastAnalysisTime;
            
            console.log('CAMEL: Cleared all refs due to navigation');
        } catch (error) {
            console.warn('CAMEL: Error clearing refs:', error);
        }
    }

    // LRU eviction: Remove least recently used refs when limit exceeded
    function evictLRURefs() {
        const refsToEvict = refAccessTimes.size - MAX_REFS + Math.floor(MAX_REFS * 0.1); // Remove 10% extra for breathing room
        if (refsToEvict <= 0) return 0;

        // Sort refs by access time (oldest first)
        const sortedRefs = Array.from(refAccessTimes.entries())
            .sort((a, b) => a[1] - b[1])
            .slice(0, refsToEvict);

        let evictedCount = 0;
        for (const [ref, _] of sortedRefs) {
            const element = refElementMap.get(ref);
            if (element) {
                // Remove aria-ref attribute from DOM
                try {
                    element.removeAttribute('aria-ref');
                } catch (e) {
                    // Element might be detached from DOM
                }
                elementRefMap.delete(element);
                
                // Remove from signature map
                const signature = generateElementSignature(element);
                if (signature && elementSignatureMap.get(signature) === ref) {
                    elementSignatureMap.delete(signature);
                }
            }
            
            refElementMap.delete(ref);
            refAccessTimes.delete(ref);
            evictedCount++;
        }

        // Persist updated maps
        window.__camelElementRefMap = elementRefMap;
        window.__camelRefElementMap = refElementMap;
        window.__camelElementSignatureMap = elementSignatureMap;
        window.__camelRefAccessTimes = refAccessTimes;

        return evictedCount;
    }

    // Update ref access time for LRU tracking
    function updateRefAccessTime(ref) {
        refAccessTimes.set(ref, Date.now());
        window.__camelRefAccessTimes = refAccessTimes;
    }

    // Generate a unique signature for an element based on its characteristics
    function generateElementSignature(element) {
        if (!element || !element.tagName) return null;

        const tagName = element.tagName.toLowerCase();
        const textContent = (element.textContent || '').trim().substring(0, 50);
        const className = element.className || '';
        const id = element.id || '';
        const href = element.href || '';
        const src = element.src || '';
        const value = element.value || '';
        const type = element.type || '';
        const placeholder = element.placeholder || '';

        // Include position in DOM tree for uniqueness
        let pathElements = [];
        let current = element;
        let depth = 0;
        while (current && current.parentElement && depth < 5) {
            const siblings = Array.from(current.parentElement.children);
            const index = siblings.indexOf(current);
            pathElements.unshift(`${current.tagName.toLowerCase()}[${index}]`);
            current = current.parentElement;
            depth++;
        }
        const domPath = pathElements.join('>');

        return `${tagName}|${textContent}|${className}|${id}|${href}|${src}|${value}|${type}|${placeholder}|${domPath}`;
    }

    // Get or assign a persistent ref for an element
    function getOrAssignRef(element) {
        // Check if element already has a ref assigned
        if (elementRefMap.has(element)) {
            const existingRef = elementRefMap.get(element);
            // Verify the ref is still valid
            if (refElementMap.get(existingRef) === element) {
                updateRefAccessTime(existingRef);
                return existingRef;
            }
        }

        // Check if element has aria-ref attribute (from previous analysis)
        const existingAriaRef = element.getAttribute('aria-ref');
        if (existingAriaRef && refElementMap.get(existingAriaRef) === element) {
            // Re-establish mappings
            elementRefMap.set(element, existingAriaRef);
            updateRefAccessTime(existingAriaRef);
            return existingAriaRef;
        }

        // Try to find element by signature (in case DOM was modified)
        const signature = generateElementSignature(element);
        if (signature && elementSignatureMap.has(signature)) {
            const existingRef = elementSignatureMap.get(signature);
            // Verify the old element is no longer in DOM or has changed
            const oldElement = refElementMap.get(existingRef);
            if (!oldElement || !document.contains(oldElement) || generateElementSignature(oldElement) !== signature) {
                // Reassign the ref to the new element
                elementRefMap.set(element, existingRef);
                refElementMap.set(existingRef, element);
                elementSignatureMap.set(signature, existingRef);
                element.setAttribute('aria-ref', existingRef);
                updateRefAccessTime(existingRef);
                return existingRef;
            }
        }

        // Check if we need to evict refs before creating new ones
        if (refElementMap.size >= MAX_REFS) {
            evictLRURefs();
        }

        // Generate new ref for new element
        const newRef = generateRef();
        elementRefMap.set(element, newRef);
        refElementMap.set(newRef, element);
        if (signature) {
            elementSignatureMap.set(signature, newRef);
        }
        element.setAttribute('aria-ref', newRef);
        updateRefAccessTime(newRef);
        return newRef;
    }

    // Enhanced cleanup function with aggressive stale ref removal
    function cleanupStaleRefs() {
        const staleRefs = [];
        const currentTime = Date.now();
        const isAggressiveCleanup = refElementMap.size > (MAX_REFS * CLEANUP_THRESHOLD);

        // Check all mapped elements to see if they're still in DOM or too old
        for (const [ref, element] of refElementMap.entries()) {
            let shouldRemove = false;

            // Standard checks: element not in DOM
            if (!element || !document.contains(element)) {
                shouldRemove = true;
            }
            // Aggressive cleanup: remove refs unused for too long
            else if (isAggressiveCleanup) {
                const lastAccess = refAccessTimes.get(ref) || 0;
                const age = currentTime - lastAccess;
                if (age > MAX_UNUSED_AGE_MS) {
                    shouldRemove = true;
                }
            }
            // Additional checks for aggressive cleanup
            else if (isAggressiveCleanup) {
                // Remove refs for elements that are hidden or have no meaningful content
                try {
                    const style = window.getComputedStyle(element);
                    const hasNoVisibleContent = !element.textContent?.trim() && 
                                               !element.value?.trim() && 
                                               !element.src && 
                                               !element.href;
                    
                    if ((style.display === 'none' || style.visibility === 'hidden') && hasNoVisibleContent) {
                        shouldRemove = true;
                    }
                } catch (e) {
                    // If we can't get computed style, element might be detached
                    shouldRemove = true;
                }
            }

            if (shouldRemove) {
                staleRefs.push(ref);
            }
        }

        // Remove stale mappings
        for (const ref of staleRefs) {
            const element = refElementMap.get(ref);
            if (element) {
                // Remove aria-ref attribute from DOM
                try {
                    element.removeAttribute('aria-ref');
                } catch (e) {
                    // Element might be detached from DOM
                }
                elementRefMap.delete(element);
                
                // Remove from signature map
                const signature = generateElementSignature(element);
                if (signature && elementSignatureMap.get(signature) === ref) {
                    elementSignatureMap.delete(signature);
                }
            }
            refElementMap.delete(ref);
            refAccessTimes.delete(ref);
        }

        // Persist maps globally
        window.__camelElementRefMap = elementRefMap;
        window.__camelRefElementMap = refElementMap;
        window.__camelElementSignatureMap = elementSignatureMap;
        window.__camelRefAccessTimes = refAccessTimes;

        return staleRefs.length;
    }

    // === Complete snapshot.js logic preservation ===

    function isVisible(node) {
        // Check if node is null or not a valid DOM node
        if (!node || typeof node.nodeType === 'undefined') return false;
        if (node.nodeType !== Node.ELEMENT_NODE) return true;

        try {
        const style = window.getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0')
                return false;
            // An element with `display: contents` is not rendered itself, but its children are.
            if (style.display === 'contents')
                return true;
            const rect = node.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        } catch (e) {
            // If there's an error getting computed style or bounding rect, assume element is not visible
            return false;
        }
    }

    // Optimized occlusion detection with fewer test points
    function isOccluded(element) {
        if (!element || element.nodeType !== Node.ELEMENT_NODE) return false;

        try {
            const rect = element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return true;

            // Simplified: Use fewer test points for better performance
            const testPoints = [
                // Center point (most important)
                { x: rect.left + rect.width * 0.5, y: rect.top + rect.height * 0.5, weight: 4 },
                // Only test 4 strategic points instead of 9
                { x: rect.left + rect.width * 0.25, y: rect.top + rect.height * 0.25, weight: 1 },
                { x: rect.left + rect.width * 0.75, y: rect.top + rect.height * 0.25, weight: 1 },
                { x: rect.left + rect.width * 0.25, y: rect.top + rect.height * 0.75, weight: 1 },
                { x: rect.left + rect.width * 0.75, y: rect.top + rect.height * 0.75, weight: 1 }
            ];

            let totalWeight = 0;
            let visibleWeight = 0;

            for (const point of testPoints) {
                // Skip points outside viewport
                if (point.x < 0 || point.y < 0 ||
                    point.x >= window.innerWidth || point.y >= window.innerHeight) {
                    continue;
                }

                const hitElement = document.elementFromPoint(point.x, point.y);
                totalWeight += point.weight;

                // Simplified visibility check
                if (hitElement && (hitElement === element || element.contains(hitElement) || hitElement.contains(element))) {
                    visibleWeight += point.weight;
                }
            }

            // If no valid test points, assume not occluded
            if (totalWeight === 0) return false;

            // Element is occluded if less than 40% of weighted points are visible
            return (visibleWeight / totalWeight) < 0.4;

        } catch (e) {
            return false;
        }
    }

    function getRole(node) {
        // Check if node is null or doesn't have required properties
        if (!node || !node.tagName || !node.getAttribute) {
            return 'generic';
        }

        const role = node.getAttribute('role');
        if (role) return role;

        const tagName = node.tagName.toLowerCase();

        // Extended role mapping to better match Playwright
        if (tagName === 'a') return 'link';
        if (tagName === 'button') return 'button';
        if (tagName === 'input') {
            const type = node.getAttribute('type')?.toLowerCase();
            if (['button', 'checkbox', 'radio', 'reset', 'submit'].includes(type)) return type;
            return 'textbox';
        }
        if (['select', 'textarea'].includes(tagName)) return tagName;
        if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) return 'heading';

        // Additional roles for better Playwright compatibility
        if (tagName === 'img') return 'img';
        if (tagName === 'main') return 'main';
        if (tagName === 'nav') return 'navigation';
        if (tagName === 'ul' || tagName === 'ol') return 'list';
        if (tagName === 'li') return 'listitem';
        if (tagName === 'em') return 'emphasis';
        if (tagName === 'form' && node.getAttribute('role') === 'search') return 'search';
        if (tagName === 'section' || tagName === 'article') return 'region';
        if (tagName === 'aside') return 'complementary';
        if (tagName === 'header') return 'banner';
        if (tagName === 'footer') return 'contentinfo';
        if (tagName === 'fieldset') return 'group';

        return 'generic';
    }

    // Playwright-inspired function to check if element receives pointer events
    function receivesPointerEvents(element) {
        if (!element || !element.nodeType || element.nodeType !== Node.ELEMENT_NODE) return false;

        try {
            let e = element;
            while (e) {
                const style = window.getComputedStyle(e);
                if (!style) break;

                const pointerEvents = style.pointerEvents;
                if (pointerEvents === 'none') return false;
                if (pointerEvents && pointerEvents !== 'auto') return true;

                e = e.parentElement;
            }
            return true;
        } catch (error) {
            return false;
        }
    }

    // Playwright-inspired function to check if element has pointer cursor
    function hasPointerCursor(element) {
        if (!element || !element.nodeType || element.nodeType !== Node.ELEMENT_NODE) return false;

        try {
            const style = window.getComputedStyle(element);
            return style.cursor === 'pointer';
        } catch (error) {
            return false;
        }
    }

    // Playwright-inspired function to get aria level
    function getAriaLevel(element) {
        if (!element || !element.tagName) return 0;

        // Native HTML heading levels (H1=1, H2=2, etc.)
        const tagName = element.tagName.toUpperCase();
        const nativeLevel = { 'H1': 1, 'H2': 2, 'H3': 3, 'H4': 4, 'H5': 5, 'H6': 6 }[tagName];
        if (nativeLevel) return nativeLevel;

        // Check aria-level attribute for roles that support it
        const role = getRole(element);
        const kAriaLevelRoles = ['heading', 'listitem', 'row', 'treeitem'];
        if (kAriaLevelRoles.includes(role)) {
            const ariaLevel = element.getAttribute('aria-level');
            if (ariaLevel !== null) {
                const value = Number(ariaLevel);
                if (Number.isInteger(value) && value >= 1) {
                    return value;
                }
            }
        }

        return 0;
    }

    function getAccessibleName(node) {
        // Check if node is null or doesn't have required methods
        if (!node || !node.hasAttribute || !node.getAttribute) return '';

        if (node.hasAttribute('aria-label')) return node.getAttribute('aria-label') || '';
        if (node.hasAttribute('aria-labelledby')) {
            const id = node.getAttribute('aria-labelledby');
            const labelEl = document.getElementById(id);
            if (labelEl) return labelEl.textContent || '';
        }
        // This is the new, visibility-aware text extraction logic.
        const text = getVisibleTextContent(node);

        // Add a heuristic to ignore code-like text that might be in the DOM
        if ((text.match(/[;:{}]/g)?.length || 0) > 2) return '';
        return text;
        }

    const textCache = new Map();
    function getVisibleTextContent(_node) {
        // Check if node is null or doesn't have nodeType
        if (!_node || typeof _node.nodeType === 'undefined') return '';

        if (textCache.has(_node)) return textCache.get(_node);

        if (_node.nodeType === Node.TEXT_NODE) {
            // For a text node, its content is visible if its parent is.
            // The isVisible check on the parent happens before this recursion.
            return _node.nodeValue || '';
        }

        if (_node.nodeType !== Node.ELEMENT_NODE || !isVisible(_node) || ['SCRIPT', 'STYLE', 'NOSCRIPT', 'META', 'HEAD'].includes(_node.tagName)) {
            return '';
        }

        let result = '';
        for (const child of _node.childNodes) {
            result += getVisibleTextContent(child);
        }

        // Caching the result for performance.
        textCache.set(_node, result);
        return result;
    }

    /**
     * Phase 1: Build an in-memory representation of the accessibility tree.
     * Complete preservation of snapshot.js buildAriaTree logic
     */
    function buildAriaTree(rootElement) {
        const visited = new Set();

        function toAriaNode(element) {
            // Check if element is null or not a valid DOM element
            if (!element || !element.tagName) return null;

            // Only consider visible elements
            if (!isVisible(element)) return null;

            const role = getRole(element);
            // 'presentation' and 'none' roles are ignored, but their children are processed.
            if (['presentation', 'none'].includes(role)) return null;

            const name = getAccessibleName(element);

            // Get persistent ref for this element
            const ref = getOrAssignRef(element);

            // Create the node
            const node = {
                role,
                name,
                children: [],
                element: element,
                ref: ref,
            };

            // Add states for interactive elements, similar to Playwright
            if (element.hasAttribute('disabled') || element.disabled) node.disabled = true;

            // NEW: Check if element is occluded and mark with occluded tag
            if (isOccluded(element)) {
                node.occluded = true; // Mark as occluded but don't disable
            }

            // Handle aria-checked and native checked
            const ariaChecked = element.getAttribute('aria-checked');
            if (ariaChecked) {
                node.checked = ariaChecked;
            } else if (element.type === 'checkbox' || element.type === 'radio') {
                node.checked = element.checked;
            }

            // Handle aria-expanded
            const ariaExpanded = element.getAttribute('aria-expanded');
            if (ariaExpanded) {
                node.expanded = ariaExpanded === 'true';
            }

            // Handle aria-selected
            const ariaSelected = element.getAttribute('aria-selected');
            if (ariaSelected === 'true') {
                node.selected = true;
            }

            // Add level support following Playwright's implementation
            const level = getAriaLevel(element);
            if (level > 0) node.level = level;

            return node;
        }

        function traverse(element, parentNode) {
            // Check if element is null or not a valid DOM element
            if (!element || !element.tagName || visited.has(element)) return;
            visited.add(element);

            // FIX: Completely skip script and style tags and their children.
            const tagName = element.tagName.toLowerCase();
            if (['script', 'style', 'meta', 'noscript'].includes(tagName))
                return;

            // Check if element is explicitly hidden by CSS - if so, skip entirely including children
            const style = window.getComputedStyle(element);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                return;
            }

            const ariaNode = toAriaNode(element);
            // If the element is not rendered or is presentational, its children
            // are attached directly to the parent.
            const newParent = ariaNode || parentNode;
            if (ariaNode) parentNode.children.push(ariaNode);

            for (const child of element.childNodes) {
                if (child.nodeType === Node.ELEMENT_NODE) {
                    traverse(child, newParent);
                } else if (child.nodeType === Node.TEXT_NODE) {
                    const text = (child.textContent || '').trim();
                    if (text) newParent.children.push(text);
                }
            }

            // Also traverse into shadow DOM if it exists
            if (element.shadowRoot) {
                for (const child of element.shadowRoot.childNodes) {
                    if (child.nodeType === Node.ELEMENT_NODE) {
                        traverse(child, newParent);
                    } else if (child.nodeType === Node.TEXT_NODE) {
                        const text = (child.textContent || '').trim();
                        if (text) newParent.children.push(text);
                    }
                }
            }

            // FIX: Remove redundant text children that match the element's name
            if (ariaNode && ariaNode.children.length > 0) {
                // Remove text children that are the same as the parent's name or are contained in it
                ariaNode.children = ariaNode.children.filter(child => {
                    if (typeof child === 'string') {
                        const childText = child.trim();
                        const parentName = ariaNode.name.trim();

                        // Remove if text child exactly matches parent name
                        if (childText === parentName) {
                            return false;
                        }

                        // Also remove if the child text is completely contained in parent name
                        // and represents a significant portion (to avoid removing important partial text)
                        if (childText.length > 3 && parentName.includes(childText)) {
                            return false;
                        }

                        return true;
                    }
                    return true;
                });

                // If after filtering, we have only one text child that equals the name, remove it
                if (ariaNode.children.length === 1 && typeof ariaNode.children[0] === 'string' && ariaNode.name === ariaNode.children[0]) {
                    ariaNode.children = [];
                }
            }
        }

        const root = { role: 'Root', name: '', children: [], element: rootElement };
        traverse(rootElement, root);
        return root;
    }

    /**
     * Phase 2: Normalize the tree by removing redundant generic wrappers.
     * Complete preservation of snapshot.js normalizeTree logic with cursor inheritance
     */
    function normalizeTree(node) {
        if (typeof node === 'string') return [node];

        const newChildren = [];
        for (const child of node.children) {
            newChildren.push(...normalizeTree(child));
        }
        node.children = newChildren;

        // Remove child elements that have the same name as their parent
        // and inherit cursor=pointer property if child had it
        const filteredChildren = [];
        for (const child of node.children) {
            if (typeof child !== 'string' && child.name && node.name) {
                const childName = child.name.trim();
                const parentName = node.name.trim();
                if (childName === parentName) {
                    // If child has same name as parent, merge its children into parent
                    filteredChildren.push(...(child.children || []));

                    // Inherit cursor=pointer from merged child
                    if (child.element && receivesPointerEvents(child.element) && hasPointerCursor(child.element)) {
                        node.inheritedCursor = true;
                    }

                    // Also inherit other properties if needed
                    if (child.disabled && !node.disabled) node.disabled = child.disabled;
                    if (child.selected && !node.selected) node.selected = child.selected;
                } else {
                    filteredChildren.push(child);
                }
            } else {
                filteredChildren.push(child);
            }
        }
        node.children = filteredChildren;

        // Also handle the case where we have only one child with same name
        if (node.children.length === 1 && typeof node.children[0] !== 'string') {
            const child = node.children[0];
            if (child.name && node.name && child.name.trim() === node.name.trim()) {
                // Inherit cursor=pointer from the child being merged
                if (child.element && receivesPointerEvents(child.element) && hasPointerCursor(child.element)) {
                    node.inheritedCursor = true;
                }

                // Also inherit other properties
                if (child.disabled && !node.disabled) node.disabled = child.disabled;
                if (child.selected && !node.selected) node.selected = child.selected;

                // Merge child's children into parent and remove the redundant child
                node.children = child.children || [];
            }
        }

        // A 'generic' role that just wraps a single other element is redundant.
        // We lift its child up to replace it, simplifying the hierarchy.
        const isRedundantWrapper = node.role === 'generic' && node.children.length === 1 && typeof node.children[0] !== 'string';
        if (isRedundantWrapper) {
            return node.children;
        }
        return [node];
    }

    /**
     * Phase 3: Render the normalized tree into the final string format.
     * Complete preservation of snapshot.js renderTree logic with Playwright enhancements
     */
    function renderTree(node, indent = '') {
        const lines = [];
        let meaningfulProps = '';
        if (node.disabled) meaningfulProps += ' [disabled]';
        if (node.occluded) meaningfulProps += ' [occluded]';
        if (node.checked !== undefined) meaningfulProps += ` checked=${node.checked}`;
        if (node.expanded !== undefined) meaningfulProps += ` expanded=${node.expanded}`;
        if (node.selected) meaningfulProps += ' [selected]';

        // Add level attribute following Playwright's format
        if (node.level !== undefined) meaningfulProps += ` [level=${node.level}]`;

        const ref = node.ref ? ` [ref=${node.ref}]` : '';

        // Add cursor=pointer detection following Playwright's implementation
        // Check both direct cursor and inherited cursor from merged children
        let cursor = '';
        const hasDirectCursor = node.element && receivesPointerEvents(node.element) && hasPointerCursor(node.element);
        const hasInheritedCursor = node.inheritedCursor;

        // Only add cursor=pointer if element is not occluded
        if ((hasDirectCursor || hasInheritedCursor) && !node.occluded) {
            cursor = ' [cursor=pointer]';
        }

        const name = (node.name || '').replace(/\s+/g, ' ').trim();

        // Skip elements with empty names and no meaningful props (ref and cursor are not considered meaningful for this check)
        if (!name && !meaningfulProps) {
            // If element has no name and no meaningful props, render its children directly at current level
            for (const child of node.children) {
                if (typeof child === 'string') {
                    const childText = child.replace(/\s+/g, ' ').trim();
                    if (childText) { // Only add non-empty text
                        lines.push(`${indent}- text "${childText}"`);
                    }
                } else {
                    lines.push(...renderTree(child, indent));
                }
            }
            return lines;
        }

        lines.push(`${indent}- ${node.role}${name ? ` "${name}"` : ''}${meaningfulProps}${ref}${cursor}`);

        for (const child of node.children) {
            if (typeof child === 'string') {
                const childText = child.replace(/\s+/g, ' ').trim();
                if (childText) { // Only add non-empty text
                    lines.push(`${indent}  - text "${childText}"`);
                }
            } else {
                lines.push(...renderTree(child, indent + '  '));
            }
        }
        return lines;
    }

    function processDocument(doc) {
        if (!doc.body) return [];

        // Clear cache for each new document processing.
        textCache.clear();
        let tree = buildAriaTree(doc.body);
        [tree] = normalizeTree(tree);

        const lines = renderTree(tree).slice(1); // Skip the root node line

        const frames = doc.querySelectorAll('iframe');
        for (const frame of frames) {
            try {
                if (frame.contentDocument) {
                    lines.push(...processDocument(frame.contentDocument));
                }
            } catch (e) {
                // Skip cross-origin iframes
            }
        }
        return lines;
    }

    // === Visual analysis functions from page_script.js ===

    // From page_script.js - check if element is topmost at coordinates
    function isTopmost(element, x, y) {
        let hit = document.elementFromPoint(x, y);
        if (hit === null) return true;

        while (hit) {
            if (hit == element) return true;
            hit = hit.parentNode;
        }
        return false;
    }

    // From page_script.js - get visual coordinates
    function getElementCoordinates(element) {
        let rects = element.getClientRects();
        let scale = window.devicePixelRatio || 1;
        let validRects = [];

        for (const rect of rects) {
            let x = rect.left + rect.width / 2;
            let y = rect.top + rect.height / 2;
            if (isTopmost(element, x, y)) {
                validRects.push({
                    x: rect.x * scale,
                    y: rect.y * scale,
                    width: rect.width * scale,
                    height: rect.height * scale,
                    top: rect.top * scale,
                    left: rect.left * scale,
                    right: rect.right * scale,
                    bottom: rect.bottom * scale
                });
            }
        }

        return validRects;
    }

    // === Unified analysis function ===

    function collectElementsFromTree(node, elementsMap) {
        if (typeof node === 'string') return;

        if (node.element && node.ref) {
            // Get visual coordinates for this element
            const coordinates = getElementCoordinates(node.element);

            // Store comprehensive element information
            elementsMap[node.ref] = {
                // Structural information (preserved from snapshot.js)
                role: node.role,
                name: node.name,
                tagName: node.element.tagName.toLowerCase(),
                disabled: node.disabled,
                checked: node.checked,
                expanded: node.expanded,
                level: node.level,

                // Visual information (from page_script.js)
                coordinates: coordinates,

                // Additional metadata
                href: node.element.href || null,
                value: node.element.value || null,
                placeholder: node.element.placeholder || null,
                scrollable: node.element.scrollHeight > node.element.clientHeight,

                // Playwright-inspired properties
                receivesPointerEvents: receivesPointerEvents(node.element),
                hasPointerCursor: hasPointerCursor(node.element)
            };
        }

        // Recursively process children
        if (node.children) {
            for (const child of node.children) {
                collectElementsFromTree(child, elementsMap);
            }
        }
    }

    function analyzePageElements() {
        // Clean up stale refs before analysis
        const cleanedRefCount = cleanupStaleRefs();

        // Performance optimization: Check if we can reuse recent analysis
        const currentTime = Date.now();
        const lastAnalysisTime = window.__camelLastAnalysisTime || 0;
        const timeSinceLastAnalysis = currentTime - lastAnalysisTime;

        // If less than 1 second since last analysis and page hasn't changed significantly
        if (timeSinceLastAnalysis < 1000 && window.__camelLastAnalysisResult && cleanedRefCount === 0) {
            const cachedResult = window.__camelLastAnalysisResult;
            // Update timestamp and memory info in cached result
            cachedResult.metadata.timestamp = new Date().toISOString();
            cachedResult.metadata.memoryInfo = {
                currentRefCount: refElementMap.size,
                maxRefs: MAX_REFS,
                memoryUtilization: (refElementMap.size / MAX_REFS * 100).toFixed(1) + '%',
                lruAccessTimesCount: refAccessTimes.size
            };
            cachedResult.metadata.cacheHit = true;
            return cachedResult;
        }

        // Generate the complete structured snapshot using original snapshot.js logic
        const outputLines = processDocument(document);
        const snapshotText = outputLines.join('\n');

        // Build the tree again to collect element information with visual data
        textCache.clear();
        // Note: Don't reset refCounter anymore - use persistent counters
        let tree = buildAriaTree(document.body);
        [tree] = normalizeTree(tree);

        const elementsMap = {};
        collectElementsFromTree(tree, elementsMap);

        // Verify uniqueness of aria-ref attributes (debugging aid)
        const ariaRefCounts = {};
        document.querySelectorAll('[aria-ref]').forEach(element => {
            const ref = element.getAttribute('aria-ref');
            ariaRefCounts[ref] = (ariaRefCounts[ref] || 0) + 1;
        });

        // Log any duplicates for debugging
        const duplicateRefs = Object.entries(ariaRefCounts).filter(([ref, count]) => count > 1);
        if (duplicateRefs.length > 0) {
            console.warn('Duplicate aria-ref attributes found:', duplicateRefs);
        }

        // Validate ref consistency
        const refValidationErrors = [];
        for (const [ref, elementInfo] of Object.entries(elementsMap)) {
            const mappedElement = refElementMap.get(ref);
            if (!mappedElement || !document.contains(mappedElement)) {
                refValidationErrors.push(`Ref ${ref} points to invalid or removed element`);
            }
        }

        const result = {
            url: window.location.href,
            elements: elementsMap,
            snapshotText: snapshotText,
            metadata: {
                timestamp: new Date().toISOString(),
                elementCount: Object.keys(elementsMap).length,
                screenInfo: {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    devicePixelRatio: window.devicePixelRatio || 1
                },
                // Enhanced debugging information
                ariaRefCounts: ariaRefCounts,
                duplicateRefsFound: duplicateRefs.length > 0,
                staleRefsCleanedUp: cleanedRefCount,
                refValidationErrors: refValidationErrors,
                totalMappedRefs: refElementMap.size,
                refCounterValue: refCounter,
                // Memory management information
                memoryInfo: {
                    currentRefCount: refElementMap.size,
                    maxRefs: MAX_REFS,
                    memoryUtilization: (refElementMap.size / MAX_REFS * 100).toFixed(1) + '%',
                    lruAccessTimesCount: refAccessTimes.size,
                    unusedAgeThreshold: MAX_UNUSED_AGE_MS + 'ms',
                    cleanupThreshold: (CLEANUP_THRESHOLD * 100).toFixed(0) + '%',
                    isAggressiveCleanup: refElementMap.size > (MAX_REFS * CLEANUP_THRESHOLD)
                },
                // Performance information
                cacheHit: false,
                analysisTime: Date.now() - currentTime
            }
        };

        // Cache the result for potential reuse
        window.__camelLastAnalysisResult = result;
        window.__camelLastAnalysisTime = currentTime;

        return result;
    }

    // Execute analysis and return result
    return analyzePageElements();
})();