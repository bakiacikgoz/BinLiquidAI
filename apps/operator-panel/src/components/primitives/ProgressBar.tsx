export function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="mc-progress" aria-label={`%${Math.round(clamped)}`}>
      <span style={{ width: `${clamped}%` }} />
    </div>
  );
}
