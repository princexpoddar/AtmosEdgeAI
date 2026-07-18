export default function Banner({ variant = "error", children }) {
  return (
    <div className={`banner banner-${variant}`} role="alert">
      {children}
    </div>
  );
}
