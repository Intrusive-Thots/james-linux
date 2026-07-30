import { useState, useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Bot,
  Send,
  Sparkles,
  StopCircle,
  Loader2,
  User,
  Terminal,
} from "lucide-react";
import type { AppState } from "../hooks/useAppState";
import { cn } from "../lib/utils";
import { useShortcutFocus } from "../hooks/useShortcutFocus";

interface AgentProps {
  state: AppState;
  connected: boolean;
  send: (action: string, params?: Record<string, any>) => void;
  addLog: (level: "info" | "warn" | "error" | "success", msg: string) => void;
  lastAgentResponse?: { response: string; ts: number } | null;
}

interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: string;
}

export function Agent({ state, connected, send, addLog, lastAgentResponse }: AgentProps) {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [autoPilotRunning, setAutoPilotRunning] = useState(false);
  const [processing, setProcessing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const commandInputRef = useShortcutFocus("k", true);
  const lastResponseTs = useRef(0);

  // Auto-scroll chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const addMessage = useCallback((role: "user" | "agent", content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        role,
        content,
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  }, []);

  // Watch for agent responses from App.tsx
  useEffect(() => {
    if (lastAgentResponse && lastAgentResponse.ts > lastResponseTs.current) {
      lastResponseTs.current = lastAgentResponse.ts;
      addMessage("agent", lastAgentResponse.response);
      setProcessing(false);
    }
  }, [lastAgentResponse, addMessage]);

  const handleSendCommand = () => {
    const cmd = input.trim();
    if (!cmd || processing) return;
    if (!connected) {
      addLog("error", "Backend offline. Start the API server first.");
      return;
    }

    setInput("");
    setHistory((prev) => [...prev, cmd]);
    setHistoryIdx(-1);
    addMessage("user", cmd);
    setProcessing(true);
    send("agent_command", { command: cmd });

    // Safety timeout: if no response in 15s, unblock
    setTimeout(() => setProcessing(false), 15000);
  };

  const handleAutoPilot = () => {
    if (!connected) {
      addLog("error", "Backend offline. Start the API server first.");
      return;
    }
    if (!state.adapter) {
      addLog("error", "No wireless adapter detected.");
      return;
    }

    if (autoPilotRunning) {
      send("abort_attack");
      setAutoPilotRunning(false);
      addMessage("agent", "🛑 Auto-Pilot abort signal sent.");
      addLog("warn", "Auto-Pilot abort requested.");
      return;
    }

    setAutoPilotRunning(true);
    addMessage("agent", "🤖 Auto-Pilot engaged. Scanning for targets, selecting the best candidate, capturing handshake, and cracking…");
    addLog("info", "Auto-Pilot launched.");
    send("auto_pilot", { interface: state.adapter });

    // Auto-reset after 5 min timeout
    setTimeout(() => setAutoPilotRunning(false), 300000);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendCommand();
    } else if (e.key === "Escape") {
      e.preventDefault();
      setInput("");
      setHistoryIdx(-1);
      e.currentTarget.blur();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (history.length > 0) {
        const nextIdx = historyIdx === -1 ? history.length - 1 : Math.max(0, historyIdx - 1);
        setHistoryIdx(nextIdx);
        setInput(history[nextIdx]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (history.length > 0 && historyIdx !== -1) {
        const nextIdx = historyIdx + 1;
        if (nextIdx >= history.length) {
          setHistoryIdx(-1);
          setInput("");
        } else {
          setHistoryIdx(nextIdx);
          setInput(history[nextIdx]);
        }
      }
    }
  };

  const isAttacking = state.attack.stage === "capturing" || state.attack.stage === "cracking";

  // Watch attack state for auto-pilot completion
  useEffect(() => {
    if (autoPilotRunning && state.attack.stage === "complete") {
      setTimeout(() => {
        setAutoPilotRunning(false);
        if (state.attack.result?.found) {
          addMessage("agent", `🎯 Auto-Pilot complete! Key found: ${state.attack.result.key}`);
        } else {
          addMessage("agent", "🔒 Auto-Pilot complete. Key not found in wordlist.");
        }
      }, 0);
    }
  }, [state.attack.stage, state.attack.result, autoPilotRunning, addMessage]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full flex flex-col p-lg"
    >
      <div className="max-w-dashboard mx-auto w-full flex flex-col flex-1 min-h-0 space-y-lg">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-h2 text-text-primary mb-[2px]">AI Agent</h2>
            <p className="text-body text-text-secondary">
              Autonomous pentesting operations powered by JAMES AI.
            </p>
          </div>
          <button
            className={cn(
              autoPilotRunning ? "btn-danger" : "btn-primary",
            )}
            onClick={handleAutoPilot}
            disabled={!connected && !autoPilotRunning}
          >
            {autoPilotRunning ? (
              <>
                <StopCircle className="w-4 h-4" />
                Abort Auto-Pilot
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Launch Auto-Pilot
              </>
            )}
          </button>
        </div>

        <div className="card flex-1 flex flex-col min-h-0">
          <div className="card-header">
            <div className="card-title">
              <Terminal className="w-5 h-5 text-accent-purple" />
              Agent Console
            </div>
            <span className={cn(
              autoPilotRunning ? "badge-cyan scanning-pulse" : isAttacking ? "badge-warning" : "badge-muted"
            )}>
              {autoPilotRunning ? "AUTO-PILOT" : isAttacking ? "ACTIVE" : "STANDBY"}
            </span>
          </div>

          {/* Chat area */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto min-h-0 space-y-md p-md"
          >
            {messages.length === 0 ? (
              <div className="flex-1 flex items-center justify-center h-full">
                <div className="text-center">
                  <Bot className="w-16 h-16 text-text-muted mx-auto mb-lg opacity-20" />
                  <h3 className="text-h3 text-text-secondary mb-sm">
                    Agent Ready
                  </h3>
                  <p className="text-body text-text-muted max-w-[400px]">
                    Send commands like <strong>scan</strong>, <strong>status</strong>,{" "}
                    <strong>loot</strong>, <strong>interfaces</strong>, or{" "}
                    <strong>help</strong>. Use Auto-Pilot for a fully autonomous
                    attack session.
                  </p>
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    "flex gap-sm",
                    msg.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {msg.role === "agent" && (
                    <div className="w-7 h-7 rounded-btn bg-accent-purple/10 flex items-center justify-center flex-shrink-0 mt-[2px]">
                      <Bot className="w-4 h-4 text-accent-purple" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "max-w-[70%] rounded-btn p-sm px-md",
                      msg.role === "user"
                        ? "bg-accent-cyan/10 border border-accent-cyan/20 text-text-primary"
                        : "bg-bg-elevated border border-border text-text-secondary"
                    )}
                  >
                    <pre className="text-small whitespace-pre-wrap font-mono leading-relaxed">
                      {msg.content}
                    </pre>
                    <div className="text-xs text-text-muted mt-[2px]">
                      {msg.timestamp}
                    </div>
                  </div>
                  {msg.role === "user" && (
                    <div className="w-7 h-7 rounded-btn bg-accent-cyan/10 flex items-center justify-center flex-shrink-0 mt-[2px]">
                      <User className="w-4 h-4 text-accent-cyan" />
                    </div>
                  )}
                </div>
              ))
            )}
            {processing && (
              <div className="flex gap-sm items-center">
                <div className="w-7 h-7 rounded-btn bg-accent-purple/10 flex items-center justify-center flex-shrink-0">
                  <Loader2 className="w-4 h-4 text-accent-purple animate-spin" />
                </div>
                <span className="text-small text-text-muted">
                  Agent is thinking…
                </span>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex items-center gap-sm pt-md border-t border-border">
            <input
              type="text"
              ref={commandInputRef}
              placeholder="Type a command (scan, status, loot, help)… (Ctrl+K)"
              className="flex-1 h-10 px-md text-body bg-bg-elevated border border-border rounded-btn text-text-primary placeholder:text-text-muted focus:border-border-hover focus:outline-none transition-colors"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={processing}
            />
            <button
              className="btn-primary"
              onClick={handleSendCommand}
              disabled={!input.trim() || processing}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
