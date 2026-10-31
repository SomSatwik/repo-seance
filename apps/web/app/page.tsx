"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import CrtOverlay from "./ghosttrace/components/crt-overlay";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const SPOOKY_GHOST_ASCII = `       .-.
      ( o o )
      |  O  |
       \\   /
        \`-\`
   🕯️  💀  🕯️`;

type HealthResponse = {
  status: string;
  db: string;
  presence?: string;
};

type SystemStatus = {
  ollama_reachable: boolean;
  model: string;
  inference_mode: string;
};

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [targetUrl, setTargetUrl] = useState("");
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [ingestRepoId, setIngestRepoId] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data as HealthResponse))
      .catch(() => setHealth({ status: "severed", db: "unreachable" }));

    fetch(`${API_URL}/system/status`)
      .then((res) => res.json())
      .then((data) => setSystem(data as SystemStatus))
      .catch(() =>
        setSystem({
          ollama_reachable: false,
          model: "gemma2:2b",
          inference_mode: "offline",
        })
      );
  }, []);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUrl.trim()) return;

    setIngestStatus("Summoning repository spirit...");
    try {
      const res = await fetch(`${API_URL}/repos/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: targetUrl.trim() }),
      });
      const data = await res.json();
      const id = data.repo_id;
      setIngestRepoId(id);
      setIngestStatus(`Ingestion started (Repo #${id}). Polling spirit status...`);

      // Poll status
      const interval = setInterval(async () => {
        try {
          const pollRes = await fetch(`${API_URL}/repos/${id}/status`);
          const pollData = await pollRes.json();
          if (pollData.status === "completed") {
            clearInterval(interval);
            setIngestStatus(`Resurrection complete! Repository #${id} is bound to memory.`);
          } else if (pollData.status === "failed") {
            clearInterval(interval);
            setIngestStatus(`Ritual failed: ${pollData.error || "Unknown error"}`);
          } else {
            setIngestStatus(`Digesting history & embedding vectors: ${pollData.status}...`);
          }
        } catch {
          clearInterval(interval);
        }
      }, 3000);
    } catch (err) {
      setIngestStatus(`Error invoking ritual: ${err}`);
    }
  };

  return (
    <div className="gt-app gt-scanlines relative flex min-h-screen flex-col font-mono text-zinc-100 selection:bg-[var(--gt-blood)] selection:text-white">
      <CrtOverlay />

      {/* Occult Top Bar */}
      <header className="border-b border-[#1f1f1f] bg-[#070707]/90 px-6 py-3 flex items-center justify-between backdrop-blur-sm z-20">
        <div className="flex items-center gap-3">
          <span className="text-[var(--gt-blood)] text-lg animate-pulse">⚰️</span>
          <div>
            <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-100">
              REPO SÉANCE <span className="text-[var(--gt-blood)]">//</span> OCCULT CODE FORENSICS
            </h1>
            <p className="text-[10px] text-zinc-500">
              Vectorized Necromancy for Abandoned Git Codebases
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              health?.db === "connected"
                ? "bg-[var(--gt-safe)] shadow-[0_0_8px_var(--gt-safe)]"
                : "bg-[var(--gt-blood)] shadow-[0_0_8px_var(--gt-blood)]"
            }`}
          />
          <span className="text-[10px] uppercase tracking-wider text-zinc-400">
            {health?.status === "haunted" ? "SPIRIT LINK ACTIVE" : "REALM UNREACHABLE"}
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 max-w-4xl mx-auto w-full z-20 gap-8">
        {/* Hero Section */}
        <div className="text-center flex flex-col items-center gap-4">
          <pre className="text-xs leading-none text-[var(--gt-blood)] select-none font-mono drop-shadow-[0_0_12px_rgba(181,18,27,0.4)]">
            {SPOOKY_GHOST_ASCII}
          </pre>
          <h2 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]">
            Summon The Past<span className="text-[var(--gt-blood)]">.</span>
          </h2>
          <p className="max-w-xl text-xs sm:text-sm text-zinc-400 leading-relaxed">
            Every repository carries ghosts—dormant commits, forgotten decisions, and abandoned logic.
            Repo Séance resurrects repository souls into a vector-backed semantic memory and answers
            your questions with strict citations.
          </p>
          <div className="flex flex-wrap gap-3 justify-center mt-2">
            <Link
              href="/ghosttrace"
              className="inline-flex items-center gap-2 px-6 py-3 text-xs uppercase tracking-wider font-bold border border-[var(--gt-blood)] bg-[var(--gt-blood)]/15 text-white hover:bg-[var(--gt-blood)] hover:text-white transition-all shadow-[0_0_15px_rgba(181,18,27,0.3)] rounded"
            >
              <span>▸</span> Enter Séance Terminal
            </Link>
            <a
              href={`${API_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-5 py-3 text-xs uppercase tracking-wider font-medium border border-zinc-800 bg-zinc-950/80 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700 transition-all rounded"
            >
              📜 API Grimoire
            </a>
          </div>
        </div>

        {/* Telemetry HUD Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 w-full">
          {/* Card 1 */}
          <div className="border border-zinc-800 bg-[#0a0a0a]/80 p-4 rounded flex flex-col justify-between">
            <div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">
                Vector Vault
              </div>
              <div className="text-sm font-bold text-zinc-200">Postgres + pgvector</div>
            </div>
            <div className="mt-3 flex items-center justify-between text-[10px]">
              <span className="text-zinc-400">Port 5434</span>
              <span className={health?.db === "connected" ? "text-[var(--gt-safe)]" : "text-[var(--gt-blood)]"}>
                {health?.db === "connected" ? "Connected" : "Severed"}
              </span>
            </div>
          </div>

          {/* Card 2 */}
          <div className="border border-zinc-800 bg-[#0a0a0a]/80 p-4 rounded flex flex-col justify-between">
            <div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">
                Occult Medium
              </div>
              <div className="text-sm font-bold text-zinc-200">Gemma 2:2B (Ollama)</div>
            </div>
            <div className="mt-3 flex items-center justify-between text-[10px]">
              <span className="text-zinc-400">nomic-embed-text</span>
              <span className="text-[#00c8ff]">
                {system?.inference_mode || "CPU Mode"}
              </span>
            </div>
          </div>

          {/* Card 3 */}
          <div className="border border-zinc-800 bg-[#0a0a0a]/80 p-4 rounded flex flex-col justify-between">
            <div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">
                Active Séance
              </div>
              <div className="text-sm font-bold text-zinc-200">Repo #10 (Verified)</div>
            </div>
            <div className="mt-3 flex items-center justify-between text-[10px]">
              <span className="text-zinc-400">repo-seance</span>
              <span className="text-[var(--gt-safe)]">18 Commits</span>
            </div>
          </div>

          {/* Card 4 */}
          <div className="border border-zinc-800 bg-[#0a0a0a]/80 p-4 rounded flex flex-col justify-between">
            <div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">
                Shell Guardian
              </div>
              <div className="text-sm font-bold text-zinc-200">GhostTrace Engine</div>
            </div>
            <div className="mt-3 flex items-center justify-between text-[10px]">
              <span className="text-zinc-400">Deterministic</span>
              <span className="text-[var(--gt-caution)]">Active</span>
            </div>
          </div>
        </div>

        {/* Resurrect Repository Card */}
        <div className="w-full border border-zinc-800 bg-[#080808]/90 p-5 rounded-lg shadow-xl">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[var(--gt-blood)] text-xs">⚡</span>
            <h3 className="text-xs uppercase tracking-widest font-bold text-zinc-200">
              Resurrect a Public Git Repository
            </h3>
          </div>
          <p className="text-[11px] text-zinc-500 mb-4">
            Input any public GitHub repository to clone its history, extract AST symbols, and embed its soul into local vector memory.
          </p>

          <form onSubmit={handleIngest} className="flex flex-col sm:flex-row gap-2">
            <input
              type="url"
              placeholder="https://github.com/owner/repository"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className="flex-1 bg-black/60 border border-zinc-800 rounded px-3 py-2 text-xs text-white placeholder-zinc-600 outline-none focus:border-[var(--gt-blood)] transition-colors"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-xs text-zinc-200 font-bold uppercase tracking-wider rounded transition-all whitespace-nowrap"
            >
              Invoke Ritual
            </button>
          </form>

          {ingestStatus && (
            <div className="mt-3 p-3 bg-black/80 border-l-2 border-[var(--gt-blood)] text-xs text-zinc-300 flex items-center justify-between">
              <span>{ingestStatus}</span>
              {ingestRepoId && (
                <Link
                  href={`/ghosttrace?repo=${ingestRepoId}`}
                  className="text-[10px] text-[var(--gt-blood)] hover:underline ml-4 whitespace-nowrap"
                >
                  ▸ Open Séance for #{ingestRepoId}
                </Link>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Occult Footer */}
      <footer className="border-t border-[#1a1a1a] bg-[#070707] py-3 px-6 text-center text-[10px] text-zinc-600 z-20 flex flex-col sm:flex-row justify-between items-center gap-2">
        <span>Repo Séance • Spooky Week & Hacktoberfest</span>
        <span className="text-zinc-500">
          Powered by FastAPI, pgvector, Ollama (Gemma 2), and Next.js
        </span>
      </footer>
    </div>
  );
}
