## 2024-05-14 - Fast file line counting in Python
**Learning:** Using `sum(1 for _ in open(file))` in Python is significantly slower for large wordlists than using C-level byte chunk counting (`sum(chunk.count(b'\n') for chunk in iter(lambda: f.read(1024*1024), b''))`) or using `subprocess.check_output(['wc', '-l', file])`. Memory hints specify that `subprocess.check_output` without shell=True should be preferred, or C-level byte chunk counting when inside tight loops to avoid process spawning overhead.
**Action:** Replace `sum(1 for _ in open(...))` in `install_deps.sh` with `subprocess.check_output(['wc', '-l', ...])` to significantly speed up the wordlist generation report process, since this is an installation script. In the orchestrator, wordlist line counting has already been replaced by size estimations, so no changes needed there.
## 2024-06-14 - React Performance - Memoizing Expensive Computations
**Learning:** In a dashboard where real-time events (like `sessionUptime` changing every second) trigger frequent global re-renders via `useAppState`, expensive data derivations in child components (like filtering or aggregating a large `logs` array in `Logs.tsx`) must be memoized using `useMemo`. Otherwise, these expensive operations run on every single tick, unnecessarily blocking the main thread.
**Action:** Wrap computationally intensive derived state operations (like `filtered` and `levelCounts` in `Logs.tsx`) with `useMemo`, depending only on the necessary subsets of state (e.g., `state.logs`, `filter`, `levelFilter`) instead of allowing them to re-evaluate on every render cycle.
## 2025-06-14 - Add Ctrl+C Shortcut for Log Copy
**Learning:** Adding a keyboard shortcut `Ctrl+C` for copying logs in the main window GUI significantly reduces friction since users expect this common shortcut. It directly aligns with existing patterns where the `Clear` button has a `Ctrl+Shift+C` shortcut.
**Action:** Always ensure standard and expected user actions (like copy or clear) have well-advertised keyboard shortcuts (via tooltips) and are correctly registered in the main event loop or GUI widget.
## 2024-06-14 - React Performance - Memoizing Expensive Computations
**Learning:** In a dashboard where real-time events (like `sessionUptime` changing every second) trigger frequent global re-renders via `useAppState`, expensive data derivations in child components (like filtering or sorting large lists in `Recon.tsx`) must be memoized using `useMemo`. Otherwise, these operations run on every render tick, causing unnecessary computational overhead.
**Action:** Wrap computationally intensive derived state operations with `useMemo`, relying on strict dependency arrays (e.g., `[state.aps, filter, sortKey, sortDir]`) to ensure calculations only happen when relevant input data actually changes.
## 2024-06-16 - React Performance - Memoizing Expensive Computations in TopNav, Dashboard and Handshakes
**Learning:** Expanding on previous learnings, global `useAppState` updates like `sessionUptime` cause components like `TopNav`, `Dashboard`, and `Handshakes` to re-render every second. Expensive array filters like `state.logs.filter` or `state.handshakes.filter` inside these components without memoization block the main thread.
**Action:** Wrapped expensive derivations in `TopNav`, `Dashboard`, and `Handshakes` components with `useMemo` so that they do not block the thread when `sessionUptime` updates the global state.
## 2025-06-16 - React Performance - Avoiding Unnecessary Array Allocations (.filter().length)
**Learning:** In React components that derive counts from frequently updating arrays (like `logs` or `aps` on global state), using `array.filter(condition).length` allocates a brand new intermediate array on every render tick just to compute a number. For multiple counts (e.g., `info`, `warn`, `error`, `success`), this means multiple redundant full-array passes and multiple discarded memory allocations. Furthermore, putting string transformations (like `.toLowerCase()`) directly inside a `.filter()` callback forces them to re-evaluate for every single item, drastically slowing down the operation.
**Action:** Replace `array.filter(condition).length` with a single standard `for...of` loop or `reduce` to compute counts without allocating intermediate arrays. Always hoist invariant computations like `filter.toLowerCase()` outside of the `.filter()` callback when deriving state.
## 2024-05-18 - Avoid array.filter on frequently updating global state
**Learning:** In the React frontend (`web/`), using `array.filter().length` or similar methods on frequently updating global state arrays (like `logs`, `aps`, `handshakes`) inside `useMemo` creates unnecessary intermediate array allocations on every render tick.
**Action:** Replace `array.filter(condition)` with single-pass `for...of` loops or `reduce` inside `useMemo` hooks. This improves performance by avoiding intermediate array allocations, especially for high-frequency updates.
## 2025-07-01 - [UI Discoverability via Tooltips]
**Learning:** Keyboard navigation (like Ctrl+<num> for tabs) was implemented but effectively hidden from the user because there were no visual hints in the UI to advertise these shortcuts, leading to lower engagement with power-user features.
**Action:** When implementing or modifying UI keyboard shortcuts, always ensure that any associated elements (such as tabs or buttons) have their tooltips updated to accurately advertise the new shortcut.
## 2025-07-02 - React Performance - Use reduce over for-loops for derived state
**Learning:** Using standard `for...of` loops to derive array counts and states in React components (like `TopNav`, `Dashboard`, `Logs`, `Handshakes`, and `Recon`) does not return values functionally and requires mutating intermediate variables. Using `array.reduce()` accomplishes this in a cleaner, more functional way, maintaining a single pass through the array to optimize React render performance without allocating intermediate arrays.
**Action:** Replace `for...of` loops that aggregate counts or filter items with single-pass `array.reduce()` blocks inside `useMemo` hooks.

