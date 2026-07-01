# Memory Persistence System for Claude Code

Un sistema de memoria persistente para mantener contexto de proyectos, preferencias y decisiones entre sesiones de Claude Code usando DeepRecall.

**Versión:** 1.0  
**Estado:** Estable  
**Licencia:** Public Domain

## ¿Qué es?

Sistema que permite a usuarios de Claude Code:

- **Memoria Persistente**: Guardar contexto sin perder información entre sesiones
- **Sincronización Automática**: Respaldo y sincronización nocturna vía cron
- **Categorización Semántica**: Organizar por tipo (user, feedback, project, reference, diario)
- **Búsqueda Inteligente**: DeepRecall carga contexto relevante automáticamente
- **Escalable**: Funciona en múltiples servidores con datos locales independientes

## Dos sabores

Este repo trae **dos** sistemas complementarios. Elige según lo que necesites:

| | Cerebro SQLite (recomendado) | Plantillas markdown |
|---|---|---|
| Qué es | Motor real: `mem.py` + hooks + consolidador + DB con FTS5 | Estructura de archivos `.md` (Auto-Memory) |
| Recuperación | Automática por relevancia (búsqueda + decaimiento/olvido) | Manual, índice en `MEMORY.md` |
| Instalación | `./install.sh` | copiar `memory/.templates/` |
| Carpeta | `engine/` + `config/` | `memory/.templates/` |

> **Importante:** replicar a otro servidor copia **solo el mecanismo**. La base de datos
> nace **vacía** — tus recuerdos personales NO viajan (los excluye `.gitignore`).

## Instalación — Cerebro SQLite (recomendado)

```bash
git clone https://github.com/cortegayb/memory-persistence.git
cd memory-persistence
./install.sh              # instala en $HOME  (o: ./install.sh /ruta/base)
```

Qué hace `install.sh` (idempotente, no pisa lo que ya exista):

1. Copia `engine/mem.py` → `~/.memory/mem.py` (el motor; deriva solo la ruta de la DB).
2. Instala `~/.memory/consolidate.sh` y el subagente `~/.claude/agents/memory-consolidator.md`.
3. Crea `~/.claude/settings.json` con los 3 hooks (SessionStart / UserPromptSubmit / Stop).
4. Crea `CLAUDE.md` (el protocolo) — edita la **sección 3** con tus reglas de proyecto.
5. Ejecuta `mem.py init` → base de datos **vacía** con tablas `episodic`/`semantic`/FTS5.

Consolidación nocturna opcional (cron):

```bash
(crontab -l 2>/dev/null; echo "0 4 * * * $HOME/.memory/consolidate.sh") | crontab -
```

Uso manual del motor:

```bash
# guardar un recuerdo
echo '{"title":"...","type":"rule","detail":"...","tags":"db","importance":90}' | python3 ~/.memory/mem.py add
# buscar
python3 ~/.memory/mem.py search "tema"
```

## Contabilidad de tokens (costo)

El hook `Stop` registra automáticamente, en la tabla `token_usage`, el consumo de
tokens de **cada respuesta** (input / cache creation / cache read / output), junto con
el modelo, la sesión, el prompt que la originó, el **proyecto** (derivado del
directorio de trabajo) y el **tipo de tarea** (clasificado por palabras clave del
prompt: `contenido`, `memoria`, `infra/git`, `codigo`, `investigacion`, `otro`).
Calcula además el **costo estimado en USD** según la tarifa de cada modelo.

```bash
python3 ~/.memory/mem.py tokens_report     # resumen global + por modelo + costo
python3 ~/.memory/mem.py tokens_daily      # desglose por día
python3 ~/.memory/mem.py tokens_project    # desglose por PROYECTO
python3 ~/.memory/mem.py tokens_func       # desglose por TIPO DE TAREA
python3 ~/.memory/mem.py tokens_detail     # una línea por consulta
python3 ~/.memory/mem.py tokens_backfill   # reetiqueta proyecto/tarea de filas ya guardadas
```

Cualquier reporte acepta un `session_id` como argumento para filtrar a una sola sesión.
`tokens_backfill` es idempotente: reprocesa los transcripts existentes y rellena
`project`/`task_type` de los registros previos (los transcripts ya rotados quedan
como `(sin etiqueta)`; los registros nuevos se etiquetan solos).

## Instalación — Plantillas markdown (Auto-Memory)

```bash
mkdir -p ~/.claude/projects/YOUR_PROJECT/memory
cp -r memory/.templates/* ~/.claude/projects/YOUR_PROJECT/memory/
```

Al iniciar Claude Code, DeepRecall busca y carga tus memorias.

## Estructura

