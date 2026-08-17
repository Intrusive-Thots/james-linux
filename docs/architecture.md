# 🏗️ System Architecture Guide — JAMES Linux

This document details the high-level architecture, layer responsibilities, execution flows, and system integration within **JAMES Linux**.

---

## 🧱 Component Layering Diagram

The following diagram illustrates how the frontend controllers, background servers, core orchestrator, tool abstractions, and OS subsystem interact:

```mermaid
graph TD
    %% Styling
    classDef frontend fill:#141e30,stroke:#00f0ff,stroke-width:2px,color:#fff;
    classDef server fill:#0c1020,stroke:#00ff88,stroke-width:2px,color:#fff;
    classDef core fill:#232526,stroke:#ff6b35,stroke-width:2px,color:#fff;
    classDef layers fill:#111,stroke:#a855f7,stroke-width:2px,color:#fff;
    classDef external fill:#2d3748,stroke:#cbd5e0,stroke-width:1px,color:#fff;

    %% Nodes
    A[PyQt5 Desktop Dashboard]:::frontend
    B[Mobile PWA Client / Browser]:::frontend
    
    C[FastAPI WebSocket / API Server]:::server
    
    D[Agent Brain / Intent Classifier]:::core
    E[Orchestrator Coordination Hub]:::core
    F[SEDGE Engine]:::core
    G[NetworkGuard Self-Protection]:::core
    
    H[Native Subprocess Execution Layer]:::layers
    I[Tool Wrapper Suites]:::layers
    
    J[Parrot OS / Linux Kernel Subsystem]:::external
    K[Wi-Fi / Ethernet Adapters]:::external

    %% Relations
    A <-->|Direct Method Calls & Signals| E
    B <-->|Secure WS + REST API| C
    C <-->|Shared Orchestrator Reference| E
    
    E <-->|Queries Context & Intent| D
    E <-->|Consults Decisions| F
    E <-->|Validates Attack Safety| G
    
    E -->|Launches Wrapper Actions| I
    I -->|Translates to CLI Strings| H
    H <-->|Subprocess Execution & Logs| J
    J <-->|Hardware Controls| K
```

---

## 🛡️ The System Layers

### 1. The Presentation Layer
JAMES provides two presentation formats that synchronize state in real time:
*   **Desktop App (`james/gui/`)**: A native Python application built using **PyQt5**. It provides dashboard widgets, terminal monitors, loot tables, and a real-time conversational chat client. It offloads heavy pentesting operations to thread pools using `QThread` and custom `Worker` objects (`james/gui/utils/worker.py`) to prevent GUI freezing.
*   **Web Console / PWA Client**: Primary modern client is the React + Vite app in `web/` (TypeScript, Tailwind). Legacy lightweight SPA remains in `james/web/` (vanilla JS PWA). Both talk to the FastAPI server. Prefer `web/` for new development.

### 2. The Server & API Layer (`james/ser
