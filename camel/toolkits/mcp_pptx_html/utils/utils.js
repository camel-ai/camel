const axios = require('axios');

function pxToIn(px) { return px ? parseFloat(px) / 96 : 0; }


function pxToPt(px) { return (px && typeof px === 'string' && px.endsWith('px')) ? parseFloat(px) / 1.333 : 0; }

function rgbaToPptxFill(rgbaStr) {
  const match = rgbaStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)/);
  if (!match) return { color: "000000" };
  const r = parseInt(match[1]).toString(16).padStart(2, '0');
  const g = parseInt(match[2]).toString(16).padStart(2, '0');
  const b = parseInt(match[3]).toString(16).padStart(2, '0');
  const alpha = parseFloat(match[4]);
  const transparency = Math.round((1 - alpha) * 100);
  return { color: `${r}${g}${b}`, transparency };
}
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
async function toBase64(url) {
  try {
    const response = await axios.get(url, { responseType: 'arraybuffer' });
    const base64 = Buffer.from(response.data, 'binary').toString('base64');
    // Try to infer mime type from url extension
    let mime = 'image/jpeg';
    if (url.endsWith('.png')) mime = 'image/png';
    else if (url.endsWith('.gif')) mime = 'image/gif';
    // Debug: log the first 100 chars
    console.log(`Base64 for ${url}:`, base64.substring(0, 100));
    return { base64, mime };
  } catch (err) {
    console.error('Failed to download or convert image:', url, err);
    throw err;
  }
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

function processShadow(shadowObj) {
  if (!shadowObj) return undefined;
  
  return {
    type: 'outer',
    color: shadowObj.color ? shadowObj.color.replace('#', '') : '000000',
    opacity: shadowObj.opacity || 0.5,
    blur: shadowObj.blur || 10,
    offset: shadowObj.offsetY || 0,
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

module.exports = {pxToPt, pxToIn, rgbaToPptxFill, toBase64 ,rgbToHex, processFill, safeHexColor, processShadow, determineBoldness };
