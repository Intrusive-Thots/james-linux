# 🧠 The Agent Brain & Intent Parser — JAMES Linux

The **Agent Brain** acts as the cognitive layer of JAMES, transforming natural language user requests into precise technical execution plans. It is implemented across [agent.py](file:///home/malcolm/Desktop/james-linux/james/core/agent.py) and [ai_engine.py](file:///home/malcolm/Desktop/james-linux/james/core/ai_engine.py).

---

## 🚦 Intent Matching Pipeline

When a user submits a text query, JAMES runs it through a tiered dispatch hierarchy designed to balance speed, offline capabilities, and advanced LLM reasoning:

```
                  ┌──────────────────────┐
                  │   User Input text    │
                  └──────────┬───────────┘
                             │
                             v
               /───────────────────────────\
              <  Gemini API available &     >
              <     GEMINI_API_KEY set?     >
               \───────────────────────────/
                       │           │
              YES      │           │ NO
    ┌──────────────────┘           └──────────────────┐
    ▼                                                 ▼
┌──────────────────────┐                     ┌──────────────────────┐
│ 1. Gemini Tool Use   │                     │ 2. Regex Match       │
│ (Function Calling)   │                     │ (Failsafe Precompiled)│
└──────────┬───────────┘                     └──────────┬───────────┘
           │                                            │
           ├─► Tool Call Found?                         ├─► Intent Found?
           │     YES: Execute                           │     YES: Execute
           │     NO: Conversational Chat                │     NO: Fuzzy Suggestion
           ▼                                            ▼
┌──────────────────────┐                     ┌──────────────────────┐
│ 3. Gemini Chat       │                     │ 4. Fuzzy Suggestion  │
│ (Advice/Explanation) │                     │ (Offline fallback)   │
└──────────────────────┘                     └──────────────────────┘
```

### Tier 1: Gemini Tool Use (Function Calling)
If the host machine is connected to the internet and has the `GEMINI_API_KEY` environment variable configured, the `GeminiEngine` is activated.
*   **Tool Schema Registry**: The engine holds a registry of 50+ tool schemas defined in the `TOOL_DECLARATIONS` table.
*   **Structured Dispatch**: It calls the `gemini-2.5-flash` model, passing the conversation history and the tool definitions. If the LLM determines a tool is needed, it returns a structured JSON payload of argument values.
*   **ActionParams**: The server maps these arguments to an `ActionParams` object. This class acts as a drop-in replacement for Python Regex match objects (`re.Match`), mapping dictionary keys to capture group indices so that downstream handlers (`_do_*`) can process requests interchangeably whether they originated from the regex parser or the LLM.

### Tier 2: Precompiled Regex Intents
If the Gemini API is offline or returns an error, JAMES falls back to a deterministic, offline regex interpreter.
*   **Pattern Precompilation**: It scans `INTENT_PATTERNS` containing over 80 pre-compiled regex sequences sorted from specific to generic.
*   **Deterministic Execution**: If a regex match is found, variables (targets, ports, interfaces) are extracted via regex capture groups, and the mapped orchestrator function is dispatched immediately.

### Tier 3: LLM Conversational Fallback
If the user's prompt is a general question (e.g. *"Explain what WPA3 Dragonblood is"*), the Gemini model will bypass function calling and return a text message, providing helpful context, strategy suggestions, or tool syntax instructions.

### Tier 4: Fuzzy Suggestion Engine (Offline Fallback)
If offline and no regex matches the input, the agent suggests the closest possible command using fuzzy string matching (Levenshtein distance) on command keywords.

---

## 🔗 Shorthand & Pronoun Resolution

To enable a natural chat experience, the agent features a persistent pronoun parser (`_resolve_pronouns`). It parses inputs looking for relative pronouns and resolves them using the active context:

| User Input | Active Context | Resolved Input |
|---|---|---|
| *"scan it"* | `{"target": "10.0.0.5"}` | *"scan 10.0.0.5"* |
| *"brute that"* | `{"target": "192.168.1.10"}` | *"brute 192.168.1.10"* |
| *"web attack"* | `{"target": "google.com", "target_url": "https://google.com"}` | *"web pwn https://google.com"* |
| *"go deeper"* | `{"target": "10.0.2.15"}` | *"full scan 10.0.2.15"* |

This resolution runs *before* passing the string to the regex matcher or Gemini model, ensuring the target parameter is always explicitly populated.

---

## 🔄 Autonomous Step Chaining (`run_chain`)

For compound goals (e.g., *"crack neighbors wifi"*), the agent switches into **Multi-Step Chain Mode**.

Instead of executing a single shot command, the agent drives a stateful planning loop:

```
 ┌────────────────────────────────────────────────────────┐
 │                      User Goal                         │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            v
           ┌──────────────────────────────────┐
           │   AI Generates Next Step / Tool  │ <── Context &
           └────────────────┬─────────────────┘     History
                            │
                            v
           ┌──────────────────────────────────┐
           │ Orchestrator Executes & Captures │
           │          Console Output          │
           └────────────────┬─────────────────┘
                            │
                            v
           ┌──────────────────────────────────┐
           │ AI Analyzes Stdout & Updates     │
           │ Context (e.g. SSID, BSSID, etc.) │
           └────────────────┬─────────────────┘
                            │
                            ├─► Goal Achieved / Halted?
                            │     YES: Return final summary
                            │     NO: Loop next step
                            ▼
```

1.  **Chaining Prompting**: System instructions force the model to output a single tool call per turn during chaining.
2.  **Observation Feedback**: The output of the executed command is fed back into the conversation history as a simulated system response.
3.  **Variable Accumulation**: The agent updates context keys (e.g., target interfaces, cracked WEP keys) after each tool output.
4.  **Loop Termination**: The loop continues until the AI returns a text completion block representing the goal summary (or until it hits a hard limit of 10 steps to prevent API billing loops).
