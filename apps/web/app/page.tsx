const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type HealthResponse = {
  status: string;
  db: string;
  detail?: string;
};

async function getHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${API_URL}/health`);
    return (await res.json()) as HealthResponse;
  } catch (err) {
    return {
      status: "error",
      db: "unreachable",
      detail: err instanceof Error ? err.message : String(err),
    };
  }
}

export default async function Home() {
  const health = await getHealth();

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
        {JSON.stringify(health, null, 2)}
      </pre>
    </main>
  );
}
