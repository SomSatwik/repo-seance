"use strict";

/* CRT scanline + vignette overlay. Subtle — never distracting. */
export default function CrtOverlay() {
  return (
    <>
      <div className="gt-scanlines pointer-events-none z-10 inset-0" />
      <div
        className="pointer-events-none z-20 inset-0"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, transparent 0%, rgba(0,0,0,0.45) 90%)",
        }}
      />
    </>
  );
}
