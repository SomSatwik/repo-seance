"use strict";

/* Ghost-themed notification banner. Distinct from a generic chat bubble. */
interface NotificationProps {
  level: "safe" | "caution" | "destructive";
  message: string;
  onClose: () => void;
}

const LEVEL_STYLE: Record<string, string> = {
  safe: "border-left-[var(--gt-safe)] text-[var(--gt-safe)]",
  caution: "border-left-[var(--gt-caution)] text-[var(--gt-caution)]",
  destructive: "border-left-[var(--gt-blood)] text-[var(--gt-blood)]",
};

export default function Notification({
  level,
  message,
  onClose,
}: NotificationProps) {
  const styleClass = LEVEL_STYLE[level] ?? LEVEL_STYLE.safe;
  const label = level === "destructive" ? "⚠ DESTRUCTIVE" : level === "caution" ? "⚠ CAUTION" : "✓ SAFE";

  return (
    <div className={`gt-notif ${styleClass}`}>
      <span className="font-bold text-xs uppercase tracking-wider">{label}</span>
      <span className="ml-2 text-xs">{message}</span>
      <span
        className="gt-notif-close"
        onClick={onClose}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && onClose()}
      >
        ✕
      </span>
    </div>
  );
}
