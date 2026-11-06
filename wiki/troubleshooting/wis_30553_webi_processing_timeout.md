---
type: troubleshooting_runbook
title: "WIS 30553 & WSR 00999: Webi Processing Server Timeout & Resource Exhaustion"
description: Root cause analysis and remediation runbook for Web Intelligence Processing Server errors WIS 30553, WIS 30551, ERR_WIS_30270, and WSR 00999.
status: active
last_updated: 2026-11-06
tags:
  - wis-30553
  - wsr-00999
  - timeout
  - memory
  - webi
related:
  - ./index.md
  - ../sap_bo/webi_raylight_lifecycle.md
  - ../tools/catalog_semantic_and_webi.md
---

# WIS 30553 & WSR 00999: Webi Processing Server Timeout & Resource Exhaustion

## 1. Error Signatures & Meaning

- **`WIS 30553` / `WIS 30551` / `ERR_WIS_30270`:** The Web Intelligence Processing Server (`wireportserver`) exceeded its memory threshold, hit an execution timeout, or terminated unexpectedly while computing microcube aggregations or streaming large datasets.
- **`WSR 00999` (HTTP 500 in Raylight REST API):** Internal Web Intelligence Server Engine exception raised during REST execution (often triggered by a corrupted Data Provider specification, an unanswered mandatory prompt, or backend `wireportserver` saturation).

---

## 2. Ranked Probable Causes

1. **Rank 1 — Unbounded Query Volume or Cartesian Product:**
   A Data Provider SQL query lacks selective `WHERE` filters or contains an unjoined table path in the universe, returning millions of rows into the Webi microcube.
2. **Rank 2 — Complex Report-Level Formulas (`ForEach`, `ForAll`, `Previous`):**
   Heavy cross-tab calculations and nested context operators exhaust the Web Intelligence Processing Server's `Maximum Memory Threshold`.
3. **Rank 3 — Server Timeout / Sizing Constraints in CMC:**
   Concurrent nocturnal batch jobs saturate the available `WebIntelligenceProcessingServer` instances or exceed the CORBA / WACS idle timeout.

---

## 3. Step-by-Step Remediation Protocol

### Step 1: Inspect Data Provider SQL & Variables via `bo-mcp`
1. Extract the generated SQL using [`get_dp(webi_doc_id)`](../tools/catalog_semantic_and_webi.md) and [`get_dp_sql(webi_doc_id, dp_id)`](../tools/catalog_semantic_and_webi.md) to check for missing filters or Cartesian joins.
2. Inspect custom report formulas via [`get_variables(webi_doc_id)`](../tools/catalog_semantic_and_webi.md) to identify expensive in-memory calculations that should be pushed down to the SQL/Universe layer.

### Step 2: CMC Server Sizing & Timeout Administration
*(Note: While relational connection tests require IDT, platform server sizing and timeouts **are** managed in the CMC).*
1. Log in to the **Central Management Console (CMC)** $\rightarrow$ **Servers** $\rightarrow$ **Web Intelligence Services**.
2. Open the properties of **WebIntelligenceProcessingServer**:
   - Inspect **Maximum Memory Threshold** (e.g., increase or clone an additional Webi Processing Server node if physical RAM allows).
   - Inspect **Idle Document Timeout** and **Server Polling Time**.
   - Check **Maximum Connections** to ensure concurrent nocturnal schedules are not queuing indefinitely.

### Step 3: Universe Query Guardrails (IDT)
In **Information Design Tool (IDT)**, open the `.unx` Business Layer / Data Foundation properties and review:
- `Limit size of result set to: <N> rows`
- `Limit execution time to: <M> minutes`
