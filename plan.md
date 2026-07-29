1. Add `onKeyDown` to the filter input in `web/src/pages/Logs.tsx` to clear the filter on Escape key.
2. Add `onKeyDown` to the filter input in `web/src/pages/Recon.tsx` to clear the filter on Escape key.
3. Update `web/src/pages/Logs.tsx` and `web/src/pages/Recon.tsx` to explicitly blur the input elements when Escape is pressed (`e.currentTarget.blur()`), matching the pattern in `web/src/pages/AgentConsole.tsx`.
4. Include pre-commit steps to ensure proper testing, verification, review, and reflection are done.
5. Submit the changes with a detailed rationale explaining the friction point (inconsistent clearing of filter inputs using Escape) and the improvement (UX enhancement for keyboard navigation).
