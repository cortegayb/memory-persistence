# Memory Persistence System — Creator

## Sistema Creado por

**Nombre:** Carlos Ortega  
**Email:** ortegac@gmail.com  
**GitHub:** [@cortegayb](https://github.com/cortegayb)

**Fecha de Creación:** 8 de mayo de 2026  
**Versión:** 1.0  
**Estado:** Estable y documentado

## Propósito

Sistema de memoria persistente para Claude Code que permite:

- Mantener contexto entre sesiones sin reexplicar
- Documentar proyectos, preferencias y decisiones
- Sincronizar automáticamente con respaldos
- Escalar a múltiples servidores con datos independientes

## Por qué fue creado

Durante desarrollo de múltiples proyectos simultáneamente, notó que:

1. **Pérdida de contexto:** Cada sesión nueva requería re-explicar el mismo contexto
2. **Inconsistencia:** Decisiones técnicas no estaban documentadas
3. **Escalabilidad:** Difícil coordinar memoria entre servidores y equipos
4. **Falta de historia:** No había forma de trackear "por qué" detrás de decisiones

Resultado: Sistema modular que otros pueden usar como template.

## Características Principales

- ✅ **Memoria Frontal + Persistente** — contexto en cada sesión + histórico permanente
- ✅ **Categorización Semántica** — 5 tipos de memoria (user, feedback, project, reference, diario)
- ✅ **DeepRecall Integration** — carga automática al iniciar Claude Code
- ✅ **Sincronización Nocturna** — cron + Tailscale para múltiples servidores
- ✅ **Datos Locales** — cada servidor maneja su propia memoria (no centralizado)
- ✅ **Extensible** — fácil de adaptar a otros casos de uso

## Uso

Este repositorio es un **template/skeleton**. Otros usuarios pueden:

1. Clonar el repositorio
2. Copiar la estructura a su Claude Code
3. Empezar de 0 con sus propias memorias
4. Cada usuario/servidor maneja sus datos localmente

## Licencia

Public Domain — Libre para usar, copiar, modificar, compartir.

---

**Mantén tus memorias actualizadas. La historia es tu mejor referencia.**
