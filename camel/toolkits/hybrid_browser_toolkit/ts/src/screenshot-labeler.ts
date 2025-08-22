// Improved screenshot labeling system for web agents
// This addresses overlapping labels and small element visibility issues

interface ElementWithCoordinates {
  ref: string;
  x: number;
  y: number;
  width: number;
  height: number;
  isClickable: boolean;
}

interface LabelPosition {
  ref: string;
  x: number;
  y: number;
  lineToElement?: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
}

export class ScreenshotLabeler {
  private readonly MIN_ELEMENT_WIDTH = 40; // Minimum width for direct labeling
  private readonly MIN_ELEMENT_HEIGHT = 70; // Minimum height for direct labeling
  private readonly LABEL_PADDING = 4;
  private readonly LABEL_HEIGHT = 16;
  private readonly LABEL_MIN_WIDTH = 24;
  private readonly LINE_WIDTH = 3; // Increased line width
  private readonly LINE_COLOR = '#FF0066'; // Bright pink/red for high visibility
  private readonly ARROW_SIZE = 8; // Arrow head size
  private readonly MIN_LABEL_SPACING = 20;

  /**
   * Main method to create improved labels for screenshot elements
   */
  public createImprovedLabels(
    elements: ElementWithCoordinates[],
    screenshotWidth: number,
    screenshotHeight: number
  ): string {
    // Step 1: Categorize elements by size
    const { largeElements, smallElements } = this.categorizeElements(elements);
    
    // Step 2: Create labels for large elements (placed inside)
    const largeLabels = this.createInternalLabels(largeElements);
    
    // Step 3: Create labels for small elements (placed outside with leader lines)
    const smallLabels = this.createExternalLabels(
      smallElements, 
      largeLabels, 
      screenshotWidth, 
      screenshotHeight
    );
    
    // Step 4: Combine all labels into SVG
    return this.generateSVG(
      [...largeElements, ...smallElements],
      [...largeLabels, ...smallLabels],
      screenshotWidth,
      screenshotHeight
    );
  }

  /**
   * Categorize elements by size
   */
  private categorizeElements(elements: ElementWithCoordinates[]) {
    const largeElements: ElementWithCoordinates[] = [];
    const smallElements: ElementWithCoordinates[] = [];
    
    elements.forEach(element => {
      if (element.width >= this.MIN_ELEMENT_WIDTH && element.height >= this.MIN_ELEMENT_HEIGHT) {
        largeElements.push(element);
      } else {
        smallElements.push(element);
      }
    });
    
    return { largeElements, smallElements };
  }

  /**
   * Create labels positioned inside large elements
   */
  private createInternalLabels(elements: ElementWithCoordinates[]): LabelPosition[] {
    const labels: LabelPosition[] = [];
    const occupiedPositions: Array<{x: number, y: number, width: number, height: number}> = [];
    
    // Sort elements by size (larger first) to prioritize label placement
    const sortedElements = [...elements].sort((a, b) => 
      (b.width * b.height) - (a.width * a.height)
    );
    
    sortedElements.forEach(element => {
      // Try different positions within the element
      const positions = [
        { x: element.x + this.LABEL_PADDING, y: element.y + this.LABEL_HEIGHT }, // Top-left
        { x: element.x + element.width - this.LABEL_MIN_WIDTH - this.LABEL_PADDING, y: element.y + this.LABEL_HEIGHT }, // Top-right
        { x: element.x + this.LABEL_PADDING, y: element.y + element.height - this.LABEL_PADDING }, // Bottom-left
        { x: element.x + element.width - this.LABEL_MIN_WIDTH - this.LABEL_PADDING, y: element.y + element.height - this.LABEL_PADDING }, // Bottom-right
        { x: element.x + element.width / 2 - this.LABEL_MIN_WIDTH / 2, y: element.y + element.height / 2 } // Center
      ];
      
      // Find first non-overlapping position
      for (const pos of positions) {
        const labelBounds = {
          x: pos.x,
          y: pos.y - this.LABEL_HEIGHT,
          width: this.LABEL_MIN_WIDTH,
          height: this.LABEL_HEIGHT
        };
        
        if (!this.overlapsWithExisting(labelBounds, occupiedPositions) &&
            this.isWithinBounds(labelBounds, element)) {
          labels.push({
            ref: element.ref,
            x: pos.x,
            y: pos.y
          });
          occupiedPositions.push(labelBounds);
          break;
        }
      }
    });
    
    return labels;
  }

