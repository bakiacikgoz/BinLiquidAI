import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent } from 'react';

import type { CanvasArtifactContent } from '../../artifactContracts';
import type { ArtifactEditorProps } from '../ArtifactEditorHost';
import {
  addCanvasShape,
  addCanvasFreeDrawStroke,
  canvasOutline,
  canvasSelection,
  deleteCanvasObjects,
  moveCanvasObjects,
  parseCanvasArtifactContent,
  resizeCanvasObject,
  withImportedCanvasAsset,
  type CanvasShapeType,
} from './canvasAdapter';

type PointerOperation =
  | { kind: 'move'; objectIds: string[]; clientX: number; clientY: number }
  | { kind: 'resize'; objectId: string; originX: number; originY: number; width: number; height: number }
  | { kind: 'pan'; clientX: number; clientY: number; panX: number; panY: number }
  | { kind: 'draw'; points: Array<{ x: number; y: number }> };

const SHAPES: Array<{ type: CanvasShapeType; label: string }> = [
  { type: 'rectangle', label: 'Rectangle' },
  { type: 'ellipse', label: 'Ellipse' },
  { type: 'text', label: 'Text' },
  { type: 'line', label: 'Line' },
  { type: 'arrow', label: 'Arrow' },
  { type: 'note', label: 'Note' },
];

function contentKey(value: CanvasArtifactContent): string {
  return JSON.stringify(value);
}

