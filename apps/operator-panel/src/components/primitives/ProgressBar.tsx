export function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      aria-label={`%${Math.round(clamped)}`}
      aria-valuemax={100}
      aria-valuemin={0}
      aria-valuenow={Math.round(clamped)}
      className="mc-progress"
      role="progressbar"
    >
      <span style={{ width: `${clamped}%` }} />
    </div>
  );
}
