# Memoria persistente tipo cerebro — protocolo operativo

Eres una instancia de Claude Code con memoria persistente entre sesiones, organizada
como memoria humana: memoria de trabajo (efímera), codificación rápida (hipocampo),
consolidación durante el "sueño" (hipocampo → neocórtex) y recuperación asociativa.
Este archivo es tu protocolo. Síguelo siempre.

## 1. Modelo mental

| Función cerebral | Componente | Mecanismo Claude Code |
|---|---|---|
| Memoria de trabajo (efímera) | ventana de contexto | — |
| Reglas/estado del proyecto | este CLAUDE.md + Auto Memory | carga al iniciar sesión |
| Codificación (hipocampo) | tabla `episodic` | hook Stop |
| Recuperación asociativa | búsqueda FTS5 | hook UserPromptSubmit (stdout entra al contexto) |
| Consolidación ("sueño") | subagente `memory-consolidator` | cron nocturno o manual |
| Memoria de largo plazo (neocórtex) | tabla `semantic` | SQLite |
| Refuerzo sináptico | `usage_count`, `last_used` | sube en cada recuperación |
| Olvido (Ebbinghaus) | decaimiento exponencial | `mem.py decay` archiva (no borra) |

**Regla de oro:** el contexto es la pizarra, no el disco. Lo que importa vive en la memoria,
no en la conversación.

## 2. Disposición de archivos

```
.memory/
  memory.db        # fuente de verdad operacional (episódica + semántica + FTS5)
  mem.py           # núcleo de memoria (búsqueda, decaimiento, codificación)
  consolidate.sh   # consolidación nocturna (cron)
.claude/
  settings.json    # hooks: SessionStart, UserPromptSubmit, Stop
  agents/
    memory-consolidator.md   # subagente "sueño"
CLAUDE.md          # este archivo (reglas curadas a mano)
```

`semantic` es la fuente de verdad para los recuerdos. Las reglas verdaderamente críticas y
estables del proyecto súbelas también a mano a la sección 3 de este CLAUDE.md.

## 3. Reglas críticas del proyecto (curadas a mano)

<!-- Este servidor arranca SIN reglas de proyecto. Añade aquí las tuyas, por ejemplo:
- Siempre trabajar en la rama `dev`. Nunca hacer commits en `master` salvo instrucción explícita.
- Ejecutar cambios directamente sin pedir confirmación previa.
-->

## 4. Protocolo por fase

### Inicio de sesión
El hook `SessionStart` ya inyectó reglas activas y lo tocado recientemente. No re-leas la base
manualmente salvo que necesites algo concreto. Confía en lo inyectado.

### Durante la conversación (codificación)
Las capturas crudas son automáticas (hook Stop). No anotes cada cosa a mano.
Si el usuario dice "recuerda X" / "a partir de ahora..." / fija una decisión, créalo como
recuerdo semántico de inmediato con importancia alta (≥85):

```bash
echo '{"title":"...","type":"rule","detail":"...","tags":"php5,db","importance":90}' | python3 __MEM_HOME__/.memory/mem.py add
```

Tipos válidos: `rule` · `decision` · `fact` · `preference` · `procedure`.

Antes de afirmar "no tenemos nada sobre eso", busca:
```bash
python3 __MEM_HOME__/.memory/mem.py search "tema"
```

### Recuperación (cada turno)
El hook `UserPromptSubmit` antepone `## Recuerdos relevantes` cuando hay coincidencias.
Úsalos como conocimiento propio; no digas "según mi base de datos". Si un recuerdo contradice
lo que el usuario dice ahora, señálalo y deja que el consolidador lo reconcilie.

### Consolidación ("sueño")
La hace el subagente `memory-consolidator` (cron de madrugada, o manual: pídeselo).
No consolides en medio de una tarea salvo que se te pida explícitamente.

### Olvido
No borras recuerdos. `mem.py decay` archiva los de importancia efectiva baja y sin uso
prolongado. La importancia efectiva decae con el tiempo y decae más lento cuanto más se usa
un recuerdo (potenciación a largo plazo).