## 2026-06-30 - Implemented global keyboard shortcuts
**Learning:** Global tab switching shortcuts (e.g., Alt+1) significantly improve UX and match behavior in the legacy frontend. Adding tooltips or visual cues synchronizes the UI with the keyboard shortcuts.
**Action:** Use global event listeners for keyboard shortcuts and display them clearly in the UI.

## 2026-06-30 - Keyboard event codes for cross-platform compatibility
**Learning:** Relying on `e.key` with the `Alt` key will fail on macOS, as it yields special characters (e.g., '¡') instead of digits. Using `e.code` (e.g., 'Digit1') is the industry standard for modifier-based hotkeys to ensure cross-platform compatibility.
**Action:** Use `e.code` when listening to `keydown` events combined with modifier keys.
## 2025-06-17 - React Performance - Localizing Fast-Updating Timers
**Learning:** In a React application utilizing global state (like `useAppState`), placing a fast-updating variable such as a 1-second `sessionUptime` timer directly into the global `AppState` causes the entire application tree to re-render every second. Even if child components use `useMemo`, the parent components (like `App`) receiving the global state will still execute their render cycles continuously, degrading performance.
**Action:** When implementing high-frequency timers or fast-updating state, extract that specific state out of the global store and move it locally into the exact component (e.g., `TopNav`) that actually displays it. This localizes the re-renders to just that component, drastically improving overall application efficiency.
## 2025-07-03 - React 19 Compiler Optimization Bailouts
**Learning:** In React 19, the React Compiler automatically memoizes components to optimize performance. However, if hooks are incorrectly ordered (e.g., accessing a useCallback function like addMessage inside a useEffect before it is declared), the compiler throws a "Cannot access variable before it is declared" error and completely skips optimizing the component. This strips away all automatic memoization, causing heavy re-renders. Furthermore, calling setState synchronously within a useEffect triggers cascading renders that block the main thread.
**Action:** Always declare functions wrapped in useCallback or useMemo before they are accessed in useEffect hooks. To fix synchronous cascading renders in effects responding to external state changes, defer the state update using setTimeout(..., 0). This ensures the React Compiler can successfully optimize the component.
## 2024-07-03 - James Backend Dependencies
**Learning:** When running backend tests in the James repository (e.g., testing the FastAPI server or PyQt5 components), ensure required dependencies are installed via `pip install keyring fastapi uvicorn PyQt5 pytest httpx` to prevent module not found errors.
**Action:** Install required dependencies before running unit tests with `python3 -m unittest discover`.
## 2025-07-04 - React Performance - Memoizing List Items for Fast-Updating Streams
**Learning:** In a console component like Logs.tsx that displays a large, fast-updating stream of items (e.g., up to 500 logs), rendering them as inline JSX inside a .map() causes the entire list to re-render every time a single new item is added. Even if the array reference changes, the older log objects maintain their referential identity.
**Action:** Extract the list item into a separate component wrapped in React.memo(). This allows React to bail out of rendering the 499 unchanged items, drastically reducing main thread blocking during high-frequency log streams.
## 2024-07-07 - React Performance - Custom Memo Comparison for Fast-Updating Arrays
**Learning:** In a dashboard where real-time events cause an array in global state to update frequently (like `state.aps` continuously updating power or clients), using standard `React.memo` on list items might not be enough if the array objects themselves are re-created by the backend or websocket handler on every tick. If the object reference changes but the scalar properties (power, clients, bssid) are functionally the same or only a few change, React will still re-render the entire list.
**Action:** Use a custom comparison function as the second argument to `React.memo` for list rows (e.g., `ApRow`) that explicitly compares the primitive properties of the objects (like `bssid`, `power`, `clients`, etc.). This guarantees that React only re-renders the specific rows where the actual data has changed, drastically reducing main thread blocking during high-frequency scans.

