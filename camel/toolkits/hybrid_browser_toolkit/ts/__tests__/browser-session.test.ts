import { HybridBrowserSession } from '../src/browser-session';

describe('HybridBrowserSession', () => {
  let session: HybridBrowserSession;

  beforeEach(() => {
    session = new HybridBrowserSession();
  });

  it('should create a new session instance', () => {
    expect(session).toBeInstanceOf(HybridBrowserSession);
  });

  describe('filterSnapshotLines', () => {
    it('should filter lines with matching refs', () => {
      const lines = [
        'div [ref=1]',
        '  span [ref=2]',
        '    text content',
        'div [ref=3]',
      ];
      const viewportRefs = new Set(['1', '2']);
      
      const result = (session as any).filterSnapshotLines(lines, viewportRefs);
      
      expect(result).toContain('div [ref=1]');
      expect(result).toContain('  span [ref=2]');
      expect(result).not.toContain('div [ref=3]');
    });

    it('should include lines without refs when they are context', () => {
      const lines = [
        'header',
        '  div [ref=1]',
        '    span [ref=2]',
      ];
      const viewportRefs = new Set(['2']);
      
      const result = (session as any).filterSnapshotLines(lines, viewportRefs);
      
      expect(result.length).toEqual(2);
      expect(result).toContain('header');
    });

    it('should handle empty viewport refs', () => {
      const lines = ['div [ref=1]', 'span [ref=2]'];
      const viewportRefs = new Set<string>();
      
      const result = (session as any).filterSnapshotLines(lines, viewportRefs);
      
      expect(result).toEqual([]);
    });

    it('should filter origin_lines.txt with refs e1, e3, e34, e35 to match filtered_lines.txt', () => {
      const fs = require('fs');
      const path = require('path');
      const originPath = path.resolve(__dirname, 'data', 'origin_lines.txt');
      const filteredPath = path.resolve(__dirname, 'data', 'filtered_lines.txt');
      const originLines = fs.readFileSync(originPath, 'utf-8').split(/\r?\n/).filter(Boolean);
      const filteredLines = fs.readFileSync(filteredPath, 'utf-8').split(/\r?\n/).filter(Boolean);
      const refs = new Set(['e1', 'e3', 'e34', 'e35']);
      const result = (session as any).filterSnapshotLines(originLines, refs);
      expect(result).toEqual(filteredLines);
    });
  });
});