  /**
   * Create labels positioned outside small elements with leader lines
   */
  private createExternalLabels(
    elements: ElementWithCoordinates[],
    existingLabels: LabelPosition[],
    screenshotWidth: number,
    screenshotHeight: number
  ): LabelPosition[] {
    const labels: LabelPosition[] = [];
    const occupiedPositions = existingLabels.map(label => ({
      x: label.x,
      y: label.y - this.LABEL_HEIGHT,
      width: this.LABEL_MIN_WIDTH,
      height: this.LABEL_HEIGHT
    }));
    
    // Group nearby small elements
    const groups = this.groupNearbyElements(elements);
    
    groups.forEach(group => {
      if (group.length === 1) {
        // Single small element - place label with leader line
        const element = group[0];
        const labelPos = this.findBestExternalPosition(
          element,
          occupiedPositions,
          elements, // Pass all small elements to avoid overlapping them
          screenshotWidth,
          screenshotHeight
        );
        
        if (labelPos) {
          labels.push({
            ref: element.ref,
            x: labelPos.x,
            y: labelPos.y,
            lineToElement: (() => {
              const actualLabelWidth = this.calculateLabelWidth(element.ref);
              const padding = 4;
              const connections = this.getBestConnectionPoints(
                labelPos.x - padding,  // Account for padding
                labelPos.y,
                actualLabelWidth,
                this.LABEL_HEIGHT + 4,  // Account for vertical padding
                element.x,
                element.y,
                element.width,
                element.height
              );
              return {
                x1: connections.start.x,
                y1: connections.start.y,
                x2: connections.end.x,
                y2: connections.end.y
              };
            })()
          });
          
          occupiedPositions.push({
            x: labelPos.x,
            y: labelPos.y - this.LABEL_HEIGHT,
            width: this.LABEL_MIN_WIDTH,
            height: this.LABEL_HEIGHT
          });
        }
      } else {
        // Multiple small elements - create a group label
        const groupBounds = this.getGroupBounds(group);
        const groupLabels = this.createGroupLabel(group, groupBounds, occupiedPositions, elements, screenshotWidth, screenshotHeight);
        
        if (groupLabels && groupLabels.length > 0) {
          // Only add labels that don't overlap with occupied positions
          groupLabels.forEach(label => {
            // Clamp Y position to screen bounds
            const clampedY = Math.max(this.LABEL_HEIGHT, Math.min(screenshotHeight, label.y));
            label.y = clampedY;
            
            // Update line coordinates if clamped
            if (label.lineToElement) {
              label.lineToElement.y1 = clampedY - this.LABEL_HEIGHT / 2;
            }
            
            const labelBounds = {
              x: label.x,
              y: label.y - this.LABEL_HEIGHT,
              width: this.LABEL_MIN_WIDTH,
              height: this.LABEL_HEIGHT
            };
            
            // Check for overlaps before adding
            if (!this.overlapsWithExisting(labelBounds, occupiedPositions)) {
              labels.push(label);
              occupiedPositions.push(labelBounds);
            }
          });
        }
      }
    });
    
    return labels;
  }

  /**
   * Group nearby small elements to avoid label clutter
   */
  private groupNearbyElements(elements: ElementWithCoordinates[]): ElementWithCoordinates[][] {
    const groups: ElementWithCoordinates[][] = [];
    const used = new Set<string>();
    const threshold = 50; // Distance threshold for grouping
    
    elements.forEach(element => {
      if (used.has(element.ref)) return;
      
      const group = [element];
      used.add(element.ref);
      
      // Find all nearby elements
      elements.forEach(other => {
        if (used.has(other.ref)) return;
        
        const distance = this.getDistance(element, other);
        if (distance < threshold) {
          group.push(other);
          used.add(other.ref);
        }
      });
      
      groups.push(group);
    });
    
    return groups;
  }

  /**
   * Calculate distance between two elements
   */
  private getDistance(a: ElementWithCoordinates, b: ElementWithCoordinates): number {
    const centerA = { x: a.x + a.width / 2, y: a.y + a.height / 2 };
    const centerB = { x: b.x + b.width / 2, y: b.y + b.height / 2 };
    
    return Math.sqrt(
      Math.pow(centerA.x - centerB.x, 2) + 
      Math.pow(centerA.y - centerB.y, 2)
    );
  }

  /**
   * Get bounding box for a group of elements
   */
  private getGroupBounds(elements: ElementWithCoordinates[]) {
    const minX = Math.min(...elements.map(e => e.x));
    const minY = Math.min(...elements.map(e => e.y));
    const maxX = Math.max(...elements.map(e => e.x + e.width));
    const maxY = Math.max(...elements.map(e => e.y + e.height));
    
    return {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY
    };
  }

