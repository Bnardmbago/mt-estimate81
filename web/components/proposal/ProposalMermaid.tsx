"use client";

import { useEffect, useRef } from "react";
import mermaid from "mermaid";

type ProposalMermaidProps = {
  id: string;
  source: string;
  title?: string;
};

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "loose",
  theme: "neutral",
});

export default function ProposalMermaid({ id, source, title }: ProposalMermaidProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function renderDiagram() {
      if (!containerRef.current || !source.trim()) {
        return;
      }
      try {
        const { svg } = await mermaid.render(`mermaid-${id}`, source);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch {
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = `<pre class="text-xs text-slate-500 whitespace-pre-wrap">${source}</pre>`;
        }
      }
    }
    void renderDiagram();
    return () => {
      cancelled = true;
    };
  }, [id, source]);

  return (
    <figure className="my-4 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40">
      {title ? (
        <figcaption className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-200">
          {title}
        </figcaption>
      ) : null}
      <div ref={containerRef} className="overflow-x-auto" />
    </figure>
  );
}
