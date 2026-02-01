/**
 * Type definitions for sheet-operations.js
 */

/**
 * Generate JavaScript code to setup copy event listener
 */
export function copyListenerCode(varName: string): string;

/**
 * Generate JavaScript code to cleanup copy event listener
 */
export function cleanupCode(varName: string): string;

/**
 * Setup copy event listener (for direct browser injection)
 */
export function setupCopyListener(varName: string): string;

/**
 * Cleanup copy event listener (for direct browser injection)
 */
export function cleanupCopyListener(varName: string): string;

/**
 * Get captured copy data (for direct browser injection)
 */
export function getCapturedData(varName: string): Array<string>;
