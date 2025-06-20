(() => {
    // Store each element as {text, priority, depth}
    const elements = [];

    // Maximum lines allowed before we start dropping lower-priority nodes
    const MAX_LINES = 400;

    // Priority helper – lower number = higher priority
    function getPriority(tag, role, text) {
        // 1. Interactive elements
        if (["input", "button", "a", "select", "textarea"].includes(tag)) return 1;
        if (["checkbox", "radio"].includes(role)) return 1;

        // 2. Labels / descriptive adjacent text (label elements)
        if (tag === "label") return 2;

        // 3. General visible text
        if (text) return 3;

        // 4. Low-value structural nodes
        return 4;
    }

    function isVisible(node) {
        const rect = node.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return false;

        const style = window.getComputedStyle(node);
        if (style.display === 'none' || style.visibility === 'hidden') return false;

        return true;
    }

    function getRole(node) {
        const tag = node.tagName.toLowerCase();
        const type = node.getAttribute('type');

        if (node.getAttribute('role')) return node.getAttribute('role');

        if (tag === 'input') {
            if (type === 'checkbox') return 'checkbox';
            if (type === 'radio') return 'radio';
            return 'input';
        }

        if (tag === 'button') return 'button';
        if (tag === 'a') return 'link';
        if (tag === 'select') return 'select';
        if (tag === 'textarea') return 'textarea';
        if (tag === 'p') return 'paragraph';
        if (tag === 'span') return 'text';

        return 'generic';
    }

    function getAccessibleName(node) {
        if (node.hasAttribute('aria-label')) {
            return node.getAttribute('aria-label');
        }
        if (node.hasAttribute('aria-labelledby')) {
            const id = node.getAttribute('aria-labelledby');
            const labelEl = document.getElementById(id);
            if (labelEl) return labelEl.textContent.trim();
        }
        if (node.hasAttribute('title')) {
            return node.getAttribute('title');
        }

        const tagName = node.tagName?.toLowerCase();
        if (['style', 'script', 'meta', 'noscript', 'svg'].includes(tagName)) {
            return '';
        }

        const text = node.textContent?.trim() || '';

        // Ignore styles, tokens, or long CSS-like expressions
        if (/^[.#]?[a-zA-Z0-9\-_]+\s*\{[^}]*\}/.test(text)) return '';
        if ((text.match(/[;:{}]/g)?.length || 0) > 2) return '';

        return text.replace(/[^\w\u4e00-\u9fa5\s\-.,?!'"（）()]/g, '').trim();
    }

    let refCounter = 1;

    function traverse(node, depth) {
        if (node.nodeType !== Node.ELEMENT_NODE) return;
        if (!isVisible(node)) return;

        const tagName = node.tagName.toLowerCase();
        const text = getAccessibleName(node).slice(0, 50);

        // Skip unlabeled links (anchors without any accessible name)
        if (tagName === 'a' && !text) {
            // Skip unlabeled links; process children if any
            for (const child of node.children) {
                traverse(child, depth + 1);
            }
            return;
        }

        const hasRoleOrText = ['button', 'a', 'input', 'select', 'textarea', 'p', 'span'].includes(tagName) ||
                              node.getAttribute('role') || text;

        if (hasRoleOrText) {
            const role = getRole(node);
            const ref = `e${refCounter++}`;
            const label = text ? `"${text}"` : '';

            // Raw line (without indent) – we will apply indentation later once we know
            // which ancestor lines survive filtering so that indentation always reflects
            // the visible hierarchy.
            const lineText = `- ${role}${label ? ` ${label}` : ''} [ref=${ref}]`;
            const priority = getPriority(tagName, role, text);

            elements.push({ text: lineText, priority, depth });

            // Always inject ref so Playwright can still locate the element even if line is later filtered out.
            node.setAttribute('aria-ref', ref);
        }

        for (const child of node.children) {
            traverse(child, depth + 1);
        }
    }

    function processDocument(doc, depth = 0) {
        try {
            traverse(doc.body, depth);
        } catch (e) {
            // Handle docs without body (e.g., about:blank)
        }

        const frames = doc.querySelectorAll('iframe');
        for (const frame of frames) {
            try {
                if (frame.contentDocument) {
                    processDocument(frame.contentDocument, depth + 1);
                }
            } catch (e) {
                // Skip cross-origin iframes
            }
        }
    }

    processDocument(document);

    // Always drop priority-4 nodes (low-value structural or invisible)
    let finalElements = elements.filter(el => el.priority <= 3);

    // Additional size condensation when still exceeding MAX_LINES
    if (finalElements.length > MAX_LINES) {
        const filterBy = (maxPriority) => finalElements.filter(el => el.priority <= maxPriority);

        // Progressively tighten: keep 1-3, then 1-2, finally only 1
        for (const limit of [3, 2, 1]) {
            const candidate = filterBy(limit);
            if (candidate.length <= MAX_LINES || limit === 1) {
                finalElements = candidate;
                break;
            }
        }
    }

    // ------------------------------------------------------------------
    // Re-apply indentation so that it matches the *visible* hierarchy only.
    // Whenever an ancestor element is removed due to priority rules, its
    // children will be re-indented one level up so the structure remains
    // intuitive.
    // ------------------------------------------------------------------
    const outputLines = [];
    const depthStack = []; // keeps track of kept original depths

    for (const el of finalElements) {
        // Pop depths that are not ancestors of current element
        while (depthStack.length && depthStack[depthStack.length - 1] >= el.depth) {
            depthStack.pop();
        }

        // Push the current depth so future descendants know their ancestor chain
        depthStack.push(el.depth);

        const compressedDepth = depthStack.length - 1; // root level has zero indent
        const indent = '\t'.repeat(compressedDepth);
        outputLines.push(indent + el.text);
    }

    return outputLines.join('\n');
})();
