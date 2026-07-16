import { useEffect, useRef } from "react";

export function useShortcutFocus(key: string, ctrl: boolean = true) {
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        (ctrl ? e.ctrlKey || e.metaKey : true) &&
        e.key.toLowerCase() === key.toLowerCase() &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        ref.current?.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [key, ctrl]);

  return ref;
}
