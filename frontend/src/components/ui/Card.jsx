export default function Card({ children, className = "" }) {
  return (
    <div className={`card ${className}`.trim()}>
      {children}
    </div>
  );
}
