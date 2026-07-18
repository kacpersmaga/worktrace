"use client";

import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-js.css";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

/** Renders the exported BPMN with bpmn-js; the layout is computed in the browser by bpmn-auto-layout. */
export function BpmnView({ analysisId }: { analysisId: string }) {
  const container = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let viewer: { destroy: () => void } | null = null;
    let cancelled = false;

    async function render() {
      try {
        const [{ default: NavigatedViewer }, { layoutProcess }, xml] = await Promise.all([
          import("bpmn-js/lib/NavigatedViewer"),
          import("bpmn-auto-layout"),
          fetch(api.bpmnUrl(analysisId)).then((response) => response.text()),
        ]);
        if (cancelled || !container.current) return;
        const laidOut = await layoutProcess(xml);
        const instance = new NavigatedViewer({ container: container.current });
        viewer = instance;
        await instance.importXML(laidOut);
        (instance.get("canvas") as { zoom: (mode: string) => void }).zoom("fit-viewport");
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Could not render the BPMN model.");
      }
    }
    render();
    return () => {
      cancelled = true;
      viewer?.destroy();
    };
  }, [analysisId]);

  if (error) return <p className="p-6 text-[13px] text-ink-2">{error}</p>;
  return <div ref={container} className="bpmn-canvas h-full w-full rounded-b-[14px] bg-white" />;
}
