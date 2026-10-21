# Design Document: Agente di Diagnostica Intelligente per SAP BusinessObjects

## 1. Executive Summary

La gestione delle elaborazioni batch notturne e delle pubblicazioni massive multi-destinatario (bursting) all'interno della Central Management Console (CMC) costituisce un carico operativo rilevante per gli amministratori di SAP BusinessObjects. In presenza di centinaia o migliaia di istanze, i fallimenti presentano spesso messaggi nativi frammentati o generici (`SI_STATUSINFO`), ritardando l'individuazione della causa primaria (Root Cause Analysis).

L'**Agente di Diagnostica Intelligente** automatizza il monitoraggio sistemico e la diagnosi delle anomalie operando via protocollo FastMCP. Il sistema esegue scansioni mirate su `CI_INFOOBJECTS` tramite `POST /biprws/v1/cmsquery`, normalizza e clusterizza i fallimenti per "error signature", arricchisce il contesto e produce un report diagnostico programmatico basato su **Pydantic v2**. Per ciascun cluster di errore identificato, l'agente fornisce **fino a 3 cause graduate per verosimiglianza** con le relative **raccomandazioni operative passo-passo**.

---

## 2. Esito della Verifica Tecnica (RESTful vs Connessione Diretta DB)

- **Perché il DB CMS non può essere interrogato via SQL diretto:**  
  Il database relazionale del CMS (Oracle, SQL Server, HANA, ecc.) memorizza gli attributi estesi (`SI_SCHEDULEINFO`, prompt, destinazioni, log) in **BLOB binari compressi e proprietari** (tabelle `CMS_INFOOBJECTS5`/`7`). L'accesso SQL diretto restituirebbe dati illeggibili, non è supportato da SAP e rischia di causare lock critici sul repository.
- **Perché la suite RESTful (`biprws` + Raylight) è la soluzione nativa ed esaustiva:**  
  L'interfaccia `POST /biprws/v1/cmsquery` delega al CMS la decodifica in memoria dei BLOB, restituendo JSON pulito con `SI_SCHEDULE_STATUS = 3`, `SI_STATUSINFO`, `SI_STARTTIME`, `SI_ENDTIME`, `SI_OWNER`, prompt e parametri di schedulazione.
- **Verdetto:** L'integrazione avviene al **100% via RESTful Web Services** sfruttando la sessione WACS già supportata dal client MCP. Nessun connettore database fisico esterno è richiesto.

---

## 3. Decision Log

| # | Argomento | Decisione Adottata | Alternative Valutate | Rationale |
|---|---|---|---|---|
| **D1** | Modalità operativa | **Solo Diagnostica & Audit (Read-Only)** | Auto-healing autonomo; Assistito con remediation | Elimina ogni rischio operativo sul CMS di produzione, focalizzandosi su RCA dettagliata per l'amministratore. |
| **D2** | Canale di integrazione | **100% RESTful WACS (`POST /biprws/v1/cmsquery` + Raylight)** | Connettore SQL diretto su DB CMS; Java SDK | Le tabelle DB CMS usano BLOB proprietari illeggibili. `cmsquery` restituisce JSON strutturato nativo. |
| **D3** | Perimetro oggetti | **Entrambi: Report Webi e Pubblicazioni (Bursting)** | Solo Webi; Solo Pubblicazioni | Copertura completa dell'intero ciclo batch notturno aziendale. |
| **D4** | Scalabilità & Volume | **Paginazione con Pre-Processing & Clustering (Error Signature)** | Analisi sequenziale esaustiva; Campionamento TOP-N cieco | Previene l'esaurimento del contesto LLM e i timeout WACS aggregando i fallimenti con lo stesso errore. |
| **D5** | Struttura Diagnostica | **Ranking fino a 3 cause più probabili con soluzioni operative** | Causa singola forzata; Diagnosi discorsiva generica | Gli errori BO sono spesso polimorfi; un ranking a 3 livelli con punteggio di confidenza guida l'amministratore in modo pratico. |
| **D6** | Motore Programmatico | **Pydantic v2 Native Structured Outputs** | CrewAI; LangGraph | Zero dipendenze pesanti aggiuntive, 100% type-safe, latenza minima, assenza di allucinazioni sintattiche. |

---

## 4. Architettura & Componenti

```
┌────────────────────────────────────────────────────────┐
│                   LLM Client (Chat / CLI)              │
└───────────────────────────▲────────────────────────────┘
                            │ MCP Protocol (JSON-RPC)
┌───────────────────────────▼────────────────────────────┐
│              FastMCP Server (server.py)                │
│    Tool: diagnose_batch_failures(hours_back, kind,...) │
└───────────────────────────▲────────────────────────────┘
                            │ Internal Call
┌───────────────────────────▼────────────────────────────┐
│       DiagnosticService (services/diagnostic_service.py)│
│  - scan_failed_instances()                             │
│  - extract_error_signature() & cluster_failures()       │
│  - smart_enrichment() (prompts Webi & bursting pub)    │
│  - Pydantic v2 Models Validation                        │
└───────────────────────────▲────────────────────────────┘
                            │ HTTP (X-SAP-LogonToken)
┌───────────────────────────▼────────────────────────────┐
│      SAP BusinessObjects BI Platform 4.3 (WACS)        │
│  - POST /biprws/v1/cmsquery (CI_INFOOBJECTS)           │
│  - GET /biprws/raylight/v1/documents/{id}/parameters   │
│  - GET /biprws/v1/publications/{id}                    │
└────────────────────────────────────────────────────────┘
```

