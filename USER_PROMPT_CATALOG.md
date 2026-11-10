# SAP BusinessObjects MCP Server - Comprehensive User Query Catalog

A domain-driven reference catalog of questions, analytical prompts, and operational tasks that users, business analysts, BI developers, and platform administrators can ask the **SAP BusinessObjects MCP Server** (`bo-mcp`).

This catalog showcases the full potential of all **56 specialized tools**, ranging from semantic metadata inspection and Web Intelligence report manipulation to real-time `.glf` log streaming, native Auditing Database (`ADS_*`) queries, and autonomous root-cause analysis (RCA).

---

## Quick Navigation

1. [Semantic Layer & Universe Modeling (UNX / UNV)](#1-semantic-layer--universe-modeling-unx--unv)
2. [Web Intelligence Documents, Structure & Metadata](#2-web-intelligence-documents-structure--metadata)
3. [Data Providers, SQL Queries & Lineage](#3-data-providers-sql-queries--lineage)
4. [Data Provider Migration & Source Repointing](#4-data-provider-migration--source-repointing)
5. [Document Refresh, Prompts & Multi-Format Data Export](#5-document-refresh-prompts--multi-format-data-export)
6. [Report Elements & Tabular Block Data Extraction](#6-report-elements--tabular-block-data-extraction)
7. [Schedule Automation, Instances & Publications](#7-schedule-automation-instances--publications)
8. [Repository Organization: Folders & Categories (InfoStore)](#8-repository-organization-folders--categories-infostore)
9. [Enterprise CMS Security, Users & Active Sessions](#9-enterprise-cms-security-users--active-sessions)
10. [Autonomous Diagnostics & Triple-Source Batch RCA](#10-autonomous-diagnostics--triple-source-batch-rca)
11. [Live Server Trace Logs (.glf) & Real-Time Forensics](#11-live-server-trace-logs-glf--real-time-forensics)
12. [Auditing Database Telemetry (ADS_* Schema)](#12-auditing-database-telemetry-ads-schema)
13. [Server Health, Runtime Diagnostics & Self-Healing](#13-server-health-runtime-diagnostics--self-healing)

---

## 1. Semantic Layer & Universe Modeling (UNX / UNV)

> **Key Tools:** `get_universes`, `get_universe_details`, `get_universe_structure`, `get_universe_related_reports`, `get_universe_connection_id`

### What You Can Ask
Explore data models, inspect business classes, measures, and dimensions, verify relational database connections, and trace report dependencies.

#### Direct & Discovery Prompts
- 🇮🇹 *"Quali universi sono pubblicati nel repository? Elenca ID, nome e cartella di appartenenza."*
  🇬🇧 *"List all available universes in the repository with their IDs, names, and folder locations."*
- 🇮🇹 *"Mostrami i dettagli dell'universo 'eFashion.unx' (ID 5508): è un formato UNX o UNV legacy?"*
  🇬🇧 *"Show me details for universe 'eFashion.unx' (ID 5508): is it UNX or legacy UNV?"*

#### Data Modeling & Structure Prompts
- 🇮🇹 *"Estrai la struttura completa dell'universo 'BI Platform Audit Analysis.unx': quali classi, cartelle e oggetti (misure, dimensioni) contiene?"*
  🇬🇧 *"Retrieve the complete object hierarchy for universe 'BI Platform Audit Analysis.unx': list all folders, classes, dimensions, and measures."*
- 🇮🇹 *"Nell'universo 'dvdrental.unx', quali sono tutte le misure relative a pagamenti e fatturato?"*
  🇬🇧 *"Within the 'dvdrental.unx' universe, what are all the measures related to payments and revenue?"*

#### Impact Analysis & Lineage Prompts
- 🇮🇹 *"Dobbiamo modificare una colonna nella tabella dell'universo 5508: quali report Web Intelligence dipendono da questo universo e potrebbero rompersi?"*
  🇬🇧 *"We plan to alter a table column in universe 5508: which Web Intelligence reports depend on this universe and would be impacted?"*
- 🇮🇹 *"Qual è l'ID della connessione relazionale associata all'universo 'mssql_test.unx'?"*
  🇬🇧 *"What is the relational connection ID bound to universe 'mssql_test.unx'?"*

> [!NOTE]
> In SAP BusinessObjects 4.x, relational connections (`.cnx` / `.cns`) must always be tested via the **Information Design Tool (IDT)** or Universe Design Tool (UDT), as the CMC does not provide a connection test interface.

---

## 2. Web Intelligence Documents, Structure & Metadata

> **Key Tools:** `get_documents`, `get_webi_docs`, `get_doc_details`, `get_doc_properties`, `save_webi_doc`, `delete_webi_doc`, `get_variables`, `get_comments`

### What You Can Ask
Inspect document metadata, explore report tabs, view calculation formulas, audit user annotations, and manage document lifecycles.

#### Catalog & Discovery Prompts
- 🇮🇹 *"Cerca tutti i documenti Web Intelligence che contengono la parola 'Vendite' o 'Sales' nel titolo."*
  🇬🇧 *"Search for all Web Intelligence documents containing 'Sales' or 'Vendite' in their title."*
- 🇮🇹 *"Mostrami le proprietà di base e la data di ultimo salvataggio del documento con ID 14820."*
  🇬🇧 *"Show me the general properties and last save date of WebI document ID 14820."*

#### Formula & Calculation Auditing
- 🇮🇹 *"Quali variabili e formule di calcolo personalizzate sono definite nel documento 14820? Mostrami le formule esatte."*
  🇬🇧 *"What custom variables and calculation formulas exist in document 14820? Display their exact syntax."*
- 🇮🇹 *"Ci sono commenti o annotazioni inserite dagli utenti nelle sezioni del documento 14820?"*
  🇬🇧 *"Are there user comments or collaborative notes attached to document 14820?"*

#### Document Lifecycle & Management
- 🇮🇹 *"Salva le modifiche apportate al documento 14820 sovrascrivendo la copia corrente."*
  🇬🇧 *"Save the modifications made to document 14820 in place."*
- 🇮🇹 *"Salva una copia del documento 14820 con il nuovo nome 'Budget 2026 - Versione Finale' nella cartella ID 576."*
  🇬🇧 *"Save a copy of document 14820 as 'Budget 2026 - Versione Finale' inside folder ID 576."*
- 🇮🇹 *"Elimina il report temporaneo di test con ID 99120 dal repository."*
  🇬🇧 *"Delete the temporary test report with ID 99120 from the repository."*

---

## 3. Data Providers, SQL Queries & Lineage

> **Key Tools:** `get_dp`, `get_dp_details`, `get_dp_sql`, `get_dp_specification`, `refresh_dp`, `purge_dp`

### What You Can Ask
Inspect the data providers feeding a report, extract exact generated SQL queries for database optimization, view raw XML query specifications, and selectively refresh or purge individual query caches.

#### SQL Extraction & Query Auditing
- 🇮🇹 *"Quali data provider alimentano il documento 14820? Elenca nome, tipo sorgente e numero di righe caricate."*
  🇬🇧 *"Which data providers feed document 14820? List their names, source types, and row counts."*
- 🇮🇹 *"Estrai la query SQL nativa generata dal data provider 'DP0' del documento 14820. Voglio analizzarla con il DBA per ottimizzare gli indici del database."*
  🇬🇧 *"Extract the native generated SQL query for data provider 'DP0' in document 14820 so our DBA can review indexing."*
- 🇮🇹 *"Mostrami la specifica XML completa del query panel (filtri, condizioni combinatorie) del data provider 'Vendite'."*
  🇬🇧 *"Show me the full XML query specification (filters, combined query conditions) for data provider 'Vendite'."*

#### Granular Cache Management
- 🇮🇹 *"Svuota la cache (purge) del solo data provider 'Storico Anni Precedenti' nel documento 14820 per ridurre le dimensioni del file."*
  🇬🇧 *"Purge data for only the 'Storico Anni Precedenti' data provider in document 14820 to reduce file size."*
- 🇮🇹 *"Aggiorna (refresh) esclusivamente il data provider 'Dati Oggi' senza ricaricare l'intero documento."*
  🇬🇧 *"Refresh only the 'Dati Oggi' data provider without refreshing the rest of the document."*

---

## 4. Data Provider Migration & Source Repointing

> **Key Tools:** `get_dp_mapping_proposal`, `change_dp_datasource`

### What You Can Ask
Automate the migration of legacy `.unv` universes to modern `.unx`, remap query objects between development and production universes, and validate candidate object mappings before applying changes.

#### Pre-Flight Mapping Analysis
- 🇮🇹 *"Stiamo dismettendo il vecchio universo UNV 5508 per passare al nuovo UNX 55037 nel documento 14820: proponi il mapping automatico degli oggetti e dimmi se ci sono colonne orfane o ambigue."*
  🇬🇧 *"We are migrating from legacy UNV 5508 to modern UNX 55037 in document 14820: generate the proposed object mapping and highlight any orphan or ambiguous fields."*
- 🇮🇹 *"Verifica se tutti gli oggetti della query 'Fatturato Mensile' trovano una corrispondenza esatta nel nuovo universo di destinazione."*
  🇬🇧 *"Verify whether all query objects in 'Fatturato Mensile' have exact matches in the target universe."*

#### Executing Source Repointing
- 🇮🇹 *"Applica il cambio sorgente dati sul data provider 'DP0' puntando all'universo UNX 55037 con il mapping standard approvato."*
  🇬🇧 *"Apply the datasource change on data provider 'DP0' repointing to UNX universe 55037 using the approved standard mapping."*
- 🇮🇹 *"Esegui il repointing del data provider specificando un mapping personalizzato per mappare l'oggetto vecchio 'Totale_Netto' sul nuovo oggetto 'Valore_Vendite_Netto'."*
  🇬🇧 *"Execute the datasource repointing with custom mapping, binding legacy object 'Totale_Netto' to new object 'Valore_Vendite_Netto'."*

---

## 5. Document Refresh, Prompts & Multi-Format Data Export

> **Key Tools:** `get_doc_parameters`, `get_parameter_lov`, `refresh_webi_doc`, `export_webi_doc`

### What You Can Ask
Inspect runtime parameters (prompts/filtri obbligatori), query Lists of Values (LOV), refresh documents with dynamic answers, and export complete reports or individual tabs to PDF, Excel (XLSX), or CSV.

#### Prompt Introspection & LOV Queries
- 🇮🇹 *"Il documento 14820 richiede parametri obbligatori o opzionali prima del refresh? Mostrami tipo dato, prompt text e valori di default."*
  🇬🇧 *"Does document 14820 require mandatory or optional prompts before refreshing? Show parameter names, types, and defaults."*
- 🇮🇹 *"Quali sono i valori consentiti (List of Values) per il parametro 'Seleziona Regione' del documento 14820?"*
  🇬🇧 *"What is the List of Values (LOV) for the 'Seleziona Regione' prompt in document 14820?"*

#### Parameterized Execution & Document Refresh
- 🇮🇹 *"Esegui il refresh completo del documento 14820 rispondendo ai prompt con Anno='2026' e Regione='EMEA'."*
  🇬🇧 *"Execute a full refresh of document 14820 answering prompts with Year='2026' and Region='EMEA'."*

#### Multi-Format Export
- 🇮🇹 *"Aggiorna il report 14820 ed esportalo immediatamente in formato PDF sul mio client locale."*
  🇬🇧 *"Refresh report 14820 and export it immediately as a PDF file to my local machine."*
- 🇮🇹 *"Esporta il tab 'Dettaglio Transazioni' del documento 14820 in formato Microsoft Excel (.xlsx)."*
  🇬🇧 *"Export the 'Dettaglio Transazioni' tab of document 14820 into Microsoft Excel (.xlsx) format."*
- 🇮🇹 *"Estrai i dati del documento 14820 in formato CSV pulito per alimentarli in una pipeline di machine learning o pandas."*
  🇬🇧 *"Export data from document 14820 as a clean CSV file for downstream processing in pandas or machine learning pipelines."*

---

## 6. Report Elements & Tabular Block Data Extraction

> **Key Tools:** `get_reports`, `get_report_elements`, `get_report_element_data`

### What You Can Ask
Inspect the visual structure of report tabs (tables, charts, sections, forms), identify table blocks, and extract formatted tabular data directly into JSON for analytical processing.

#### Visual Layout Discovery
- 🇮🇹 *"Quali schede/tab compongono il documento 14820? Mostrami ID e nome di ciascun report."*
  🇬🇧 *"What report tabs exist inside document 14820? List their IDs and display names."*
- 🇮🇹 *"Nel report 'Dashboard Vendite' (ID 1), quali elementi grafici e tabelle sono presenti? Identifica l'ID del blocco tabella principale."*
  🇬🇧 *"In report tab 'Dashboard Vendite' (ID 1), what visual elements and tables are configured? Identify the block ID of the primary table."*

#### Data Extraction from Visual Tables
- 🇮🇹 *"Estrai i dati della tabella 'Top Clienti' (blocco ID 5) del documento 14820 come tabella strutturata con colonne e valori numerici."*
  🇬🇧 *"Extract the tabular data from block ID 5 ('Top Clienti') in document 14820 as structured column/row JSON."*
- 🇮🇹 *"Mostrami le prime 20 righe della matrice di fatturato per canale contenuta nel blocco 12."*
  🇬🇧 *"Show me the first 20 rows of the revenue-by-channel matrix located in block 12."*

---

## 7. Schedule Automation, Instances & Publications

> **Key Tools:** `get_doc_schedules`, `get_doc_instances`, `get_instance_details`, `delete_instance`

### What You Can Ask
Audit recurring schedule definitions, review nocturnal batch history, check execution runtimes, identify failed instances, and perform cleanup of obsolete instance outputs.

#### Schedule Audit & Recurrence Rules
- 🇮🇹 *"Quali schedulazioni automatiche o ricorrenti sono attive per il documento 14820? A che ora girano e con quale frequenza?"*
  🇬🇧 *"What recurring schedule rules are configured for document 14820? When do they trigger and with what cadence?"*
- 🇮🇹 *"Chi è il proprietario della schedulazione del report mensile e quale destinazione di consegna (email, cartella, FTP) è impostata?"*
  🇬🇧 *"Who owns the recurring schedule for the monthly report, and what delivery destination (email, inbox, FTP) is configured?"*

#### Instance History & Failure Analysis
- 🇮🇹 *"Mostrami la cronologia delle ultime 10 istanze generate per il documento 14820. Ci sono esecuzioni fallite?"*
  🇬🇧 *"Show the history of the last 10 generated instances for document 14820. Are there any failed runs?"*
- 🇮🇹 *"L'istanza con ID 78430 è fallita: estrai i dettagli completi, il codice di errore CMS e l'ora di inizio/fine."*
  🇬🇧 *"Instance ID 78430 failed: retrieve its detailed execution status, CMS error string, and start/finish timestamps."*

#### Repository Housekeeping
- 🇮🇹 *"Elimina dal repository le vecchie istanze storiche fallite del 2025 relative al documento 14820."*
  🇬🇧 *"Delete obsolete failed 2025 instances belonging to document 14820 from the repository."*

---

## 8. Repository Organization: Folders & Categories (InfoStore)

> **Key Tools:** `get_folders`, `get_folder_details`, `create_folder`, `delete_folder`, `get_categories`

### What You Can Ask
Navigate the corporate folder hierarchy, search document categories, create structured directory trees for new business units, and clean up empty directories.

#### Folder Navigation & Tree Inspection
- 🇮🇹 *"Mostrami l'albero delle cartelle a partire dalla radice del repository (Root Folder)."*
  🇬🇧 *"Display the folder hierarchy starting from the repository Root Folder."*
- 🇮🇹 *"Quali cartelle e sottocartelle si trovano all'interno della directory 'Amministrazione e Finanza' (ID 576)?"*
  🇬🇧 *"What subfolders are located inside folder ID 576 ('Amministrazione e Finanza')?"*
- 🇮🇹 *"Quali categorie aziendali (Corporate Categories / Personal Categories) sono configurate nella piattaforma?"*
  🇬🇧 *"What corporate and personal categories are defined in the platform?"*

#### Directory Provisioning & Lifecycle
- 🇮🇹 *"Crea una nuova sottocartella denominata 'Report Trimestrali 2026' all'interno della cartella ID 576 con descrizione 'Reportistica chiusure trimestrali'."*
  🇬🇧 *"Create a new subfolder named 'Report Trimestrali 2026' under parent folder ID 576 with a descriptive note."*
- 🇮🇹 *"Elimina la cartella di staging temporanea con ID 89012."*
  🇬🇧 *"Delete the temporary staging folder ID 89012."*

---

## 9. Enterprise CMS Security, Users & Active Sessions

> **Key Tools:** `cms_query`, `get_users`, `get_user_details`, `set_user_status`, `get_user_groups`, `get_group_users`, `get_active_sessions`, `terminate_session`, `login`, `logout`

### What You Can Ask
Inspect enterprise accounts, audit group memberships, monitor active user sessions, terminate orphaned connections, and run advanced CMS SQL queries against the system database.

#### User & Group Governance
- 🇮🇹 *"Elenca tutti gli utenti registrati sul cluster SAP BusinessObjects. Chi ha effettuato l'accesso di recente?"*
  🇬🇧 *"List all user accounts registered in SAP BusinessObjects. Who logged in recently?"*
- 🇮🇹 *"Quali sono i dettagli dell'account 'aballarin'? A quali gruppi di sicurezza appartiene e qual è il suo indirizzo email?"*
  🇬🇧 *"Show profile details for user 'aballarin': which security groups does he belong to and what is his registered email?"*
- 🇮🇹 *"Quali utenti sono membri del gruppo 'Administrators' o 'BO_PowerUsers'?"*
  🇬🇧 *"Which users are members of the 'Administrators' or 'BO_PowerUsers' group?"*
- 🇮🇹 *"Disabilita temporaneamente l'account 'utente_consulente' per motivi di sicurezza durante la finestra di manutenzione."*
  🇬🇧 *"Temporarily disable account 'utente_consulente' for maintenance window security."*
- 🇮🇹 *"Riabilita l'account 'utente_consulente'."*
  🇬🇧 *"Re-enable account 'utente_consulente'."*

#### Session Concurrency & Auditing
- 🇮🇹 *"Quante sessioni utente sono attualmente attive sul cluster CMS? Mostrami username, orario di logon e client di origine."*
  🇬🇧 *"How many user sessions are currently active on the CMS cluster? Show username, logon time, and client origin."*
- 🇮🇹 *"Termina la sessione orfana o bloccata con ID 'AQiJ3r.A90NImlq...' per liberare una licenza nominale o concorrente."*
  🇬🇧 *"Terminate orphaned session ID 'AQiJ3r.A90NImlq...' to release a concurrent license."*

#### Custom CMS Repository Queries
- 🇮🇹 *"Esegui una query CMS per trovare tutti i documenti Web Intelligence creati dall'utente 'Administrator' dopo il primo gennaio 2026: `SELECT SI_ID, SI_NAME, SI_UPDATE_TS FROM CI_INFOOBJECTS WHERE SI_KIND = 'Webi' AND SI_OWNER = 'Administrator'`"*
  🇬🇧 *"Run a CMS query to locate all WebI documents owned by 'Administrator' updated after Jan 1st 2026: `SELECT SI_ID, SI_NAME, SI_UPDATE_TS FROM CI_INFOOBJECTS WHERE SI_KIND = 'Webi' AND SI_OWNER = 'Administrator'`"*
- 🇮🇹 *"Esegui una query CMS per contare quante pubblicazioni (Publication) sono censite nel repository: `SELECT COUNT(SI_ID) FROM CI_INFOOBJECTS WHERE SI_KIND = 'Publication'`"*
  🇬🇧 *"Run a CMS query counting how many publications exist in the repository: `SELECT COUNT(SI_ID) FROM CI_INFOOBJECTS WHERE SI_KIND = 'Publication'`"*

---

## 10. Autonomous Diagnostics & Triple-Source Batch RCA

> **Key Tool:** `diagnose_batch_failures`

### What You Can Ask
Launch an end-to-end, multi-source root-cause analysis (RCA) that automatically links failed schedule instances (`SI_SCHEDULE_STATUS = 3`), parses matching `.glf` server trace log errors, and correlates Auditing Database failure telemetry.

#### Batch Health & Failure Clustering Prompts
- 🇮🇹 *"Diagnostica i fallimenti delle schedulazioni notturne nelle ultime 24 ore: quali report sono falliti, come sono raggruppati per errore e cosa raccomandi di fare per ripristinarli?"*
  🇬🇧 *"Diagnose nocturnal batch failures over the past 24 hours: which reports failed, how are they clustered by error signature, and what remediation steps do you recommend?"*
- 🇮🇹 *"Analizza le schedulazioni fallite nelle ultime 48 ore limitando la ricerca ai soli documenti nella cartella 'Chiusura_Mese' (ID 5511)."*
  🇬🇧 *"Analyze failed schedules over the last 48 hours restricted to folder 'Chiusura_Mese' (ID 5511)."*
- 🇮🇹 *"Fornisci un executive summary sintetico sullo stato dei batch notturni: c'è stato qualche disservizio generale (ad es. database sorgente non raggiungibile, CMS down o password scaduta)?"*
  🇬🇧 *"Provide an executive summary on nocturnal batch health: did any systemic outage occur (e.g., source DB unreachable, CMS down, or expired service credentials)?"*

---

## 11. Live Server Trace Logs (.glf) & Real-Time Forensics

> **Key Tools:** `list_bo_logs`, `search_bo_logs`, `get_bo_log_context`

### What You Can Ask
Inspect physical server trace logs (`.glf`, `.log`, `.trc`) on the SAP BusinessObjects host in real time, stream backwards to find the newest errors without loading multi-gigabyte files into memory, and retrieve surrounding stack traces.

#### Log Discovery & File Tracking
- 🇮🇹 *"Quali file di traccia .glf sono stati generati o modificati nelle ultime 6 ore nella directory di log di SAP BO? Elencali per server component."*
  🇬🇧 *"What .glf trace files were created or modified in the last 6 hours inside the SAP BO log directory? Group them by server component."*
- 🇮🇹 *"Mostrami i file di log più recenti relativi al solo componente 'WebIntelligenceProcessingServer' o 'AdaptiveProcessingServer'."*
  🇬🇧 *"Show me the most recent log files belonging specifically to 'WebIntelligenceProcessingServer' or 'AdaptiveProcessingServer'."*

#### Fast Reverse Pattern Searching
- 🇮🇹 *"Cerca nei log di traccia delle ultime 4 ore la presenza dell'errore 'WIS 30553' o 'IES 10901'. Quante occorrenze ci sono e su quali server?"*
  🇬🇧 *"Search recent trace logs (last 4 hours) for error code 'WIS 30553' or 'IES 10901'. How many occurrences exist and on which servers?"*
- 🇮🇹 *"Cerca nel log dell'AdaptiveJobServer eventuali errori di timeout di connessione al database (es. 'ORA-01017' o 'Connection refused')."*
  🇬🇧 *"Scan AdaptiveJobServer logs for database connection timeouts (e.g., 'ORA-01017' or 'Connection refused')."*

#### Stack Trace & Context Extraction
- 🇮🇹 *"Nel file 'aps_orarhel01.AdaptiveProcessingServer_trace.001623.glf', estrai il contesto attorno alla riga 62142 (20 righe prima e 20 dopo) per analizzare la stack trace Java dell'eccezione."*
  🇬🇧 *"In file 'aps_orarhel01.AdaptiveProcessingServer_trace.001623.glf', extract the context surrounding line 62142 (20 lines before/after) to analyze the full Java exception stack trace."*
- 🇮🇹 *"Estrai l'header completo di configurazione e tracciamento (COLUMNS / SEVERITY_MAP) del file trace attivo di WebI."*
  🇬🇧 *"Extract the metadata header (COLUMNS / SEVERITY_MAP) from the active WebI trace file."*

---

## 12. Auditing Database Telemetry (ADS_* Schema)

> **Key Tools:** `get_audit_failed_events`, `get_audit_heavy_reports`, `get_audit_user_activity`, `query_audit_db`

### What You Can Ask
Directly query the SAP BusinessObjects Auditing Database via ODBC (`pyodbc` in an isolated child process) to detect system failures, identify slow reports, audit user actions, and run custom read-only ANSI SQL queries with strict safety guardrails.

#### Failed Platform Events & Login Audits
- 🇮🇹 *"Quali eventi di errore o fallimento sono stati registrati nel database di auditing nelle ultime 24 ore? Mostrami utente, tipo evento (Logon, Refresh, Export) e messaggio di errore."*
  🇬🇧 *"What failure events were logged in the Auditing Database over the last 24 hours? Display username, event type (Logon, Refresh, Export), and error description."*
- 🇮🇹 *"Ci sono stati tentativi di accesso falliti (Logon Failed) da parte di utenti o servizi nelle ultime 48 ore?"*
  🇬🇧 *"Were there any failed logon attempts recorded in the Auditing DB over the past 48 hours?"*

#### Heavy & Slow Report Telemetry
- 🇮🇹 *"Quali sono i 10 report più lenti e pesanti eseguiti nell'ultima settimana? Mostrami nome documento, numero totale di esecuzioni, durata massima e durata media in millisecondi."*
  🇬🇧 *"What are the top 10 slowest and heaviest reports executed in the past week? Display document name, execution count, max duration, and average duration in milliseconds."*
- 🇮🇹 *"Identifica i report la cui durata media supera i 60 secondi nell'ultimo mese per valutare un piano di ottimizzazione query o schedulazione notturna."*
  🇬🇧 *"Identify all reports averaging more than 60 seconds of execution duration over the last month."*

#### User Action Tracking
- 🇮🇹 *"Cosa ha fatto l'utente 'Administrator' o 'alessio' sulla piattaforma nelle ultime 24 ore? Mostrami tutti gli eventi di apertura, refresh, salvataggio ed esportazione."*
  🇬🇧 *"What activities did user 'Administrator' or 'alessio' perform on the platform in the last 24 hours? List all view, refresh, save, and export events."*

#### Custom Read-Only SQL Queries
- 🇮🇹 *"Esegui una query SQL di conteggio sul database di audit per verificare quanti eventi totali sono censiti in `ADS_EVENT`: `SELECT COUNT(*) AS totale FROM ADS_EVENT`"*
  🇬🇧 *"Run a count query on the Auditing DB to check how many events are stored in `ADS_EVENT`: `SELECT COUNT(*) AS totale FROM ADS_EVENT`"*
- 🇮🇹 *"Raggruppa gli eventi dell'ultima settimana per tipo operazione (con decodifica nome in lingua inglese) ed ordina per volume decrescente: `SELECT et.Event_Type_Name, COUNT(*) AS Vol FROM ADS_EVENT e LEFT JOIN ADS_EVENT_TYPE_STR et ON et.Event_Type_ID = e.Event_Type_ID AND et.Language = 'EN' GROUP BY et.Event_Type_Name ORDER BY Vol DESC`"*
  🇬🇧 *"Group audit events from the past week by event type name (English) ordered by descending volume."*

---

## 13. Server Health, Runtime Diagnostics & Self-Healing

> **Key Tools:** `get_mcp_server_diagnostics`

### What You Can Ask
Run comprehensive self-diagnostics across all local and remote subsystems (REST API reachability, physical log folder access, ODBC driver & Auditing DB connection, process memory, active session isolation), and view recent internal server logs.

#### Runtime Health & Subsystem Probing
- 🇮🇹 *"Esegui la diagnostica completa di salute del server MCP e mostrami lo stato di tutti i sottosistemi (REST API, Log Directory, Database di Auditing)."*
  🇬🇧 *"Run comprehensive server diagnostics and show the operational status of all subsystems (REST API, Log directory, Auditing DB)."*
- 🇮🇹 *"Qual è la latenza di rete rilevata verso la REST API (`biprws`) e verso il database ODBC di auditing?"*
  🇬🇧 *"What network latency is measured towards the REST API (`biprws`) and towards the Auditing ODBC database?"*
- 🇮🇹 *"Verifica se il processo MCP sta girando in modalità remota o stdio locale, quale utente di sistema lo esegue e quanta memoria sta consumando."*
  🇬🇧 *"Check whether the MCP server is operating in remote or local stdio mode, which OS user is running it, and its current memory usage."*

#### Internal Log Ring-Buffer Inspection
- 🇮🇹 *"Mostrami gli ultimi 20 log interni generati dal server MCP per verificare se ci sono avvisi o eccezioni non gestite."*
  🇬🇧 *"Show the last 20 internal log entries from the MCP server ring buffer to inspect recent warnings or unhandled exceptions."*

---

## 14. Advanced Cross-Domain Composite Workflows

These complex workflows combine multiple tools in an intelligent sequence to solve real-world BI operational challenges in a single conversational request.

### Scenario A: The Emergency Morning Batch Incident
> **Prompt:**  
> 🇮🇹 *"Controlla se i batch della notte sono andati a buon fine. Se ci sono fallimenti, dimmi quali report sono impattati, estrai le righe di errore corrispondenti dai log `.glf` del server, verifica se nell'Audit DB c'è traccia di disconnessioni del database, e indicami la causa principale con i passi per risolverla."*  
> 🇬🇧 *"Check if nocturnal batch runs completed successfully. If failures occurred, identify impacted reports, extract matching error lines from server `.glf` logs, verify whether the Auditing DB recorded database disconnects, and provide the root cause with remediation steps."*
>
> **Behind the scenes:** Calls `diagnose_batch_failures` $\rightarrow$ `search_bo_logs` $\rightarrow$ `get_bo_log_context` $\rightarrow$ `get_audit_failed_events`.

---

### Scenario B: The Performance Bottleneck Review
> **Prompt:**  
> 🇮🇹 *"Trova i 3 report Web Intelligence più lenti dell'ultima settimana dall'Auditing DB. Per ciascuno di essi, estrai la query SQL generata dal relativo data provider, verifica l'universo utilizzato e controlla quante istanze sono attualmente pianificate."*  
> 🇬🇧 *"Identify the top 3 slowest WebI reports from the past week using the Auditing DB. For each, extract the native generated SQL from its data provider, verify the underlying universe, and inspect active schedules."*
>
> **Behind the scenes:** Calls `get_audit_heavy_reports` $\rightarrow$ `get_dp` $\rightarrow$ `get_dp_sql` $\rightarrow$ `get_universe_details` $\rightarrow$ `get_doc_schedules`.

---

### Scenario C: Safe Universe Migration Pipeline
> **Prompt:**  
> 🇮🇹 *"Dobbiamo migrare il report 14820 dal vecchio universo UNV 5508 al nuovo UNX 55037. Prima analizza l'impatto proponendo il mapping automatico degli oggetti; se non ci sono colonne non mappate, esegui il repointing del data provider, ricarica il documento e mandami una notifica con il nuovo stato."*  
> 🇬🇧 *"We need to migrate report 14820 from UNV 5508 to UNX 55037. First perform impact analysis with proposed object mapping; if all columns match cleanly, execute the datasource repointing, refresh the document, and confirm status."*
>
> **Behind the scenes:** Calls `get_dp_mapping_proposal` $\rightarrow$ `change_dp_datasource` $\rightarrow$ `refresh_webi_doc` $\rightarrow$ `save_webi_doc`.

---

### Scenario D: Enterprise User Offboarding & Cleanup
> **Prompt:**  
> 🇮🇹 *"L'utente 'consulente_esterno' ha terminato il contratto: controlla quali sessioni attive ha sul CMS e chiudile, disabilita il suo account utente, e verifica quali documenti WebI o schedulazioni erano di sua proprietà nel repository."*  
> 🇬🇧 *"User 'consulente_esterno' has left: inspect his active CMS sessions and terminate them, disable his account, and audit all WebI documents or schedules owned by him in the repository."*
>
> **Behind the scenes:** Calls `get_active_sessions` $\rightarrow$ `terminate_session` $\rightarrow$ `set_user_status` $\rightarrow$ `cms_query`.
