---
type: sap_domain
title: CMS Query Language & Virtual Tables
description: Reference guide for the SAP BusinessObjects Central Management Server (CMS) SQL dialect, virtual tables, relationship properties, and query syntax constraints.
status: active
last_updated: 2026-11-06
tags:
  - cms
  - sql
  - ci_infoobjects
  - ci_systemobjects
  - ci_appobjects
related:
  - ./index.md
  - ../tools/catalog_cms_admin_and_infostore.md
  - ../architecture/intelligent_diagnostics_engine.md
---

# CMS Query Language & Virtual Tables

The Central Management Server (CMS) exposes an SQL-like metadata query engine accessible via `POST /biprws/v1/cmsquery` and the [`cms_query`](../tools/catalog_cms_admin_and_infostore.md) MCP tool.

---

## 1. Virtual Tables

The CMS repository abstracts physical database tables into three logical virtual tables:

| Virtual Table | Purpose | Common `SI_KIND` Values |
| :--- | :--- | :--- |
| **`CI_INFOOBJECTS`** | Business content, documents, schedules, folders, and categories. | `'Webi'`, `'CrystalReport'`, `'Publication'`, `'Folder'`, `'FavoritesFolder'`, `'Category'`, `'Txt'`, `'Pdf'`, `'Excel'` |
| **`CI_SYSTEMOBJECTS`** | Security principals, platform servers, connections, and active sessions. | `'User'`, `'UserGroup'`, `'Server'`, `'ServerGroup'`, `'Connection'` |
| **`CI_APPOBJECTS`** | Semantic layer universes, relational connections, and enterprise applications. | `'DSL.MetaDataFile'` (UNX Universe), `'Universe'` (Legacy UNV), `'CCIS.DataConnection'` (Relational Connection) |

> **Multi-Table Union Queries:** You can query across virtual tables simultaneously using comma-separated table names in the `FROM` clause when searching for relationships or mixed kinds:
> `SELECT SI_ID, SI_NAME, SI_KIND FROM CI_INFOOBJECTS, CI_SYSTEMOBJECTS, CI_APPOBJECTS WHERE ...`

---

## 2. Grammar Rules & Engine Limitations

CMS SQL is **not** standard ANSI SQL. Violating these rules results in syntax exceptions or empty result sets:

1. **No `JOIN` Clauses:** Table joins (`INNER JOIN`, `LEFT JOIN`) are unsupported. To resolve relationships across objects, execute a two-step query or use CMS relationship functions (`PARENTS()`, `CHILDREN()`, `RELATIONSHIPS()`).
2. **No `GROUP BY` or Aggregate Functions:** `GROUP BY`, `HAVING`, `SUM()`, `AVG()`, and `MIN()/MAX()` are not supported. (`COUNT(SI_ID)` has limited legacy support, so count rows in Python or inspect pagination metadata).
3. **Avoid `SELECT *`:** Selecting all properties deserializes massive internal property bags and degrades WACS performance. Always specify explicit projections (`SELECT SI_ID, SI_NAME, SI_CUID, SI_KIND ...`).
4. **String Quoting:** Enclose string literals in single quotes (`'Webi'`).
5. **Instance Filtering (`SI_INSTANCE` & `SI_SCHEDULE_STATUS`):**
   - Master document templates have `SI_INSTANCE = 0`.
   - Scheduled execution instances have `SI_INSTANCE = 1`.
   - `SI_SCHEDULE_STATUS` values: `1` = Success, `3` = Failed, `0` = Running, `9` = Pending/Paused.

---

## 3. Canonical CMS Query Patterns

### 3.1 List Webi Document Templates in a Folder
```sql
SELECT SI_ID, SI_CUID, SI_NAME, SI_PARENTID, SI_UPDATE_TS
FROM CI_INFOOBJECTS
WHERE SI_KIND = 'Webi' AND SI_INSTANCE = 0 AND SI_PARENTID = 23855
```

### 3.2 List Published Universes (UNX & UNV)
```sql
SELECT SI_ID, SI_CUID, SI_NAME, SI_KIND, SI_PARENTID
FROM CI_APPOBJECTS
WHERE SI_KIND IN ('DSL.MetaDataFile', 'Universe') AND SI_INSTANCE = 0
```

### 3.3 Find Webi Reports Bound to a Specific UNX Universe
```sql
SELECT SI_ID, SI_NAME, SI_DSL_UNIVERSE
FROM CI_APPOBJECTS, CI_INFOOBJECTS
WHERE PARENTS("SI_NAME='dataprovider-universe'", "SI_ID=15412")
```
*(For legacy `.unv` universes, replace `SI_DSL_UNIVERSE` with `SI_UNIVERSE` and `'dataprovider-universe'` with `'Webi-Universe'`).*

### 3.4 Find Relational Connection Linked to a UNX Universe
```sql
SELECT SI_ID, SI_NAME, SI_KIND
FROM CI_APPOBJECTS
WHERE CHILDREN("SI_NAME='DataConnection-Universe'", "SI_ID=15412")
```

### 3.5 Scan Failed Scheduled Instances (`SI_SCHEDULE_STATUS = 3`)
```sql
SELECT SI_ID, SI_NAME, SI_KIND, SI_PARENTID, SI_OWNER,
       SI_STARTTIME, SI_ENDTIME, SI_STATUSINFO, SI_SCHEDULEINFO
FROM CI_INFOOBJECTS
WHERE SI_INSTANCE = 1
  AND SI_SCHEDULE_STATUS = 3
  AND SI_STARTTIME >= '2026.11.05.18.00.00'
ORDER BY SI_STARTTIME DESC
```
