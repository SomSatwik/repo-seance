"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type HealthResponse = {
  status: string;
  db: string;
  detail?: string;
};

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data as HealthResponse))
      .catch(() => setHealth({ status: "error", db: "unreachable" }));
  }, []);

  return (
    <main className="flex min-h-full flex-col items-center justify-center gap-6 p-8 text-center">
      <pre className="font-mono text-sm leading-tight">
        {`  .-.\n ( o o )\n  | O |`}
      </pre>
      <h1 className="text-3xl font-semibold tracking-tight">
        Repo Séance
      </h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Live API health — fetched from{" "}
        <code className="font-mono">{API_URL}/health</code>
      </p>
      <pre className="w-full max-w-xl rounded-lg bg-zinc-100 p-4 text-left font-mono text-sm dark:bg-zinc-900">
        {JSON.stringify(health ?? { status: "loading…" }, null, 2)}
      </pre>
      <div className="mt-8 flex flex-col gap-2">
        <Link
          href="/ghosttrace"
          className="inline-block px-6 py-3 font-mono text-sm border border-zinc-300 bg-zinc-50 text-zinc-900 hover:bg-zinc-100 dark:bg-zinc-900 dark:text-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800 transition rounded"
        >
          ▸ Open GhostTrace terminal
        </Link>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Horror-styled terminal companion — tone shifts, not a different site.
        </p>
      </div>
    </main>
  );
}
