import { describe, it, expect } from 'vitest';
import { cn } from '../utils';

describe('cn', () => {
  it('should merge class names', () => {
    const result = cn('foo', 'bar');
    expect(result).toBe('foo bar');
  });

  it('should handle conditional classes', () => {
    const result = cn('base', true && 'active', false && 'disabled');
    expect(result).toBe('base active');
  });

  it('should handle undefined and null values', () => {
    const result = cn('base', undefined, null, 'extra');
    expect(result).toBe('base extra');
  });

  it('should handle arrays', () => {
    const result = cn('foo', ['bar', 'baz']);
    expect(result).toBe('foo bar baz');
  });

  it('should handle objects', () => {
    const result = cn('base', { active: true, disabled: false });
    expect(result).toBe('base active');
  });

  it('should merge tailwind classes correctly', () => {
    // twMerge should handle conflicting tailwind classes
    const result = cn('px-2 py-1', 'px-4');
    expect(result).toBe('py-1 px-4');
  });

  it('should handle empty arguments', () => {
    const result = cn();
    expect(result).toBe('');
  });

  it('should handle complex combinations', () => {
    const isActive = true;
    const isDisabled = false;

    const result = cn(
      'btn',
      'btn-primary',
      isActive && 'btn-active',
      isDisabled && 'btn-disabled',
      { 'btn-loading': false, 'btn-success': true }
    );

    expect(result).toBe('btn btn-primary btn-active btn-success');
  });
});