export function CanvasArtifactEditor(props: ArtifactEditorProps) {
  const incoming = useMemo(() => parseCanvasArtifactContent(props.content), [props.content]);
  const incomingKey = useMemo(() => contentKey(incoming), [incoming]);
  const [canvas, setCanvas] = useState<CanvasArtifactContent>(incoming);
  const canvasRef = useRef(canvas);
  const emittedKey = useRef(incomingKey);
  const [history, setHistory] = useState<CanvasArtifactContent[]>([incoming]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const operation = useRef<PointerOperation | null>(null);
  const [importing, setImporting] = useState(false);
  const [freeDraw, setFreeDraw] = useState(false);
  const editable = props.mode !== 'view' && props.artifact.status !== 'archived';
  const outline = useMemo(() => canvasOutline(canvas), [canvas]);

  useEffect(() => {
    if (incomingKey === emittedKey.current) return;
    canvasRef.current = incoming;
    setCanvas(incoming);
    setHistory([incoming]);
    setHistoryIndex(0);
    setSelectedIds([]);
  }, [incoming, incomingKey]);

  const select = useCallback((objectIds: string[]) => {
    const next = objectIds.length ? canvasSelection(objectIds).objectIds : [];
    setSelectedIds(next);
    props.onSelectionChange(next.length ? canvasSelection(next) : null);
    return next;
  }, [props]);

  const preview = useCallback((next: CanvasArtifactContent) => {
    canvasRef.current = next;
    setCanvas(next);
  }, []);

  const persist = useCallback((next: CanvasArtifactContent, nextSelection = selectedIds) => {
    const parsed = parseCanvasArtifactContent(next);
    const key = contentKey(parsed);
    preview(parsed);
    emittedKey.current = key;
    setHistory((previous) => [...previous.slice(0, historyIndex + 1), parsed]);
    setHistoryIndex((previous) => Math.min(previous + 1, historyIndex + 1));
    props.onChange(parsed, nextSelection.length ? canvasSelection(nextSelection) : undefined);
  }, [historyIndex, preview, props, selectedIds]);

  const moveSelected = useCallback((deltaX: number, deltaY: number) => {
    if (!editable || selectedIds.length === 0) return;
    persist(moveCanvasObjects(canvasRef.current, selectedIds, deltaX, deltaY));
  }, [editable, persist, selectedIds]);

  const undo = () => {
    if (!editable || historyIndex === 0) return;
    const next = history[historyIndex - 1];
    const remaining = selectedIds.filter((id) => next.snapshot.objects.some((object) => object.id === id));
    preview(next);
    emittedKey.current = contentKey(next);
    setHistoryIndex(historyIndex - 1);
    select(remaining);
    props.onChange(next, remaining.length ? canvasSelection(remaining) : undefined);
  };

  const redo = () => {
    if (!editable || historyIndex >= history.length - 1) return;
    const next = history[historyIndex + 1];
    const remaining = selectedIds.filter((id) => next.snapshot.objects.some((object) => object.id === id));
    preview(next);
    emittedKey.current = contentKey(next);
    setHistoryIndex(historyIndex + 1);
    select(remaining);
    props.onChange(next, remaining.length ? canvasSelection(remaining) : undefined);
  };

  const onObjectPointerDown = (event: PointerEvent<HTMLDivElement>, objectId: string) => {
    if (!editable) return;
    event.preventDefault();
    event.stopPropagation();
    const nextSelection = event.shiftKey
      ? selectedIds.includes(objectId)
        ? selectedIds.filter((id) => id !== objectId)
        : [...selectedIds, objectId]
      : selectedIds.includes(objectId) ? selectedIds : [objectId];
    const normalized = select(nextSelection);
    operation.current = { kind: 'move', objectIds: normalized, clientX: event.clientX, clientY: event.clientY };
  };

  const onStagePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const active = operation.current;
    if (!active) return;
    if (active.kind === 'move') {
      const deltaX = (event.clientX - active.clientX) / zoom;
      const deltaY = (event.clientY - active.clientY) / zoom;
      if (deltaX || deltaY) {
        preview(moveCanvasObjects(canvasRef.current, active.objectIds, deltaX, deltaY));
        operation.current = { ...active, clientX: event.clientX, clientY: event.clientY };
      }
    } else if (active.kind === 'resize') {
      const nextWidth = active.width + (event.clientX - active.originX) / zoom;
      const nextHeight = active.height + (event.clientY - active.originY) / zoom;
      preview(resizeCanvasObject(canvasRef.current, active.objectId, nextWidth, nextHeight));
    } else if (active.kind === 'pan') {
      setPan({ x: active.panX + event.clientX - active.clientX, y: active.panY + event.clientY - active.clientY });
    } else {
      active.points.push({ x: (event.clientX - pan.x) / zoom, y: (event.clientY - pan.y) / zoom });
    }
  };

  const onStagePointerUp = () => {
    const active = operation.current;
    operation.current = null;
    if (!active || active.kind === 'pan') return;
    if (active.kind === 'draw') {
      const stroke = addCanvasFreeDrawStroke(canvasRef.current, active.points);
      if (stroke.objectIds.length) {
        select(stroke.objectIds);
        persist(stroke.content, stroke.objectIds);
      }
      return;
    }
    persist(canvasRef.current, active.kind === 'move' ? active.objectIds : selectedIds);
  };

  const selectedObject = selectedIds.length === 1
    ? canvas.snapshot.objects.find((object) => object.id === selectedIds[0])
    : undefined;

  return (
    <section aria-label={`Canvas editor: ${props.artifact.title}`} style={{ display: 'grid', gap: 12 }}>
      <header style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
        <strong>{props.artifact.title}</strong>
        <span role="status" aria-live="polite">{props.saveState === 'saving' ? 'Saving canvas…' : 'Canvas ready'}</span>
        {editable ? <span>{selectedIds.length ? `${selectedIds.length} selected` : 'No selection'}</span> : <span>Read-only</span>}
      </header>

      <div role="toolbar" aria-label="Canvas tools" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {SHAPES.map((shape) => (
          <button key={shape.type} type="button" disabled={!editable} onClick={() => {
            const next = addCanvasShape(canvasRef.current, shape.type);
            const id = next.snapshot.objects.at(-1)?.id;
            const nextSelection = id ? select([id]) : [];
            persist(next, nextSelection);
          }}>Add {shape.label.toLowerCase()}</button>
        ))}
        <button type="button" disabled={!editable} aria-pressed={freeDraw} onClick={() => setFreeDraw((value) => !value)}>Free draw</button>
        <button type="button" disabled={!editable || selectedIds.length === 0} onClick={() => {
          persist(deleteCanvasObjects(canvasRef.current, selectedIds), []);
          select([]);
        }}>Delete selection</button>
        <button type="button" disabled={!editable || importing || !props.onImportAsset} onClick={async () => {
          if (!props.onImportAsset) return;
          setImporting(true);
          try {
            const asset = await props.onImportAsset();
            if (!asset) return;
            const next = withImportedCanvasAsset(canvasRef.current, asset.assetId);
            const id = next.snapshot.objects.at(-1)?.id;
            const nextSelection = id ? select([id]) : [];
            persist(next, nextSelection);
          } finally {
            setImporting(false);
          }
        }}>{importing ? 'Importing local image…' : 'Import local image'}</button>
        <button type="button" disabled={!editable || historyIndex === 0} onClick={undo}>Undo</button>
        <button type="button" disabled={!editable || historyIndex >= history.length - 1} onClick={redo}>Redo</button>
        <button type="button" onClick={() => props.onRequestExport('json')}>Export JSON</button>
        <button type="button" onClick={() => props.onRequestExport('svg')}>Export SVG</button>
        <button type="button" onClick={() => props.onRequestExport('png')}>Export PNG</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(180px, 260px)', gap: 12 }}>
        <div
          aria-label="Canvas stage"
          onPointerDown={(event) => {
            if (!editable || event.target !== event.currentTarget) return;
            operation.current = freeDraw
              ? { kind: 'draw', points: [{ x: (event.clientX - pan.x) / zoom, y: (event.clientY - pan.y) / zoom }] }
              : { kind: 'pan', clientX: event.clientX, clientY: event.clientY, panX: pan.x, panY: pan.y };
          }}
          onPointerMove={onStagePointerMove}
          onPointerUp={onStagePointerUp}
          onPointerCancel={onStagePointerUp}
          onWheel={(event) => {
            if (!event.ctrlKey && !event.metaKey) return;
            event.preventDefault();
            setZoom((current) => Math.min(4, Math.max(0.25, current + (event.deltaY < 0 ? 0.1 : -0.1))));
          }}
          style={{ position: 'relative', overflow: 'hidden', minHeight: 420, border: '1px solid #94a3b8', borderRadius: 8, background: 'repeating-linear-gradient(0deg, transparent, transparent 23px, rgba(100,116,139,.12) 24px), repeating-linear-gradient(90deg, transparent, transparent 23px, rgba(100,116,139,.12) 24px)', touchAction: 'none' }}
        >
          <div style={{ position: 'absolute', inset: 0, transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: '0 0' }}>
            {canvas.snapshot.objects.map((object) => {
              const selected = selectedIds.includes(object.id);
              const isLine = object.type === 'line' || object.type === 'arrow';
              return (
                <div
                  key={object.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`${object.type} ${object.id}`}
                  aria-pressed={selected}
                  onPointerDown={(event) => onObjectPointerDown(event, object.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      select(event.shiftKey ? [...selectedIds, object.id] : [object.id]);
                    }
                    if (editable && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
                      event.preventDefault();
                      const delta = event.shiftKey ? 10 : 1;
                      moveSelected(event.key === 'ArrowLeft' ? -delta : event.key === 'ArrowRight' ? delta : 0, event.key === 'ArrowUp' ? -delta : event.key === 'ArrowDown' ? delta : 0);
                    }
                  }}
                  style={{ position: 'absolute', left: object.x, top: object.y, width: object.width, height: object.height, boxSizing: 'border-box', cursor: editable ? 'move' : 'default', borderRadius: object.type === 'ellipse' ? '50%' : object.type === 'note' ? 8 : 0, display: 'grid', placeItems: 'center', padding: 8, textAlign: 'center', userSelect: 'none', ...(isLine ? { background: 'transparent', border: 'none', borderBottom: selected ? '3px solid #4f46e5' : '2px solid #334155', transform: 'skewY(24deg)' } : { background: object.type === 'note' ? '#fef3c7' : '#fff', border: selected ? '3px solid #4f46e5' : '2px solid #334155' }) }}
                >
                  <span>{object.type === 'image' ? `Local asset: ${object.assetId}` : object.text ?? object.type}</span>
                  {editable && selected && selectedIds.length === 1 ? <button type="button" aria-label={`Resize ${object.id}`} onPointerDown={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    operation.current = { kind: 'resize', objectId: object.id, originX: event.clientX, originY: event.clientY, width: object.width, height: object.height };
                  }} style={{ position: 'absolute', right: -8, bottom: -8, width: 16, height: 16, padding: 0, border: '1px solid #312e81', background: '#c7d2fe', cursor: 'nwse-resize' }}><span className="sr-only">Resize</span></button> : null}
                </div>
              );
            })}
          </div>
          <div style={{ position: 'absolute', right: 8, bottom: 8, display: 'flex', gap: 4 }}>
            <button type="button" aria-label="Zoom out" onClick={() => setZoom((current) => Math.max(0.25, current - 0.1))}>−</button>
            <output aria-label="Canvas zoom">{Math.round(zoom * 100)}%</output>
            <button type="button" aria-label="Zoom in" onClick={() => setZoom((current) => Math.min(4, current + 0.1))}>+</button>
            <button type="button" aria-label="Reset view" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}>Reset</button>
          </div>
        </div>

        <aside style={{ display: 'grid', alignContent: 'start', gap: 12 }}>
          <nav aria-label="Canvas outline">
            <strong>Canvas outline</strong>
            <ol>
              {outline.map((item) => <li key={item.id}><button type="button" aria-label={`Select ${item.id} from outline`} aria-pressed={selectedIds.includes(item.id)} onClick={(event) => {
                select(event.shiftKey ? [...selectedIds, item.id] : [item.id]);
              }}>{item.label} <small>({item.type}; x {canvas.snapshot.objects.find((object) => object.id === item.id)?.x ?? 0}, y {canvas.snapshot.objects.find((object) => object.id === item.id)?.y ?? 0})</small></button></li>)}
            </ol>
          </nav>
          <div aria-label="Canvas inspector">
            <strong>Inspector</strong>
            {selectedObject?.text !== undefined ? <label style={{ display: 'grid', gap: 4 }}>Text
              <textarea aria-label="Canvas text" disabled={!editable} value={selectedObject.text ?? ''} maxLength={10_000} onChange={(event) => {
                const next = parseCanvasArtifactContent({ ...canvasRef.current, snapshot: { objects: canvasRef.current.snapshot.objects.map((object) => object.id === selectedObject.id ? { ...object, text: event.target.value } : object) } });
                persist(next, [selectedObject.id]);
              }} />
            </label> : <p>{selectedIds.length ? 'Select one text or note object to edit its text.' : 'Select an object.'}</p>}
          </div>
        </aside>
      </div>
    </section>
  );
}
