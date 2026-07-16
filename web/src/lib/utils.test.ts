import { describe, it, expect, vi, beforeEach } from 'vitest';
import { cn, downloadFile, toCSV } from './utils';

describe('utils', () => {
  describe('cn', () => {
    it('merges class names correctly', () => {
      expect(cn('bg-red-500', 'text-white')).toBe('bg-red-500 text-white');
      expect(cn('p-4', { 'bg-red-500': true, 'text-white': false })).toBe('p-4 bg-red-500');
    });

    it('handles tailwind conflicts', () => {
      expect(cn('p-4 p-8')).toBe('p-8');
      expect(cn('bg-red-500', 'bg-blue-500')).toBe('bg-blue-500');
    });
  });

  describe('downloadFile', () => {
    beforeEach(() => {
      globalThis.URL.createObjectURL = vi.fn(() => 'blob:test-url');
      globalThis.URL.revokeObjectURL = vi.fn();
    });

    it('creates a download link and triggers click', () => {
      const appendChildSpy = vi.spyOn(document.body, 'appendChild');
      const removeChildSpy = vi.spyOn(document.body, 'removeChild');
      const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

      downloadFile('test.csv', 'a,b\n1,2', 'text/csv');

      expect(globalThis.URL.createObjectURL).toHaveBeenCalled();
      expect(appendChildSpy).toHaveBeenCalled();
      expect(clickSpy).toHaveBeenCalled();
      expect(removeChildSpy).toHaveBeenCalled();
      expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith('blob:test-url');
    });
  });

  describe('toCSV', () => {
    it('converts array of objects to CSV string', () => {
      const rows = [
        { name: 'Alice', age: 30 },
        { name: 'Bob', age: 25 },
      ];
      const csv = toCSV(rows, ['name', 'age']);
      expect(csv).toBe('name,age\nAlice,30\nBob,25');
    });

    it('handles missing values by replacing them with empty string', () => {
      const rows = [
        { name: 'Alice', age: 30 },
        { name: 'Bob' }, // age is missing
      ] as Record<string, unknown>[];
      const csv = toCSV(rows, ['name', 'age']);
      expect(csv).toBe('name,age\nAlice,30\nBob,');
    });

    it('escapes values containing commas or quotes', () => {
      const rows = [
        { note: 'Hello, World', val: 'Test' },
        { note: 'He said "Hi"', val: 'Yes' },
      ];
      const csv = toCSV(rows, ['note', 'val']);
      expect(csv).toBe('note,val\n"Hello, World",Test\n"He said ""Hi""",Yes');
    });
  });
});
