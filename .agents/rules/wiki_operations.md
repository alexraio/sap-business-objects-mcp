# LLM-Wiki Operations & Open Knowledge Format (OKF) Specification

This rule file governs how AI agents interact with, maintain, and evolve the project's self-contained knowledge base located in [`wiki/`](../../wiki/index.md).

The architecture combines:
- **Andrej Karpathy's LLM-Wiki Pattern** (*"Compile once, query fast forever"* — separating immutable `wiki/raw/` sources from agent-maintained synthesis pages inside `wiki/`).
- **Google Cloud's Open Knowledge Format (OKF)** (structured YAML frontmatter, progressive disclosure via `index.md`, temporal tracking via `log.md`, and relative Markdown graph links).

---

## 1. Directory Topology (`wiki/`)

All LLM-Wiki assets are clustered inside a single root folder `wiki/` (compatible as a standalone Obsidian vault or OKF bundle):

- **`wiki/index.md`**: Global OKF catalog and entry point for progressive disclosure.
- **`wiki/log.md`**: Chronological, append-only operation log (`ingest`, `update`, `lint`).
- **`wiki/raw/`**: Immutable primary sources (original design RFCs, SAP Notes, API dumps, trace logs). Agents **read** from `wiki/raw/` during ingestion, but **never edit** files inside `wiki/raw/`.
- **`wiki/architecture/`**: System design, authentication, session isolation, and diagnostics engine specs.
- **`wiki/sap_bo/`**: SAP BusinessObjects 4.3 SP5 domain truths (CMS SQL, IDT vs CMC rules, Raylight, Universes).
- **`wiki/tools/`**: MCP tool catalogs, input/output contracts, and safety tiers.
- **`wiki/troubleshooting/`**: Diagnostic runbooks keyed by SAP BO error codes (`IES 10901`, `WIS 30553`, `ORA-01017`, etc.).

---

## 2. Open Knowledge Format (OKF) Page Standard

Every compiled concept page in `wiki/` (excluding `wiki/log.md` and `wiki/raw/**`) **must** begin with valid YAML frontmatter containing at least `type`, `title`, and `description`:

```yaml
---
type: architecture | sap_domain | tool_catalog | troubleshooting_runbook | index
title: Concise Human- and Agent-Readable Title
description: One-sentence summary of the page's scope for progressive disclosure.
status: active | draft | deprecated
last_updated: YYYY-MM-DD
tags:
  - tag1
  - tag2
related:
  - ../sap_bo/connections_and_idt.md
  - ../tools/catalog_schedules_and_diagnostics.md
---
```

### Graph Linking Rules:
- Use **bundle-relative standard Markdown links** (e.g., `[IDT Connection Rules](../sap_bo/connections_and_idt.md)`) so links work natively in GitHub, VS Code, Obsidian, and agent file readers.
- Whenever a concept page references another domain concept, error code, or MCP tool, link it bi-directionally in the prose and in the `related` frontmatter list.

---

## 3. Core Agent Operations

### Operation 1: `QUERY` (Progressive Disclosure Navigation)
When answering technical questions, debugging SAP BO issues, or designing new features:
1. **Read `wiki/index.md` first** to identify relevant concept pages.
2. Follow links to the specific category `index.md` or directly to the target concept file(s).
3. Load only the necessary concept pages into context rather than scanning the entire repository.
4. If an investigation produces a novel, verified technical insight, offer to persist it into `wiki/`.

### Operation 2: `INGEST` (Knowledge Compilation)
When the user adds new material to `wiki/raw/` or codebase features change:
1. Read the source material from `wiki/raw/` or the updated source code in `core/` / `services/` / `server.py`.
2. Identify which pages in `wiki/` need to be created or surgically updated.
3. Author or update the target Markdown pages in **English** with complete YAML frontmatter and relative graph links.
4. Update the relevant category `index.md` and root `wiki/index.md` if new pages were added or descriptions changed.
5. Append a timestamped entry to `wiki/log.md` using the format:
   ```markdown
   ## [YYYY-MM-DD] ingest | <Short Title>
   - **Source:** `<source path or commit>`
   - **Updated Pages:** `<list of modified/created wiki pages>`
   - **Summary:** <1-2 sentences describing the compiled knowledge>
   ```

### Operation 3: `LINT` (Knowledge Graph Auditing)
When asked to lint or audit the wiki:
1. **Link Integrity:** Verify that all relative Markdown links and `related` frontmatter paths resolve to existing files.
2. **Orphan Detection:** Ensure every compiled page in `wiki/` is listed in its category `index.md` and `wiki/index.md`, and has at least one incoming link.
3. **Codebase Alignment:** Cross-check `wiki/tools/` and `wiki/architecture/` against `server.py`, `core/`, and `services/` to detect undocumented tools or stale signatures.
4. **Domain Rule Compliance:** Verify that all pages strictly adhere to [`.agents/rules/project_rules.md`](./project_rules.md) (English language only; relational connection tests strictly via **IDT**/**UDT**, never CMC).
5. Append a `lint` entry to `wiki/log.md` summarizing findings and fixes.
