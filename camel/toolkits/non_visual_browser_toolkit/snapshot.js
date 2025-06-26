(() => {
    // Playwright's snapshot logic focuses on semantics and visibility, not arbitrary limits.
    // We will first build a semantic tree in memory, then render it.

    function isVisible(node) {
        if (node.nodeType !== Node.ELEMENT_NODE) return true;
        const style = window.getComputedStyle(node);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0')
            return false;
        // An element with `display: contents` is not rendered itself, but its children are.
        if (style.display === 'contents')
            return true;
        const rect = node.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    function getRole(node) {
        const role = node.getAttribute('role');
        if (role) return role;

        const tagName = node.tagName.toLowerCase();
        if (tagName === 'a') return 'link';
        if (tagName === 'button') return 'button';
        if (tagName === 'input') {
            const type = node.getAttribute('type')?.toLowerCase();
            if (['button', 'checkbox', 'radio', 'reset', 'submit'].includes(type)) return type;
            return 'textbox';
        }
        if (['select', 'textarea'].includes(tagName)) return tagName;
        if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) return 'heading';
        return 'generic';
    }

    function getAccessibleName(node) {
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

    let refCounter = 1;
    function generateRef() {
        return `e${refCounter++}`;
    }

    /**
     * Phase 1: Build an in-memory representation of the accessibility tree.
     */
    function buildAriaTree(rootElement) {
        const visited = new Set();

        function toAriaNode(element) {
            // Only consider visible elements
            if (!isVisible(element)) return null;

            const role = getRole(element);
            // 'presentation' and 'none' roles are ignored, but their children are processed.
            if (['presentation', 'none'].includes(role)) return null;

            const name = getAccessibleName(element);

            // Create the node
            const node = {
                role,
                name,
                children: [],
                element: element,
                ref: generateRef(),
            };

            // Add states for interactive elements, similar to Playwright
            if (element.hasAttribute('disabled')) node.disabled = true;
            if (element.hasAttribute('aria-checked')) node.checked = element.getAttribute('aria-checked');
            if (element.hasAttribute('aria-expanded')) node.expanded = element.getAttribute('aria-expanded');

            // Tag element with a ref for later lookup
            element.setAttribute('aria-ref', node.ref);

            return node;
        }

        function traverse(element, parentNode) {
            if (visited.has(element)) return;
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

            // FIX: If an element's name is the same as its only text child, remove the redundant child.
            if (ariaNode && ariaNode.children.length === 1 && typeof ariaNode.children[0] === 'string' && ariaNode.name === ariaNode.children[0]) {
                ariaNode.children = [];
            }
        }

        const root = { role: 'Root', name: '', children: [], element: rootElement };
        traverse(rootElement, root);
        return root;
    }

    /**
     * Phase 2: Normalize the tree by removing redundant generic wrappers.
     * This is a key optimization in Playwright to simplify the structure.
     */
    function normalizeTree(node) {
        if (typeof node === 'string') return [node];

        const newChildren = [];
        for (const child of node.children) {
            newChildren.push(...normalizeTree(child));
        }
        node.children = newChildren;

        // Remove child elements that have the same name as their parent
        if (node.children.length === 1 && typeof node.children[0] !== 'string') {
            const child = node.children[0];
            if (child.name && node.name && child.name.trim() === node.name.trim()) {
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
     */
    function renderTree(node, indent = '') {
        const lines = [];
        let meaningfulProps = '';
        if (node.disabled) meaningfulProps += ' disabled';
        if (node.checked !== undefined) meaningfulProps += ` checked=${node.checked}`;
        if (node.expanded !== undefined) meaningfulProps += ` expanded=${node.expanded}`;

        const ref = node.ref ? ` [ref=${node.ref}]` : '';
        const name = (node.name || '').replace(/\s+/g, ' ').trim();

        // Skip elements with empty names and no meaningful props (ref is not considered meaningful)
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

        lines.push(`${indent}- ${node.role}${name ? ` "${name}"` : ''}${meaningfulProps}${ref}`);

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

    const outputLines = processDocument(document);
    return outputLines.join('\n');
})();
