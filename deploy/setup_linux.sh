#!/usr/bin/env bash
# =============================================================================
# SAP BusinessObjects MCP Server - Linux Host Setup & Health Check
# =============================================================================
# Master bootstrap script for configuring bo-mcp natively on a Linux host
# running SAP BusinessObjects BI Platform 4.3 SP5.
#
# Follows defensive bash patterns (bash-pro):
#   - Strict mode: set -Eeuo pipefail
#   - Safe PATH resolution and cleanup traps
#   - Automated uv detection and non-root installation
#   - Subsystem validation via `python server.py doctor`
# =============================================================================

set -Eeuo pipefail
shopt -s inherit_errexit 2>/dev/null || true

# --- Script Metadata & Paths ---
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
readonly SCRIPT_NAME="$(basename -- "${BASH_SOURCE[0]}")"

# --- Formatting & Colors ---
if [[ -t 1 ]]; then
  readonly CLR_RESET='\033[0m'
  readonly CLR_BOLD='\033[1m'
  readonly CLR_GREEN='\033[0;32m'
  readonly CLR_YELLOW='\033[1;33m'
  readonly CLR_RED='\033[0;31m'
  readonly CLR_CYAN='\033[0;36m'
else
  readonly CLR_RESET=''
  readonly CLR_BOLD=''
  readonly CLR_GREEN=''
  readonly CLR_YELLOW=''
  readonly CLR_RED=''
  readonly CLR_CYAN=''
fi

log_info() {
  printf "${CLR_CYAN}[INFO]${CLR_RESET} %s\n" "$*"
}

log_success() {
  printf "${CLR_GREEN}${CLR_BOLD}[OK]${CLR_RESET} %s\n" "$*"
}

log_warn() {
  printf "${CLR_YELLOW}[WARN]${CLR_RESET} %s\n" "$*" >&2
}

log_error() {
  printf "${CLR_RED}${CLR_BOLD}[ERROR]${CLR_RESET} %s\n" "$*" >&2
}

error_trap() {
  local exit_code="$?"
  local line_no="$1"
  log_error "Command failed with exit code ${exit_code} at line ${line_no} in ${SCRIPT_NAME}"
}
trap 'error_trap ${LINENO}' ERR

print_banner() {
  printf "${CLR_CYAN}${CLR_BOLD}"
  cat <<'EOF'
  =============================================================
     SAP BusinessObjects 4.3 SP5 - bo-mcp Linux Host Setup
  =============================================================
EOF
  printf "${CLR_RESET}\n"
}

# --- Step 1: Detect Environment & User ---
check_system_environment() {
  log_info "Target project directory: ${PROJECT_ROOT}"
  log_info "Operating System: $(uname -s) $(uname -r) ($(uname -m))"
  log_info "Executing as user: $(id -un) (UID: $(id -u))"

  if [[ "$(id -u)" -eq 0 ]]; then
    log_warn "Running as root! For production SAP BO environments, it is recommended"
    log_warn "to run bo-mcp under the non-root account owning the SAP BO install (e.g. 'bobj')."
  fi
}

# --- Step 2: Ensure uv package manager is available ---
ensure_uv_installed() {
  export PATH="${HOME}/.local/bin:${PATH}"

  if command -v uv >/dev/null 2>&1; then
    log_success "Astral 'uv' package manager found: $(uv --version)"
    return 0
  fi

  log_warn "'uv' not found on PATH. Attempting automatic user-level installation..."
  if ! command -v curl >/dev/null 2>&1; then
    log_error "'curl' is required to install uv automatically. Please install curl or install uv manually:"
    log_error "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    return 1
  fi

  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"

  if command -v uv >/dev/null 2>&1; then
    log_success "'uv' successfully installed: $(uv --version)"
  else
    log_error "Failed to locate 'uv' after installation. Ensure ~/.local/bin is in your PATH."
    return 1
  fi
}

# --- Step 3: Synchronize dependencies ---
sync_dependencies() {
  log_info "Synchronizing Python virtual environment and dependencies via uv..."
  cd -- "${PROJECT_ROOT}"
  uv sync --extra audit
  log_success "Dependencies synchronized successfully."
}

# --- Step 4: Ensure .env configuration exists ---
setup_env_file() {
  local env_file="${PROJECT_ROOT}/.env"
  local env_example="${PROJECT_ROOT}/.env.example"

  if [[ -f "${env_file}" ]]; then
    log_info "Existing configuration file found at: ${env_file}"
  else
    if [[ -f "${env_example}" ]]; then
      log_warn "No .env file found. Creating from .env.example..."
      cp -- "${env_example}" "${env_file}"
      log_success "Created '${env_file}'. Please review and update credentials if needed."
    else
      log_error ".env.example not found in ${PROJECT_ROOT}."
      return 1
    fi
  fi
}

# --- Step 5: Check SAP BO unixODBC environment ---
check_sap_odbc_environment() {
  log_info "Checking SAP BusinessObjects ODBC environment variables..."

  if [[ -z "${ODBCINI:-}" ]]; then
    local default_odbcini="/opt/bobj/sap_bobj/enterprise_xi40/odbc.ini"
    if [[ -f "${default_odbcini}" ]]; then
      export ODBCINI="${default_odbcini}"
      log_success "Auto-detected SAP BO ODBCINI: ${ODBCINI}"
    else
      log_warn "ODBCINI is not set. If querying Auditing DB via ODBC, ensure ODBCINI points"
      log_warn "to your SAP BO odbc.ini (e.g. /opt/bobj/sap_bobj/enterprise_xi40/odbc.ini)."
    fi
  else
    log_success "ODBCINI is set to: ${ODBCINI}"
  fi

  if [[ -z "${LD_LIBRARY_PATH:-}" ]]; then
    log_warn "LD_LIBRARY_PATH is not set. If using proprietary ODBC drivers (e.g. SQL Anywhere 17 / Oracle),"
    log_warn "ensure LD_LIBRARY_PATH includes SAP BO shared libraries before running."
  else
    log_info "LD_LIBRARY_PATH is populated."
  fi
}

# --- Step 6: Run self-diagnostics probe ---
run_server_doctor() {
  log_info "Running comprehensive self-diagnostics probe (server.py doctor)..."
  printf "\n"
  cd -- "${PROJECT_ROOT}"
  uv run python server.py doctor
  printf "\n"
  log_success "Doctor probe completed."
}

# --- Main Entry Point ---
main() {
  print_banner
  check_system_environment
  ensure_uv_installed
  sync_dependencies
  setup_env_file
  check_sap_odbc_environment
  run_server_doctor

  printf "\n${CLR_GREEN}${CLR_BOLD}=============================================================${CLR_RESET}\n"
  printf "${CLR_GREEN}${CLR_BOLD}   Setup & Verification Completed Successfully!${CLR_RESET}\n"
  printf "${CLR_GREEN}${CLR_BOLD}=============================================================${CLR_RESET}\n\n"
  printf "To start the remote MCP server in foreground mode for live testing:\n"
  printf "  ${CLR_CYAN}uv run python server.py --transport streamable-http --host 0.0.0.0 --port 8000${CLR_RESET}\n\n"
  printf "To install bo-mcp as a background systemd service:\n"
  printf "  ${CLR_CYAN}sudo cp deploy/bo-mcp.service /etc/systemd/system/${CLR_RESET}\n"
  printf "  ${CLR_CYAN}sudo systemctl daemon-reload && sudo systemctl enable --now bo-mcp${CLR_RESET}\n\n"
}

main "$@"