  /**
   * Create labels for a group of small elements
   */
  private createGroupLabel(
    group: ElementWithCoordinates[],
    groupBounds: {x: number, y: number, width: number, height: number},
    occupiedPositions: Array<{x: number, y: number, width: number, height: number}>,
    allSmallElements: ElementWithCoordinates[],
    screenshotWidth: number,
    screenshotHeight: number
  ): LabelPosition[] {
    const labels: LabelPosition[] = [];
    
    // Sort elements by Y position to minimize line crossings
    const sortedGroup = [...group].sort((a, b) => (a.y + a.height / 2) - (b.y + b.height / 2));
    
    // Try to place labels in a column to the side of the group
    let labelX = groupBounds.x + groupBounds.width + 20;
    let useLeftSide = false;
    
    // Check if right side placement would go off-screen
    if (labelX + this.LABEL_MIN_WIDTH > screenshotWidth) {
      // Try left side instead
      const leftX = groupBounds.x - this.LABEL_MIN_WIDTH - 20;
      if (leftX >= 0) {
        labelX = leftX;
        useLeftSide = true;
      } else {
        // Can't place on either side
        return labels;
      }
    }
    
    // Calculate initial Y position and clamp to screen bounds
    let labelY = Math.max(this.LABEL_HEIGHT, groupBounds.y);
    
    // Try to find a non-overlapping position for the column
    let columnShift = 0;
    const maxShiftAttempts = 10;
    let foundValidPosition = false;
    
    for (let attempt = 0; attempt < maxShiftAttempts; attempt++) {
      const testLabels: LabelPosition[] = [];
      let allFit = true;
      
      // Test all labels in this column position
      for (let i = 0; i < sortedGroup.length; i++) {
        const labelYPosition = labelY + columnShift + (i * this.MIN_LABEL_SPACING);
        
        // Clamp Y to screen bounds
        if (labelYPosition > screenshotHeight || labelYPosition < this.LABEL_HEIGHT) {
          allFit = false;
          break;
        }
        
        const labelBounds = {
          x: labelX,
          y: labelYPosition - this.LABEL_HEIGHT,
          width: this.LABEL_MIN_WIDTH,
          height: this.LABEL_HEIGHT
        };
        
        // Check for overlaps with existing labels and small elements
        if (this.overlapsWithExisting(labelBounds, occupiedPositions) ||
            this.overlapsWithExisting(labelBounds, allSmallElements)) {
          allFit = false;
          break;
        }
        
        const actualLabelWidth = this.calculateLabelWidth(sortedGroup[i].ref);
        const padding = 4;
        const connections = this.getBestConnectionPoints(
          labelX - padding,  // Account for padding
          labelYPosition,
          actualLabelWidth,
          this.LABEL_HEIGHT + 4,  // Account for vertical padding
          sortedGroup[i].x,
          sortedGroup[i].y,
          sortedGroup[i].width,
          sortedGroup[i].height
        );
        
        testLabels.push({
          ref: sortedGroup[i].ref,
          x: labelX,
          y: labelYPosition,
          lineToElement: {
            x1: connections.start.x,
            y1: connections.start.y,
            x2: connections.end.x,
            y2: connections.end.y
          }
        });
      }
      
      if (allFit) {
        labels.push(...testLabels);
        foundValidPosition = true;
        break;
      }
      
      // Try shifting up or down
      columnShift = attempt % 2 === 0 ? -(attempt + 1) * 10 : (attempt + 1) * 10;
    }
    
    // If no valid position found, place what we can with clamping
    if (!foundValidPosition) {
      sortedGroup.forEach((element, index) => {
        const labelYPosition = Math.max(this.LABEL_HEIGHT, 
          Math.min(screenshotHeight, labelY + (index * this.MIN_LABEL_SPACING)));
        
        const actualLabelWidth = this.calculateLabelWidth(element.ref);
        const padding = 4;
        const connections = this.getBestConnectionPoints(
          labelX - padding,  // Account for padding
          labelYPosition,
          actualLabelWidth,
          this.LABEL_HEIGHT + 4,  // Account for vertical padding
          element.x,
          element.y,
          element.width,
          element.height
        );
        
        labels.push({
          ref: element.ref,
          x: labelX,
          y: labelYPosition,
          lineToElement: {
            x1: connections.start.x,
            y1: connections.start.y,
            x2: connections.end.x,
            y2: connections.end.y
          }
        });
      });
    }
    
    return labels;
  }

