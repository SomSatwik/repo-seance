"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import CrtOverlay from "./crt-overlay";
import Notification from "./notification";

interface TerminalProps {
  repoId: number;
}

/* Original GhostTrace ASCII mark: three ghost-head silhouettes over a
   terminal cursor block. Combined ghost + terminal companion identity. */
const ASCII_ART = `  ___       ___       ___
 /\\_ \\     /\\_ \\     /\\_ \\
 \\/_/ /    \\/_/ /    \\/_/ /
   / /      / /      / /
  / /      / /      / /
 / /   ___ / /   ___ / /
 / /   / __\\ \\ \\   / __\\ \\
/ /___/ /   \\ \\_\\ / /   \\ \\
 \\ \\____/  / / / /____/  / /
  \\/_____/   \\/_/ \\/_____/ \\/_/
         ||█||
         █  █`;

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const WS_URL = API_URL.replace(/^http/, "ws");

type Level = "SAFE" | "CAUTION" | "DESTRUCTIVE" | "INFO" | "SEANCE";

interface Message {
  id: number;
  sender: "user" | "system";
  text: string;
  level?: Level;
  matchedRules?: string[];
  time: string;
}

export default function Terminal({ repoId }: TerminalProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [notification, setNotification] = useState<{
    level: Level;
    message: string;
  } | null>(null);
  const [connected, setConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const addSystemMessage = useCallback(
    (text: string, level?: Level, extra?: { matchedRules?: string[]; evidence?: unknown[] }) => {
      const id = Date.now();
      const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setMessages((prev) => [
        ...prev,
        { id, sender: "system", text, level, matchedRules: extra?.matchedRules, time: now },
      ]);
      return id;
    },
    []
  );

  const addUserMessage = useCallback((text: string) => {
    const id = Date.now() + 1;
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages((prev) => [...prev, { id, sender: "user", text, time: now }]);
  }, []);

  const showNotification = useCallback((level: Level, message: string) => {
    setNotification({ level, message });
    setTimeout(() => setNotification(null), 6000);
  }, []);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws/ghosttrace?repo_id=${repoId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (wsRef.current === ws) {
        setConnected(true);
        addSystemMessage(
          "GhostTrace + Repo Séance unified terminal ready. Type '? <question>', 'history', 'gap', 'roadmap', a shell command, or 'help'.",
          "SAFE"
        );
      }
    };
    ws.onclose = () => {
      if (wsRef.current === ws) {
        setConnected(false);
        wsRef.current = null;
      }
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          addSystemMessage(`[error] ${data.error}`, "DESTRUCTIVE");
          return;
        }
        addUserMessage(data.command);
        addSystemMessage(data.explanation, data.level as Level, {
          matchedRules: data.matchedRules,
          evidence: data.evidence,
        });
        if (data.level === "DESTRUCTIVE") {
          showNotification("DESTRUCTIVE", data.explanation);
        } else if (data.level === "CAUTION") {
          showNotification("CAUTION", data.explanation);
        }
      } catch {
        addSystemMessage("[error] invalid server response", "DESTRUCTIVE");
      }
    };

    return () => {
      if (wsRef.current === ws) wsRef.current = null;
      ws.close();
    };
  }, [repoId, addSystemMessage, addUserMessage, showNotification]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cmd = input.trim();
    if (!cmd) return;
    setInput("");

    // --- Help command ---
    if (cmd.toLowerCase() === "help") {
      addUserMessage(cmd);
      addSystemMessage(
        `GHOSTTRACE + REPO SÉANCE COMMANDS:\n\n` +
        `  ? <question> or ask <question>\n` +
        `    Interrogate repository history with AI & citations\n\n` +
        `  history or contributors\n` +
        `    View commit log, active timeline, and top authors\n\n` +
        `  gap\n` +
        `    Check development dormancy & activity gaps\n\n` +
        `  roadmap\n` +
        `    Synthesize a recovery and revival roadmap\n\n` +
        `  <shell command> (e.g. 'rm -rf ./build')\n` +
        `    Test any command for pre-flight safety verdicts`,
        "INFO"
      );
      return;
    }

    // --- Séance Forensic Q&A ---
    if (cmd.startsWith("?") || cmd.toLowerCase().startsWith("ask ") || cmd.toLowerCase().startsWith("seance ")) {
      addUserMessage(cmd);
      const question = cmd.startsWith("?") ? cmd.slice(1).trim() : cmd.split(" ").slice(1).join(" ").trim();
      if (!question) {
        addSystemMessage("Please provide a question, e.g. '? Who created this project?'", "CAUTION");
        return;
      }
      const waitingId = addSystemMessage("Interrogating repository ghosts...", "SEANCE");
      try {
        const res = await fetch(`${API_URL}/repos/${repoId}/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        });
        const data = await res.json();
        const citations = data.citations?.map((c: { source_type: string; source_ref: string }) => `[${c.source_type}:${c.source_ref}]`).join(", ");
        const text = `${data.answer}${citations ? `\n\nCitations: ${citations}` : ""}`;
        setMessages(prev => prev.filter(m => m.id !== waitingId));
        addSystemMessage(text, "SEANCE");
      } catch (err) {
        setMessages(prev => prev.filter(m => m.id !== waitingId));
        addSystemMessage(`[error] failed to reach séance: ${err}`, "DESTRUCTIVE");
      }
      return;
    }

    // --- History & Contributor Stats ---
    if (cmd.toLowerCase() === "history" || cmd.toLowerCase() === "contributors") {
      addUserMessage(cmd);
      try {
        const res = await fetch(`${API_URL}/repos/${repoId}/history`);
        const data = await res.json();
        const topContribs = data.contributors?.slice(0, 5).map((c: { author: string; commit_count: number }) => `  - ${c.author}: ${c.commit_count} commits`).join("\n") || "  None";
        const recentCommits = data.log?.slice(0, 5).map((c: { short_hash: string; message: string; author: string }) => `  [${c.short_hash}] ${c.message?.split('\n')[0]} (${c.author})`).join("\n") || "  None";
        const text = `TOP CONTRIBUTORS:\n${topContribs}\n\nRECENT COMMITS:\n${recentCommits}${data.gap?.message ? `\n\n${data.gap.message}` : ""}`;
        addSystemMessage(text, "INFO");
      } catch (err) {
        addSystemMessage(`[error] failed to fetch history: ${err}`, "DESTRUCTIVE");
      }
      return;
    }

    // --- Activity Gap / Dormancy ---
    if (cmd.toLowerCase() === "gap" || cmd.toLowerCase() === "dormancy") {
      addUserMessage(cmd);
      try {
        const res = await fetch(`${API_URL}/repos/${repoId}/history`);
        const data = await res.json();
        addSystemMessage(data.gap?.message || "No activity gap detected.", "INFO");
      } catch (err) {
        addSystemMessage(`[error] failed to fetch gap: ${err}`, "DESTRUCTIVE");
      }
      return;
    }

    // --- Recovery Roadmap ---
    if (cmd.toLowerCase() === "roadmap" || cmd.toLowerCase() === "revive") {
      addUserMessage(cmd);
      const waitingId = addSystemMessage("Synthesizing project recovery roadmap...", "INFO");
      try {
        const res = await fetch(`${API_URL}/repos/${repoId}/roadmap`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const data = await res.json();
        setMessages(prev => prev.filter(m => m.id !== waitingId));
        addSystemMessage(data.roadmap || "No roadmap generated.", "INFO");
      } catch (err) {
        setMessages(prev => prev.filter(m => m.id !== waitingId));
        addSystemMessage(`[error] failed to generate roadmap: ${err}`, "DESTRUCTIVE");
      }
      return;
    }

    // --- GhostTrace Shell Safety Classification ---
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      addSystemMessage("[error] WebSocket disconnected", "DESTRUCTIVE");
      return;
    }
    wsRef.current.send(JSON.stringify({ command: cmd }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSubmit(e as unknown as React.FormEvent);
  };

  const levelClass = (level?: Level) => {
    switch (level) {
      case "DESTRUCTIVE":
        return "gt-destructive border-l-4 border-l-[var(--gt-blood)] pl-3";
      case "CAUTION":
        return "gt-caution border-l-4 border-l-[var(--gt-caution)] pl-3";
      case "SAFE":
        return "gt-safe border-l-2 border-l-[var(--gt-safe)] pl-3";
      case "SEANCE":
        return "border-l-2 border-l-[#00c8ff] text-[#e0f7ff] pl-3";
      case "INFO":
        return "border-l-2 border-l-[#af52de] text-[#f3e8ff] pl-3";
      default:
        return "";
    }
  };

  const levelLabel = (level?: Level) => {
    switch (level) {
      case "DESTRUCTIVE":
        return "DESTRUCTIVE";
      case "CAUTION":
        return "CAUTION";
      case "SAFE":
        return "SAFE";
      case "SEANCE":
        return "SÉANCE";
      case "INFO":
        return "FORENSICS";
      default:
        return "";
    }
  };

  return (
    <div className="gt-app flex flex-col h-screen">
      {/* CRT overlay */}
      <CrtOverlay />

      {/* Header bar */}
      <header className="gt-panel border-b border-[#1a1a1a] px-4 py-3 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <pre className="font-mono text-xs text-[var(--gt-blood)] leading-none">
            {ASCII_ART}
          </pre>
          <div>
            <h1 className="font-mono text-sm font-bold text-[var(--gt-fg)] leading-tight">
              GhostTrace<span className="gt-cursor" aria-hidden="true">█</span>
            </h1>
            <p className="font-mono text-xs text-[var(--gt-muted)]">
              Terminal companion • repo #{repoId} •{" "}
              <span
                className={`font-mono ${connected ? "text-[var(--gt-safe)]" : "text-[var(--gt-blood)]"}`}
              >
                {connected ? "LIVE" : "OFFLINE"}
              </span>
            </p>
          </div>
        </div>
        <div className="font-mono text-xs text-[var(--gt-muted)]">
          Safety engine: deterministic (no LLM verdict)
        </div>
      </header>

      {/* Scrollback area */}
      <main className="flex-1 overflow-y-auto px-4 py-4 pr-12 scroll-smooth relative">
        <div ref={messagesEndRef} />
        {messages.map((m) => (
          <div
            key={m.id}
            className={`mb-4 font-mono text-sm leading-relaxed ${levelClass(m.level)}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`text-[10px] uppercase tracking-wider font-bold ${
                  m.sender === "user"
                    ? "text-[var(--gt-muted)]"
                    : m.level === "DESTRUCTIVE"
                    ? "text-[var(--gt-blood)]"
                    : m.level === "CAUTION"
                    ? "text-[var(--gt-caution)]"
                    : "text-[var(--gt-safe)]"
                }`}
              >
                {m.sender === "user" ? "you" : "séance"}
              </span>
              {m.level && (
                <span className="text-[10px] font-bold uppercase tracking-wider">
                  {levelLabel(m.level)}
                </span>
              )}
              <span className="text-[10px] text-[var(--gt-muted)] ml-auto">{m.time}</span>
            </div>
            <div className="whitespace-pre-wrap text-[var(--gt-fg)]">{m.text}</div>
            {m.matchedRules && m.matchedRules.length > 0 && (
              <div className="mt-1 text-[10px] text-[var(--gt-muted)]">
                rules: {m.matchedRules.join(", ")}
              </div>
            )}
          </div>
        ))}
        {messages.length === 0 && (
          <div className="text-[var(--gt-muted)] text-[10px] mt-8 text-center font-mono">
            awaiting command… type in the terminal below
          </div>
        )}
      </main>

      {/* Input area */}
      <footer className="gt-panel border-t border-[#1a1a1a] px-4 py-3 z-20">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <span className="font-mono text-[var(--gt-blood)] text-sm select-none">▸</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command, or '? <question>', 'history', 'gap', 'roadmap', 'help'..."
            className="flex-1 bg-transparent border-none outline-none text-[var(--gt-fg)] font-mono text-sm placeholder-[var(--gt-muted)] w-full"
            disabled={!connected}
          />
          <button
            type="submit"
            disabled={!connected || !input.trim()}
            className="px-3 py-1 font-mono text-xs border border-[#1a1a1a] bg-[var(--gt-bg-panel)] text-[var(--gt-fg)] hover:bg-[#1a1a1a] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {connected ? "send" : "offline"}
          </button>
        </form>
        <p className="text-[10px] text-[var(--gt-muted)] mt-1">
          Safety verdicts are deterministic — Gemma only explains, never decides.
        </p>
      </footer>

      {/* Ghost notification */}
      {notification && (
        <Notification
          level={notification.level.toLowerCase() as "safe" | "caution" | "destructive"}
          message={notification.message}
          onClose={() => setNotification(null)}
        />
      )}
    </div>
  );
}