```
memory-persistence/
├── install.sh              # Instalador del cerebro SQLite
├── engine/                 # El motor (se copia a ~/.memory y ~/.claude/agents)
│   ├── mem.py                    # núcleo: FTS5 + decaimiento + add/search/log
│   ├── consolidate.sh            # consolidación nocturna (cron)
│   └── memory-consolidator.md    # subagente "sueño"
├── config/                 # Plantillas de configuración (usan __MEM_HOME__)
│   ├── settings.json             # hooks SessionStart/UserPromptSubmit/Stop
│   └── CLAUDE.md                 # el protocolo (sección 3 vacía para tus reglas)
└── memory/.templates/      # Sistema markdown (Auto-Memory), alternativo
    ├── feedback_template.md      # Template: Reglas y preferencias
    ├── project_template.md       # Template: Proyectos
    ├── diario_template.md        # Template: Resúmenes de sesiones
    ├── user_template.md          # Template: Datos del usuario
    └── reference_template.md     # Template: Links externos
```

## Cómo Usar

### Crear una Memoria de Feedback

```bash
cp memory/.templates/feedback_template.md memory/feedback_mi_preferencia.md
```

Luego editar con tu regla:

```yaml
---
name: mi_preferencia
description: Mi preferencia de trabajo
metadata:
  type: feedback
---

**Regla:** Explicación breve

**Why:** Por qué es importante

**How to apply:** Cuándo aplica
```

### Crear una Memoria de Proyecto

```bash
cp memory/.templates/project_template.md memory/project_mi_proyecto.md
```

### Crear un Diario

```bash
cp memory/.templates/diario_template.md memory/diario_2026-07-01.md
```

## Tipos de Memoria

### user_*.md
Información sobre ti: rol, preferencias, conocimiento, skills.

```yaml
---
name: mi_rol
description: Soy developer full-stack
metadata:
  type: user
---

**Rol:** Desarrollador Full-Stack

**Preferencias:** 
- Responder en español
- Sin explicaciones largas

**Skills:**
- Python, JavaScript, React
```

### feedback_*.md
Reglas validadas de cómo trabajar contigo, decisiones técnicas.

```yaml
---
name: testing_philosophy
description: No usar mocks en tests de persistencia
metadata:
  type: feedback
---

**Regla:** Integración, nunca mocks

**Why:** Experiencia pasada mostró que mocked tests pasaron pero prod falló

**How to apply:** En tests de BD y migraciones, usar BD real
```

### project_*.md
Contexto de proyectos en desarrollo.

```yaml
---
name: proyecto_x
description: Sistema de gestión para empresa Y
metadata:
  type: project
---

**Proyecto:** Nombre y descripción

**Why:** Motivación, deadline, stakeholders

**How to apply:** Cómo este contexto influye en decisiones
```

### reference_*.md
Pointers a información externa (Linear, Figma, docs).

```yaml
---
name: bugs_linear
description: Tracker de bugs en Linear
metadata:
  type: reference
---

Linear project "BACKEND" en https://linear.app/...
```

### diario_*.md
Resúmenes de sesiones (YYYY-MM-DD).

```yaml
---
name: diario_2026-07-01
description: Sesión 1 julio - Features completadas
metadata:
  type: diario
---

## Resumen
- Feature X completada
- Bug Y fixed

## Pendientes
- Revisar Z antes de lunes
```

## Sincronización Nocturna (Opcional)

Para sincronización automática, crea un cron:

```bash
# ~/.local/bin/memory-sync.sh
#!/bin/bash
tar -czf ~/backups/memory_$(date +%Y%m%d).tar.gz ~/.claude/projects/*/memory/
rsync -av ~/.claude/projects/*/memory/ remote_server:~/backups/
```

Luego:
```bash
crontab -e
# 0 4 * * * ~/.local/bin/memory-sync.sh  # 4 AM diario
```

## Límites de Contexto

### NO guardes en memoria:
- Código (usa git log)
- Patrones arquitectónicos (están en el código)
- Git history (git blame es autoridad)
- Debugging recipes (están en commits)

### SÍ guarda:
- Decisiones no-obvias
- Porqué detrás de elecciones técnicas
- Preferencias de trabajo
- Contexto de stakeholders
- Deadlines y constrainsts

## Integración con Git

Excluye datos sensibles de git:

```bash
# .gitignore
.env
.env.local
*.key
secret*.md
credentials/
```

## Contribuciones

Este es un sistema template. Úsalo como base para:

- Tu propia memoria persistente
- Compartir con tu equipo
- Adaptarlo a otros LLMs

## Licencia

Public Domain - Libre para usar, copiar, modificar y compartir.

## Autor

**Sistema creado por:** Carlos Ortega (@cortegayb)  
**Fecha:** 8 de mayo de 2026  
**GitHub:** https://github.com/cortegayb

---

**¿Preguntas?** Abre un issue o fork el repositorio.
