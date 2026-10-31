"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
  const [searchQuery, setSearchQuery] = useState("");

  // Use relative proxy on browser to eliminate Mixed Content & CORS
  const API_ENDPOINT = "/api-proxy";

  useEffect(() => {
    fetch(`${API_ENDPOINT}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data as HealthResponse))
      .catch(() => setHealth({ status: "severed", db: "unreachable" }));

    fetch(`${API_ENDPOINT}/system/status`)
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

  const isLive =
    health?.db === "connected" &&
    (health?.status === "haunted" || health?.status === "ok");

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = (targetUrl || searchQuery).trim();
    if (!url) return;

    setIngestStatus("Invoking ritual... cloning and embedding repository spirit.");
    try {
      const res = await fetch(`${API_ENDPOINT}/repos/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      const id = data.repo_id;
      setIngestRepoId(id);
      setIngestStatus(`Ritual started (Repo #${id}). Extracting commits and symbols...`);

      const interval = setInterval(async () => {
        try {
          const pollRes = await fetch(`${API_ENDPOINT}/repos/${id}/status`);
          const pollData = await pollRes.json();
          if (pollData.status === "completed") {
            clearInterval(interval);
            setIngestStatus(`Resurrection complete! Repository #${id} is bound to vector memory.`);
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
    <div className="ff-night-bg min-h-screen text-zinc-100 flex flex-col font-sans relative overflow-x-hidden selection:bg-[#9ef368] selection:text-black">
      {/* Background Ambience: Night Clouds & Victorian Haunted Mansion Silhouette */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-0 opacity-40">
        {/* Haunted House Silhouette on Right */}
        <svg
          className="absolute right-0 bottom-0 h-[650px] w-auto max-w-none text-[#020507]"
          viewBox="0 0 600 700"
          fill="currentColor"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Mansion Body & Gables */}
          <path d="M350 700 L350 480 L310 440 L310 380 L380 320 L450 380 L450 700 Z" />
          <path d="M440 700 L440 380 L490 320 L540 380 L540 700 Z" />
          <path d="M250 700 L250 520 L290 480 L320 520 L320 700 Z" />
          {/* Tall Tower & Spire */}
          <path d="M470 320 L485 180 L490 100 L495 180 L510 320 Z" />
          <path d="M490 60 L487 100 L493 100 Z" stroke="#000" strokeWidth="2" />
          {/* Lit Windows Glowing Eerie Green/Yellow */}
          <rect x="360" y="420" width="25" height="40" rx="10" fill="#a4f872" opacity="0.85" filter="drop-shadow(0 0 8px #a4f872)" />
          <rect x="405" y="420" width="25" height="40" rx="10" fill="#a4f872" opacity="0.85" filter="drop-shadow(0 0 8px #a4f872)" />
          <rect x="475" y="240" width="20" height="35" rx="8" fill="#e9ff8a" opacity="0.9" filter="drop-shadow(0 0 10px #e9ff8a)" />
          <rect x="460" y="420" width="22" height="35" rx="8" fill="#a4f872" opacity="0.6" />
          <rect x="500" y="420" width="22" height="35" rx="8" fill="#a4f872" opacity="0.6" />
          <rect x="270" y="550" width="25" height="35" rx="5" fill="#a4f872" opacity="0.75" />
          {/* Spooky Weather Vane / Bats */}
          <path d="M120 180 Q140 165 150 175 Q160 165 180 180 Q160 175 150 190 Q140 175 120 180 Z" fill="#000" opacity="0.8" />
          <path d="M220 140 Q235 125 245 135 Q255 125 270 140 Q255 135 245 150 Q235 135 220 140 Z" fill="#000" opacity="0.7" />
          <path d="M80 230 Q90 220 100 225 Q110 220 120 230 Q110 225 100 235 Q90 225 80 230 Z" fill="#000" opacity="0.6" />
          {/* Spooky Gnarled Tree Silhouette */}
          <path d="M50 700 Q70 600 65 520 Q40 470 20 440 Q45 450 65 500 Q80 430 110 390 Q95 430 80 490 Q105 530 115 700 Z" />
        </svg>
      </div>

      {/* Top Utility Bar (Like FrightFind's top bar) */}
      <div className="w-full bg-[#03090d]/90 border-b border-[#0f2127] px-6 py-2 flex items-center justify-between text-[11px] font-mono tracking-wider z-20">
        <div className="flex items-center gap-3">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              isLive
                ? "bg-[#9ef368] shadow-[0_0_8px_#9ef368]"
                : "bg-red-500 shadow-[0_0_8px_red]"
            }`}
          />
          <span className="text-zinc-400">
            TELEMETRY:{" "}
            <strong className={isLive ? "text-[#9ef368]" : "text-red-400"}>
              {isLive ? "SPIRIT LINK ACTIVE (HAUNTED)" : "REALM UNREACHABLE"}
            </strong>
          </span>
          <span className="text-zinc-600 hidden sm:inline">•</span>
          <span className="text-zinc-400 hidden sm:inline">
            INFERENCE: <strong className="text-[#5ce1e6]">{system?.inference_mode || "CPU"}</strong>
          </span>
        </div>
        <div className="flex items-center gap-4 text-zinc-400 uppercase text-[10px]">
          <a href="#summon" className="hover:text-[#9ef368] transition-colors">
            Add Your Haunt
          </a>
          <span className="text-zinc-700">|</span>
          <Link href="/ghosttrace" className="text-[#9ef368] hover:underline font-bold">
            Live Terminal
          </Link>
          <span className="text-zinc-700">|</span>
          <a
            href="https://github.com/SomSatwik/repo-seance"
            target="_blank"
            rel="noreferrer"
            className="hover:text-zinc-200"
          >
            GitHub
          </a>
        </div>
      </div>

      {/* Main Header / Brand Row */}
      <header className="max-w-6xl mx-auto w-full px-6 pt-6 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-4 z-20">
        <div>
          <Link href="/" className="inline-block group">
            <h1 className="font-creepster text-5xl sm:text-6xl tracking-wider text-[#9ef368] drop-shadow-[0_0_14px_rgba(158,243,104,0.65)] hover:scale-105 transition-transform duration-200">
              FRIGHTFIND
            </h1>
            <p className="text-[10px] font-mono text-zinc-400 tracking-[0.25em] -mt-1 uppercase">
              Repo Séance // Digital Code Necromancy
            </p>
          </Link>
        </div>

        {/* Search Bar on Right */}
        <form onSubmit={handleIngest} className="flex items-center gap-1 w-full md:w-auto">
          <input
            type="text"
            placeholder="Looking For Repo... (owner/repo or url)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-[#051318]/90 border border-[#1b3d45] rounded-l px-3 py-2 text-xs text-white placeholder-zinc-500 w-full md:w-64 outline-none focus:border-[#9ef368] font-mono shadow-inner"
          />
          <button
            type="submit"
            className="bg-[#122e35] hover:bg-[#1a414a] border border-[#23535d] text-[#9ef368] px-4 py-2 text-xs font-mono font-bold uppercase tracking-wider rounded-r transition-all shadow-md active:scale-95"
          >
            SEARCH
          </button>
        </form>
      </header>

      {/* Gothic Beveled Navigation Ribbon */}
      <nav className="max-w-6xl mx-auto w-full px-6 mb-8 z-20">
        <div className="ff-ribbon rounded px-4 py-3 flex flex-wrap items-center justify-around gap-2 text-[11px] sm:text-xs font-mono font-bold tracking-widest text-[#a8d3da] uppercase shadow-2xl">
          <Link href="/ghosttrace" className="hover:text-[#9ef368] transition-colors py-1 px-2">
            Haunted Repos
          </Link>
          <span className="text-[#1e464f] select-none">•</span>
          <a href="#active-haunt" className="hover:text-[#9ef368] transition-colors py-1 px-2">
            Real Haunts
          </a>
          <span className="text-[#1e464f] select-none">•</span>
          <a href="#dormancy" className="hover:text-[#9ef368] transition-colors py-1 px-2">
            Patches & Mazes
          </a>
          <span className="text-[#1e464f] select-none">•</span>
          <a href="#ecosystems" className="hover:text-[#9ef368] transition-colors py-1 px-2">
            Ecosystem Haunts
          </a>
          <span className="text-[#1e464f] select-none">•</span>
          <a href="#butcher" className="hover:text-[#9ef368] transition-colors py-1 px-2">
            Forensic News
          </a>
          <span className="text-[#1e464f] select-none">•</span>
          <Link
            href="/ghosttrace"
            className="text-[#9ef368] hover:text-white transition-colors bg-[#08181c]/70 px-3 py-1 rounded border border-[#23535d]"
          >
            Open Haunted Terminal ⚡
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="max-w-6xl mx-auto w-full px-6 flex-1 flex flex-col items-center z-20">
        <div className="text-center max-w-2xl mt-4 mb-8">
          <h2 className="font-medieval text-4xl sm:text-5xl font-bold ff-glow-green mb-3 leading-tight">
            Find Haunted Repositories Near You
          </h2>
          <p className="font-medieval text-sm sm:text-base text-zinc-300 leading-relaxed font-light">
            Welcome, scream-seekers. Looking for haunted repositories or real abandoned codebases
            this Halloween? We’ll help you interrogate their ghosts.
          </p>
        </div>

        {/* Featured Haunt Card (Exact match to "Bhangarh fort" card) */}
        <div id="active-haunt" className="w-full max-w-md mb-4">
          <div className="bg-[#041217]/90 border border-[#1d414a] p-3 rounded-lg shadow-[0_10px_30px_rgba(0,0,0,0.8)] backdrop-blur-md flex items-center gap-4 hover:border-[#9ef368] transition-all group">
            {/* Thumbnail */}
            <div className="h-16 w-16 rounded bg-[#091f24] border border-[#234c54] overflow-hidden flex-shrink-0 flex items-center justify-center relative">
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent z-10" />
              <span className="text-2xl select-none group-hover:scale-110 transition-transform">
                🏰
              </span>
            </div>
            {/* Info */}
            <div className="flex-1 min-w-0">
              <h3 className="font-medieval text-base sm:text-lg text-zinc-100 font-bold truncate group-hover:text-[#9ef368] transition-colors">
                Repo Séance #10 (Active Spirit)
              </h3>
              <p className="font-mono text-[11px] text-zinc-400 uppercase tracking-wider">
                SomSatwik / repo-seance
              </p>
              <div className="flex items-center gap-2 mt-1 text-[10px] font-mono text-[#5ce1e6]">
                <span>18 Commits</span>
                <span>•</span>
                <span>1 Ghost</span>
                <span>•</span>
                <span className="text-[#9ef368]">1.0D Gap</span>
              </div>
            </div>
          </div>
          <div className="text-center mt-2">
            <Link
              href="/ghosttrace"
              className="text-xs font-mono text-[#5ce1e6] hover:text-[#9ef368] hover:underline transition-colors"
            >
              Enter séance terminal for this haunt →
            </Link>
          </div>
        </div>

        {/* Live Summoner Form Bar */}
        <div id="summon" className="w-full max-w-2xl bg-[#061419]/80 border border-[#16353d] rounded-lg p-4 my-8 backdrop-blur-sm shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-xs uppercase font-bold text-[#9ef368] flex items-center gap-2">
              <span>⚰️</span> Resurrect Any GitHub Repository
            </span>
            <span className="text-[10px] font-mono text-zinc-400">
              Tree-Sitter AST • nomic-embed-text • pgvector
            </span>
          </div>
          <form onSubmit={handleIngest} className="flex gap-2">
            <input
              type="url"
              placeholder="https://github.com/owner/repository"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className="flex-1 bg-[#02090c] border border-[#1d414a] rounded px-3 py-2 text-xs font-mono text-white placeholder-zinc-600 outline-none focus:border-[#9ef368]"
            />
            <button
              type="submit"
              className="bg-[#1b434d] hover:bg-[#235865] border border-[#2c6e7e] text-white px-5 py-2 text-xs font-mono font-bold uppercase tracking-wider rounded transition-all"
            >
              Summon
            </button>
          </form>
          {ingestStatus && (
            <div className="mt-3 p-3 bg-black/80 border-l-2 border-[#9ef368] text-xs font-mono text-zinc-300 flex items-center justify-between">
              <span>{ingestStatus}</span>
              {ingestRepoId && (
                <Link
                  href={`/ghosttrace?repo=${ingestRepoId}`}
                  className="text-[#9ef368] hover:underline font-bold ml-2 whitespace-nowrap"
                >
                  ▸ Open Haunt #{ingestRepoId}
                </Link>
              )}
            </div>
          )}
        </div>

        {/* Two-Column Section (Exact Match to FrightFind Bottom Grid) */}
        <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-8 my-10">
          {/* Left: Tasty Morsels (2 cols on md) */}
          <div id="butcher" className="md:col-span-2">
            <h3 className="font-medieval text-lg sm:text-xl font-bold ff-glow-green uppercase tracking-wide mb-4">
              Tasty Morsels From The Resident Butcher
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Story Card 1 */}
              <div className="bg-[#051318]/80 border border-[#18363e] rounded-lg overflow-hidden shadow-lg hover:border-[#9ef368] transition-all flex flex-col">
                <div className="h-32 bg-[#091e24] relative flex items-center justify-center overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-t from-[#051318] to-transparent z-10" />
                  <span className="text-4xl opacity-80">🕸️</span>
                </div>
                <div className="p-4 flex-1 flex flex-col justify-between">
                  <div>
                    <h4 className="font-medieval text-base font-bold text-zinc-100 mb-1 hover:text-[#9ef368] transition-colors">
                      The Most Haunted Hotels & Repositories in America
                    </h4>
                    <p className="text-xs text-zinc-400 line-clamp-3 font-serif">
                      Explore abandoned git archives where tip commits date back over a decade, yet
                      their unresolved issues still stir in the darkness of GitHub.
                    </p>
                  </div>
                  <Link
                    href="/ghosttrace"
                    className="mt-3 inline-block font-mono text-xs text-[#5ce1e6] hover:text-[#9ef368]"
                  >
                    Read forensic report →
                  </Link>
                </div>
              </div>

              {/* Story Card 2 */}
              <div className="bg-[#051318]/80 border border-[#18363e] rounded-lg overflow-hidden shadow-lg hover:border-[#9ef368] transition-all flex flex-col">
                <div className="h-32 bg-[#091e24] relative flex items-center justify-center overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-t from-[#051318] to-transparent z-10" />
                  <span className="text-4xl opacity-80">💀</span>
                </div>
                <div className="p-4 flex-1 flex flex-col justify-between">
                  <div>
                    <h4 className="font-medieval text-base font-bold text-zinc-100 mb-1 hover:text-[#9ef368] transition-colors">
                      GhostTrace: Why AI Must Never Decide Shell Safety Alone
                    </h4>
                    <p className="text-xs text-zinc-400 line-clamp-3 font-serif">
                      A deep dive into deterministic pre-flight regex guards versus stochastic LLM
                      explanations. How Repo Séance halts destructive commands before they strike.
                    </p>
                  </div>
                  <Link
                    href="/ghosttrace"
                    className="mt-3 inline-block font-mono text-xs text-[#5ce1e6] hover:text-[#9ef368]"
                  >
                    Explore safety engine →
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Haunts by State / Ecosystem (1 col on md) */}
          <div id="ecosystems">
            <h3 className="font-medieval text-lg sm:text-xl font-bold ff-glow-green uppercase tracking-wide mb-4">
              Haunts By Ecosystem
            </h3>
            <div className="bg-[#051318]/90 border border-[#18363e] rounded-lg p-3 font-mono text-xs shadow-xl divide-y divide-[#0f252b]">
              {[
                { name: "Python Repos", count: 21 },
                { name: "TypeScript Haunts", count: 36 },
                { name: "JavaScript Ghosts", count: 18 },
                { name: "Rust Dormancies", count: 14 },
                { name: "C & C++ Ruins", count: 24 },
                { name: "Docker Phantoms", count: 16 },
                { name: "PostgreSQL & pgvector", count: 10 },
                { name: "Go Sanctuaries", count: 9 },
              ].map((item) => (
                <div
                  key={item.name}
                  className="py-2 px-3 flex items-center justify-between text-zinc-300 hover:bg-[#0c242c] hover:text-[#9ef368] transition-colors cursor-pointer rounded"
                >
                  <span>{item.name}</span>
                  <span className="text-[#5ce1e6] font-bold">({item.count})</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#11262d] bg-[#02070a] py-6 px-6 text-center text-xs font-mono text-zinc-500 z-20">
        <p className="mb-1 text-zinc-400">
          Repo Séance • FrightFind Edition for Hacktoberfest & Spooky Week
        </p>
        <p className="text-[10px] text-zinc-600">
          Powered by FastAPI, PostgreSQL (pgvector), Ollama (Gemma 2:2B), and Next.js 15.
        </p>
      </footer>
    </div>
  );
}
