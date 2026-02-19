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
      // Prepare element geometry data for export
      const elementGeometry: any[] = [];
      // Inject and capture in one go
      // Collect visibility debug info
      const visibilityDebugInfo: any[] = [];

      const result = await page.evaluate(async (data) => {
        const { elements, clickable, filterDebugInfo, enableDebug } = data;
        const markedElements: any[] = [];

        // Use Set for O(1) lookup instead of Array.includes O(n)
        const clickableSet = new Set(clickable);

        // Debug info collector - only if enabled
        const debugInfo: any[] = enableDebug ? [...filterDebugInfo] : [];

        // Helper function to check element visibility based on coordinates
        // Returns both visibility result and cached elementsAtCenter for reuse
        function checkElementVisibilityByCoords(
          coords: { x: number, y: number, width: number, height: number },
          ref: string,
          elementInfo: any
        ): { visibility: 'visible' | 'partial' | 'hidden', elementsAtCenter: Element[] | null } {
          // Skip if element is outside viewport
          if (coords.y + coords.height < 0 || coords.y > window.innerHeight ||
              coords.x + coords.width < 0 || coords.x > window.innerWidth) {
            return { visibility: 'hidden', elementsAtCenter: null };
          }

          // For elements inside iframes (indicated by frameIndex or frameUrl),
          // we cannot use document.elementsFromPoint() to check visibility
          // because it doesn't penetrate iframes. Check if an iframe exists
          // at the element's position.
          if (elementInfo?.frameIndex > 0 || elementInfo?.frameUrl) {
            const centerX = coords.x + coords.width * 0.5;
            const centerY = coords.y + coords.height * 0.5;

            // Check if there's an iframe at this position
            const iframeElements = document.elementsFromPoint(centerX, centerY);
            for (const elem of iframeElements) {
              if (elem.tagName.toUpperCase() === 'IFRAME') {
                return { visibility: 'visible', elementsAtCenter: iframeElements };
              }
            }
            // Element has frame info but no iframe found at position -
            // still consider visible as iframe might be transformed/scrolled.
            return { visibility: 'visible', elementsAtCenter: iframeElements };
          }

          // Simple approach: just check the center point
          // If center is visible and shows our element (or its child), consider it visible
          const centerX = coords.x + coords.width * 0.5;
          const centerY = coords.y + coords.height * 0.5;

          try {
            const elementsAtCenter = document.elementsFromPoint(centerX, centerY);
            if (!elementsAtCenter || elementsAtCenter.length === 0) {
              return { visibility: 'hidden', elementsAtCenter: null };
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
                  return { visibility: 'visible', elementsAtCenter };
                }

                // If not topmost, check if the topmost element is a child of our target
                const topmostElem = elementsAtCenter[0];
                const containsTopmost = elem.contains(topmostElem);

                // Also check if they share a common parent (sibling relationship in composite widgets)
                // This handles Material Design buttons where DIV (ripple) and SPAN (text) are siblings
                const shareParent = elem.parentElement && elem.parentElement.contains(topmostElem);
                const isCompositeWidget = shareParent &&
                  ['DIV', 'SPAN', 'I', 'SVG', 'IMG'].includes(topmostElem.tagName.toUpperCase()) &&
                  ['DIV', 'SPAN', 'BUTTON', 'A'].includes(elem.tagName.toUpperCase());

                if (containsTopmost || isCompositeWidget) {
                  // Topmost is our child or sibling in composite widget - element is visible
                  return { visibility: 'visible', elementsAtCenter };
                }

                // Otherwise, we're obscured
                return { visibility: 'hidden', elementsAtCenter };
              }
            }

            // If we didn't find our target element at all
            if (!targetFound) {
              // Special handling for composite widgets
              const topElement = elementsAtCenter[0];
              const tagName = topElement.tagName.toUpperCase();
              const topRect = topElement.getBoundingClientRect();

              // Check if topElement is a Web Component (custom element with Shadow DOM)
              // Custom elements have a hyphen in their tag name (e.g., NTP-APP, MY-COMPONENT)
              const isCustomElement = tagName.includes('-');
              // Also check if it's a shadow host
              const isShadowHost = !!(topElement as any).shadowRoot;

              // If the top element is a Web Component that covers our target area,
              // assume the target is visible inside the shadow DOM
              if (isCustomElement || isShadowHost) {
                // Check if our target coords are within the custom element's bounds
                const targetInCustomElement =
                  coords.x >= topRect.left - 5 &&
                  coords.y >= topRect.top - 5 &&
                  coords.x + coords.width <= topRect.right + 5 &&
                  coords.y + coords.height <= topRect.bottom + 5;

                if (targetInCustomElement) {
                  return { visibility: 'visible', elementsAtCenter };
                }
              }

              // Get element role/type for better decision making
              const elementRole = elementInfo?.role || '';
              const elementTagName = elementInfo?.tagName || '';

              // Check if topElement is likely a child of our target element using multiple strategies:
              // 1. Check if topElement center is within target bounds (most reliable)
              const topCenterX = topRect.left + topRect.width / 2;
              const topCenterY = topRect.top + topRect.height / 2;
              const topCenterInTarget =
                topCenterX >= coords.x - 5 &&
                topCenterX <= coords.x + coords.width + 5 &&
                topCenterY >= coords.y - 5 &&
                topCenterY <= coords.y + coords.height + 5;

              // 2. Check for significant overlap between topElement and target
              const overlapLeft = Math.max(topRect.left, coords.x);
              const overlapRight = Math.min(topRect.right, coords.x + coords.width);
              const overlapTop = Math.max(topRect.top, coords.y);
              const overlapBottom = Math.min(topRect.bottom, coords.y + coords.height);
              const overlapWidth = Math.max(0, overlapRight - overlapLeft);
              const overlapHeight = Math.max(0, overlapBottom - overlapTop);
              const overlapArea = overlapWidth * overlapHeight;
              const topArea = topRect.width * topRect.height;
              const significantOverlap = topArea > 0 && (overlapArea / topArea) > 0.5;

              // If top element overlaps significantly with our target (like SPAN/DIV inside button),
              // consider the target visible
              if ((topCenterInTarget || significantOverlap) &&
                  (elementRole === 'button' || elementRole === 'link' ||
                   elementTagName.toUpperCase() === 'BUTTON' || elementTagName.toUpperCase() === 'A')) {
                return { visibility: 'visible', elementsAtCenter };
              }

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
                    return { visibility: 'visible', elementsAtCenter };
                  }

                  // For button/generic elements covered by INPUT with exact same bounds
                  if ((elementRole === 'button' || elementRole === 'generic') && tagName === 'INPUT') {
                    const rectMatch = Math.abs(rect.left - coords.x) < 2 &&
                                      Math.abs(rect.top - coords.y) < 2 &&
                                      Math.abs(rect.width - coords.width) < 2 &&
                                      Math.abs(rect.height - coords.height) < 2;
                    if (rectMatch) {
                      return { visibility: 'visible', elementsAtCenter };
                    }
                  }

                  // For other form-related elements with similar positioning
                  const sizeDiff = Math.abs(rect.width - coords.width) + Math.abs(rect.height - coords.height);
                  if (sizeDiff < 50) {
                    return { visibility: 'visible', elementsAtCenter };
                  }
                }
              }

              return { visibility: 'hidden', elementsAtCenter };
            }

            return { visibility: 'partial', elementsAtCenter };

          } catch (e) {
            // Fallback: use simple elementFromPoint check
            const elem = document.elementFromPoint(centerX, centerY);
            if (!elem) return { visibility: 'hidden', elementsAtCenter: null };

            const rect = elem.getBoundingClientRect();
            if (Math.abs(rect.left - coords.x) < 5 &&
                Math.abs(rect.top - coords.y) < 5) {
              return { visibility: 'visible', elementsAtCenter: null };
            }
            return { visibility: 'partial', elementsAtCenter: null };
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
          // Use Set for O(1) lookup
          if (element.coordinates && clickableSet.has(ref)) {
            const result = checkElementVisibilityByCoords(element.coordinates, ref, element);
            elementStates.set(ref, result.visibility);

            // Add debug info only if enabled (reuse cached elementsAtCenter)
            if (enableDebug) {
              const centerX = element.coordinates.x + element.coordinates.width * 0.5;
              const centerY = element.coordinates.y + element.coordinates.height * 0.5;
              const elementsAtCenter = result.elementsAtCenter;
              const topmostElement = elementsAtCenter?.[0];

              debugInfo.push({
                ref,
                coords: element.coordinates,
                centerPoint: { x: centerX, y: centerY },
                visibilityResult: result.visibility,
                elementRole: element.role || 'unknown',
                elementTagName: element.tagName || '',
                topmostElement: topmostElement ? {
                  tagName: topmostElement.tagName,
                  className: (topmostElement as HTMLElement).className || '',
                  id: topmostElement.id
                } : null,
                elementsAtCenterCount: elementsAtCenter?.length || 0
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
          if (element.coordinates && clickableSet.has(ref)) {
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
          overlayId: overlay.id,
          elementCount: overlay.children.length,
          markedElements,
          debugInfo
        };
      }, {
        elements: snapshotResult.elements,
        clickable: Array.from(clickableElements),
        filterDebugInfo: [],
        enableDebug: !!exportPath  // Only enable debug when exporting
      });

      // Take screenshot immediately (no need to wait)
      const screenshotBuffer = await page.screenshot({
        fullPage: false,
        type: 'png'
      });

      // Clean up overlay immediately after screenshot
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
          screenshot_time_ms: Date.now() - startTime,
          snapshot_time_ms: 0, // Will be filled by caller
          coordinate_enrichment_time_ms: 0, // Will be filled by caller
          visual_marking_time_ms: Date.now() - startTime,
          injection_method: 'optimized',
          elements_count: result.elementCount,
          display_duration_ms: 0, // No artificial wait
          parent_child_filter_time_ms: 0, // Filtering is done before this method
          filtered_count: 0
        }
      };

    } catch (error) {
      console.error('SOM screenshot injection error:', error);
      throw error;
    }
  }
}