  /**
   * Find best external position for a label
   */
  private findBestExternalPosition(
    element: ElementWithCoordinates,
    occupiedPositions: Array<{x: number, y: number, width: number, height: number}>,
    allSmallElements: ElementWithCoordinates[],
    screenshotWidth: number,
    screenshotHeight: number
  ): {x: number, y: number} | null {
    // Try positions around the element
    const positions = [
      { x: element.x + element.width + 10, y: element.y + element.height / 2 }, // Right
      { x: element.x - this.LABEL_MIN_WIDTH - 10, y: element.y + element.height / 2 }, // Left
      { x: element.x + element.width / 2 - this.LABEL_MIN_WIDTH / 2, y: element.y - this.LABEL_HEIGHT - 10 }, // Top
      { x: element.x + element.width / 2 - this.LABEL_MIN_WIDTH / 2, y: element.y + element.height + 10 + this.LABEL_HEIGHT } // Bottom
    ];
    
    for (const pos of positions) {
      const labelBounds = {
        x: pos.x,
        y: pos.y - this.LABEL_HEIGHT,
        width: this.LABEL_MIN_WIDTH,
        height: this.LABEL_HEIGHT
      };
      
      if (this.isWithinScreenBounds(labelBounds, screenshotWidth, screenshotHeight) &&
          !this.overlapsWithExisting(labelBounds, occupiedPositions) &&
          !this.overlapsWithExisting(labelBounds, allSmallElements)) {
        return pos;
      }
    }
    
    return null;
  }

  /**
   * Check if label is within element bounds
   */
  private isWithinBounds(label: {x: number, y: number, width: number, height: number}, element: ElementWithCoordinates): boolean {
    return label.x >= element.x &&
           label.y >= element.y &&
           label.x + label.width <= element.x + element.width &&
           label.y + label.height <= element.y + element.height;
  }

  /**
   * Check if label is within screenshot bounds
   */
  private isWithinScreenBounds(label: {x: number, y: number, width: number, height: number}, width: number, height: number): boolean {
    return label.x >= 0 &&
           label.y >= 0 &&
           label.x + label.width <= width &&
           label.y + label.height <= height;
  }

  /**
   * Calculate the best connection points for a line between label and element
   */
  private getBestConnectionPoints(
    labelX: number,
    labelY: number,
    labelWidth: number,
    labelHeight: number,
    elementX: number,
    elementY: number,
    elementWidth: number,
    elementHeight: number
  ): {start: {x: number, y: number}, end: {x: number, y: number}} {
    
    // Calculate all possible connection points on the label
    // Note: labelY is the baseline of the text, not the top of the label box
    const labelBoxTop = labelY - labelHeight;
    const labelBoxBottom = labelY;
    const labelCenterX = labelX + labelWidth / 2;
    const labelCenterY = labelBoxTop + labelHeight / 2;
    
    const labelPoints = [
      { x: labelX, y: labelCenterY }, // Left edge center
      { x: labelX + labelWidth, y: labelCenterY }, // Right edge center  
      { x: labelCenterX, y: labelBoxTop }, // Top edge center
      { x: labelCenterX, y: labelBoxBottom } // Bottom edge center
    ];
    
    // Calculate all possible connection points on the element
    const elementCenterX = elementX + elementWidth / 2;
    const elementCenterY = elementY + elementHeight / 2;
    
    const elementPoints = [
      { x: elementX, y: elementCenterY }, // Left edge center
      { x: elementX + elementWidth, y: elementCenterY }, // Right edge center
      { x: elementCenterX, y: elementY }, // Top edge center
      { x: elementCenterX, y: elementY + elementHeight } // Bottom edge center
    ];
    
    // Find the pair of points with minimum distance
    let bestLabelPoint = labelPoints[0];
    let bestElementPoint = elementPoints[0];
    let minDistance = Number.MAX_VALUE;
    
    labelPoints.forEach(labelPoint => {
      elementPoints.forEach(elementPoint => {
        const distance = Math.sqrt(
          Math.pow(labelPoint.x - elementPoint.x, 2) + 
          Math.pow(labelPoint.y - elementPoint.y, 2)
        );
        if (distance < minDistance) {
          minDistance = distance;
          bestLabelPoint = labelPoint;
          bestElementPoint = elementPoint;
        }
      });
    });
    
    
    return { start: bestLabelPoint, end: bestElementPoint };
  }

  /**
   * Check if label overlaps with existing labels
   */
  private overlapsWithExisting(
    label: {x: number, y: number, width: number, height: number},
    existing: Array<{x: number, y: number, width: number, height: number}>
  ): boolean {
    return existing.some(existing => 
      !(label.x + label.width < existing.x ||
        existing.x + existing.width < label.x ||
        label.y + label.height < existing.y ||
        existing.y + existing.height < label.y)
    );
  }

