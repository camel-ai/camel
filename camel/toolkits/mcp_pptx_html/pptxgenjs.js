const pptxgen = require('pptxgenjs');
const { pxToIn, rgbaToPptxFill, toBase64 } = require('./utils/utils');

// Constants
const TEXT_TAGS = [
  'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P', 'SPAN', 'TEXT', 
  'LABEL', 'STRONG', 'EM', 'B', 'I', 'U'
];

const PRESENTATION_CONFIG = {
  layout: { name: 'LAYOUT_16x9', width: 13.33, height: 7.5 },
  defaultFont: 'Arial',
  defaultFontSize: 18
};

// Color utility functions
function rgbToHex(rgb) {
  if (!rgb) return '000000';
  const result = rgb.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/);
  if (!result) return '000000';
  
  const [r, g, b] = result.slice(1).map(val => 
    parseInt(val).toString(16).padStart(2, '0')
  );
  return r + g + b;
}

function processFill(fillObj) {
  if (!fillObj?.color) return undefined;
  
  const color = fillObj.color;
  let transparency = fillObj.transparency || 0;
  
  // Convert transparency from 0-1 scale to 0-100 scale
  if (transparency <= 1) {
    transparency = Math.round(transparency * 100);
  }
  
  // Handle rgba() strings
  const rgbaMatch = color.match(/rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)/);
  if (rgbaMatch) {
    const [r, g, b] = rgbaMatch.slice(1, 4).map(val => 
      parseInt(val).toString(16).padStart(2, '0')
    );
    const alpha = parseFloat(rgbaMatch[4]);
    transparency = Math.round((1 - alpha) * 100);
    return { color: `${r}${g}${b}`, transparency };
  }
  
  // Handle rgb() strings
  const rgbMatch = color.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/);
  if (rgbMatch) {
    const [r, g, b] = rgbMatch.slice(1).map(val => 
      parseInt(val).toString(16).padStart(2, '0')
    );
    return { color: `${r}${g}${b}`, transparency };
  }
  
  // Handle hex colors
  if (color.startsWith('#')) {
    return { color: color.replace('#', ''), transparency };
  }
  if (color.match(/^([0-9a-fA-F]{6})$/)) {
    return { color, transparency };
  }
  
  return undefined;
}

function safeHexColor(val, fallback = '000000') {
  if (!val || typeof val !== 'string' || val.trim() === '') return fallback;
  if (val.startsWith('#')) return val.replace('#', '');
  if (val.match(/^([0-9a-fA-F]{6})$/)) return val;
  if (val.startsWith('rgb')) return rgbToHex(val);
  return fallback;
}

// Shadow processing
function processShadow(shadowObj) {
  if (!shadowObj) return undefined;
  
  return {
    type: 'outer',
    color: shadowObj.color ? shadowObj.color.replace('#', '') : '000000',
    opacity: shadowObj.opacity || 0.5,
    blur: shadowObj.blurRadius || 10,
    offsetX: shadowObj.offsetX || 0,
    offsetY: shadowObj.offsetY || 4
  };
}

// Rectangle options builder
function buildRectangleOptions(node) {
  console.error('Building rectangle options:', JSON.stringify(node, null, 2));
  const fill = node.fill && typeof node.fill.color === 'string' 
    ? processFill(node.fill) 
    : undefined;

    
    
  return {
    x: pxToIn(node.rect?.x || 0),
    y: pxToIn(node.rect?.y || 0),
    w: pxToIn(node.rect?.width || 0),
    h: pxToIn(node.rect?.height || 0),
    ...(fill && { fill }),
    rectRadius: typeof node.rectRadius === 'number' ? node.rectRadius : 0,
    //Todo:fix shadow
    shadow: processShadow(node.shadow)
  };
}

