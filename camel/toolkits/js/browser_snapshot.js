function getVisibleElements() {
    const elements = [];

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

    let refCounter = 1;

    function traverse(node, depth) {
        if (node.nodeType !== Node.ELEMENT_NODE) return;

        if (!isVisible(node)) return;

        const tagName = node.tagName.toLowerCase();
        const text = node.textContent?.trim().slice(0, 50) || '';

        const hasRoleOrText = ['button', 'a', 'input', 'select', 'textarea', 'p', 'span'].includes(tagName) || 
                                      node.getAttribute('role') || text;

        if (hasRoleOrText) {
            const role = getRole(node);
            const ref = `e${refCounter++}`;
            const label = text ? `"${text}"` : '';
            const indent = '  '.repeat(depth);

            elements.push(`${indent}- ${role} ${label} [ref=${ref}]`);
            node.setAttribute('aria-ref', ref);
        }

        for (let child of node.children) {
            traverse(child, depth + 1);
        }
    }

    traverse(document.body, 0);
    return elements.join('\\n');
}

return getVisibleElements();
