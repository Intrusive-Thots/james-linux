"""Self-Evolving Decision Graph Engine (SEDGE).

Status: **stable / frozen**.
Do not add new features or CORE IDEA rewrites without an explicit task in
JULES_WORK_QUEUE.md. Existing API (Node, Edge, DecisionGraph, LearningEngine,
DecisionEngine, SelfEvolvingAgent, build_parrot_wifi_graph) is the supported surface.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import random
from james.tools.constants import (
    SEDGE_EPSILON,
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL,
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)
