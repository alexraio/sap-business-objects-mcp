---
type: sap_domain
title: Semantic Layer, Universes & Change Data Source
description: Technical reference for UNX and UNV universes, Semantic Layer REST endpoints (/sl/v1/universes), impact lineage, and automated Change Data Source mapping strategies.
status: active
last_updated: 2026-11-06
tags:
  - universe
  - unx
  - unv
  - semantic-layer
  - change-datasource
related:
  - ./index.md
  - ./connections_and_idt.md
  - ./webi_raylight_lifecycle.md
  - ../tools/catalog_semantic_and_webi.md
---

# Semantic Layer, Universes & Change Data Source

The SAP BusinessObjects Semantic Layer translates physical database schemas into business-friendly hierarchies of classes (folders), dimensions, measures, attributes, and predefined filters.

---

## 1. Universe Formats (`UNX` vs. `UNV`)

| Characteristic | UNX (`DSL.MetaDataFile`) | UNV (`Universe`) |
| :--- | :--- | :--- |
| **Authoring Tool** | Information Design Tool (IDT) | Universe Design Tool (UDT) |
| **CMS Virtual Table** | `CI_APPOBJECTS` (`SI_KIND = 'DSL.MetaDataFile'`) | `CI_APPOBJECTS` (`SI_KIND = 'Universe'`) |
| **Webi Relationship Property** | `SI_DSL_UNIVERSE` (`dataprovider-universe`) | `SI_UNIVERSE` (`Webi-Universe`) |
| **Connection Relationship** | `DataConnection-Universe` (`.cns` in `CI_APPOBJECTS`) | `DataConnection-Universe` |
| **Semantic Layer REST API** | Full support via `GET /biprws/sl/v1/universes/{id}` | Metadata inspection via CMS; limited `/sl/v1` support |

---

## 2. Inspecting Business Layer Structure & Lineage

1. **Business Hierarchy (`get_universe_structure`):**
   Calls `GET /biprws/sl/v1/universes/{universe_id}` to retrieve the recursive business layer tree, exposing each object's `@id` (e.g., `OBJ_147`), display `name`, folder path, data type, and qualification (`Dimension`, `Measure`, `Attribute`, `Filter`).
2. **Blast-Radius & Report Lineage (`get_universe_related_reports`):**
   Before modifying or deprecating a universe, query all dependent Webi reports via `get_universe_related_reports(universe_id)`. `UniverseService` automatically detects whether the universe is `unx` or `unv` and executes the appropriate `PARENTS()` CMS relationship query.

---

## 3. Automated Change Data Source (Universe Repointing)

When migrating Web Intelligence reports from a legacy `.unv` to a converted `.unx`, or repointing between development/QA/production universes, Raylight provides the `/documents/{docId}/dataproviders/mappings` API, wrapped by [`get_dp_mapping_proposal`](../tools/catalog_semantic_and_webi.md) and [`change_dp_datasource`](../tools/catalog_semantic_and_webi.md).

### 3.1 Mapping Evaluation Strategies
Raylight evaluates object matching strategies in the exact sequence supplied via the `strategies` parameter (recommended default: **`SameID,SamePath,SameName`**):

| Strategy | Matching Mechanism | Precision & Best Use Case |
| :--- | :--- | :--- |
| **`SameID`** | Matches source and target objects with identical internal CUID/Object IDs. | **100% Exact.** Ideal when a `.unv` was converted to `.unx` via IDT, which preserves internal object IDs even if objects were renamed. |
| **`SamePath`** | Matches objects sharing the exact qualified folder hierarchy (e.g., `Sales/Customer/Country`). | **High Precision.** Safely disambiguates homonymous objects (e.g., `Customer/Name` vs. `Product/Name`). |
| **`SameTechnicalName`** | Matches objects by underlying SQL column or technical name. | Useful when business display names were localized or renamed, but database columns remain identical. |
| **`SameName`** | Matches objects by display name anywhere in the universe tree. | **Medium Precision.** Handles objects moved across folders; returns `@status = "Ambiguous"` if duplicate names exist in different classes. |
| **`CloseName`** | Fuzzy Levenshtein string similarity matching. | **Use with Caution.** Helpful for minor typos or pluralization differences, but requires human verification to avoid false-positive bindings. |

### 3.2 Recommended Migration Workflow
1. **Simulate & Audit (Tier 1 Read-Only):**
   Call `get_dp_mapping_proposal(webi_doc_id, dp_id, target_datasource_id)`.
   `WebiService` enriches Raylight's raw IDs with human-readable object names and folder paths from both source and target universes, reporting `mapped_ok`, `ambiguous`, and `unmapped` counts.
2. **Resolve Ambiguous or Unmapped Objects:**
   Prepare a `custom_mappings` override list (`[{"source_id": "OBJ_12", "target_id": "OBJ_98"}]`) for any object not automatically matched.
3. **Commit Repointing (Tier 2 State-Altering):**
   After explicit user confirmation, call `change_dp_datasource(webi_doc_id, dp_id, target_datasource_id, custom_mappings=..., save=True)`.
