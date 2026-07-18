export default function Skeleton({ width = "100%", height = "16px", className = "" }) {
  return (
    <div
      className={`skeleton ${className}`.trim()}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}
