"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import CrtOverlay from "./ghosttrace/components/crt-overlay";

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

type RepoHistory = {
  repo_id: number;
  log: Array<{ hash: string; short_hash: string; author: string; date: string; message: string }>;
  contributors: Array<{ author: string; commit_count: number }>;
  gap?: { days: number; message: string };
};

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [history, setHistory] = useState<RepoHistory | null>(null);
  const [targetUrl, setTargetUrl] = useState("");
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [ingestRepoId, setIngestRepoId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [crtEnabled, setCrtEnabled] = useState(true);
  const [activeTab, setActiveTab] = useState<"all" | "haunted" | "mazes" | "real">("all");

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

    // Fetch verified live repo #10 history
    fetch(`${API_ENDPOINT}/repos/10/history`)
      .then((res) => res.json())
      .then((data) => setHistory(data as RepoHistory))
      .catch(() => setHistory(null));
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
    <div className={`ff-night-bg min-h-screen text-zinc-100 flex flex-col font-sans relative overflow-x-hidden selection:bg-[#9ef368] selection:text-black ${crtEnabled ? "gt-scanlines" : ""}`}>
      {/* Global Toggleable CRT Overlay */}
      {crtEnabled && <CrtOverlay />}

      {/* Background Ambience: Night Fog & Victorian Haunted Mansion Silhouette */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-0 opacity-40">
        <svg
          className="absolute right-0 bottom-0 h-[650px] w-auto max-w-none text-[#020507]"
          viewBox="0 0 600 700"
          fill="currentColor"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M350 700 L350 480 L310 440 L310 380 L380 320 L450 380 L450 700 Z" />
          <path d="M440 700 L440 380 L490 320 L540 380 L540 700 Z" />
          <path d="M250 700 L250 520 L290 480 L320 520 L320 700 Z" />
          <path d="M470 320 L485 180 L490 100 L495 180 L510 320 Z" />
          <path d="M490 60 L487 100 L493 100 Z" stroke="#000" strokeWidth="2" />
          <rect x="360" y="420" width="25" height="40" rx="10" fill="#a4f872" opacity="0.85" filter="drop-shadow(0 0 8px #a4f872)" />
          <rect x="405" y="420" width="25" height="40" rx="10" fill="#a4f872" opacity="0.85" filter="drop-shadow(0 0 8px #a4f872)" />
          <rect x="475" y="240" width="20" height="35" rx="8" fill="#e9ff8a" opacity="0.9" filter="drop-shadow(0 0 10px #e9ff8a)" />
          <rect x="460" y="420" width="22" height="35" rx="8" fill="#a4f872" opacity="0.6" />
          <rect x="500" y="420" width="22" height="35" rx="8" fill="#a4f872" opacity="0.6" />
          <rect x="270" y="550" width="25" height="35" rx="5" fill="#a4f872" opacity="0.75" />
          {/* Bats */}
          <path d="M120 180 Q140 165 150 175 Q160 165 180 180 Q160 175 150 190 Q140 175 120 180 Z" fill="#000" opacity="0.8" />
          <path d="M220 140 Q235 125 245 135 Q255 125 270 140 Q255 135 245 150 Q235 135 220 140 Z" fill="#000" opacity="0.7" />
          <path d="M80 230 Q90 220 100 225 Q110 220 120 230 Q110 225 100 235 Q90 225 80 230 Z" fill="#000" opacity="0.6" />
          <path d="M50 700 Q70 600 65 520 Q40 470 20 440 Q45 450 65 500 Q80 430 110 390 Q95 430 80 490 Q105 530 115 700 Z" />
        </svg>
      </div>

      {/* Top Utility Bar with CRT Toggle Button */}
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
          {/* CRT Monitor Switch */}
          <button
            onClick={() => setCrtEnabled(!crtEnabled)}
            className="flex items-center gap-1 px-2.5 py-0.5 rounded border border-[#26535c] bg-[#0c2228] text-[#9ef368] hover:bg-[#133742] transition-colors"
            title="Toggle retro CRT scanlines and screen flicker"
          >
            <span>📺</span> CRT VISUAL: <strong className="underline">{crtEnabled ? "ON" : "OFF"}</strong>
          </button>
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

      {/* Gothic Beveled Navigation Ribbon with Interactive Filters */}
      <nav className="max-w-6xl mx-auto w-full px-6 mb-8 z-20">
        <div className="ff-ribbon rounded px-4 py-3 flex flex-wrap items-center justify-around gap-2 text-[11px] sm:text-xs font-mono font-bold tracking-widest text-[#a8d3da] uppercase shadow-2xl">
          <button
            onClick={() => setActiveTab("haunted")}
            className={`py-1 px-2 transition-colors rounded ${activeTab === "haunted" ? "text-[#9ef368] bg-[#0c262e] border border-[#22505c]" : "hover:text-[#9ef368]"}`}
          >
            Haunted Repos
          </button>
          <span className="text-[#1e464f] select-none">•</span>
          <button
            onClick={() => setActiveTab("real")}
            className={`py-1 px-2 transition-colors rounded ${activeTab === "real" ? "text-[#9ef368] bg-[#0c262e] border border-[#22505c]" : "hover:text-[#9ef368]"}`}
          >
            Real Haunts
          </button>
          <span className="text-[#1e464f] select-none">•</span>
          <button
            onClick={() => setActiveTab("mazes")}
            className={`py-1 px-2 transition-colors rounded ${activeTab === "mazes" ? "text-[#9ef368] bg-[#0c262e] border border-[#22505c]" : "hover:text-[#9ef368]"}`}
          >
            Patches & Mazes
          </button>
          <span className="text-[#1e464f] select-none">•</span>
          <button
            onClick={() => setActiveTab("all")}
            className={`py-1 px-2 transition-colors rounded ${activeTab === "all" ? "text-[#9ef368] bg-[#0c262e] border border-[#22505c]" : "hover:text-[#9ef368]"}`}
          >
            All Haunts
          </button>
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
        <div className="text-center max-w-2xl mt-2 mb-6">
          <h2 className="font-medieval text-4xl sm:text-5xl font-bold ff-glow-green mb-3 leading-tight">
            Find Haunted Repositories Near You
          </h2>
          <p className="font-medieval text-sm sm:text-base text-zinc-300 leading-relaxed font-light">
            Welcome, scream-seekers. Looking for haunted repositories or real abandoned codebases
            this Halloween? We’ll help you interrogate their ghosts.
          </p>
        </div>

        {/* Featured Haunt Card (Exact match to "Bhangarh fort" card) */}
        <div id="active-haunt" className="w-full max-w-md mb-6">
          <div className="bg-[#041217]/90 border border-[#1d414a] p-3 rounded-lg shadow-[0_10px_30px_rgba(0,0,0,0.8)] backdrop-blur-md flex items-center gap-4 hover:border-[#9ef368] transition-all group">
            <div className="h-16 w-16 rounded bg-[#091f24] border border-[#234c54] overflow-hidden flex-shrink-0 flex items-center justify-center relative">
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent z-10" />
              <span className="text-2xl select-none group-hover:scale-110 transition-transform">
                🏰
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medieval text-base sm:text-lg text-zinc-100 font-bold truncate group-hover:text-[#9ef368] transition-colors">
                Bhangarh Fort (Repo Séance #10)
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
              More haunts near me →
            </Link>
          </div>
        </div>

        {/* SECTION 1: HAUNTED REPOS DIRECTORY (Cursed Codebases) */}
        {(activeTab === "all" || activeTab === "haunted") && (
          <div className="w-full my-6">
            <div className="flex items-center justify-between mb-4 border-b border-[#1b3d45] pb-2">
              <h3 className="font-medieval text-xl font-bold ff-glow-green uppercase tracking-wide flex items-center gap-2">
                <span>🕯️</span> Haunted Repositories Directory
              </h3>
              <span className="font-mono text-xs text-[#5ce1e6]">4 Cursed Artifacts Cataloged</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Cursed Repo 1 */}
              <div className="bg-[#051318]/85 border border-[#18363e] rounded-lg p-4 hover:border-[#9ef368] transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medieval text-lg font-bold text-zinc-100">
                      The Phantom of Left-Pad
                    </h4>
                    <span className="font-mono text-[10px] bg-red-950/80 text-red-400 border border-red-800 px-2 py-0.5 rounded">
                      SPECTRAL DELETION
                    </span>
                  </div>
                  <p className="font-mono text-xs text-zinc-400 mb-2">npm/left-pad • Unpublished 2016</p>
                  <p className="text-xs text-zinc-300 font-serif leading-relaxed">
                    Removed by its author in 2016. In minutes, thousands of builds worldwide broke into shrieking error codes.
                    Its eleven lines of string padding vanished, leaving a hollow vacuum that still echoes across node_modules.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-[#132c33] flex items-center justify-between">
                  <span className="font-mono text-[10px] text-zinc-500">Dormancy: 8.5 Years</span>
                  <Link href="/ghosttrace" className="font-mono text-xs text-[#9ef368] hover:underline">
                    Interrogate Ghost →
                  </Link>
                </div>
              </div>

              {/* Cursed Repo 2 */}
              <div className="bg-[#051318]/85 border border-[#18363e] rounded-lg p-4 hover:border-[#9ef368] transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medieval text-lg font-bold text-zinc-100">
                      The Cursed Monorepo Graveyard
                    </h4>
                    <span className="font-mono text-[10px] bg-yellow-950/80 text-yellow-400 border border-yellow-800 px-2 py-0.5 rounded">
                      3,000+ UNRESOLVED ISSUES
                    </span>
                  </div>
                  <p className="font-mono text-xs text-zinc-400 mb-2">github/enterprise-decay • Dormant 2021</p>
                  <p className="text-xs text-zinc-300 font-serif leading-relaxed">
                    A labyrinthine monorepo where PRs wait for reviews that will never come. The original architects
                    have departed; automated CI bots relentlessly re-run tests on dead branches, trapped in an infinite loop.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-[#132c33] flex items-center justify-between">
                  <span className="font-mono text-[10px] text-zinc-500">Merge Conflict: Critical</span>
                  <Link href="/ghosttrace" className="font-mono text-xs text-[#9ef368] hover:underline">
                    Interrogate Ghost →
                  </Link>
                </div>
              </div>

              {/* Cursed Repo 3 */}
              <div className="bg-[#051318]/85 border border-[#18363e] rounded-lg p-4 hover:border-[#9ef368] transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medieval text-lg font-bold text-zinc-100">
                      The Undead Zero-Day (Log4Shell)
                    </h4>
                    <span className="font-mono text-[10px] bg-red-950/80 text-red-400 border border-red-800 px-2 py-0.5 rounded">
                      CVE-2021-44228
                    </span>
                  </div>
                  <p className="font-mono text-xs text-zinc-400 mb-2">apache/logging-log4j2 • Risen 2021</p>
                  <p className="text-xs text-zinc-300 font-serif leading-relaxed">
                    A dormant JNDI lookup vulnerability slumbered undisturbed for eight years in commit archives.
                    When awakened, servers across the globe trembled as payloads summoned arbitrary code from the void.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-[#132c33] flex items-center justify-between">
                  <span className="font-mono text-[10px] text-zinc-500">Exploit Level: Critical</span>
                  <Link href="/ghosttrace" className="font-mono text-xs text-[#9ef368] hover:underline">
                    Interrogate Ghost →
                  </Link>
                </div>
              </div>

              {/* Cursed Repo 4 */}
              <div className="bg-[#051318]/85 border border-[#18363e] rounded-lg p-4 hover:border-[#9ef368] transition-all flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medieval text-lg font-bold text-zinc-100">
                      Repo Séance Necromancer
                    </h4>
                    <span className="font-mono text-[10px] bg-[#9ef368]/20 text-[#9ef368] border border-[#9ef368]/40 px-2 py-0.5 rounded">
                      ACTIVE RESURRECTION
                    </span>
                  </div>
                  <p className="font-mono text-xs text-zinc-400 mb-2">SomSatwik/repo-seance • Verified Live</p>
                  <p className="text-xs text-zinc-300 font-serif leading-relaxed">
                    The tool built to summon the spirits of all other repositories. Ingests full git histories,
                    extracts AST symbols with tree-sitter, and equips developers with deterministic GhostTrace wards.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-[#132c33] flex items-center justify-between">
                  <span className="font-mono text-[10px] text-zinc-500">Status: Bound to Vector Memory</span>
                  <Link href="/ghosttrace" className="font-mono text-xs text-[#9ef368] hover:underline font-bold">
                    Open CRT Séance →
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SECTION 2: PATCHES & MAZES (Git Branch Catacombs) */}
        {(activeTab === "all" || activeTab === "mazes") && (
          <div id="dormancy" className="w-full my-6 bg-[#040e13]/90 border border-[#173740] rounded-lg p-5 shadow-2xl backdrop-blur-md">
            <div className="flex items-center justify-between mb-3 border-b border-[#16353d] pb-2">
              <h3 className="font-medieval text-xl font-bold ff-glow-green uppercase tracking-wide flex items-center gap-2">
                <span>🕸️</span> Patches & Mazes: The Git Catacombs
              </h3>
              <span className="font-mono text-xs text-[#5ce1e6]">Git Branch Labyrinth</span>
            </div>
            <p className="text-xs text-zinc-400 font-serif mb-4">
              Navigate the treacherous labyrinth of branches where commits become detached, merges conflict in the shadows,
              and rebase operations risk erasing entire developer lineages.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
              <div className="bg-[#06151a] border border-[#1c3e47] p-3 rounded">
                <div className="text-[10px] text-red-400 font-bold mb-1">MAZE TRAP #1</div>
                <div className="text-sm font-bold text-white mb-1">Detached HEAD Void</div>
                <p className="text-[11px] text-zinc-400">
                  You checked out commit <code className="text-[#9ef368]">4c8e5ebe</code> without a branch. Commits made here exist only in the reflog before the garbage collector takes them.
                </p>
              </div>

              <div className="bg-[#06151a] border border-[#1c3e47] p-3 rounded">
                <div className="text-[10px] text-yellow-400 font-bold mb-1">MAZE TRAP #2</div>
                <div className="text-sm font-bold text-white mb-1">Merge Conflict Crypt</div>
                <p className="text-[11px] text-zinc-400">
                  Two developer phantoms edited line 42 simultaneously. Both changes look plausible; choosing one sacrifices the other’s memory.
                </p>
              </div>

              <div className="bg-[#06151a] border border-[#1c3e47] p-3 rounded">
                <div className="text-[10px] text-[#5ce1e6] font-bold mb-1">MAZE TRAP #3</div>
                <div className="text-sm font-bold text-white mb-1">The Stale Reflog Maze</div>
                <p className="text-[11px] text-zinc-400">
                  A rebase from hell rewrote commit hashes. Ancient SHA-1 references in bug trackers now point to forgotten ghosts in the graveyard.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* SECTION 3: REAL HAUNTS (Live Forensic Evidence from Repo #10) */}
        {(activeTab === "all" || activeTab === "real") && (
          <div className="w-full my-6 bg-[#040e13]/90 border border-[#173740] rounded-lg p-5 shadow-2xl backdrop-blur-md">
            <div className="flex items-center justify-between mb-3 border-b border-[#16353d] pb-2">
              <h3 className="font-medieval text-xl font-bold ff-glow-green uppercase tracking-wide flex items-center gap-2">
                <span>🏰</span> Real Haunts: Live Git Forensics (#10)
              </h3>
              <span className="font-mono text-xs text-[#9ef368]">
                {history ? `${history.contributors[0]?.commit_count || 18} Commits Indexed` : "Fetching Spectral Telemetry..."}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Commit Log */}
              <div className="bg-[#06151a] border border-[#1c3e47] p-3 rounded font-mono text-xs">
                <div className="text-[11px] font-bold text-[#5ce1e6] uppercase tracking-wider mb-2">
                  Dormant Commits Whispering in Memory:
                </div>
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-2">
                  {history?.log ? (
                    history.log.slice(0, 6).map((c) => (
                      <div key={c.hash} className="text-[11px] text-zinc-300 flex items-start gap-2">
                        <span className="text-[#9ef368]">{c.short_hash}</span>
                        <span className="truncate">{c.message.split("\n")[0]}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-zinc-500">Reading commit graves...</div>
                  )}
                </div>
              </div>

              {/* Activity Gap & Ghost */}
              <div className="bg-[#06151a] border border-[#1c3e47] p-3 rounded font-mono text-xs flex flex-col justify-between">
                <div>
                  <div className="text-[11px] font-bold text-[#5ce1e6] uppercase tracking-wider mb-2">
                    Dormancy & Ghost Identity:
                  </div>
                  <p className="text-zinc-300 text-xs mb-2">
                    {history?.gap?.message || "Development gap of 1.0 days detected (2026-10-30 -> 2026-10-31)."}
                  </p>
                  <p className="text-zinc-400 text-[11px]">
                    Creator Spirit: <strong className="text-[#9ef368]">{history?.contributors[0]?.author || "ssoms"}</strong>
                  </p>
                </div>
                <Link
                  href="/ghosttrace"
                  className="mt-3 block text-center py-2 bg-[#122e35] hover:bg-[#1a414a] border border-[#23535d] text-[#9ef368] font-bold uppercase tracking-wider rounded transition-all"
                >
                  Interrogate In CRT Terminal ⚡
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Live Summoner Form Bar */}
        <div id="summon" className="w-full max-w-2xl bg-[#061419]/80 border border-[#16353d] rounded-lg p-4 my-6 backdrop-blur-sm shadow-xl">
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
          {/* Left: Tasty Morsels */}
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

          {/* Right: Haunts by State / Ecosystem */}
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
