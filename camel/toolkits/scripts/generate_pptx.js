
import PptxGenJS from "pptxgenjs";
import fs from "fs";

// Get arguments
const args = process.argv.slice(2);
if (args.length < 2) {
    console.error("Usage: node generate_pptx.js <filename> <content_json>");
    process.exit(1);
}

const filename = args[0];
const contentJson = args[1];

let slidesData;
try {
    slidesData = JSON.parse(contentJson);
} catch (e) {
    console.error("Error parsing JSON content:", e);
    process.exit(1);
}

// Create Presentation
const pres = new PptxGenJS();

// Process slides
if (Array.isArray(slidesData)) {
    slidesData.forEach((slideData) => {
        const slide = pres.addSlide();

        // simple layout heuristics based on keys
        if (slideData.title) {
            slide.addText(slideData.title, { x: 1, y: 1, w: "80%", h: 1, fontSize: 24, bold: true, color: "363636" });
        }

        if (slideData.subtitle) {
            slide.addText(slideData.subtitle, { x: 1, y: 2.5, w: "80%", h: 1, fontSize: 18, color: "737373" });
        }

        if (slideData.heading) {
            slide.addText(slideData.heading, { x: 0.5, y: 0.5, w: "90%", h: 0.5, fontSize: 20, bold: true, color: "000000" });
        }

        if (slideData.bullet_points && Array.isArray(slideData.bullet_points)) {
            const bullets = slideData.bullet_points.map(bp => ({ text: bp, options: { fontSize: 14, bullet: true, color: "000000", breakLine: true } }));
            slide.addText(bullets, { x: 1, y: 1.5, w: "80%", h: 4 });
        }

        if (slideData.text) {
            slide.addText(slideData.text, { x: 1, y: 1.5, w: "80%", h: 4, fontSize: 14, color: "000000" });
        }

        // Table support
        if (slideData.table) {
            const tableData = [];
            // headers
            if (slideData.table.headers) {
                tableData.push(slideData.table.headers.map(h => ({ text: h, options: { bold: true, fill: "F7F7F7" } })));
            }
            // rows
            if (slideData.table.rows) {
                slideData.table.rows.forEach(row => {
                    tableData.push(row);
                });
            }
            slide.addTable(tableData, { x: 1, y: 2, w: "80%" });
        }
    });
}

// Save File
pres.writeFile({ fileName: filename })
    .then((fileName) => {
        console.log(`PowerPoint presentation successfully created: ${fileName}`);
    })
    .catch((err) => {
        console.error("Error saving file:", err);
        process.exit(1);
    });
