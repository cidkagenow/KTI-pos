import { Input } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useRef, type KeyboardEvent, type CSSProperties } from 'react';
import type { InputRef } from 'antd';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  /** The first matching result's label — shown as ghost text if it starts with the typed value */
  suggestion?: string;
  placeholder?: string;
  style?: CSSProperties;
  autoFocus?: boolean;
}

export default function SearchInput({
  value,
  onChange,
  suggestion,
  placeholder,
  style,
  autoFocus,
}: SearchInputProps) {
  const inputRef = useRef<InputRef>(null);

  const trimmed = value.trim();
  const match =
    trimmed.length > 0 &&
    suggestion &&
    suggestion.toLowerCase().startsWith(trimmed.toLowerCase());
  // Preserve user's typed casing + append the rest of the suggestion
  const ghostText = match ? trimmed + suggestion!.slice(trimmed.length) : '';

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Tab' && ghostText) {
      e.preventDefault();
      onChange(ghostText);
    }
  };

  return (
    <div style={{ position: 'relative', ...style }}>
      {/* Ghost suggestion behind the real input */}
      {ghostText && (
        <Input
          prefix={<SearchOutlined style={{ opacity: 0 }} />}
          value={ghostText}
          readOnly
          tabIndex={-1}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            opacity: 0.4,
            background: 'transparent',
            borderColor: 'transparent',
            pointerEvents: 'none',
            zIndex: 0,
          }}
        />
      )}
      {/* Actual input */}
      <Input
        ref={inputRef}
        prefix={<SearchOutlined />}
        allowClear
        autoFocus={autoFocus}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        style={{
          background: ghostText ? 'transparent' : undefined,
          position: 'relative',
          zIndex: 1,
        }}
      />
    </div>
  );
}
