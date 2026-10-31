"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Terminal from "@/app/ghosttrace/components/terminal";

function GhostTraceContent() {
  const searchParams = useSearchParams();
  const repoParam = searchParams.get("repo") || searchParams.get("repo_id");
  const repoId = repoParam ? parseInt(repoParam, 10) : 10;
  return <Terminal repoId={isNaN(repoId) ? 10 : repoId} />;
}

export default function GhostTracePage() {
  return (
    <Suspense fallback={<div className="p-6 font-mono text-xs text-zinc-500">Loading terminal...</div>}>
      <GhostTraceContent />
    </Suspense>
  );
}