### Componenti Principali:
1. **`core/models.py` (Data Contracts Pydantic):**
   - `FailureCategory`: Enum con macro-categorie di fallimento.
   - `PotentialCause`: Modello per singola causa (`rank` 1..3, `probability_score`, `category`, `title`, `technical_explanation`, `recommended_actions`).
   - `ClusterDiagnosis`: Modello per cluster di errore (`cluster_id`, `error_signature`, `affected_count`, `top_causes` max 3).
   - `BatchDiagnosticsReport`: Modello di report aggregato (`scan_timestamp`, `hours_back`, `total_failed_instances`, `clusters`, `executive_summary`).
2. **`services/diagnostic_service.py`:**
   - Esegue la scansione a CMS con `SI_SCHEDULE_STATUS = 3`.
   - Normalizza i messaggi `SI_STATUSINFO` isolando codici d'errore (`WIS`, `ORA`, `CRS`, `FBE`) ed eliminando parametri volatili (timestamp, PID).
   - Raggruppa i fallimenti in cluster deduplicati.
   - Esegue l'arricchimento mirato dei prompt mancanti solo per i cluster correlati.
   - Restituisce l'oggetto `BatchDiagnosticsReport`.
3. **`server.py`:**
   - Espone il tool FastMCP `@mcp.tool() def diagnose_batch_failures(...)`.

---

## 5. Modello Dati Pydantic (Specifica)

```python
from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class FailureCategory(str, Enum):
    NETWORK_TIMEOUT = "Infrastruttura / Timeout Rete"
    AUTH_CREDENTIALS = "Credenziali / Autenticazione DB"
    MISSING_PROMPTS = "Prompt Obbligatori Mancanti"
    DB_LOCK_CONCURRENCY = "Lock Tabelle / Concorrenza DB"
    SERVER_RESOURCE_OOM = "Saturazione Risorse / Memoria WACS-APS"
    CACHE_CORRUPTED = "Corruzione Cache Data Provider"
    BURSTING_RECIPIENT = "Errore Destinatari Dinamici Pubblicazione"
    UNKNOWN_GENERIC = "Eccezione Non Classificata"


class PotentialCause(BaseModel):
    rank: int = Field(..., ge=1, le=3, description="Priorità decrescente (1..3)")
    probability_score: float = Field(..., ge=0.0, le=1.0, description="Confidenza stimata da 0.0 a 1.0")
    category: FailureCategory
    title: str = Field(..., description="Titolo sintetico della causa")
    technical_explanation: str = Field(..., description="Dettaglio tecnico correlato ai log/parametri")
    recommended_actions: List[str] = Field(..., description="Passi operativi guidati per la risoluzione")


class ClusterDiagnosis(BaseModel):
    cluster_id: str
    error_signature: str
    affected_count: int
    sample_instance_ids: List[str]
    sample_report_names: List[str]
    top_causes: List[PotentialCause] = Field(..., max_length=3)


class BatchDiagnosticsReport(BaseModel):
    scan_timestamp: str
    hours_back: int
    total_failed_instances: int
    clusters_count: int
    clusters: List[ClusterDiagnosis]
    executive_summary: str
```

---

## 6. Gestione Errori & Edge Cases

1. **Zero Failures (`Clean Batch Night`):** Ritorna `total_failed_instances = 0`, lista cluster vuota ed executive summary di conformità.
2. **Messaggi d'Errore Vuoti o Tronchi:** Fallback su `SI_ERROR_SEARCH_KEY` e calcolo durata istanza (`SI_ENDTIME - SI_STARTTIME`); classificazione come crash o interruzione anomala di processo.
3. **Oggetti Orfani:** Intercettazione dei 404 durante l'ispezione dei prompt di documenti cancellati post-fallimento.
4. **Volumi Massivi di Fallimenti:** Paginazione controllata e flag `is_truncated` nel report per evidenziare blackout sistemici globali senza saturare il server WACS.

---

## 7. Strategia di Test & Validazione

- **Unit Test Offline (`tests/test_diagnostic_service.py`):**
  - Normalizzazione regex su log SAP BO reali (`WIS 30553`, `ORA-00060`, `FBE60502`, timeout socket).
  - Clustering di 50+ istanze simulate in 3 cluster distinti.
  - Verifica della validazione Pydantic (max 3 cause per cluster, ranking 1..3, score compresi tra 0 e 1).
  - Test casi limite (zero fallimenti, `SI_STATUSINFO` assente, documento orfano).
- **Tool Test (`tests/test_server_tools.py`):**
  - Invocazione del tool MCP `diagnose_batch_failures` e verifica dello schema JSON in risposta.
- **CI/CD:** Esecuzione automatica in GitHub Actions con `pytest --cov` e linting `ruff`.
