#!/bin/bash
# Consolidación nocturna de memoria — se ejecuta vía cron
# Log: __MEM_HOME__/.memory/consolidation.log

cd __MEM_HOME__

LOG="__MEM_HOME__/.memory/consolidation.log"
DATE=$(date '+%Y-%m-%d %H:%M')

echo "" >> "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$LOG"
echo "[${DATE}] INICIO CONSOLIDACIÓN NOCTURNA" >> "$LOG"

# Contar episódicos pendientes antes de consolidar
PENDING=$(python3 __MEM_HOME__/.memory/mem.py count_pending 2>/dev/null)
echo "  Episódicos pendientes: ${PENDING:-?}" >> "$LOG"

if [ "${PENDING}" = "0" ]; then
    echo "  Sin conversaciones nuevas. Nada que consolidar." >> "$LOG"
    echo "[${DATE}] FIN (sin cambios)" >> "$LOG"
    exit 0
fi

# Invocar subagente consolidador y capturar su resumen
RESULT=$(claude --dangerously-skip-permissions -p \
    "Actúa como memory-consolidator. Ejecuta la consolidación nocturna completa según el protocolo. Al finalizar imprime un resumen en este formato exacto:
EPISODICOS_PROCESADOS: N
NUEVOS: título1 (tipo, impN) | título2 (tipo, impN)
ACTUALIZADOS: título1 (vN) | título2 (vN)
ARCHIVADOS: título1 | título2
TOTAL_ACTIVOS: N
Si no hay items en una categoría escribe NINGUNO." 2>&1)

# Parsear y escribir resumen legible
echo "" >> "$LOG"
echo "  RESULTADO:" >> "$LOG"

EP=$(echo "$RESULT" | grep "EPISODICOS_PROCESADOS:" | sed 's/EPISODICOS_PROCESADOS: //')
NW=$(echo "$RESULT" | grep "^NUEVOS:" | sed 's/^NUEVOS: //')
UP=$(echo "$RESULT" | grep "^ACTUALIZADOS:" | sed 's/^ACTUALIZADOS: //')
AR=$(echo "$RESULT" | grep "^ARCHIVADOS:" | sed 's/^ARCHIVADOS: //')
TO=$(echo "$RESULT" | grep "TOTAL_ACTIVOS:" | sed 's/TOTAL_ACTIVOS: //')

[ -n "$EP" ] && echo "  Conversaciones procesadas : ${EP}" >> "$LOG"
[ -n "$NW" ] && echo "  Nuevos recuerdos          : ${NW}" >> "$LOG"
[ -n "$UP" ] && echo "  Actualizados              : ${UP}" >> "$LOG"
[ -n "$AR" ] && echo "  Archivados (olvido)       : ${AR}" >> "$LOG"
[ -n "$TO" ] && echo "  Total activos neocórtex   : ${TO}" >> "$LOG"

# Si el parseo no funcionó, guardar output completo igual
if [ -z "$EP" ] && [ -z "$NW" ]; then
    echo "  (respuesta completa del consolidador):" >> "$LOG"
    echo "$RESULT" | head -40 | sed 's/^/    /' >> "$LOG"
fi

echo "[${DATE}] FIN CONSOLIDACIÓN" >> "$LOG"