// Text options builder
function buildTextOptions(node) {
  const fill = node.fill && typeof node.fill.color === 'string' 
    ? processFill(node.fill) 
    : undefined;
    
  const isBold = determineBoldness(node);
  
  return {
    x: pxToIn(node.rect?.x || 0),
    y: pxToIn(node.rect?.y || 0),
    w: pxToIn(node.rect?.width || 0),
    h: pxToIn(node.rect?.height || 0),
    color: safeHexColor(node.color || (node.fill && node.fill.color)),
    fontFace: node.fontFace || PRESENTATION_CONFIG.defaultFont,
    fontSize: node.fontSize || PRESENTATION_CONFIG.defaultFontSize,
    bold: isBold,
    italic: node.italic || false,
    align: node.align || 'left',
    autoFit: node.autoFit || false,
    valign: node.valign || 'middle',
    outline: node.outline
      ? { color: safeHexColor(node.outline.color), size: node.outline.size || 0 }
      : undefined,
    underline: node.underline
      ? { style: node.underline.style || 'none', color: safeHexColor(node.underline.color) }
      : undefined,
    fill: fill,
    shadow: processShadow(node.shadow)
  };
}

function determineBoldness(node) {
  if (node.bold !== undefined) {
    return Boolean(node.bold);
  }
  
  if (node.styles?.['font-weight']) {
    const fontWeight = parseInt(node.styles['font-weight']);
    return !isNaN(fontWeight) && fontWeight >= 700;
  }
  
  return false;
}

// Image data processing
async function processImageData(node) {
  let imgData = node.data;
  
  if (!imgData && node.path) {
    const { base64, mime } = await toBase64(node.path);
    imgData = `${mime};base64,${base64}`;
  }
  
  return imgData;
}

// Slide element handlers
function handleDiv(slide, rectOpts, pres) {
  const shapeType = rectOpts.rectRadius > 0 
    ? pres.ShapeType.roundRect 
    : pres.ShapeType.rect;
  slide.addShape(shapeType, rectOpts);
}

function handleImage(slide, rectOpts) {
  slide.addImage(rectOpts);
}

function handleText(slide, text, textOpts) {
  slide.addText(text, textOpts);
}

// Node rendering logic
async function renderDivNode(slide, node, pres) {
  const rectOpts = buildRectangleOptions(node);
  handleDiv(slide, rectOpts, pres);
  
  // Render children
  if (node.children) {
    for (const child of node.children) {
      await renderNode(slide, child, pres);
    }
  }
}

async function renderImageNode(slide, node) {
  const imgData = await processImageData(node);
  const rectOpts = {
    x: pxToIn(node.rect?.x || 0),
    y: pxToIn(node.rect?.y || 0),
    w: pxToIn(node.rect?.width || 0),
    h: pxToIn(node.rect?.height || 0),
    data: imgData
  };
  
  handleImage(slide, rectOpts);
}

async function renderTextNode(slide, node) {
  const textOpts = buildTextOptions(node);
  handleText(slide, node.text || '', textOpts);
}

// Main node rendering function
async function renderNode(slide, node, pres) {
  if (!node) return;
  console.error('Rendering node:', node.tag);
  
  if (Array.isArray(node)) {
    for (const n of node) {
      await renderNode(slide, n, pres);
    }
    return;
  }
  
  const tag = node.tag?.toUpperCase();
  
  switch (tag) {
    case 'DIV' || 'UL' || 'OL':
      await renderDivNode(slide, node, pres);
      break;
      
    case 'IMG':
      await renderImageNode(slide, node);
      break;
      
    default:
      if (TEXT_TAGS.includes(tag)) {
        await renderTextNode(slide, node);
      }
      
      // Recursively render children for other tags
      if (node.children && !['DIV', 'IMG'].includes(tag)) {
        for (const child of node.children) {
          await renderNode(slide, child, pres);
        }
      }
      break;
  }
}

// Main function
async function generatePptxFromRenderTree(tree) {
  console.error('Generating PPTX from render tree...');
  const pres = new pptxgen();
  pres.defineLayout(PRESENTATION_CONFIG.layout);
  pres.layout = PRESENTATION_CONFIG.layout.name;
  
  const slide = pres.addSlide();
  
  await renderNode(slide, tree[0][0], pres);
  
  return await pres.write('nodebuffer');
}

module.exports = { generatePptxFromRenderTree };