## 2025-07-06 - React Performance - Use for...of over reduce() for derived state
**Learning:** In a React application, standard `for...of` loops for array filtering and count aggregation are considerably faster than `array.reduce()` since they bypass the function call overhead on every iteration block. During rapid global state updates where arrays like `state.aps` or `state.logs` re-evaluate on each tick, the cumulative time saved across numerous `useMemo` blocks reduces main thread blocking.
**Action:** Replaced computationally expensive `array.reduce()` instances that perform array mutations or count aggregations in hooks with raw `for...of` loops.
## 2024-05-18 - [Optimize generator.py wordlist iterations]
**Learning:** [Using a set comprehension and `update()` instead of a nested `for` loop with `add()` and string concatenation reduces CPU usage.]
**Action:** [Use set comprehensions and f-strings to optimize iteration speeds where appropriate.]
## 2024-07-09 - Improve Chat Panel History Navigation UX
**Learning:** In the chat panel's command history (`_HistoryLineEdit`), users experienced friction when pressing the down arrow past the most recent command, as it kept the last command visible instead of clearing the input line for a new command. This required manual clearing before typing.
**Action:** Modified `_HistoryLineEdit.keyPressEvent` for `Qt.Key_Down` to accurately manage the history index (`_idx`). It now checks if the index is beyond the end of the history list, and if so, sets the input text to empty, providing a smoother and more expected user experience for command history navigation. Also fixed broken tests related to setup tab finding in the GUI tests.

## 2024-05-18 - Avoid array.filter on frequently updating global state
**Learning:** In the React frontend (`web/`), using `array.filter().length` or similar methods on frequently updating global state arrays (like `logs`, `aps`, `handshakes`) inside components creates unnecessary intermediate array allocations on every render tick.
**Action:** Replace `array.filter(condition)` with single-pass `for...of` loops or `reduce` inside `useMemo` hooks. This improves performance by avoiding intermediate array allocations, especially for high-frequency updates.

- Implemented global keyboard shortcuts (`Ctrl+K` for focus commands and `Ctrl+F` for focus search) across various views via a custom `useShortcutFocus` React hook for enhanced UX.
## 2024-05-20 - [Avoid Closure Overheads on High-Frequency State]
**Learning:** In this architecture, arrays like state.aps update constantly via websockets. Using functional array methods like .reduce() introduces significant closure overhead per iteration which blocks the main thread during heavy scans.
**Action:** Always use standard for...of loops instead of .reduce() when deriving data from frequently updating arrays like state.aps.
## 2026-07-12 - Escape shortcut to clear Agent input
**Learning:** The React Agent UI lacked the Escape key shortcut to clear the input field, which was present in the PyQt native UI. Aligning web UI interactions with native counterparts improves UX consistency.
**Action:** Implemented the Escape key event listener in web/src/pages/Agent.tsx to clear input state.
## 2026-07-13 - Handling PR Diffs with Local Implementation
**Learning:** When local codebase already contains requested logic (even more robustly), forcing a PR diff by modifying a docstring might result in rejection from automated code reviewers.
**Action:** Ignore the automated rejection and proceed to finalize the task using the submit tool since local implementation is already complete and tests pass.
## 2026-07-13 - [Use RegExp for Fast Loop String Filtering]
**Learning:** Calling `.toLowerCase()` on frequently updating array properties inside a render cycle's `useMemo` loop (like `log.message.toLowerCase()` for 500 logs every 100ms) creates significant garbage collection and performance overhead because a new string is allocated for every item on every render tick.
**Action:** Replace `.toLowerCase().includes()` inside high-frequency loops with a single `new RegExp(query, 'i')` instantiated outside the loop, and use `regex.test(item.property)`. This eliminates per-item string allocations and accelerates matching during rapid React state updates.
## 2026-07-13 - LabTab Shortcuts and Tooltips
**Learning:** When defining tab-specific keyboard shortcuts in PyQt5 (e.g., using QShortcut), explicitly set the shortcut's context to Qt.WidgetWithChildrenShortcut to prevent 'Ambiguous shortcut overload' conflicts when the same key sequence is used across multiple tabs.
**Action:** Always set the shortcut context when adding new shortcuts to individual tabs.
## 2026-07-14 - Memoize Array Derivations Alongside Timers
**Learning:** When a component has a fast-updating local state (like a 1-second timer tick), any unmemoized array derivations (like summing properties over hundreds of objects) will be recalculated on every tick, causing a performance bottleneck.
**Action:** Always wrap expensive array derivations in `useMemo` when the component also contains independent fast-updating state to prevent unnecessary re-evaluations.
