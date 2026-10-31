"use client";

/* CRT scanline + vignette overlay. Full viewport fixed layer with toggleable state. */
export default function CrtOverlay() {
  return (
    <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden select-none">
      <div className="gt-scanlines absolute inset-0 opacity-75" />
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, transparent 45%, rgba(0,0,0,0.55) 95%)",
          boxShadow: "inset 0 0 120px rgba(0,0,0,0.85)",
        }}
      />
    </div>
  );
}
