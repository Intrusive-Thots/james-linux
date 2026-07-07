import { useState, useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Bot,
  Send,
  Loader2,
  User,
  Terminal,
} from "lucide-react";
import type { AppState } from "../hooks/useAppState";
import { cn } from "../lib/utils";

interface AgentConsoleProps {
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

export function AgentConsole({ state: _state, connected, send, addLog, lastAgentResponse }: AgentConsoleProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [processing, setProcessing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastResponseTs = useRef(0);

  // Auto-scroll chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Watch for agent responses
  useEffect(() => {
    if (lastAgentResponse && lastAgentResponse.ts > lastResponseTs.current) {
      lastResponseTs.current = lastAgentResponse.ts;
      addMessage("agent", lastAgentResponse.response);
      setProcessing(false);
    }
  }, [lastAgentResponse]);

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

  const handleSendCommand = () => {
    const cmd = input.trim();
    if (!cmd || processing) return;
    if (!connected) {
      addLog("error", "Backend offline. Start the API server first.");
      return;
    }

    setInput("");
    addMessage("user", cmd);
    setProcessing(true);
    send("agent_command", { command: cmd });

    // Safety timeout
    setTimeout(() => setProcessing(false), 15000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendCommand();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full flex flex-col p-lg"
    >
      <div className="max-w-dashboard mx-auto w-full flex flex-col flex-1 min-h-0 space-y-lg">
        <div>
          <h2 className="text-h2 text-text-primary mb-[2px] flex items-center gap-sm">
            <Terminal className="w-6 h-6 text-accent-purple" />
            Agent Console
          </h2>
          <p className="text-body text-text-secondary">
            Send commands to the JAMES AI agent. Try{" "}
            <strong>scan</strong>, <strong>status</strong>, <strong>loot</strong>,{" "}
            <strong>interfaces</strong>, or <strong>help</strong>.
          </p>
        </div>

        <div className="card flex-1 flex flex-col min-h-0">
          <div className="card-header">
            <div className="card-title">
              <Bot className="w-5 h-5 text-accent-purple" />
              Live Session
            </div>
            <span
              className={cn(
                processing ? "badge-cyan scanning-pulse" : "badge-muted"
              )}
            >
              {processing ? "PROCESSING" : "READY"}
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
                    Send natural language commands to control JAMES.
                    The agent will interpret your intent and execute the
                    appropriate operations.
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
              placeholder="Type a command (scan, status, loot, help)…"
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
