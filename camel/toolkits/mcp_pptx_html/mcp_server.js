const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { extractRenderTreeFromHtml, extractRenderTreesFromHtmlList } = require('./render_tree.js');
const { generatePptxFromRenderTree } = require('./pptxgenjs.js');

// Create a simple MCP server
const server = new Server(
  {
    name: 'html-to-pptx-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define tools
const tools = [
  {
    name: 'convert_html_to_pptx',
    description: 'Convert HTML content(s) to a PowerPoint presentation (PPTX). Use "html" for a single slide, or "htmlList" for multiple slides (one per HTML).',
    inputSchema: {
      type: 'object',
      properties: {
        html: {
          type: 'string',
          description: 'The HTML content to convert to PPTX'
        },
        htmlList: {
          type: 'array',
          items: {
            type: 'string'
          },
          description: 'An array of HTML contents to convert to PPTX, one slide per HTML'
        },
        outputPath: {
          type: 'string',
          description: 'Optional path to save the PPTX file. If not provided, returns base64 data.'
        }
      },
      required: ['html']
    }
  }
];

// Handle tool calls
async function handleToolCall(request) {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'convert_html_to_pptx':
      return await convertHtmlToPptx(args);
    case 'extract_render_tree':
      return await extractRenderTree(args);
    case 'generate_pptx_from_tree':
      return await generatePptxFromTree(args);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

async function convertHtmlToPptx(args) {
  try {
    const { html, htmlList, outputPath } = args;
    
    if (!html && (!htmlList || !Array.isArray(htmlList))) {
      throw new Error('Either "html" or "htmlList" is required');
    }

    let renderTrees;
    if (html) {
      console.error('Extracting render tree from HTML...');
      renderTrees = [await extractRenderTreeFromHtml(html)];
    } else if (htmlList && Array.isArray(htmlList)) {
      console.error('Extracting render trees from HTML list...');
      renderTrees = await extractRenderTreesFromHtmlList(htmlList);
    }

    console.error('Generating PPTX from render trees...');
    const pptxBuffer = await generatePptxFromRenderTree(renderTrees);

    if (outputPath) {
      // Save to file
      const fs = require('fs');
      fs.writeFileSync(outputPath, pptxBuffer);
      return {
        content: [
          {
            type: 'text',
            text: `PPTX file successfully generated and saved to: ${outputPath}`
          }
        ]
      };
    } else {
      // Return base64 data
      const base64Data = pptxBuffer.toString('base64');
      return {
        content: [
          {
            type: 'text',
            text: `PPTX generated successfully. Base64 data: ${base64Data}`
          }
        ]
      };
    }
  } catch (error) {
    console.error('Error converting HTML to PPTX:', error);
    throw new Error(`Failed to convert HTML to PPTX: ${error.message}`);
  }
}

async function extractRenderTree(args) {
  try {
    const { html } = args;
    
    if (!html) {
      throw new Error('HTML content is required');
    }

    console.error('Extracting render tree from HTML...');
    const renderTree = await extractRenderTreeFromHtml(html);
    
    return {
      content: [
        {
          type: 'text',
          text: `Render tree extracted successfully. Tree structure: ${JSON.stringify(renderTree, null, 2)}`
        }
      ]
    };
  } catch (error) {
    console.error('Error extracting render tree:', error);
    throw new Error(`Failed to extract render tree: ${error.message}`);
  }
}

async function generatePptxFromTree(args) {
  try {
    const { renderTree, outputPath } = args;
    
    if (!renderTree) {
      throw new Error('Render tree is required');
    }

    console.error('Generating PPTX from render tree...');
    const pptxBuffer = await generatePptxFromRenderTree(renderTree);

    if (outputPath) {
      // Save to file
      const fs = require('fs');
      fs.writeFileSync(outputPath, pptxBuffer);
      return {
        content: [
          {
            type: 'text',
            text: `PPTX file successfully generated and saved to: ${outputPath}`
          }
        ]
      };
    } else {
      // Return base64 data
      const base64Data = pptxBuffer.toString('base64');
      return {
        content: [
          {
            type: 'text',
            text: `PPTX generated successfully. Base64 data: ${base64Data}`
          }
        ]
      };
    }
  } catch (error) {
    console.error('Error generating PPTX from tree:', error);
    throw new Error(`Failed to generate PPTX from tree: ${error.message}`);
  }
}

// Set up request handlers using a different approach
server._requestHandlers.set('tools/call', async (request) => {
  return await handleToolCall(request);
});

server._requestHandlers.set('tools/list', async () => {
  return { tools };
});

// Run the server
async function run() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('HTML to PPTX MCP Server started');
}

// Run if this file is executed directly
if (require.main === module) {
  run().catch(console.error);
}

module.exports = { server, tools, handleToolCall }; 