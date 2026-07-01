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

## Instalación Rápida

### 1. Clonar el repositorio

```bash
git clone https://github.com/cortegayb/memory-persistence.git
cd memory-persistence
```

### 2. Configurar para Claude Code

Coloca la carpeta `memory/` en tu instalación local de Claude Code:

```bash
mkdir -p ~/.claude/projects/YOUR_PROJECT/memory
cp -r memory/.templates/* ~/.claude/projects/YOUR_PROJECT/memory/
```

### 3. DeepRecall cargará automáticamente

Al iniciar Claude Code, DeepRecall busca y carga tus memorias.

## Estructura

```
memory/
├── MEMORY.md              # Índice principal de todas las memorias
├── .templates/
│   ├── feedback_template.md      # Template: Reglas y preferencias
│   ├── project_template.md       # Template: Proyectos
│   ├── diario_template.md        # Template: Resúmenes de sesiones
│   ├── user_template.md          # Template: Datos del usuario
│   └── reference_template.md     # Template: Links externos
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
