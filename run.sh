#!/bin/bash
# RagStudio launcher: 7 checks, then the desktop app.
#   ./run.sh            checks + start the app
#   ./run.sh --dev      checks + app with hot reload (electron-vite dev)
#   ./run.sh --demo     load the demo corpus, run the offline quick runbook (mock provider), start the app in mock mode
#   ./run.sh --no-app   checks only (environment for the CLI: ./rs <group> <command>)
# Works from any directory.

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
ENV_NAME="ragstudio"

MODE="start"; DEMO=0
for arg in "$@"; do
    case "$arg" in
        --dev) MODE="dev" ;;
        --no-app) MODE="none" ;;
        --demo) DEMO=1 ;;
        -h|--help) sed -n 2,7p "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo -e "${RED}Opção desconhecida: $arg${NC}"; exit 2 ;;
    esac
done

echo -e "${GREEN}=== RagStudio Launcher ===${NC}"

# --- 1. Conda ---------------------------------------------------------------
echo -e "${CYAN}[1/7] Verificando ambiente Conda...${NC}"
CONDA_BASE=""
if command -v conda &> /dev/null; then CONDA_BASE="$(conda info --base 2>/dev/null)"; fi
for cand in "$HOME/miniforge3" "$HOME/miniconda3" "$HOME/anaconda3" "/opt/miniconda3" "/opt/miniforge3" "/opt/anaconda3"; do
    [ -z "$CONDA_BASE" ] && [ -d "$cand" ] && CONDA_BASE="$cand"
done
[ -z "$CONDA_BASE" ] && { echo -e "${RED}Erro: Conda não encontrado.${NC}"; exit 1; }
CONDA_SH="$CONDA_BASE/etc/profile.d/conda.sh"
[ -f "$CONDA_SH" ] || { echo -e "${RED}Erro: conda.sh não encontrado em $CONDA_SH${NC}"; exit 1; }
. "$CONDA_SH"
if ! conda env list | grep -qw "$ENV_NAME"; then
    echo -e "${YELLOW}Ambiente '$ENV_NAME' não encontrado. Criando a partir de environment.yml...${NC}"
    conda env create -f environment.yml || { echo -e "${RED}Falha ao criar o ambiente conda.${NC}"; exit 1; }
fi
conda activate "$ENV_NAME" || { echo -e "${RED}Falha ao ativar '$ENV_NAME'.${NC}"; exit 1; }
[ "$CONDA_DEFAULT_ENV" = "$ENV_NAME" ] || { echo -e "${RED}Ambiente ativo é '$CONDA_DEFAULT_ENV', esperado '$ENV_NAME'.${NC}"; exit 1; }
export RAGSTUDIO_PYTHON="$(command -v python)"   # Electron (main process) and ./rs use exactly this interpreter
echo -e "${GREEN}Conda '$ENV_NAME' ativado ($RAGSTUDIO_PYTHON).${NC}"

# --- 2. Python env ----------------------------------------------------------
echo -e "${CYAN}[2/7] Verificando ambiente Python...${NC}"
if ! python -c "import numpy, pandas, requests, yaml, matplotlib, jinja2" 2>/dev/null; then
    echo -e "${YELLOW}Dependências Python ausentes. Instalando requirements.txt...${NC}"
    pip install -r requirements.txt || { echo -e "${RED}Falha ao instalar dependências Python.${NC}"; exit 1; }
fi
python -c "import docling" 2>/dev/null || echo -e "${YELLOW}Aviso: docling não encontrado. Importação de PDF indisponível (use .md, .txt ou .json).${NC}"
echo -e "${GREEN}Ambiente Python OK.${NC}"

# --- 3. SQLite schema -------------------------------------------------------
echo -e "${CYAN}[3/7] Aplicando migrações do banco...${NC}"
DB_LINE="$(python -m ragstudio db migrate | tail -1)"
DB_PATH="$(printf '%s' "$DB_LINE" | python -c 'import json,sys; r=json.loads(sys.stdin.read()); print(r["data"]["database"] if r.get("ok") else "")' 2>/dev/null)"
[ -n "$DB_PATH" ] || { echo -e "${RED}Falha nas migrações do SQLite: $DB_LINE${NC}"; exit 1; }
echo -e "${GREEN}Banco OK ($DB_PATH).${NC}"

# --- 4. Provider de modelos (informativo) -----------------------------------
echo -e "${CYAN}[4/7] Verificando provider de modelos...${NC}"
[ "$DEMO" = 1 ] && export RAGSTUDIO_PROVIDER=mock
PROVIDER_REPORT="$(python -m ragstudio config test-connection | tail -1 | python -c '
import json, sys
r = json.loads(sys.stdin.read())
d = r.get("data") or {}
if d.get("ok"):
    print("OK|%s: embedding %s, llm %s" % (d["provider"], d["embedding"].get("model"), d["llm"].get("model")))
