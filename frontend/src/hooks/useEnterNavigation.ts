import { useRef, useCallback, useEffect, useState } from 'react';

/**
 * Enables Enter-key navigation between form fields inside a container.
 * Also auto-selects InputNumber values on focus so typing replaces them.
 *
 * Supports `data-enter-skip` attribute on any parent element to exclude
 * its inputs from the Enter navigation chain.
 *
 * Works inside Modals (portals) thanks to callback ref pattern.
 */

function getFocusableInputs(container: HTMLElement): HTMLInputElement[] {
  const inputs = Array.from(container.querySelectorAll<HTMLInputElement>('input'));
  return inputs.filter((el) => {
    if (el.disabled) return false;
    if (el.type === 'hidden') return false;
    if (el.getAttribute('tabindex') === '-1') return false;
    if (el.closest('[data-enter-skip]')) return false;
    // Skip inputs hidden by tabs, display:none, etc.
    if (el.offsetParent === null && !el.closest('.ant-select')) return false;
    return true;
  });
}

function isNumberInput(el: HTMLElement): boolean {
  return !!el.closest('.ant-input-number');
}

export default function useEnterNavigation(onLastField?: () => void, onAutoAddRow?: () => void) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const onLastFieldRef = useRef(onLastField);
  onLastFieldRef.current = onLastField;
  const onAutoAddRowRef = useRef(onAutoAddRow);
  onAutoAddRowRef.current = onAutoAddRow;

  // Callback ref — fires when the DOM node mounts/unmounts (including inside Modals)
  const containerRef = useCallback((node: HTMLDivElement | null) => {
    setContainer(node);
  }, []);

  // Auto-focus first visible input when container mounts
  useEffect(() => {
    if (!container) return;
    // Small delay to let Modal/Tab animations finish
    const timer = setTimeout(() => {
      const fields = getFocusableInputs(container);
      if (fields.length > 0 && !container.contains(document.activeElement)) {
        fields[0].focus();
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [container]);

  useEffect(() => {
    if (!container) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Enter') return;

      const target = e.target as HTMLElement;
      if (target.tagName === 'TEXTAREA') return;
      if (target.tagName !== 'INPUT') return;

      const fields = getFocusableInputs(container);
      const idx = fields.indexOf(target as HTMLInputElement);
      if (idx === -1) return;

      // Auto-add row: when Enter is pressed on a field inside [data-enter-add-row]
      if (target.closest('[data-enter-add-row]') && onAutoAddRowRef.current) {
        e.preventDefault();
        e.stopPropagation();
        // Check if there's already a next product search input (next row exists)
        let nextProductInput: HTMLInputElement | null = null;
        for (let i = idx + 1; i < fields.length; i++) {
          if (fields[i].closest('.ant-select')) {
            nextProductInput = fields[i];
            break;
          }
        }
        if (nextProductInput) {
          nextProductInput.focus();
        } else {
          onAutoAddRowRef.current();
          setTimeout(() => {
            if (!container) return;
            const newFields = getFocusableInputs(container);
            for (let i = newFields.length - 1; i >= 0; i--) {
              if (newFields[i].closest('.ant-select')) {
                newFields[i].focus();
                break;
              }
            }
          }, 100);
        }
        return;
      }

      // Check if inside an open Select/AutoComplete dropdown
      const selectWrapper = target.closest('.ant-select');
      if (selectWrapper?.classList.contains('ant-select-open')) {
        if (idx < fields.length - 1) {
          const next = fields[idx + 1];
          setTimeout(() => { next.focus(); next.select(); }, 0);
        } else if (onLastFieldRef.current) {
          setTimeout(onLastFieldRef.current, 0);
        }
        return;
      }

      if (idx < fields.length - 1) {
        e.preventDefault();
        e.stopPropagation();
        const next = fields[idx + 1];
        next.focus();
        next.select();
      } else if (onLastFieldRef.current) {
        e.preventDefault();
        onLastFieldRef.current();
      }
    };

    const handleFocusIn = (e: FocusEvent) => {
      const target = e.target as HTMLInputElement;
      if (target.tagName !== 'INPUT') return;
      if (isNumberInput(target)) {
        requestAnimationFrame(() => target.select());
      }
    };

    container.addEventListener('keydown', handleKeyDown, true);
    container.addEventListener('focusin', handleFocusIn);
    return () => {
      container.removeEventListener('keydown', handleKeyDown, true);
      container.removeEventListener('focusin', handleFocusIn);
    };
  }, [container]);

  return containerRef;
}
