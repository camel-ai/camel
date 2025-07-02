const pptxgen = require('pptxgenjs');
const { pxToIn, rgbToHex, toBase64, processFill, safeHexColor, processShadow, determineBoldness } = require('./utils/utils');

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
  // Ensure input is always an array of slide root nodes
  const slideNodes = Array.isArray(tree) ? tree : [tree];
  console.error('Generating PPTX from render tree...');
  const pres = new pptxgen();
  pres.defineLayout(PRESENTATION_CONFIG.layout);
  pres.layout = PRESENTATION_CONFIG.layout.name;
  // Multi-slide support: loop over all root nodes
  for (const slideNode of slideNodes) {
    const slide = pres.addSlide();
    await renderNode(slide, slideNode, pres);
  }
  return await pres.write('nodebuffer');
}

module.exports = { generatePptxFromRenderTree };
