/**
 * Alternative implementation of SOM-screenshot using JS injection
 * This avoids CDP resolution issues by rendering labels directly in the page
 */

import { Page } from 'playwright';
import { SnapshotResult, VisualMarkResult } from './types';

export class SomScreenshotInjected {
  /**
   * Take a screenshot with SOM-labels injected into the page
   * This approach uses a single script injection for better performance
   */
  static async captureOptimized(
    page: Page,
    snapshotResult: SnapshotResult,
    clickableElements: Set<string>
  ): Promise<VisualMarkResult & { timing: any }> {
    const startTime = Date.now();
    
    try {
      // Inject and capture in one go
      const result = await page.evaluate(async (data) => {
        const { elements, clickable } = data;
        
        // Create overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 2147483647;
        `;
        
        // Add labels
        Object.entries(elements).forEach(([ref, element]: [string, any]) => {
          if (element.coordinates && clickable.includes(ref)) {
            const label = document.createElement('div');
            const { x, y, width, height } = element.coordinates;
            
            label.style.cssText = `
              position: absolute;
              left: ${x}px;
              top: ${y}px;
              width: ${width}px;
              height: ${height}px;
              border: 3px solid #FF0066;
              border-radius: 4px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            `;
            
            // Add ref number
            const refLabel = document.createElement('div');
            refLabel.textContent = ref;
            refLabel.style.cssText = `
              position: absolute;
              top: 4px;
              left: 4px;
              background: #FF0066;
              color: white;
              font: bold 12px Arial, sans-serif;
              padding: 2px 6px;
              border-radius: 2px;
              min-width: 20px;
              text-align: center;
              box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            `;
            
            label.appendChild(refLabel);
            overlay.appendChild(label);
          }
        });
        
        document.body.appendChild(overlay);
        
        // Force repaint
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        return { 
          overlayId: overlay.id = 'camel-som-overlay-temp',
          elementCount: overlay.children.length
        };
      }, {
        elements: snapshotResult.elements,
        clickable: Array.from(clickableElements)
      });
      
      // Take screenshot
      const screenshotBuffer = await page.screenshot({
        fullPage: false,
        type: 'png'
      });
      
      // Keep the overlay visible for 1 second before cleanup
      await page.waitForTimeout(1000);
      
      // Clean up
      await page.evaluate((overlayId) => {
        const overlay = document.getElementById(overlayId);
        if (overlay) overlay.remove();
      }, result.overlayId);
      
      const base64Image = screenshotBuffer.toString('base64');
      const dataUrl = `data:image/png;base64,${base64Image}`;
      
      return {
        text: `Visual webpage screenshot captured with ${result.elementCount} interactive elements marked`,
        images: [dataUrl],
        timing: {
          total_time_ms: Date.now() - startTime,
          screenshot_time_ms: Date.now() - startTime - 1100, // Approximate screenshot time (excluding 1s wait)
          snapshot_time_ms: 0, // Will be filled by caller
          coordinate_enrichment_time_ms: 0, // Will be filled by caller
          visual_marking_time_ms: 1100, // Injection, rendering and 1s display time
          injection_method: 'optimized',
          elements_count: result.elementCount,
          display_duration_ms: 1000 // Time the overlay is kept visible
        }
      };
      
    } catch (error) {
      console.error('SOM screenshot injection error:', error);
      throw error;
    }
  }
}