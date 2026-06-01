import { useState } from 'react';

type RawInspectorProps = {
  value: unknown;
  label?: string;
  description?: string;
  defaultOpen?: boolean;
  className?: string;
};

export function RawInspector({
  value,
  label = 'Advanced / Raw',
  description = 'Debug payload. Do not use this view as the primary operator summary.',
  defaultOpen = false,
  className = '',
}: RawInspectorProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <details
      className={`raw-inspector details-panel compact ${className}`.trim()}
      data-raw-inspector="true"
      open={isOpen}
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
    >
      <summary>{label}</summary>
      {isOpen ? (
        <>
          <p className="supporting raw-inspector-description">{description}</p>
          <pre className="json-panel" data-raw-inspector-panel="true">
            {JSON.stringify(value ?? {}, null, 2)}
          </pre>
        </>
      ) : null}
    </details>
  );
}
