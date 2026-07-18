export default function Spinner({ size = "md" }) {
  return (
    <div className={`spinner spinner-${size}`} role="status" aria-label="Loading" />
  );
}
