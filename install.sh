#!/usr/bin/env bash
# Instalador del sistema de memoria persistente tipo cerebro (SQLite).
# Copia SOLO el mecanismo (motor + hooks + protocolo). NO trae recuerdos
# personales: la base de datos nace VACÍA.
#
# Uso:  ./install.sh [BASE]
#   BASE = directorio raíz donde viven .memory/ y .claude/ (por defecto: $HOME)
set -euo pipefail

BASE="${1:-$HOME}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MEM="$BASE/.memory"
CLA="$BASE/.claude"
AGENTS="$CLA/agents"

echo "==> Instalando memoria persistente (cerebro SQLite) en: $BASE"

command -v python3 >/dev/null || { echo "ERROR: se requiere python3"; exit 1; }
command -v sqlite3 >/dev/null || echo "AVISO: sqlite3 CLI no encontrado (el consolidador lo usa)."

mkdir -p "$MEM" "$AGENTS"

# 1. Motor (portátil: mem.py deriva la ruta de la DB de su propia ubicación)
install -m 755 "$REPO/engine/mem.py" "$MEM/mem.py"
echo "==> engine/mem.py -> $MEM/mem.py"

# 2. Script de consolidación nocturna (sustituye la ruta base)
sed "s|__MEM_HOME__|$BASE|g" "$REPO/engine/consolidate.sh" > "$MEM/consolidate.sh"
chmod 755 "$MEM/consolidate.sh"
echo "==> engine/consolidate.sh -> $MEM/consolidate.sh"

# 3. Subagente consolidador
sed "s|__MEM_HOME__|$BASE|g" "$REPO/engine/memory-consolidator.md" > "$AGENTS/memory-consolidator.md"
echo "==> agente memory-consolidator instalado"

# 4. Hooks en settings.json (no se sobrescribe si ya existe)
if [ -f "$CLA/settings.json" ]; then
  echo "!! Ya existe $CLA/settings.json — NO se sobrescribe."
  echo "   Fusiona manualmente el bloque \"hooks\" desde: $REPO/config/settings.json"
  echo "   (recuerda reemplazar __MEM_HOME__ por $BASE)"
else
  sed "s|__MEM_HOME__|$BASE|g" "$REPO/config/settings.json" > "$CLA/settings.json"
  echo "==> settings.json creado con los 3 hooks (SessionStart / UserPromptSubmit / Stop)"
fi

# 5. CLAUDE.md (protocolo). No pisar si ya existe.
if [ -f "$BASE/CLAUDE.md" ]; then
  echo "!! Ya existe $BASE/CLAUDE.md — NO se sobrescribe. Plantilla en: $REPO/config/CLAUDE.md"
else
  sed "s|__MEM_HOME__|$BASE|g" "$REPO/config/CLAUDE.md" > "$BASE/CLAUDE.md"
  echo "==> CLAUDE.md (protocolo) creado. Edita la sección 3 con tus reglas de proyecto."
fi

# 6. Base de datos VACÍA (episodic + semantic + FTS5 + triggers)
python3 "$MEM/mem.py" init

echo ""
echo "==> LISTO. Memoria vacía inicializada en $MEM/memory.db"
echo ""
echo "    Verifica:   python3 $MEM/mem.py context   (no debe imprimir nada aún)"
echo "    Cron de consolidación nocturna (opcional):"
echo "      (crontab -l 2>/dev/null; echo '0 4 * * * $MEM/consolidate.sh') | crontab -"
