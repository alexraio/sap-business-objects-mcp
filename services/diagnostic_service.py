"""
Diagnostic Service for SAP BusinessObjects 4.3 SP5.
Provides intelligent batch monitoring, error signature extraction, failure clustering,
and automated multi-cause root cause analysis (RCA) with Pydantic v2 structured contracts.
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.client import BOEClient
from core.models import (
    BatchDiagnosticsReport,
    ClusterDiagnosis,
    FailureCategory,
    PotentialCause,
)

logger = logging.getLogger("DiagnosticService")


class DiagnosticService:
    """Service to scan, cluster, and intelligently diagnose failed batch schedules and publications."""

    def __init__(self, client: BOEClient):
        self.client = client

    # =========================================================================
    # 1. Scanning CMS Repository for Failures
    # =========================================================================

    def scan_failed_instances(
        self,
        hours_back: int = 12,
        kind: str = "All",
        folder_id: Optional[str] = None,
        max_instances: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Interrogates CI_INFOOBJECTS via biprws cmsquery to detect failed batch instances
        (SI_INSTANCE = 1 AND SI_SCHEDULE_STATUS = 3) executed in the given time window.
        """
        cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")

        where_clauses = [
            "SI_INSTANCE = 1",
            "SI_SCHEDULE_STATUS = 3",
            f"SI_STARTTIME >= '{cutoff_str}'",
        ]

        normalized_kind = kind.strip().lower()
        if normalized_kind == "webi":
            where_clauses.append("SI_KIND = 'Webi'")
        elif normalized_kind == "publication":
            where_clauses.append("SI_KIND = 'Publication'")

        if folder_id:
            where_clauses.append(f"SI_PARENTID = {folder_id}")

        where_expr = " AND ".join(where_clauses)
        query = (
            f"SELECT TOP {max_instances} SI_ID, SI_NAME, SI_KIND, SI_PARENTID, SI_STARTTIME, SI_ENDTIME, "
            f"SI_OWNER, SI_STATUSINFO, SI_ERROR_SEARCH_KEY, SI_SCHEDULEINFO "
            f"FROM CI_INFOOBJECTS WHERE {where_expr} ORDER BY SI_STARTTIME DESC"
        )

        url = f"{self.client.query_url}/cmsquery?page=1&pagesize={max_instances}"
        try:
            resp = self.client.post(url, json_data={"query": query})
            if isinstance(resp, dict) and "entries" in resp:
                return resp["entries"]
            return []
        except Exception as e:
            logger.error("Failed to execute CMS scan query: %s", str(e))
            return []

    # =========================================================================
    # 2. Error Normalization and Signature Extraction
    # =========================================================================

    def extract_error_signature(
        self,
        status_info: Optional[Any],
        search_key: Optional[str] = None,
    ) -> str:
        """
        Normalizes variable error messages into a deterministic signature by stripping
        volatile elements (timestamps, PIDs, IP addresses, object IDs) and extracting
        standard SAP/DB failure codes (WIS, ORA, FBE, CRS, SocketTimeout, etc.).
        Handles both string messages and CMS dictionary structures (e.g. SI_RESOURCEID).
        """
        if isinstance(status_info, dict):
            if "SI_RESOURCEID" in status_info:
                raw_msg = f"SI_RESOURCEID_{status_info['SI_RESOURCEID']}"
            elif not status_info:
                raw_msg = ""
            else:
                raw_msg = " ".join(str(v) for v in status_info.values() if v)
        else:
            raw_msg = str(status_info or "").strip()
            if raw_msg in ("{}", "None", "null"):
                raw_msg = ""

        raw_key = str(search_key or "").strip()

        if not raw_msg and not raw_key:
            return "UNKNOWN_ABRUPT_SERVER_TERMINATION: SI_STATUSINFO vuoto (possibile crash di processo o stop nodo)"

        text = f"{raw_key} {raw_msg}".strip()

        # Check for specific signature patterns
        # 1. Oracle Deadlock / DB lock
        if re.search(r"(ORA-00060|deadlock|lock request time out|database lock)", text, re.IGNORECASE):
            return "DB_LOCK_DEADLOCK: Rilevato blocco transazionale o deadlock sul database sorgente (es. ORA-00060)"

        # 2. Oracle / Database Authentication failure
        if re.search(r"(ORA-01017|invalid username/password|logon denied|authentication failed)", text, re.IGNORECASE):
            return (
                "DB_AUTH_FAILURE: Credenziali di accesso o autenticazione al database non valide o scadute (ORA-01017)"
            )

        # 3. Connection / Network Timeout
        if re.search(
            r"(Connection refused|timed out|SocketTimeout|Communications link failure|UnknownHostException|Network is unreachable)",
            text,
            re.IGNORECASE,
        ):
            return "NETWORK_TIMEOUT: Connessione di rete o socket timeout verso il database o servizio esterno"

        # 4. WIS Specific Codes
        wis_match = re.search(r"(WIS\s*\d+)", text, re.IGNORECASE)
        if wis_match:
            wis_code = wis_match.group(1).upper()
            if "30553" in wis_code:
                return f"{wis_code}: Errore di elaborazione Data Provider / Cache (processDPCommandsEx)"
            if "30270" in wis_code or "30271" in wis_code:
                return f"{wis_code}: Valore prompt o parametro mancante / non valido"
            return f"{wis_code}: Errore del motore Web Intelligence"

        # 5. Publication / Bursting Codes
        fbe_match = re.search(r"(FBE\s*\d+|CRS\s*\d+)", text, re.IGNORECASE)
        if fbe_match:
            code = fbe_match.group(1).upper()
            return f"{code}: Errore del motore di Pubblicazione / Distribuzione Bursting (Publishing Service)"

        # 6. Out of Memory / Server Resource
        if re.search(r"(OutOfMemory|Java heap space|GC overhead limit)", text, re.IGNORECASE):
            return "SERVER_OOM: Esaurimento memoria heap Java del server di elaborazione (Adaptive Processing Server / WACS)"

        # 7. Fallback: normalize generic string by stripping numbers, timestamps and IPs
        clean = re.sub(r"\d{4}[-/.]\d{2}[-/.]\d{2}", "", text)  # remove dates
        clean = re.sub(r"\d{2}:\d{2}:\d{2}", "", clean)  # remove times
        clean = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "IP_ADDR", clean)  # remove IPs
        clean = re.sub(r"0x[0-9a-fA-F]+", "HEX_ADDR", clean)  # remove hex
        clean = re.sub(r"\b\d{5,}\b", "ID_NUM", clean)  # remove large IDs
        clean = " ".join(clean.split())  # normalize whitespaces
        return clean[:120] if clean else "GENERIC_EXECUTION_FAILURE"

    def _generate_cluster_id(self, signature: str) -> str:
        """Generates a short deterministic hash for the cluster ID."""
        return "cluster-" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:8]

    # =========================================================================
    # 3. Multi-Cause Ranking Engine
    # =========================================================================

    def classify_and_rank_causes(
        self,
        error_signature: str,
        sample_status_info: str,
        missing_prompts: Optional[List[str]] = None,
    ) -> List[PotentialCause]:
        """
        Evaluates the error signature, status info, and contextual cues to assign
        up to 3 ranked probable root causes with confidence scores and actionable remediation steps.
        """
        sig_upper = error_signature.upper()
        info_upper = sample_status_info.upper()

        # Scenario A: Database Lock / Deadlock
        if "DB_LOCK" in sig_upper or "DEADLOCK" in sig_upper or "ORA-00060" in info_upper:
            return [
                PotentialCause(
                    rank=1,
                    probability_score=0.80,
                    category=FailureCategory.DB_LOCK_CONCURRENCY,
                    title="Deadlock transazionale o contesa risorse sul Database Sorgente",
                    technical_explanation=(
                        "Il job batch è stato terminato dal gestore delle transazioni del database (es. ORA-00060) "
                        "a causa di lock concorrenti prolungati generati da altre sessioni batch simultanee."
                    ),
                    recommended_actions=[
                        "Verificare le sessioni concorrenti attive sul DB durante la fascia oraria tramite i DBA.",
                        "Valutare uno sfasamento temporale (staggering) di 15-30 minuti tra le schedulazioni notturne.",
                        "Eseguire una riesecuzione manuale del report per verificare il superamento del lock.",
                    ],
                ),
                PotentialCause(
                    rank=2,
                    probability_score=0.15,
                    category=FailureCategory.NETWORK_TIMEOUT,
                    title="Timeout di attesa rilascio risorsa JDBC",
                    technical_explanation=(
                        "Il data provider Web Intelligence ha esaurito il timeout di attesa query mentre attendeva "
                        "il rilascio delle tabelle bloccate."
                    ),
                    recommended_actions=[
                        "Controllare il parametro 'Query execution time limit' nei parametri della connessione nel CMC.",
                        "Verificare la presenza di lock su indici o tabelle di staging del DWH.",
                    ],
                ),
                PotentialCause(
                    rank=3,
                    probability_score=0.05,
                    category=FailureCategory.SERVER_RESOURCE_OOM,
                    title="Sovraccarico thread pool Adaptive Job Server",
                    technical_explanation=(
                        "Elevata concorrenza di job contemporanei che ha causato saturazione delle connessioni disponibili."
                    ),
                    recommended_actions=[
                        "Monitorare la coda dei job in esecuzione nel CMC (Adaptive Job Server).",
                    ],
                ),
            ]

        # Scenario B: Database Authentication / Credentials Expired
        if "DB_AUTH" in sig_upper or "ORA-01017" in info_upper or "AUTHENTICATION" in sig_upper:
            return [
                PotentialCause(
                    rank=1,
                    probability_score=0.85,
                    category=FailureCategory.AUTH_CREDENTIALS,
                    title="Credenziali Database o Service Account scadute/errate",
                    technical_explanation=(
                        "L'accesso al database relazionale sottostante è stato respinto con errore di autenticazione. "
                        "Spesso causato da rotazione password dell'utenza tecnica senza aggiornamento della connessione BO."
                    ),
                    recommended_actions=[
                        "Accedere al CMC e testare la connessione relazionale associata all'universo del report.",
                        "Aggiornare la password del service account nella connessione e salvare la configurazione.",
                        "Verificare che l'account non sia stato bloccato sul DB per superamento tentativi falliti.",
                    ],
                ),
                PotentialCause(
                    rank=2,
                    probability_score=0.10,
                    category=FailureCategory.NETWORK_TIMEOUT,
                    title="Rifiuto connessione a livello di firewall/whitelist DB",
                    technical_explanation=(
                        "I nodi di elaborazione BO potrebbero tentare la connessione da un IP non autorizzato dalle ACL del DB."
                    ),
                    recommended_actions=[
                        "Verificare se sono stati aggiunti nuovi nodi o modificati gli indirizzi IP dei Job Server.",
                    ],
                ),
                PotentialCause(
                    rank=3,
                    probability_score=0.05,
                    category=FailureCategory.UNKNOWN_GENERIC,
                    title="Configurazione TNSNames o driver JDBC non aggiornata",
                    technical_explanation="Alias TNS o stringa di connessione non più valida sul server SAP BO.",
                    recommended_actions=[
                        "Verificare il file tnsnames.ora o la configurazione JDBC sulla macchina server.",
                    ],
                ),
            ]

        # Scenario C: Missing Prompts / Parameters
        if "PROMPT" in sig_upper or "30270" in sig_upper or missing_prompts:
            prompts_detail = ", ".join(missing_prompts) if missing_prompts else "uno o più prompt obbligatori"
            return [
                PotentialCause(
                    rank=1,
                    probability_score=0.85,
                    category=FailureCategory.MISSING_PROMPTS,
                    title="Prompt obbligatori non valorizzati nella schedulazione",
                    technical_explanation=(
                        f"Il report Web Intelligence richiede valori obbligatori per i parametri ({prompts_detail}), "
                        "ma la definizione di schedulazione non include risposte predefinite valide."
                    ),
                    recommended_actions=[
                        "Aprire il report nel BI Launch Pad o CMC e verificare i parametri obbligatori.",
                        "Modificare la schedulazione ricorrente specificando valori di default validi per tutti i prompt.",
                        "Salvare la nuova configurazione di schedulazione e rieseguire.",
                    ],
                ),
                PotentialCause(
                    rank=2,
                    probability_score=0.10,
                    category=FailureCategory.CACHE_CORRUPTED,
                    title="Modifica struttura query o eliminazione LOV associata",
                    technical_explanation=(
                        "La query o l'elenco dei valori (LOV) dell'universo è mutato, invalidando i vecchi valori salvati."
                    ),
                    recommended_actions=[
                        "Aprire il report in modalità modifica, aggiornare la query e risalvare il documento.",
                    ],
                ),
                PotentialCause(
                    rank=3,
                    probability_score=0.05,
                    category=FailureCategory.AUTH_CREDENTIALS,
                    title="Restrizione Data Security Profile su prompt",
                    technical_explanation="L'utente che esegue lo schedule non ha diritti di visualizzazione sui valori LOV.",
                    recommended_actions=[
                        "Controllare i profili di sicurezza dati dell'utente assegnati nell'Information Design Tool (IDT).",
                    ],
                ),
            ]

        # Scenario D: WIS 30553 / Data Provider Cache Corruption
        if "WIS 30553" in sig_upper or "PROCESSDPCOMMANDSEX" in sig_upper:
            return [
                PotentialCause(
                    rank=1,
                    probability_score=0.70,
                    category=FailureCategory.CACHE_CORRUPTED,
                    title="Corruzione della Cache Data Provider o struttura micro-cubo",
                    technical_explanation=(
                        "L'errore WIS 30553 indica un fallimento interno durante la chiamata 'processDPCommandsEx', "
                        "tipicamente dovuto a micro-cubi di cache temporanea obsoleti o corrotti nel documento Webi."
                    ),
                    recommended_actions=[
                        "Eseguire la purga (Purge) dei dati di tutti i Data Provider del documento Webi.",
                        "Salvare il documento dopo la purga e rieseguire la schedulazione.",
                        "In caso di persistenza, verificare se la query contiene filtri complessi incompatibili con la versione del DB.",
                    ],
                ),
                PotentialCause(
                    rank=2,
                    probability_score=0.20,
                    category=FailureCategory.NETWORK_TIMEOUT,
                    title="Chiusura anomala del socket durante il fetch dei dati",
                    technical_explanation=(
                        "Il database remoto ha chiuso la connessione TCP durante la trasmissione del result set."
                    ),
                    recommended_actions=[
                        "Verificare i log di rete e la stabilità della connessione tra Processing Server e database.",
                    ],
                ),
                PotentialCause(
                    rank=3,
                    probability_score=0.10,
                    category=FailureCategory.SERVER_RESOURCE_OOM,
                    title="Superamento soglia memoria del Webi Processing Server",
                    technical_explanation="Volume record estratto superiore al buffer massimo di riga configurato nel CMC.",
                    recommended_actions=[
                        "Verificare il parametro 'Maximum Character Stream Size' nel Webi Processing Server nel CMC.",
                    ],
                ),
            ]

        # Scenario E: Publication / Bursting / FBE60502
        if "PUBLICATION" in sig_upper or "FBE" in sig_upper or "CRS" in sig_upper or "BURSTING" in sig_upper:
            return [
                PotentialCause(
                    rank=1,
                    probability_score=0.75,
                    category=FailureCategory.BURSTING_RECIPIENT,
                    title="Fallimento risoluzione destinatari dinamici o formattazione email",
                    technical_explanation=(
                        "La pubblicazione con bursting non è riuscita a mappare o filtrare i dati per uno o più destinatari, "
                        "oppure la sorgente dinamica conteneva indirizzi email nulli o sintatticamente non validi."
                    ),
                    recommended_actions=[
                        "Verificare il report sorgente dei Dynamic Recipient assicurandosi che tutti i record abbiano email e ID validi.",
                        "Ispezionare la history della pubblicazione nel CMC e scaricare il log 'PublicationAdminErrorLog'.",
                        "Testare la pubblicazione con un singolo destinatario statico di test.",
                    ],
                ),
                PotentialCause(
                    rank=2,
                    probability_score=0.15,
                    category=FailureCategory.SERVER_RESOURCE_OOM,
                    title="Saturazione JVM Heap dell'Adaptive Processing Server (Publishing Service)",
                    technical_explanation=(
                        "Generazione massiva contemporanea di centinaia di stream PDF/Excel che ha esaurito la memoria heap dell'APS."
                    ),
                    recommended_actions=[
                        "Incrementare il parametro -Xmx (JVM Heap Size) dell'APS dedicato al Publishing Service nel CMC.",
                        "Ripartire il carico suddividendo la pubblicazione in batch con finestre orarie distinte.",
                    ],
                ),
                PotentialCause(
                    rank=3,
                    probability_score=0.10,
                    category=FailureCategory.NETWORK_TIMEOUT,
                    title="Rifiuto o throttling dal server SMTP di posta",
                    technical_explanation="Il server SMTP ha rifiutato l'invio massivo per superamento limite messaggi/minuto.",
                    recommended_actions=[
                        "Verificare i log del server di posta aziendale e accordare limiti di invio con il team di messaggistica.",
                    ],
                ),
            ]

        # Scenario F: Network / Socket Timeout
        if "NETWORK" in sig_upper or "TIMEOUT" in sig_upper or "REFUSED" in sig_upper:
            return [
                PotentialCause(
                    rank=1,
                    probability_score=0.80,
                    category=FailureCategory.NETWORK_TIMEOUT,
                    title="Mancata risposta o interruzione della connettività verso il server DB",
                    technical_explanation=(
                        "La richiesta verso il database o servizio di destinazione è andata in timeout dopo l'attesa massima. "
                        "Tipico di manutenzioni notturne non comunicate sul database sorgente."
                    ),
                    recommended_actions=[
                        "Verificare se durante la notte sono state applicate finestre di manutenzione o backup sul DB.",
                        "Eseguire un ping/traceroute dal server BusinessObjects verso l'host DB.",
                        "Rieseguire il job non appena la connettività di rete è ristabilita.",
                    ],
                ),
                PotentialCause(
                    rank=2,
                    probability_score=0.15,
                    category=FailureCategory.AUTH_CREDENTIALS,
                    title="Blocco connessione da firewall perimetrale",
                    technical_explanation="Regole firewall o inspection che hanno interrotto pacchetti TCP a lunga durata.",
                    recommended_actions=[
                        "Verificare il parametro TCP KeepAlive sui server SAP BO e sulle regole del firewall.",
                    ],
                ),
                PotentialCause(
                    rank=3,
                    probability_score=0.05,
                    category=FailureCategory.SERVER_RESOURCE_OOM,
                    title="Timeout dovuto a saturazione thread del sistema operativo",
                    technical_explanation="Tutti i socket effimeri disponibili sull'host risultavano temporaneamente esauriti.",
                    recommended_actions=[
                        "Verificare i parametri di rete e socket time_wait del sistema operativo ospitante.",
                    ],
                ),
            ]

        # Scenario G: Generic / Unknown / Abrupt crash
        return [
            PotentialCause(
                rank=1,
                probability_score=0.50,
                category=FailureCategory.SERVER_RESOURCE_OOM,
                title="Interruzione improvvisa del Job Server o crash del nodo",
                technical_explanation=(
                    "L'assenza di dettagli specifici in SI_STATUSINFO indica solitamente un crash non gestito del processo "
                    "Adaptive Job Server (kill del processo, riavvio VM o esaurimento memoria di sistema)."
                ),
                recommended_actions=[
                    "Verificare nel CMC lo stato dei server (Servers > Core Services) per confermare se qualche servizio è 'Stopped'.",
                    "Ispezionare i log di sistema operativo (Event Viewer o /var/log/messages) per riavvii o kill di processi.",
                    "Riavviare i servizi CMC se necessario e rieseguire le istanze fallite.",
                ],
            ),
            PotentialCause(
                rank=2,
                probability_score=0.30,
                category=FailureCategory.NETWORK_TIMEOUT,
                title="Disconnessione del canale di comunicazione CORBA tra CMS e Job Server",
                technical_explanation="Interruzione temporanea dei messaggi heartbeat tra il CMS centrale e il nodo batch.",
                recommended_actions=[
                    "Verificare la risoluzione DNS e la stabilità del cluster SAP BO.",
                ],
            ),
            PotentialCause(
                rank=3,
                probability_score=0.20,
                category=FailureCategory.UNKNOWN_GENERIC,
                title="Eccezione non documentata nel repository CMS",
                technical_explanation=(
                    f"Messaggio grezzo intercettato: {sample_status_info[:150]}. "
                    "Richiede analisi approfondita dei file di trace (.glf) sul server."
                ),
                recommended_actions=[
                    "Attivare il livello di Tracing 'High' nel CMC per il servizio interessato.",
                    "Consultare la Knowledge Base SAP (SAP Support Portal) inserendo il testo esatto dell'errore.",
                ],
            ),
        ]

    # =========================================================================
    # 4. Smart Contextual Enrichment
    # =========================================================================

    def smart_enrichment(self, parent_id: str) -> Dict[str, Any]:
        """
        Enriches diagnostic context by querying the original document definition for mandatory
        prompts without defaults. Safely ignores 404s (e.g., if parent doc was deleted).
        """
        if not parent_id or str(parent_id) in ("0", "-1"):
            return {"missing_prompts": []}

        url = f"{self.client.webi_url}/documents/{parent_id}/parameters"
        missing_prompts: List[str] = []

        try:
            resp = self.client.get(url)
            if isinstance(resp, dict) and "parameters" in resp:
                raw_params = resp["parameters"].get("parameter", [])
                if isinstance(raw_params, dict):
                    raw_params = [raw_params]
                for p in raw_params:
                    # Check if prompt is mandatory and has no default answer
                    is_optional = p.get("@optional") in ("true", True, "True")
                    has_answers = bool(p.get("answer"))
                    has_defaults = bool(p.get("defaultValues"))
                    if not is_optional and not has_answers and not has_defaults:
                        prompt_name = p.get("name") or p.get("technicalName") or f"Param_{p.get('id', '')}"
                        missing_prompts.append(prompt_name)
        except Exception:
            # Document might be deleted (orphan) or not a Webi document (e.g. Publication template)
            pass

        return {"missing_prompts": missing_prompts}

    # =========================================================================
    # 5. Full Batch Diagnostic Orchestration
    # =========================================================================

    def diagnose_batch(
        self,
        hours_back: int = 12,
        kind: str = "All",
        folder_id: Optional[str] = None,
        max_instances: int = 100,
    ) -> BatchDiagnosticsReport:
        """
        Main entry point for batch diagnostics.
        Interrogates CMS, clusters failures by signature, performs smart contextual enrichment,
        evaluates multi-cause ranking, and returns a validated Pydantic BatchDiagnosticsReport.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        entries = self.scan_failed_instances(
            hours_back=hours_back,
            kind=kind,
            folder_id=folder_id,
            max_instances=max_instances,
        )

        total_failed = len(entries)
        is_truncated = total_failed >= max_instances

        # Edge Case 1: Clean Batch Night (Zero Failures)
        if total_failed == 0:
            summary = (
                f"Tutti i batch notturni completati con successo nelle ultime {hours_back} ore. "
                f"Nessuna istanza in stato di fallimento rilevata su {kind}."
            )
            return BatchDiagnosticsReport(
                scan_timestamp=now_iso,
                hours_back=hours_back,
                kind=kind,
                folder_id=folder_id,
                total_failed_instances=0,
                clusters_count=0,
                is_truncated=False,
                clusters=[],
                executive_summary=summary,
            )

        # Grouping by error signature
        clusters_map: Dict[str, Dict[str, Any]] = {}

        for entry in entries:
            status_info_raw = entry.get("SI_STATUSINFO")
            status_info = str(status_info_raw or "")
            search_key = str(entry.get("SI_ERROR_SEARCH_KEY", ""))
            instance_id = str(entry.get("SI_ID", ""))
            report_name = str(entry.get("SI_NAME", "Unnamed Report"))
            parent_id = str(entry.get("SI_PARENTID", ""))

            signature = self.extract_error_signature(status_info_raw, search_key)

            cluster_id = self._generate_cluster_id(signature)

            if cluster_id not in clusters_map:
                clusters_map[cluster_id] = {
                    "cluster_id": cluster_id,
                    "error_signature": signature,
                    "affected_instances": [],
                    "report_names": set(),
                    "parent_ids": set(),
                    "sample_status_info": status_info,
                }

            clusters_map[cluster_id]["affected_instances"].append(instance_id)
            clusters_map[cluster_id]["report_names"].add(report_name)
            if parent_id and parent_id not in ("0", "-1"):
                clusters_map[cluster_id]["parent_ids"].add(parent_id)

        # Build ClusterDiagnosis list
        diagnosed_clusters: List[ClusterDiagnosis] = []

        for c_id, c_data in clusters_map.items():
            signature = c_data["error_signature"]
            sample_status = c_data["sample_status_info"]
            affected_ids = c_data["affected_instances"]
            report_names_list = sorted(list(c_data["report_names"]))

            # Smart enrichment: inspect sample parent document for missing prompts if signature suggests it
            missing_prompts: List[str] = []
            if "PROMPT" in signature.upper() or "30270" in signature:
                sample_parent = next(iter(c_data["parent_ids"]), None)
                if sample_parent:
                    enrichment = self.smart_enrichment(sample_parent)
                    missing_prompts = enrichment.get("missing_prompts", [])

            # Rank up to 3 causes
            top_causes = self.classify_and_rank_causes(
                error_signature=signature,
                sample_status_info=sample_status,
                missing_prompts=missing_prompts,
            )

            diagnosed_clusters.append(
                ClusterDiagnosis(
                    cluster_id=c_id,
                    error_signature=signature,
                    affected_count=len(affected_ids),
                    sample_instance_ids=affected_ids[:5],
                    sample_report_names=report_names_list[:5],
                    top_causes=top_causes[:3],
                )
            )

        # Sort clusters by affected_count descending (highest impact first)
        diagnosed_clusters.sort(key=lambda c: c.affected_count, reverse=True)

        # Compose executive summary
        summary = (
            f"Rilevati {total_failed} fallimenti distribuiti su {len(diagnosed_clusters)} pattern/cluster distinti "
            f"nelle ultime {hours_back} ore. "
        )
        if diagnosed_clusters:
            primary_cluster = diagnosed_clusters[0]
            summary += (
                f"Cluster principale ad alto impatto ({primary_cluster.affected_count} istanze): "
                f"'{primary_cluster.top_causes[0].title}'."
            )

        if is_truncated:
            summary += (
                f" ATTENZIONE: Il volume totale ha raggiunto il limite di campionamento ({max_instances} istanze); "
                "si raccomanda un'analisi con finestra temporale più ristretta."
            )

        return BatchDiagnosticsReport(
            scan_timestamp=now_iso,
            hours_back=hours_back,
            kind=kind,
            folder_id=folder_id,
            total_failed_instances=total_failed,
            clusters_count=len(diagnosed_clusters),
            is_truncated=is_truncated,
            clusters=diagnosed_clusters,
            executive_summary=summary,
        )
