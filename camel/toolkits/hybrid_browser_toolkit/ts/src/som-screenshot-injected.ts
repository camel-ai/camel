/**
 * Alternative implementation of SOM-screenshot using JS injection
 * This avoids CDP resolution issues by rendering labels directly in the page
 */

import { Page } from 'playwright';
import { SnapshotResult, VisualMarkResult } from './types';
import { writeFile } from 'fs/promises';

export class SomScreenshotInjected {
  /**
   * Take a screenshot with SOM-labels injected into the page
   * This approach uses a single script injection for better performance
   */
  static async captureOptimized(
    page: Page,
    snapshotResult: SnapshotResult,
    clickableElements: Set<string>,
    exportPath?: string
  ): Promise<VisualMarkResult & { timing: any }> {
    const startTime = Date.now();
    
    try {
      // Use the already filtered clickableElements directly
      const filterStartTime = Date.now();
      const filterTime = Date.now() - filterStartTime;
      console.log(`Using pre-filtered clickable elements: ${clickableElements.size} elements`);
      
      // Prepare element geometry data for export
      const elementGeometry: any[] = [];
      // Inject and capture in one go
      // Collect visibility debug info
      const visibilityDebugInfo: any[] = [];
      
      const result = await page.evaluate(async (data) => {
        const { elements, clickable, filterDebugInfo } = data;
        const markedElements: any[] = [];
        
        // Debug info collector - include filter debug info
        const debugInfo: any[] = [...filterDebugInfo];
        
        // Helper function to check element visibility based on coordinates
        function checkElementVisibilityByCoords(
          coords: { x: number, y: number, width: number, height: number }, 
          ref: string,
          elementInfo: any
        ): 'visible' | 'partial' | 'hidden' {
          // Skip if element is outside viewport
          if (coords.y + coords.height < 0 || coords.y > window.innerHeight ||
              coords.x + coords.width < 0 || coords.x > window.innerWidth) {
            return 'hidden';
          }
          
          // Simple approach: just check the center point
          // If center is visible and shows our element (or its child), consider it visible
          const centerX = coords.x + coords.width * 0.5;
          const centerY = coords.y + coords.height * 0.5;
          
          try {
            const elementsAtCenter = document.elementsFromPoint(centerX, centerY);
            if (!elementsAtCenter || elementsAtCenter.length === 0) {
              return 'hidden';
            }
            
            // Find our target element in the stack
            let targetFound = false;
            let targetIsTopmost = false;
            
            for (let i = 0; i < elementsAtCenter.length; i++) {
              const elem = elementsAtCenter[i];
              const rect = elem.getBoundingClientRect();
              
              // Check if this element matches our expected bounds (within tolerance)
              if (Math.abs(rect.left - coords.x) < 5 && 
                  Math.abs(rect.top - coords.y) < 5 &&
                  Math.abs(rect.width - coords.width) < 10 &&
                  Math.abs(rect.height - coords.height) < 10) {
                targetFound = true;
                targetIsTopmost = (i === 0);
                
                // If target is topmost, it's definitely visible
                if (targetIsTopmost) {
                  return 'visible';
                }
                
                // If not topmost, check if the topmost element is a child of our target
                const topmostElem = elementsAtCenter[0];
                if (elem.contains(topmostElem)) {
                  // Topmost is our child - element is visible
                  return 'visible';
                }
                
                // Otherwise, we're obscured
                return 'hidden';
              }
            }
            
            // If we didn't find our target element at all
            if (!targetFound) {
              // Special handling for composite widgets
              const topElement = elementsAtCenter[0];
              const tagName = topElement.tagName.toUpperCase();
              
              // Get element role/type for better decision making
              const elementRole = elementInfo?.role || '';
              const elementTagName = elementInfo?.tagName || '';
              
              // Only apply special handling for form controls that are part of composite widgets
              if (['SELECT', 'INPUT', 'TEXTAREA', 'BUTTON'].includes(tagName)) {
                const isFormRelatedElement = ['combobox', 'select', 'textbox', 'searchbox', 'spinbutton'].includes(elementRole) ||
                                           ['SELECT', 'INPUT', 'TEXTAREA', 'BUTTON', 'OPTION'].includes(elementTagName.toUpperCase());
                
                // Check if the form control approximately matches our area
                const rect = topElement.getBoundingClientRect();
                const overlap = Math.min(rect.right, coords.x + coords.width) - Math.max(rect.left, coords.x) > 0 &&
                               Math.min(rect.bottom, coords.y + coords.height) - Math.max(rect.top, coords.y) > 0;
                
                if (overlap && isFormRelatedElement) {
                  // Check for specific composite widget patterns
                  // For combobox with search input (like Amazon search)
                  if (elementRole === 'combobox' && tagName === 'INPUT') {
                    // This is likely a search box with category selector - mark as visible
                    return 'visible';
                  }
                  
                  // For button/generic elements covered by INPUT with exact same bounds
                  // This usually indicates the INPUT is the actual interactive element for the button
                  if ((elementRole === 'button' || elementRole === 'generic') && tagName === 'INPUT') {
                    const rectMatch = Math.abs(rect.left - coords.x) < 2 && 
                                      Math.abs(rect.top - coords.y) < 2 &&
                                      Math.abs(rect.width - coords.width) < 2 &&
                                      Math.abs(rect.height - coords.height) < 2;
                    if (rectMatch) {
                      // The INPUT is the actual interactive element for this button
                      return 'visible';
                    }
                  }
                  
                  // For other form-related elements, only mark as visible if they share similar positioning
                  // (i.e., they're likely part of the same widget)
                  const sizeDiff = Math.abs(rect.width - coords.width) + Math.abs(rect.height - coords.height);
                  if (sizeDiff < 50) {  // Tolerance for size difference
                    return 'visible';
                  }
                }
              }
              
              return 'hidden';
            }
            
            return 'partial';
            
          } catch (e) {
            // Fallback: use simple elementFromPoint check
            const elem = document.elementFromPoint(centerX, centerY);
            if (!elem) return 'hidden';
            
            const rect = elem.getBoundingClientRect();
            // Check if the element at center matches our bounds
            if (Math.abs(rect.left - coords.x) < 5 && 
                Math.abs(rect.top - coords.y) < 5) {
              return 'visible';
            }
            return 'partial';
          }
        }
        
        
        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'camel-som-overlay-temp';  // Set ID immediately for cleanup
        overlay.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 2147483647;
        `;
        
        // Check visibility for each element using coordinates
        const elementStates = new Map<string, 'visible' | 'partial' | 'hidden'>();
        
        Object.entries(elements).forEach(([ref, element]: [string, any]) => {
          if (element.coordinates && clickable.includes(ref)) {
            const visibility = checkElementVisibilityByCoords(element.coordinates, ref, element);
            elementStates.set(ref, visibility);
            
            // Add debug info
            const centerX = element.coordinates.x + element.coordinates.width * 0.5;
            const centerY = element.coordinates.y + element.coordinates.height * 0.5;
            
            try {
              const elementsAtCenter = document.elementsFromPoint(centerX, centerY);
              const topmostElement = elementsAtCenter[0];
              
              debugInfo.push({
                ref,
                coords: element.coordinates,
                centerPoint: { x: centerX, y: centerY },
                visibilityResult: visibility,
                elementRole: element.role || 'unknown',
                elementTagName: element.tagName || '',
                topmostElement: topmostElement ? {
                  tagName: topmostElement.tagName,
                  className: topmostElement.className,
                  id: topmostElement.id
                } : null,
                elementsAtCenterCount: elementsAtCenter.length
              });
            } catch (e) {
              debugInfo.push({
                ref,
                coords: element.coordinates,
                visibilityResult: visibility,
                elementRole: element.role || 'unknown',
                elementTagName: element.tagName || '',
                error: 'Failed to get elements at center'
              });
            }
          }
        });
        
        // Track label positions to avoid overlap
        const labelPositions: Array<{x: number, y: number, width: number, height: number, ref: string}> = [];
        
        // Helper to check if two rectangles overlap
        function rectsOverlap(r1: any, r2: any): boolean {
          return !(r1.x + r1.width < r2.x || 
                   r2.x + r2.width < r1.x || 
                   r1.y + r1.height < r2.y || 
                   r2.y + r2.height < r1.y);
        }
        
        // Helper to find non-overlapping position for label
        function findLabelPosition(element: any, labelWidth: number, labelHeight: number): {x: number, y: number} {
          const { x, y, width, height } = element.coordinates;
          const isSmallElement = height < 70;
          const margin = 2; // Space between label and element
          
          // Try different positions in order of preference
          const positions = [];
          
          if (isSmallElement) {
            // For small elements, try outside positions
            // 1. Above element
            positions.push({ x: x - 2, y: y - labelHeight - margin });
            // 2. Below element
            positions.push({ x: x - 2, y: y + height + margin });
            // 3. Left of element
            positions.push({ x: x - labelWidth - margin, y: y });
            // 4. Right of element
            positions.push({ x: x + width + margin, y: y });
          } else {
            // For large elements, inside top-left
            positions.push({ x: x + 4, y: y + 4 });
          }
          
          // Check each position
          for (const pos of positions) {
            // Adjust for viewport boundaries
            const adjustedPos = { ...pos };
            
            // Keep within viewport
            adjustedPos.x = Math.max(0, Math.min(adjustedPos.x, window.innerWidth - labelWidth));
            adjustedPos.y = Math.max(0, Math.min(adjustedPos.y, window.innerHeight - labelHeight));
            
            // Check for overlaps with existing labels
            const testRect = { x: adjustedPos.x, y: adjustedPos.y, width: labelWidth, height: labelHeight };
            let hasOverlap = false;
            
            for (const existing of labelPositions) {
              if (rectsOverlap(testRect, existing)) {
                hasOverlap = true;
                break;
              }
            }
            
            if (!hasOverlap) {
              return adjustedPos;
            }
          }
          
          // If all positions overlap, try to find space by offsetting
          // Try positions around the element in a spiral pattern
          const offsets = [
            { dx: 0, dy: -labelHeight - margin - 20 },    // Further above
            { dx: 0, dy: height + margin + 20 },          // Further below
            { dx: -labelWidth - margin - 20, dy: 0 },     // Further left
            { dx: width + margin + 20, dy: 0 },           // Further right
            { dx: -labelWidth - margin, dy: -labelHeight - margin }, // Top-left
            { dx: width + margin, dy: -labelHeight - margin },       // Top-right
            { dx: -labelWidth - margin, dy: height + margin },       // Bottom-left
            { dx: width + margin, dy: height + margin },             // Bottom-right
          ];
          
          for (const offset of offsets) {
            const pos = {
              x: Math.max(0, Math.min(x + offset.dx, window.innerWidth - labelWidth)),
              y: Math.max(0, Math.min(y + offset.dy, window.innerHeight - labelHeight))
            };
            
            const testRect = { x: pos.x, y: pos.y, width: labelWidth, height: labelHeight };
            let hasOverlap = false;
            
            for (const existing of labelPositions) {
              if (rectsOverlap(testRect, existing)) {
                hasOverlap = true;
                break;
              }
            }
            
            if (!hasOverlap) {
              return pos;
            }
          }
          
          // Fallback: use original logic but ensure within viewport
          if (isSmallElement) {
            const fallbackY = y >= 25 ? y - 25 : y + height + 2;
            return {
              x: Math.max(0, Math.min(x - 2, window.innerWidth - labelWidth)),
              y: Math.max(0, Math.min(fallbackY, window.innerHeight - labelHeight))
            };
          } else {
            return { x: x + 4, y: y + 4 };
          }
        }
        
        // Add labels and collect geometry data (only for filtered elements)
        Object.entries(elements).forEach(([ref, element]: [string, any]) => {
          if (element.coordinates && clickable.includes(ref)) {
            const state = elementStates.get(ref);
            
            // Skip completely hidden elements
            if (state === 'hidden') return;
            const label = document.createElement('div');
            const { x, y, width, height } = element.coordinates;
            
            label.style.cssText = `
              position: absolute;
              left: ${x}px;
              top: ${y}px;
              width: ${width}px;
              height: ${height}px;
              border: 2px ${state === 'partial' ? 'dashed' : 'solid'} #FF0066;
              border-radius: 4px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            `;
            
            // Add ref number with smart positioning
            const refLabel = document.createElement('div');
            refLabel.textContent = ref;
            
            // Create temporary label to measure its size
            refLabel.style.cssText = `
              position: absolute;
              visibility: hidden;
              background: #FF0066;
              color: white;
              font: bold 12px Arial, sans-serif;
              padding: 2px 6px;
              border-radius: 2px;
              min-width: 20px;
              text-align: center;
              white-space: nowrap;
            `;
            document.body.appendChild(refLabel);
            const labelWidth = refLabel.offsetWidth;
            const labelHeight = refLabel.offsetHeight;
            document.body.removeChild(refLabel);
            
            // Find non-overlapping position
            const labelPos = findLabelPosition(element, labelWidth, labelHeight);
            
            // Apply final position
            refLabel.style.cssText = `
              position: absolute;
              left: ${labelPos.x - x}px;
              top: ${labelPos.y - y}px;
              background: #FF0066;
              color: white;
              font: bold 12px Arial, sans-serif;
              padding: 2px 6px;
              border-radius: 2px;
              min-width: 20px;
              text-align: center;
              box-shadow: 0 2px 4px rgba(0,0,0,0.2);
              opacity: ${state === 'partial' ? '0.8' : '1'};
              z-index: 1;
              white-space: nowrap;
            `;
            
            // Track this label position
            labelPositions.push({
              x: labelPos.x,
              y: labelPos.y,
              width: labelWidth,
              height: labelHeight,
              ref: ref
            });
            
            label.appendChild(refLabel);
            overlay.appendChild(label);
            
            // Collect geometry data
            markedElements.push({
              ref,
              x,
              y,
              width,
              height,
              center: {
                x: x + width / 2,
                y: y + height / 2
              },
              area: width * height,
              type: element.role || 'unknown',
              text: element.text || '',
              attributes: element.attributes || {},
              tagName: element.tagName || '',
              isFiltered: false
            });
          }
        });
        
        document.body.appendChild(overlay);
        
        // Force repaint
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        return { 
          overlayId: overlay.id,  // Use the ID that was set earlier
          elementCount: overlay.children.length,
          markedElements,
          debugInfo
        };
      }, {
        elements: snapshotResult.elements,
        clickable: Array.from(clickableElements),
        filterDebugInfo: []
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
      
      // Export element geometry if path is provided
      if (exportPath && result.markedElements) {
        try {
          const pageUrl = page.url();
          const timestamp = new Date().toISOString();
          const exportData = {
            timestamp,
            url: pageUrl,
            viewport: await page.viewportSize(),
            elements: result.markedElements,
            summary: {
              totalElements: result.markedElements.length,
              byType: result.markedElements.reduce((acc: any, el: any) => {
                acc[el.type] = (acc[el.type] || 0) + 1;
                return acc;
              }, {}),
              averageSize: {
                width: result.markedElements.reduce((sum: number, el: any) => sum + el.width, 0) / result.markedElements.length,
                height: result.markedElements.reduce((sum: number, el: any) => sum + el.height, 0) / result.markedElements.length
              }
            }
          };
          
          if (typeof writeFile !== 'undefined') {
            await writeFile(exportPath, JSON.stringify(exportData, null, 2));
            console.log(`Element geometry exported to: ${exportPath}`);
          }
          
          // Also save visibility debug info
          if (result.debugInfo) {
            const debugPath = exportPath.replace('.json', '-visibility-debug.json');
            
            const debugData = {
              timestamp,
              url: pageUrl,
              totalElements: result.debugInfo.length,
              summary: {
                visible: result.debugInfo.filter((d: any) => d.visibilityResult === 'visible').length,
                partial: result.debugInfo.filter((d: any) => d.visibilityResult === 'partial').length,
                hidden: result.debugInfo.filter((d: any) => d.visibilityResult === 'hidden').length
              },
              elements: result.debugInfo.sort((a: any, b: any) => {
                // Sort by visibility status: hidden first, then partial, then visible
                const order: any = { hidden: 0, partial: 1, visible: 2 };
                return order[a.visibilityResult] - order[b.visibilityResult];
              })
            };
            
            if (typeof writeFile !== 'undefined') {
              await writeFile(debugPath, JSON.stringify(debugData, null, 2));
              console.log(`Visibility debug info exported to: ${debugPath}`);
            }
          }
        } catch (error) {
          console.error('Failed to export element geometry:', error);
        }
      }
      
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
          display_duration_ms: 1000, // Time the overlay is kept visible
          parent_child_filter_time_ms: filterTime,
          filtered_count: 0 // Filtering is done before this method is called
        }
      };
      
    } catch (error) {
      console.error('SOM screenshot injection error:', error);
      throw error;
    }
  }
}