  /**
   * Escape XML entities to prevent injection
   */
  private escapeXML(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  /**
   * Estimate text width for dynamic sizing
   */
  private estimateTextWidth(text: string, fontSize: number, fontFamily: string): number {
    // Rough estimation: average character width is about 0.6 * fontSize for Arial
    const avgCharWidth = fontSize * 0.6;
    return text.length * avgCharWidth;
  }

  /**
   * Calculate actual label width including padding
   */
  private calculateLabelWidth(ref: string): number {
    const padding = 4;
    const textWidth = this.estimateTextWidth(ref, 11, 'Arial, sans-serif');
    return Math.max(this.LABEL_MIN_WIDTH, textWidth + padding * 2);
  }

  /**
   * Generate final SVG with all elements and labels
   */
  private generateSVG(
    elements: ElementWithCoordinates[],
    labels: LabelPosition[],
    screenshotWidth: number,
    screenshotHeight: number
  ): string {
    const elementsSVG = elements.map(element => {
      // All elements are now clickable/interactive - use blue color scheme
      const colors = {
        fill: 'rgba(0, 150, 255, 0.15)',
        stroke: '#0096FF'
      };
      
      return `
        <rect x="${element.x}" y="${element.y}" width="${element.width}" height="${element.height}"
              fill="${colors.fill}" stroke="${colors.stroke}" stroke-width="2" rx="2"/>
      `;
    }).join('');
    
    // First render all leader lines (below all labels)
    const linesSVG = labels.map(label => {
      if (!label.lineToElement) return '';
      
      const padding = 4;
      const textWidth = this.estimateTextWidth(label.ref, 11, 'Arial, sans-serif');
      const labelWidth = Math.max(this.LABEL_MIN_WIDTH, textWidth + padding * 2);
      
      return `
        <defs>
          <marker id="arrow-${label.ref}" markerWidth="${this.ARROW_SIZE}" markerHeight="${this.ARROW_SIZE}" 
                  refX="${this.ARROW_SIZE}" refY="${this.ARROW_SIZE/2}" orient="auto" markerUnits="userSpaceOnUse">
            <path d="M0,0 L${this.ARROW_SIZE},${this.ARROW_SIZE/2} L0,${this.ARROW_SIZE} L${this.ARROW_SIZE/4},${this.ARROW_SIZE/2} Z" 
                  fill="${this.LINE_COLOR}" />
          </marker>
        </defs>
        <!-- White outline for contrast -->
        <line x1="${label.lineToElement.x1}" y1="${label.lineToElement.y1}"
              x2="${label.lineToElement.x2}" y2="${label.lineToElement.y2}"
              stroke="white" stroke-width="${this.LINE_WIDTH + 2}" 
              opacity="0.8"/>
        <!-- Main colored line with arrow -->
        <line x1="${label.lineToElement.x1}" y1="${label.lineToElement.y1}"
              x2="${label.lineToElement.x2}" y2="${label.lineToElement.y2}"
              stroke="${this.LINE_COLOR}" stroke-width="${this.LINE_WIDTH}" 
              opacity="0.9" marker-end="url(#arrow-${label.ref})"/>
        <!-- Circle at start point -->
        <circle cx="${label.lineToElement.x1}" cy="${label.lineToElement.y1}" r="3" 
                fill="${this.LINE_COLOR}" stroke="white" stroke-width="1"/>
      `;
    }).join('');
    
    // Then render all labels (above all lines)
    const labelsSVG = labels.map(label => {
      // All labels use blue color for clickable elements
      const textColor = '#0096FF';
      const fontSize = 11;
      const fontFamily = 'Arial, sans-serif';
      const padding = 4;
      
      // Escape the label text to prevent XML injection
      const escapedRef = this.escapeXML(label.ref);
      
      // Calculate dynamic width based on text content
      const textWidth = this.estimateTextWidth(label.ref, fontSize, fontFamily);
      const labelWidth = Math.max(this.LABEL_MIN_WIDTH, textWidth + padding * 2);
      
      // Add label background with dynamic width
      return `
        <rect x="${label.x - padding}" y="${label.y - this.LABEL_HEIGHT - 2}" 
              width="${labelWidth}" height="${this.LABEL_HEIGHT + 4}"
              fill="white" opacity="0.9" rx="2"/>
        <text x="${label.x}" y="${label.y}" font-family="${fontFamily}"
              font-size="${fontSize}" fill="${textColor}" font-weight="bold">${escapedRef}</text>
      `;
    }).join('');
    
    return `${elementsSVG}${linesSVG}${labelsSVG}`;
  }

}