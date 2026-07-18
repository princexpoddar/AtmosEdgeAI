export default function Button({
  variant = "secondary",
  size = "md",
  disabled = false,
  onClick,
  children,
  type = "button",
  className = "",
}) {
  return (
    <button
      type={type}
      className={`btn btn-${variant} btn-${size} ${className}`.trim()}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