else:
    part = next((p for p in (d.get("embedding", {}), d.get("llm", {})) if not p.get("ok")), {})
    print("NO|%s: %s" % (d.get("provider", "?"), part.get("error") or r.get("error") or "sem resposta"))
' 2>/dev/null)"
if [ "${PROVIDER_REPORT%%|*}" = "OK" ]; then
    echo -e "${GREEN}Provider ${PROVIDER_REPORT#*|}.${NC}"
else
    echo -e "${YELLOW}Nenhum provider pronto (${PROVIDER_REPORT#*|})${NC}"
    echo -e "${YELLOW}Configure em Configurações → Provider e modelos, ou rode ./run.sh --demo para o modo simulado.${NC}"
fi

if [ "$DEMO" = 1 ]; then
    echo -e "${CYAN}      Carregando a demonstração offline (provider simulado)...${NC}"
    python -m ragstudio corpus import --path tests/fixtures/docs --name energia >/dev/null 2>&1
    python -m ragstudio questions import-json --path tests/fixtures/questions.json --corpus energia >/dev/null 2>&1
    python -m ragstudio experiments run --file configs/examples/quick_mock.yaml | tail -1
fi

if [ "$MODE" = "none" ]; then
    echo ""
    echo -e "${GREEN}Ambiente pronto para a CLI. A partir de $PROJECT_DIR:${NC}"
    echo "  ./rs techniques list"
    exit 0
fi

# --- 5. Node ----------------------------------------------------------------
echo -e "${CYAN}[5/7] Verificando Node.js...${NC}"
command -v npm &> /dev/null || { echo -e "${RED}Erro: npm não encontrado. Instale o Node.js (https://nodejs.org/) ou use ./run.sh --no-app para a CLI.${NC}"; exit 1; }
echo -e "${GREEN}Node.js $(node -v) / npm $(npm -v)${NC}"

# --- 6. Node deps -----------------------------------------------------------
echo -e "${CYAN}[6/7] Verificando dependências Node.js...${NC}"
if [ ! -d "Frontend/node_modules" ]; then
    echo -e "${YELLOW}Instalando dependências em Frontend/...${NC}"
    (cd Frontend && npm install) || { echo -e "${RED}Falha no npm install.${NC}"; exit 1; }
else
    echo -e "${GREEN}Dependências Node.js encontradas.${NC}"
fi

# --- 7. Electron binary (Dropbox sync pitfall) -------------------------------
echo -e "${CYAN}[7/7] Verificando binário do Electron...${NC}"
OS_NAME="$(uname -s)"; SYSTEM_ARCH="$(uname -m)"; ELECTRON_PKG="$PROJECT_DIR/Frontend/node_modules/electron"
electron_problem() {
    local rel actual info
    [ -f "$ELECTRON_PKG/path.txt" ] || { echo "path.txt ausente"; return; }
    rel="$(<"$ELECTRON_PKG/path.txt")"
    actual="$ELECTRON_PKG/dist/$rel"
    [ -f "$actual" ] || { echo "binário ausente ($actual)"; return; }
    if [ "$OS_NAME" = "Darwin" ]; then
        info="$(file "$actual")"
        [[ "$info" == *ELF* ]] && { echo "binário Linux (ELF) em macOS, sincronizado pelo Dropbox de outra máquina"; return; }
        [[ "$SYSTEM_ARCH" == "arm64" && "$info" != *arm64* ]] && { echo "binário x86_64 em sistema arm64"; return; }
        [[ "$SYSTEM_ARCH" == "x86_64" && "$info" == *arm64* && "$info" != *x86_64* ]] && { echo "binário arm64 em sistema x86_64"; return; }
    fi
    "$actual" --version >/dev/null 2>&1 || echo "binário não executa (sincronização do Dropbox incompleta?)"
}
ELECTRON_REASON="$(electron_problem)"
if [ -n "$ELECTRON_REASON" ]; then
    echo -e "${YELLOW}Electron inválido: $ELECTRON_REASON. Reinstalando...${NC}"
    (cd Frontend && rm -rf node_modules/electron && npm install electron) || { echo -e "${RED}Falha ao reinstalar Electron.${NC}"; exit 1; }
    ELECTRON_REASON="$(electron_problem)"
    [ -n "$ELECTRON_REASON" ] && { echo -e "${RED}Electron continua inválido: $ELECTRON_REASON.${NC}"; exit 1; }
    echo -e "${GREEN}Electron reinstalado.${NC}"
else
    echo -e "${GREEN}Binário do Electron OK.${NC}"
fi

echo ""
echo -e "${GREEN}=== Iniciando RagStudio ===${NC}"
cd Frontend
if [ "$MODE" = "dev" ]; then npm run dev; else npm run start; fi
