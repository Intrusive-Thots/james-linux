import { useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { COMMANDS, usePhantom } from "../lib/store";
import { CollapsibleDrawer } from "./CollapsibleDrawer";

export function ConsoleDrawer() {
  const open = usePhantom((s) => s.consoleOpen);
  const setOpen = usePhantom((s) => s.setConsoleOpen);
  const exec = usePhantom((s) => s.exec);
  const history = usePhantom((s) => s.cmdHistory);
  const output = usePhantom((s) => s.cmdOutput);
  const logs = usePhantom((s) => s.logs);
  const last = logs[logs.length - 1];
  const [value, setValue] = useState("");
  const [histIdx, setHistIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = useMemo(() => {
    const v = value.trim().toLowerCase();
    if (!v) return [];
    return COMMANDS.filter((c) => c.startsWith(v) && c !== v).slice(0, 5);
  }, [value]);

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (e.key === "`" || (e.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA")) {
        e.preventDefault();
        setOpen(true);
        window.setTimeout(() => inputRef.current?.focus(), 20);
      }
      if (e.key === "Escape" && open) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const run = async (line: string) => {
    const t = line.trim();
    if (!t) return;
    setValue("");
    setHistIdx(-1);
    await exec(t);
  };

  const onKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      void run(value);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!history.length) return;
      const next = histIdx < 0 ? history.length - 1 : Math.max(0, histIdx - 1);
      setHistIdx(next);
      setValue(history[next] ?? "");
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (histIdx < 0) return;
      const next = histIdx + 1;
      if (next >= history.length) {
        setHistIdx(-1);
        setValue("");
      } else {
        setHistIdx(next);
        setValue(history[next] ?? "");
      }
    } else if (e.key === "Tab") {
      e.preventDefault();
      const hit = suggestions[0];
      if (hit) setValue(hit);
    }
  };

  return (
    <div className="shrink-0 border-t border-line bg-panel px-4">
      <CollapsibleDrawer
        title="Console"
        meta={!open && last ? last.message : undefined}
        open={open}
        onToggle={() => setOpen(!open)}
      >
        <div className="pb-3">
          <pre className="max-h-36 overflow-auto py-3 font-mono text-xs leading-5 text-muted">
            {output.join("\n") || "Type help for commands."}
          </pre>
          {suggestions.length > 0 ? (
            <div className="flex flex-wrap gap-2 pb-2">
              {suggestions.map((s) => (
                <button key={s} type="button" className="min-h-8 text-xs text-accent" onClick={() => setValue(s)}>
                  {s}
                </button>
              ))}
            </div>
          ) : null}
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void run(value);
            }}
          >
            <label htmlFor="phantom-cmd" className="shrink-0 font-mono text-xs text-muted">
              phantom@ops
            </label>
            <input
              id="phantom-cmd"
              ref={inputRef}
              value={value}
              autoComplete="off"
              spellCheck={false}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={onKeyDown}
              className="h-11 min-w-0 flex-1 rounded-md bg-raised px-3 font-mono text-sm text-fg outline-none"
              placeholder="help · scan · poa lab · workflow psk-hunt"
            />
            <button type="submit" className="min-h-11 rounded-md px-3 text-sm text-muted hover:text-fg">
              Run
            </button>
          </form>
        </div>
      </CollapsibleDrawer>
    </div>
  );
}
