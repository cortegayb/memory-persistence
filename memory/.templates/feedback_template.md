---
name: feedback_example
description: Ejemplo de feedback - regla o preferencia de trabajo
metadata:
  type: feedback
---

# Feedback Template

Usa este archivo para guardar reglas, preferencias y decisiones validadas sobre cómo trabajar.

## Tu Regla

**Regla:** Explicación breve de qué no hacer o siempre hacer

Ejemplo:
- "No usar mocks en tests de BD"
- "Responder siempre en español"
- "Hacer commit antes de destructive operations"

## Why (Por qué)

**Why:** Explica la razón detrás. Esto es crucial para futuros casos edge.

Ejemplo: "Experiencia pasada mostró que mocked tests pasaron pero la prod migration falló"

## How to Apply (Cuándo aplica)

**How to apply:** Describe situaciones específicas donde esta regla debe cumplirse.

Ejemplo: "Aplica en todos los tests que tocan persistencia: migrations, seed, fixtures"

---

## Campos opcionales

- **Desde:** Fecha cuando empezó a aplicar
- **Contexto:** Proyecto o área donde aplica
- **Excepciones:** Casos donde no aplica
- **Revisado:** Última vez que verificaste si sigue siendo válida
