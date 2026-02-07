
import PptxGenJS from "pptxgenjs";
import fs from "fs";
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Get arguments
const args = process.argv.slice(2);
if (args.length < 2) {
    console.error("Usage: node generate_pptx.js <filename> <content_json>");
    process.exit(1);
}

const filename = args[0];
const contentJson = args[1];

let data;
try {
    data = JSON.parse(contentJson);
} catch (e) {
    console.error("Error parsing JSON content:", e);
    process.exit(1);
}

let slidesData = [];
let themeName = "default";
let layout = "LAYOUT_16x9";

if (Array.isArray(data)) {
    slidesData = data;
} else if (typeof data === 'object' && data !== null) {
    if (Array.isArray(data.slides)) {
        slidesData = data.slides;
    }
    if (data.theme) {
        themeName = data.theme;
    }
    if (data.layout) {
        layout = data.layout;
    }
}

// Load theme
let theme = {};
try {
    const themePath = join(__dirname, 'themes', `${themeName}.json`);
    if (fs.existsSync(themePath)) {
        const themeContent = fs.readFileSync(themePath, 'utf8');
        theme = JSON.parse(themeContent);
    } else {
        console.warn(`Theme '${themeName}' not found. Using internal defaults.`);
        // Fallback or just empty object, relying on defaults below if needed
    }
} catch (e) {
    console.error(`Error loading theme '${themeName}':`, e);
}

const styles = theme.styles || {};

// Helper to get style or default
const getStyle = (key, defaultStyle) => {
    return { ...defaultStyle, ...styles[key] };
};


// Create Presentation
const ppt = new PptxGenJS();
if (layout && layout !== "LAYOUT_16x9") {
    ppt.layout = layout;
}

// Process slides
if (Array.isArray(slidesData)) {
    slidesData.forEach((slideData) => {
        const slide = ppt.addSlide();

        // simple layout heuristics based on keys
        if (slideData.title) {
            const style = getStyle("title", { x: 1, y: 1, w: "80%", h: 1, fontSize: 24, bold: true, color: "363636" });
            slide.addText(slideData.title, style);
        }

        if (slideData.subtitle) {
            const style = getStyle("subtitle", { x: 1, y: 2.5, w: "80%", h: 1, fontSize: 18, color: "737373" });
            slide.addText(slideData.subtitle, style);
        }

        if (slideData.heading) {
            const style = getStyle("heading", { x: 0.5, y: 0.5, w: "90%", h: 0.5, fontSize: 20, bold: true, color: "000000" });
            slide.addText(slideData.heading, style);
        }

        if (slideData.bullet_points && Array.isArray(slideData.bullet_points)) {
            const bulletOpts = getStyle("bullet_point", { fontSize: 14, bullet: true, color: "000000", breakLine: true });
            const listStyle = getStyle("bullet_list", { x: 1, y: 1.5, w: "80%", h: 4 });

            const bullets = slideData.bullet_points.map(bp => ({ text: bp, options: bulletOpts }));
            slide.addText(bullets, listStyle);
        }

        if (slideData.text) {
            const style = getStyle("body_text", { x: 1, y: 1.5, w: "80%", h: 4, fontSize: 14, color: "000000" });
            slide.addText(slideData.text, style);
        }

        // Table support
        if (slideData.table) {
            const tableData = [];
            const headerStyle = getStyle("table_header", { bold: true, fill: "F7F7F7" });

            // headers
            if (slideData.table.headers) {
                tableData.push(slideData.table.headers.map(h => ({ text: h, options: headerStyle })));
            }
            // rows
            if (slideData.table.rows) {
                slideData.table.rows.forEach(row => {
                    tableData.push(row);
                });
            }
            const tableStyle = getStyle("table", { x: 1, y: 2, w: "80%" });
            slide.addTable(tableData, tableStyle);
        }
    });
}

// Save File
ppt.writeFile({ fileName: filename })
    .then((fileName) => {
        const result = {
            success: true,
            path: fileName,
            slides: Array.isArray(slidesData) ? slidesData.length : 0
        };
        console.log(JSON.stringify(result));
    })
    .catch((err) => {
        const result = {
            success: false,
            error: err.toString()
        };
        console.log(JSON.stringify(result));
        process.exit(1);
    });
