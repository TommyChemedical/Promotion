"use client";

import { useState } from "react";

export default function CollapsibleSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <section>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span className="text-base leading-none">{open ? "▾" : "▸"}</span>
        {title}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </section>
  );
}
