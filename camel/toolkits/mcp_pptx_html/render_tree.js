const puppeteer = require('puppeteer');
const fs = require('fs');
async function extractRenderTreeFromHtml(html) {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'networkidle0' });
  await page.setViewport({ width: 1280, height: 720 });
  const { elements, debug } = await page.evaluate(() => {
    const debug = [];
   
    function extract(el) {
      const rect = el.getBoundingClientRect();
      const styles = window.getComputedStyle(el);

      // Collect all attributes
      const attrs = {};
      for (const attr of el.attributes || []) {
        attrs[attr.name] = attr.value;
      }

      // Collect all computed styles
      const styleObj = {};
      for (const style of styles) {
        styleObj[style] = styles.getPropertyValue(style);
      }

      // Recursively extract children
      const children = [];
      for (const child of el.children) {
        children.push(extract(child));
      }
      if (el.tagName === 'DIV' || el.tagName === 'UL' || el.tagName === 'OL' || el.tagName === 'LI') {
        function pxToIn(px) { return px ? parseFloat(px) / 96 : 0; }
        // Manually extract each border radius corner
        const borderRadius = {
          topLeft: styles['borderTopLeftRadius'] ? pxToIn(styles['borderTopLeftRadius']) : 0,
          topRight: styles['borderTopRightRadius'] ? pxToIn(styles['borderTopRightRadius']) : 0,
          bottomLeft: styles['borderBottomLeftRadius'] ? pxToIn(styles['borderBottomLeftRadius']) : 0,
          bottomRight: styles['borderBottomRightRadius'] ? pxToIn(styles['borderBottomRightRadius']) : 0
        };
        debug.push({
          tag: el.tagName,
          borderRadius: styles.borderRadius,
          borderTopLeftRadius: styles['borderTopLeftRadius'],
          borderTopRightRadius: styles['borderTopRightRadius'],
          borderBottomLeftRadius: styles['borderBottomLeftRadius'],
          borderBottomRightRadius: styles['borderBottomRightRadius'],
          class: el.className
        });
        // Set rectRadius for pptxgenjs (max border radius normalized by width)
        const borderRadiusVals = Object.values(borderRadius);
        const maxRadius = Math.max(...borderRadiusVals);
        const rectRadius = (maxRadius > 0 && rect.width > 0) ? maxRadius / (rect.width / 96) : 0; // rect.width is in px, convert to inches
        // Extract properties with defaults or from styles/attributes
        const align = el.getAttribute('data-align') || styles.textAlign || 'center';
        const fill = {
          color: styles.backgroundColor !== 'rgba(0, 0, 0, 0)' ? styles.backgroundColor : undefined,
          transparency: styles.opacity ? 1 - parseFloat(styles.opacity) : 0
        };
        const flipH = el.getAttribute('data-flip-h') === 'true' || false;
        const flipV = el.getAttribute('data-flip-v') === 'true' || false;
        const hyperlink = el.getAttribute('data-hyperlink') || undefined;
        const line = {
          color: styles.borderColor !== 'rgba(0, 0, 0, 0)' ? styles.borderColor : undefined,
          width: styles.borderWidth ? parseFloat(styles.borderWidth) : undefined,
          style: styles.borderStyle || undefined
        };
        const rotate = el.getAttribute('data-rotate') ? parseFloat(el.getAttribute('data-rotate')) : 0;
        const shadow = {
          type: 'outer',
          color: '#000000', // fallback to black, or parse from boxShadow if needed
          blur: 70,
          opacity: 1,
          offsetY: 0
        };

        return {
          tag: el.tagName,
          align,
          fill,
          flipH,
          flipV,
          hyperlink,
          line,
          rectRadius,
          borderRadius,
          rotate,
          // shadow,
          rect: {
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
            top: rect.top,
            left: rect.left,
            right: rect.right,
            bottom: rect.bottom
          },
          attributes: attrs,
          // styles: styleObj,
          text: el.innerText,
          innerHTML: el.innerHTML,
          children: children.length > 0 ? children : undefined
        };
      }
      if (el.tagName === 'IMG') {
        // Manually extract each border radius corner
        function pxToIn(px) { return px ? parseFloat(px) / 96 : 0; }
        const borderRadius = {
          topLeft: styles['borderTopLeftRadius'] ? pxToIn(styles['borderTopLeftRadius']) : 0,
          topRight: styles['borderTopRightRadius'] ? pxToIn(styles['borderTopRightRadius']) : 0,
          bottomLeft: styles['borderBottomLeftRadius'] ? pxToIn(styles['borderBottomLeftRadius']) : 0,
          bottomRight: styles['borderBottomRightRadius'] ? pxToIn(styles['borderBottomRightRadius']) : 0
        };
        const src = el.getAttribute('src') || '';
        const isBase64 = src.startsWith('data:image');
        const data = isBase64 ? src : null;
        const path = !isBase64 ? src : null;
        const altText = el.getAttribute('alt') || '';
        const transform = styles.transform || '';
        const flipH = transform.includes('scaleX(-1)');
        const flipV = transform.includes('scaleY(-1)');
        // Check if parent is <a> for hyperlink
        let hyperlink = null;
        if (el.parentElement && el.parentElement.tagName === 'A') {
          const href = el.parentElement.getAttribute('href');
          if (href) hyperlink = { url: href };
        }
        // Infer placeholder from class
        let placeholder = null;
        const classList = el.className ? el.className.split(' ') : [];
        if (classList.includes('title')) placeholder = 'title';
        else if (classList.includes('body')) placeholder = 'body';
        // Extract rotate from transform
        let rotate = 0;
        const rotateMatch = transform.match(/rotate\\(([-\\d.]+)deg\\)/);
        if (rotateMatch) rotate = parseInt(rotateMatch[1], 10);
        // Rounding: border-radius 50%
        const rounding = styles.borderRadius === '50%';
        // Sizing: object-fit, width, height (convert px to inches)
        const sizing = {
          fit: styles.objectFit || undefined,
          width: pxToIn(styles.width.endsWith('px') ? styles.width : el.width ? el.width + '' : undefined),
          height: pxToIn(styles.height.endsWith('px') ? styles.height : el.height ? el.height + '' : undefined)
        };
        // Transparency: from opacity
        const transparency = styles.opacity ? (1 - parseFloat(styles.opacity)) * 100 : 0;
        return {
          tag: el.tagName,
          data,
          path,
          altText,
          flipH,
          flipV,
          hyperlink,
          placeholder,
          rotate,
          rounding,
          borderRadius,
          sizing,
          transparency,
          rect: {
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
            top: rect.top,
            left: rect.left,
            right: rect.right,
            bottom: rect.bottom
          },
          attributes: attrs,
          children: children.length > 0 ? children : undefined
        };
      }
      // Handle text-related tags
      const textTags = ['SPAN', 'P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LI'];
      if (textTags.includes(el.tagName)) {
        // Helper functions
        function pxToPt(px) { return (px && typeof px === 'string' && px.endsWith('px')) ? parseFloat(px) / 1.333 : 0; }
        function pxToIn(px) { return (px && typeof px === 'string' && px.endsWith('px')) ? parseFloat(px) / 96 : 0; }
        function rgbToHex(rgb) {
          if (!rgb || rgb === 'transparent' || rgb === 'rgba(0, 0, 0, 0)') return 'transparent';
          const result = rgb.match(/rgba?\((\d+), (\d+), (\d+)(, [\d.]+)?\)/);
          if (!result) return rgb;
          return (
            '#' +
            ((1 << 24) + (parseInt(result[1]) << 16) + (parseInt(result[2]) << 8) + parseInt(result[3]))
              .toString(16)
              .slice(1)
              .toUpperCase()
          );
        }
        // Debug: log all computed styles for this element
        console.log('Computed styles for', el.tagName, el.innerText, styles);
        // Extract properties with robust checks
        const align = styles.textAlign || 'left';
        const autoFit = false;
        const baseline = styles.baselineShift ? pxToPt(styles.baselineShift) : 0;
        const bold = styles.fontWeight ? parseInt(styles.fontWeight) >= 700 : false;
        const breakLine = true;
        let bullet = false;
        if (el.tagName === 'LI') {
          if (styles.listStyleType === 'disc') bullet = true;
          else if (styles.listStyleType === 'decimal') bullet = { type: 'number' };
          else if (styles.listStyleType === 'lower-alpha') bullet = { style: 'alphaLcPeriod' };
        }
        const charSpacing = styles.letterSpacing ? pxToPt(styles.letterSpacing) : 0;
        const color = styles.color ? rgbToHex(styles.color) : undefined;
        const fill = styles.backgroundColor ? rgbToHex(styles.backgroundColor) : 'transparent';
        const fit = undefined;
        const fontFace = styles.fontFamily ? styles.fontFamily.split(',')[0].replace(/['"]/g, '') : undefined;
        const fontSize = styles.fontSize ? pxToPt(styles.fontSize) : undefined;
        // Glow from text-shadow (use first shadow if multiple)
        let glow = undefined;
        if (styles.textShadow && styles.textShadow !== 'none') {
          const match = styles.textShadow.match(/rgba?\((\d+), (\d+), (\d+), ([\d.]+)\) ([-\d.]+)px ([-\d.]+)px ([-\d.]+)px/);
          if (match) {
            glow = {
              size: parseFloat(match[7]),
              opacity: parseFloat(match[4]),
              color: rgbToHex(`rgb(${match[1]}, ${match[2]}, ${match[3]})`)
            };
          }
        }
        const highlight = undefined;
        const hyperlink = null;
        const indentLevel = 0;
        const inset = (styles.paddingLeft && styles.paddingRight && styles.paddingTop && styles.paddingBottom)
          ? (pxToIn(styles.paddingLeft) + pxToIn(styles.paddingRight) + pxToIn(styles.paddingTop) + pxToIn(styles.paddingBottom)) / 4
          : 0;
        const isTextBox = false;
        const italic = styles.fontStyle === 'italic';
        const lang = styles['-webkit-locale'] ? styles['-webkit-locale'].replace(/['"]/g, '').replace('en', 'en-US') : undefined;
        const line = {
          width: styles.borderBottomWidth ? pxToPt(styles.borderBottomWidth) : 0,
          color: styles.borderBottomColor ? rgbToHex(styles.borderBottomColor) : undefined
        };
        const lineSpacing = styles.lineHeight && styles.lineHeight.endsWith('px') ? pxToPt(styles.lineHeight) : undefined;
        const lineSpacingMultiple = styles.lineHeight && !styles.lineHeight.endsWith('px') ? parseFloat(styles.lineHeight) : undefined;
        const margin = styles.marginBottom ? pxToPt(styles.marginBottom) : 0;
        const outline = (styles['-webkit-text-stroke-width'] && styles['-webkit-text-stroke-color']) ? {
          color: rgbToHex(styles['-webkit-text-stroke-color']),
          size: pxToPt(styles['-webkit-text-stroke-width'])
        } : undefined;
        const paraSpaceAfter = styles.marginBottom ? pxToPt(styles.marginBottom) : 0;
        const paraSpaceBefore = styles.marginTop ? pxToPt(styles.marginTop) : 0;
        const rectRadius = styles.borderRadius ? pxToIn(styles.borderRadius) : 0;
        let rotate = 0;
        const transform = styles.transform || '';
        const rotateMatch = transform.match(/rotate\(([-\d.]+)deg\)/);
        if (rotateMatch) rotate = parseInt(rotateMatch[1], 10);
        const rtlMode = styles.direction === 'rtl';
        // Shadow from text-shadow (use first shadow if multiple)
        let shadow = undefined;
        if (styles.textShadow && styles.textShadow !== 'none') {
          const match = styles.textShadow.match(/rgba?\((\d+), (\d+), (\d+), ([\d.]+)\) ([-\d.]+)px ([-\d.]+)px ([-\d.]+)px/);
          if (match) {
            shadow = {
              type: 'outer',
              color: rgbToHex(`rgb(${match[1]}, ${match[2]}, ${match[3]})`),
              opacity: parseFloat(match[4]),
              blur: parseFloat(match[7]),
              offset: parseFloat(match[5]),
            };
          }
        }
        const softBreakBefore = false;
        let strike = null;
        if (styles.textDecorationLine && styles.textDecorationLine.includes('line-through')) strike = 'sngStrike';
        const subscript = styles.verticalAlign === 'sub';
        const superscript = styles.verticalAlign === 'super';
        const transparency = styles.opacity ? (1 - parseFloat(styles.opacity)) * 100 : 0;
        let underline = undefined;
        if (styles.textDecorationLine && styles.textDecorationLine.includes('underline')) {
          underline = { style: 'sng', color: color };
        } else {
          underline = { style: 'none', color: color };
        }
        const valign = undefined;
        const vert = styles.writingMode && styles.writingMode.startsWith('vertical') ? 'vert' : 'horz';
        const wrap = styles.overflowWrap === 'normal' || styles.textWrapMode === 'wrap';
        return {
          tag: el.tagName,
          align,
          autoFit,
          baseline,
          bold,
          breakLine,
          bullet,
          charSpacing,
          color,
          fill,
          fit,
          fontFace,
          fontSize,
          glow,
          highlight,
          hyperlink,
          indentLevel,
          inset,
          isTextBox,
          italic,
          lang,
          line,
          lineSpacing,
          lineSpacingMultiple,
          margin,
          outline,
          paraSpaceAfter,
          paraSpaceBefore,
          rectRadius,
          rotate,
          rtlMode,
          shadow,
          softBreakBefore,
          strike,
          subscript,
          superscript,
          transparency,
          underline,
          valign,
          vert,
          wrap,
          rect: {
            x: rect.x,
            y: rect.y,
            width: rect.width ,
            height: rect.height + 0,
            top: rect.top,
            left: rect.left,
            right: rect.right,
            bottom: rect.bottom
          },
          attributes: attrs,
          text: el.innerText,
          innerHTML: el.innerHTML,
          children: children.length > 0 ? children : undefined
        };
      }
      // Handle Font Awesome icons
      const isFontAwesome = el.classList && (
        el.classList.contains('fa') || 
        el.classList.contains('fas') || 
        el.classList.contains('far') || 
        el.classList.contains('fab') || 
        el.classList.contains('fal') || 
        el.classList.contains('fad') ||
        el.classList.contains('fa-solid') ||
        el.classList.contains('fa-regular') ||
        el.classList.contains('fa-light') ||
        el.classList.contains('fa-thin') ||
        el.classList.contains('fa-duotone') ||
        el.classList.contains('fa-brands')
      );
      if (isFontAwesome) {
        // Extract Font Awesome specific properties
        const iconClass = Array.from(el.classList).find(cls => cls.startsWith('fa-') && !['fa-solid', 'fa-regular', 'fa-light', 'fa-thin', 'fa-duotone', 'fa-brands'].includes(cls));
        const iconName = iconClass ? iconClass.replace('fa-', '') : '';
        // Determine icon style/weight
        let iconStyle = 'solid'; // default
        if (el.classList.contains('far') || el.classList.contains('fa-regular')) iconStyle = 'regular';
        if (el.classList.contains('fal') || el.classList.contains('fa-light')) iconStyle = 'light';
        if (el.classList.contains('fat') || el.classList.contains('fa-thin')) iconStyle = 'thin';
        if (el.classList.contains('fad') || el.classList.contains('fa-duotone')) iconStyle = 'duotone';
        if (el.classList.contains('fab') || el.classList.contains('fa-brands')) iconStyle = 'brands';
        // Extract size modifiers
        let sizeModifier = null;
        const sizeClasses = ['fa-xs', 'fa-sm', 'fa-lg', 'fa-xl', 'fa-2xl', 'fa-1x', 'fa-2x', 'fa-3x', 'fa-4x', 'fa-5x', 'fa-6x', 'fa-7x', 'fa-8x', 'fa-9x', 'fa-10x'];
        sizeModifier = Array.from(el.classList).find(cls => sizeClasses.includes(cls));
        // Get computed font properties for accurate sizing
        const fontSize = styles.fontSize ? styles.fontSize : '32px';
        const color = styles.color ? styles.color : '#000000';
        // Render the icon to a canvas and extract as base64
        const rect = el.getBoundingClientRect();
        // Create a temporary canvas
        const canvas = document.createElement('canvas');
        canvas.width = Math.ceil(rect.width || 32);
        canvas.height = Math.ceil(rect.height || 32);
        const ctx = canvas.getContext('2d');
        // Set background transparent
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        // Set font and color
        ctx.font = `${styles.fontWeight || 'normal'} ${fontSize} ${styles.fontFamily || 'FontAwesome'}`;
        ctx.fillStyle = color;
        ctx.textBaseline = 'top';
        // Get the unicode character from ::before pseudo-element
        let iconUnicode = window.getComputedStyle(el, '::before').content?.replace(/['"]/g, '');
        if (!iconUnicode || iconUnicode === 'normal') iconUnicode = el.innerText;
        // Draw the icon
        ctx.fillText(iconUnicode, 0, 0);
        // Get base64 image
        const data = canvas.toDataURL('image/png');
        // Check for hyperlink (if wrapped in <a>)
        let hyperlink = null;
        if (el.parentElement && el.parentElement.tagName === 'A') {
          const href = el.parentElement.getAttribute('href');
          if (href) hyperlink = { url: href };
        }
        return {
          tag: 'IMG',
          data,
          altText: iconName,
          iconName,
          iconStyle,
          sizeModifier,
          fontSize,
          color,
          hyperlink,
          rect: {
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
            top: rect.top,
            left: rect.left,
            right: rect.right,
            bottom: rect.bottom
          },
          attributes: attrs,
          children: children.length > 0 ? children : undefined
        };
      }
      // If tag is BODY, skip it and return its children directly (flattened)
      if (el.tagName === 'BODY') {
        return children.length > 0 ? children : undefined;
      }
      // Default: return a generic node with children (without styles)
      return {
        tag: el.tagName,
        attributes: attrs,
        rect: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          top: rect.top,
          left: rect.left,
          right: rect.right,
          bottom: rect.bottom
        },
        text: el.innerText,
        innerHTML: el.innerHTML,
        children: children.length > 0 ? children : undefined
      };
    }

    // Find all top-level .slide divs
    const slideDivs = Array.from(document.querySelectorAll('body > div.slide'));
    // If none found, fallback to body as a single slide
    const roots = slideDivs.length > 0 ? slideDivs : [document.body];
    const elements = roots.map(root => extract(root));
    return { elements, debug };
  });
  await browser.close();
  // Save debug info to a file
  try {
    fs.writeFileSync('render-tree-debug.json', JSON.stringify(debug, null, 2));
  } catch (e) {
    console.error('Failed to write render-tree-debug.json:', e);
  }
  return elements;
}

// New: Extract render trees from a list of HTML strings
async function extractRenderTreesFromHtmlList(htmlList) {
  if (!Array.isArray(htmlList)) throw new Error('htmlList must be an array');
  const allSlides = [];
  for (const html of htmlList) {
    const slides = await extractRenderTreeFromHtml(html);
    if (Array.isArray(slides)) {
      allSlides.push(...slides);
    } else if (slides) {
      allSlides.push(slides);
    }
  }
  return allSlides;
}

module.exports = { extractRenderTreeFromHtml, extractRenderTreesFromHtmlList };
