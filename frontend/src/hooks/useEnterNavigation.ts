import { useEffect, useRef, useCallback } from 'react';

/**
 * Enables Enter-key navigation between form fields inside a container.
 * Also auto-selects InputNumber values on focus so typing replaces them.
 *
 * Supports `data-enter-skip` attribute on any parent element to exclude
 * its inputs from the Enter navigation chain.
 */

function getFocusableInputs(container: HTMLElement): HTMLInputElement[] {
  const inputs = Array.from(container.querySelectorAll<HTMLInputElement>('input'));
  return inputs.filter((el) => {
    if (el.disabled) return false;
    if (el.type === 'hidden') return false;
    if (el.getAttribute('tabindex') === '-1') return false;
    if (el.closest('[data-enter-skip]')) return false;
    return true;
  });
}

function isNumberInput(el: HTMLElement): boolean {
  return !!el.closest('.ant-input-number');
}

export default function useEnterNavigation(onLastField?: () => void) {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key !== 'Enter') return;

      const target = e.target as HTMLElement;
      if (target.tagName === 'TEXTAREA') return;
      if (target.tagName !== 'INPUT') return;

      const container = containerRef.current;
      if (!container) return;

      const fields = getFocusableInputs(container);
      const idx = fields.indexOf(target as HTMLInputElement);
      if (idx === -1) return;

      // Check if inside an open Select/AutoComplete dropdown
      const selectWrapper = target.closest('.ant-select');
      if (selectWrapper?.classList.contains('ant-select-open')) {
        if (idx < fields.length - 1) {
          const next = fields[idx + 1];
          setTimeout(() => { next.focus(); next.select(); }, 0);
        } else if (onLastField) {
          setTimeout(onLastField, 0);
        }
        return;
      }

      if (idx < fields.length - 1) {
        e.preventDefault();
        e.stopPropagation();
        const next = fields[idx + 1];
        next.focus();
        next.select();
      } else if (onLastField) {
        e.preventDefault();
        onLastField();
      }
    },
    [onLastField],
  );

  // Auto-select InputNumber values on any focus (click, tab, etc.)
  const handleFocusIn = useCallback((e: FocusEvent) => {
    const target = e.target as HTMLInputElement;
    if (target.tagName !== 'INPUT') return;
    if (isNumberInput(target)) {
      requestAnimationFrame(() => target.select());
    }
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.addEventListener('keydown', handleKeyDown, true);
    container.addEventListener('focusin', handleFocusIn);
    return () => {
      container.removeEventListener('keydown', handleKeyDown, true);
      container.removeEventListener('focusin', handleFocusIn);
    };
  }, [handleKeyDown, handleFocusIn]);

  return containerRef;
}
