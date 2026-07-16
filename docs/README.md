# 📖 JAMES Linux — Technical Documentation Index

Welcome to the technical documentation suite for **JAMES Linux**, the autonomous AI-driven penetration testing agent. This documentation is written for security researchers, developers, and operators who want to understand the inner workings of JAMES, modify its behavior, or extend its capabilities.

---

## 🗺️ Documentation Map

To deep dive into specific components or concepts, select from the guides below:

*   ### 🏗️ [System Architecture](file:///home/malcolm/Desktop/james-linux/docs/architecture.md)
    An end-to-end breakdown of the platform's layers, process coordination, state management, context persistence, and communication flow between PyQt5 and FastAPI.

*   ### 🧠 [The Agent Brain & Intent Parser](file:///home/malcolm/Desktop/james-linux/docs/agent_brain.md)
    Details the natural language processing pipeline: intent mapping, pronoun resolution, function calling via Gemini, and autonomous step chaining.

*   ### 📈 [Self-Evolving Decision Graph Engine (SEDGE)](file:///home/malcolm/Desktop/james-linux/docs/sedge_engine.md)
    Explains the custom reinforcement learning-inspired engine that models decisions as a graph, learns from test success/failure feedback, and evolves optimal attack pathways.

*   ### ⚙️ [Orchestrator, Subprocess Layer & Tool Wrappers](file:///home/malcolm/Desktop/james-linux/docs/orchestrator_and_tools.md)
    Understand how JAMES manages subprocesses asynchronously with streaming logs, handles first-time automated setup/monitor mode, checks network protection rules (`NetworkGuard`), and parses pentesting tools.

*   ### 🖥️ [GUI, API Server & PWA remote](file:///home/malcolm/Desktop/james-linux/docs/gui_and_api.md)
    Information about the PyQt5 dashboard tabs, FastAPI uvicorn server endpoints, authenticated WebSocket sessions, and the progressive web application (PWA) client.

*   ### 🛠️ [Writing Custom Skills & Extension Guide](file:///home/malcolm/Desktop/james-linux/docs/skills_and_extension.md)
    A step-by-step developer tutorial on creating custom JSON-based attack workflow templates (skills) and wrapping new terminal tools for the agent.

---

## 🌟 Architecture Overview at a Glance

JAMES splits its core capabilities into three primary systems:

```
                  ┌──────────────────────┐
                  │      User Input      │
                  └──────────┬───────────┘
                             │
                             v
                  ┌──────────────────────┐
                  │     Agent Brain      │ <── Pronoun Resolution / Intent Mapping
                  └──────────┬───────────┘
                             │
                             v
                  ┌──────────────────────┐
                  │     Orchestrator     │ <── Sudo Caching / Task Log / Loot Cache
                  └─────┬──────────┬─────┘
                        │          │
         ┌──────────────┘          └──────────────┐
         v                                        v
┌─────────────────┐                      ┌─────────────────┐
│  Native Layer   │                      │  SEDGE Engine   │
│ (Subprocesses)  │                      │ (Decision Graph)│
└────────┬────────┘                      └────────┬────────┘
         │                                        │
         v                                        v
┌─────────────────┐                      ┌─────────────────┐
│  Hacking Tools  │                      │  Optimal Paths  │
└─────────────────┘                      └─────────────────┘
```

---

## 🚦 Recommended Reading Order

1.  **First time looking at the codebase?** Start with the [System Architecture Guide](file:///home/malcolm/Desktop/james-linux/docs/architecture.md) to understand how the modules fit together.
2.  **Curious how the AI works?** Read the [Agent Brain Guide](file:///home/malcolm/Desktop/james-linux/docs/agent_brain.md).
3.  **Want to understand the reinforcement learning engine?** Check out the [SEDGE Engine Guide](file:///home/malcolm/Desktop/james-linux/docs/sedge_engine.md).
4.  **Ready to write your own workflows?** Head over to the [Skills & Extensions Guide](file:///home/malcolm/Desktop/james-linux/docs/skills_and_extension.md).
