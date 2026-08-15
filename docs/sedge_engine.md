# 📈 Self-Evolving Decision Graph Engine (SEDGE) — JAMES Linux

> **Status: stable / frozen.**  
> New SEDGE features or “CORE IDEA” rewrites require an explicit task in `JULES_WORK_QUEUE.md`.  
> Do not expand the graph engine until structure work (agent/orchestrator splits) lands.

The **Self-Evolving Decision Graph Engine (SEDGE)**, implemented in `james/core/sedge.py`, is a reinforcement learning-inspired decision system. 

Instead of relying on hardcoded procedural scripts, SEDGE models pentesting strategies as a directed weighted graph. Over time, successful pathways are reinforced, allowing optimal scanning, analysis, and exploitation policies to emerge automatically from usage feedback.

---

## 🧭 The Decision Graph Structure

SEDGE represents decisions as a `DecisionGraph` composed of two primary elements:

### 1. Nodes (`Node`)
A node represents either a state of intelligence or a direct action:
*   **State Nodes**: Represent the agent's current understanding of the target system (e.g., `START`, `NETWORK_DISCOVERY`, `TARGET_ANALYSIS`, `SECURITY_PROFILING`).
*   **Action Nodes**: Represent active operations executed using wrappers (e.g., `PASSIVE_SCAN`, `HANDSHAKE_CAPTURE`, `DEAUTH_TEST`, `EVIL_TWIN_SIMULATION`).

### 2. Edges (`Edge`)
An edge defines a valid transition from one node to another. It contains statistics that determine transition behavior:
*   `success_weight`: Cumulative metric representing positive outcomes from traversing the edge.
*   `failure_weight`: Cumulative metric representing negative outcomes.
*   `visits`: The total count of times the agent traversed this edge.

### 📐 Utility Score Formula
The value of an edge is calculated as the ratio of success to failure, with a small epsilon (`SEDGE_EPSILON` = `1e-5`) added to prevent division by zero errors:

$$\text{Utility Score} = \frac{\text{success\_weight}}{\text{failure\_weight} + \epsilon}$$

---

## 🧠 Policy & Learning Engines

See source for DecisionEngine (stochastic weighted selection) and LearningEngine (success/failure/partial backpropagation).

## 📡 Case Study: Parrot WiFi Graph

`build_parrot_wifi_graph()` maps standard wireless campaign stages. Path convergence reinforces successful routes.
