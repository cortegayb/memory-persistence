#!/usr/bin/env python3
# Núcleo de memoria: FTS5 + decaimiento exponencial. Sin dependencias externas.
import sys, os, re, json, math, sqlite3
from datetime import datetime, timezone

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db")
TAU_BASE = 30.0          # vida media base (días)
ARCHIVE_THRESHOLD = 8    # importancia efectiva mínima para seguir activa
ARCHIVE_IDLE_DAYS = 45   # días sin uso para archivar
TOPK = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS episodic(
  id INTEGER PRIMARY KEY, ts TEXT NOT NULL DEFAULT (datetime('now')),
  session_id TEXT, role TEXT, content TEXT NOT NULL,
  consolidated INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS semantic(
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, type TEXT NOT NULL DEFAULT 'fact',
  detail TEXT NOT NULL, tags TEXT DEFAULT '', project TEXT DEFAULT '',
  importance INTEGER NOT NULL DEFAULT 50,
  created TEXT NOT NULL DEFAULT (datetime('now')),
  last_used TEXT NOT NULL DEFAULT (datetime('now')),
  usage_count INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'active');
CREATE TABLE IF NOT EXISTS links(
  src INTEGER, dst INTEGER, kind TEXT, PRIMARY KEY(src,dst,kind));
CREATE TABLE IF NOT EXISTS token_usage(
  id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT,
  msg_id TEXT UNIQUE, request_id TEXT, model TEXT,
  turn_uuid TEXT, prompt TEXT,
  input_tokens INTEGER DEFAULT 0, cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
  project TEXT DEFAULT '', task_type TEXT DEFAULT '');
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
  title, detail, tags, content='semantic', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS sem_ai AFTER INSERT ON semantic BEGIN
  INSERT INTO memory_fts(rowid,title,detail,tags) VALUES(new.id,new.title,new.detail,new.tags);
END;
CREATE TRIGGER IF NOT EXISTS sem_ad AFTER DELETE ON semantic BEGIN
  INSERT INTO memory_fts(memory_fts,rowid,title,detail,tags)
  VALUES('delete',old.id,old.title,old.detail,old.tags);
END;
CREATE TRIGGER IF NOT EXISTS sem_au AFTER UPDATE ON semantic BEGIN
  INSERT INTO memory_fts(memory_fts,rowid,title,detail,tags)
  VALUES('delete',old.id,old.title,old.detail,old.tags);
  INSERT INTO memory_fts(rowid,title,detail,tags) VALUES(new.id,new.title,new.detail,new.tags);
END;
"""

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c
def now(): return datetime.now(timezone.utc)
def days_since(ts):
    try: t = datetime.fromisoformat(str(ts).replace("Z","")).replace(tzinfo=timezone.utc)
    except Exception: return 0.0
    return max(0.0, (now()-t).total_seconds()/86400.0)
def eff_importance(r):
    tau = TAU_BASE*(1+math.log1p(r["usage_count"]))
    return r["importance"]*math.exp(-days_since(r["last_used"])/tau)
def fts_query(text):
    toks = [t for t in re.findall(r"[\wáéíóúñü]+", (text or "").lower()) if len(t)>2][:12]
    return " OR ".join(f'"{t}"' for t in toks) if toks else None
def read_prompt():
    try: return (json.load(sys.stdin) or {}).get("prompt","")
    except Exception: return ""
def extract_text(m):
    c = m.get("content") or m.get("text") or m.get("message")
    if isinstance(c,str): return c
    if isinstance(c,list): return " ".join(b.get("text","") for b in c if isinstance(b,dict))
    if isinstance(c,dict): return extract_text(c)
    return ""

def cmd_init(_): conn().executescript(SCHEMA); print("memoria inicializada")

def cmd_search(arg):
    q = fts_query(arg if arg else read_prompt())
    if not q: return
    c = conn()
    rows = c.execute("""SELECT s.*, bm25(memory_fts) AS rank
        FROM memory_fts JOIN semantic s ON s.id=memory_fts.rowid
        WHERE memory_fts MATCH ? AND s.status='active'
        ORDER BY rank LIMIT 20""", (q,)).fetchall()
    if not rows: return
    ranks = [r["rank"] for r in rows]; rmin,rmax = min(ranks),max(ranks); span=(rmax-rmin) or 1.0
    scored = []
    for r in rows:
        sim = 1-(r["rank"]-rmin)/span
        rec = math.exp(-days_since(r["last_used"])/60.0)
        imp = eff_importance(r)/100.0
        scored.append((0.55*sim+0.15*rec+0.30*imp, r))
    scored.sort(key=lambda x:x[0], reverse=True)
    top = scored[:TOPK]
    ids = [r["id"] for _,r in top]
    c.executemany("UPDATE semantic SET usage_count=usage_count+1,last_used=? WHERE id=?",
                  [(now().isoformat(), i) for i in ids]); c.commit()
    print("## Recuerdos relevantes (memoria de largo plazo)")
    for _,r in top: print(f"- [{r['type']}] {r['title']}: {r['detail']}")

def cmd_context(_):
    c = conn()
    rules = c.execute("""SELECT title,detail FROM semantic WHERE status='active'
        AND type IN('rule','preference') ORDER BY importance DESC LIMIT 8""").fetchall()
    recent = c.execute("""SELECT title FROM semantic WHERE status='active'
        ORDER BY last_used DESC LIMIT 5""").fetchall()
    if rules:
        print("## Reglas y preferencias activas (memoria)")
        for r in rules: print(f"- {r['title']}: {r['detail']}")
    if recent: print("## Tocado recientemente: " + ", ".join(r["title"] for r in recent))

def cmd_count_pending(_):
    c = conn()
    n = c.execute("SELECT COUNT(*) FROM episodic WHERE consolidated=0").fetchone()[0]
    print(n)

def cmd_add(_):
    d = json.load(sys.stdin); c = conn()
    c.execute("""INSERT INTO semantic(title,type,detail,tags,project,importance)
        VALUES(?,?,?,?,?,?)""",(d["title"],d.get("type","fact"),d["detail"],
        d.get("tags",""),d.get("project",""),int(d.get("importance",50)))); c.commit()
    print(c.execute("SELECT last_insert_rowid()").fetchone()[0])

def cmd_log(_):
    try: d = json.load(sys.stdin)
    except Exception: return
    p = d.get("transcript_path"); sid = d.get("session_id","")
    if not p or not os.path.exists(p): return
    lu = la = ""
    with open(p) as f:
        for line in f:
            try: m = json.loads(line)
            except Exception: continue
            role = m.get("role") or m.get("type"); t = extract_text(m)
            if not t: continue
            if role=="user": lu=t
            elif role=="assistant": la=t
    c = conn()
    for role,t in (("user",lu),("assistant",la)):
        if t: c.execute("INSERT INTO episodic(session_id,role,content) VALUES(?,?,?)",(sid,role,t[:4000]))
    c.commit()

TOKEN_DDL = """CREATE TABLE IF NOT EXISTS token_usage(
  id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT,
  msg_id TEXT UNIQUE, request_id TEXT, model TEXT,
  turn_uuid TEXT, prompt TEXT,
  input_tokens INTEGER DEFAULT 0, cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
  project TEXT DEFAULT '', task_type TEXT DEFAULT '');"""

def _migrate_tokens(c):
    # Añade columnas project/task_type a bases ya existentes (idempotente).
    cols = {r[1] for r in c.execute("PRAGMA table_info(token_usage)")}
    if "project" not in cols:
        c.execute("ALTER TABLE token_usage ADD COLUMN project TEXT DEFAULT ''")
    if "task_type" not in cols:
        c.execute("ALTER TABLE token_usage ADD COLUMN task_type TEXT DEFAULT ''")
    c.commit()

def derive_project(cwd):
    # Proyecto = primer subdirectorio bajo /home/<user>/ (ej. profe_jarvis);
    # el propio home = 'general'. Fallback: basename del cwd.
    if not cwd: return "general"
    m = re.match(r"^/home/[^/]+/([^/]+)", cwd)
    if m: return m.group(1)
    if re.match(r"^/home/[^/]+/?$", cwd): return "general"
    return os.path.basename(cwd.rstrip("/")) or "general"

# Clasificador de tipo de tarea por palabras clave del prompt (primer match gana).
# Los términos son raíces: matchean con frontera a la izquierda y continuación libre
# (ej. "recuerd" cubre recuerda/recuerdo; "leccion" cubre lecciones), así "api" no
# matchea "rapido" ni "si" matchea "necesito".
TASK_RULES = [
    ("contenido",     ("leccion","lección","banco","pregunta","rubrica","rúbrica","diagnostic",
                       "diagnóstic","evaluacion","evaluación","transcri","savia","libro",
                       "contenido","misconcept","estudiar","tutor","jarvis","cuento","habilidad",
                       "indicador","concepto")),
    ("memoria",       ("memoria","recuerd","mem.py","consolid","cerebro","semantic","semántic",
                       "episodic","episódic","olvido","decay","token","tarea","feedback_template",
                       "errata")),
    ("infra/git",     ("git","commit","push","deploy","ssh","systemctl","apache","nginx","certbot",
                       "dns","cron","hook","permis","servidor","vhost","proxy","credential",
                       "llave","pat","correo","mandrill","smtp","rama","directorio","terminal",
                       "reinicia","reiniciste","conecta","conectar")),
    ("investigacion", ("informe","analiz","análisi","investiga","research","reporte","resumen",
                       "dato","cuantific","churn","métrica","metrica","revisa","consulta","query",
                       "sql","tabla","log","visor","colegio","licencia","rbd","usuario","estadistic",
                       "listame","lista ","muestra","detalle","region","región","alumno","profesor",
                       "adopcion","adopción","apertura","usabilidad","perdida","pérdida","fuga",
                       "registro","filas","proceso","conteo","contando","cuenta","tsv","csv","xls",
                       "excel","importar","comparativa","compara","busc","id de")),
    ("codigo",        ("implementa","código","codigo","script","bug","fix","refactor","endpoint",
                       "api","frontend","backend","componente","funcion","función","error","build",
                       "compila","vista","menu","menú","boton","botón","btn","card","diseño","css",
                       "bootstrap","rota","undefined","migrar","alter","python","fastapi","react",
                       "node","mysql","desarroll","valida")),
]

# Ruido del harness (no es una consulta real del usuario).
def _is_sistema(p):
    return (p.startswith("<task-notification") or p.startswith("<command") or
            p.startswith("caveat:") or "session is being continued" in p or
            "hay mucha demanda y no puedo responder" in p)

# Saludos y confirmaciones (charla, no trabajo técnico).
_FILLERS = {"si","sí","no","ok","okay","oka","hola","hi","hey","holi","dale","listo","gracias",
            "yapo","ya","ahora","ahora si","ahora sí","excelente","perfecto","bien","buenas",
            "buenos dias","buenos días","chao","sip","nop","claro","de acuerdo","incuye todo",
            "intentemos usar por ahora","vuelve a intentar","echoahora","ahora si","no yo lo reviso"}
_RECALL = ("te acuerdas","acuerdas de","en que quedamos","en qué quedamos","que hicimos",
           "qué hicimos","me cuentas","en que quedo","en qué quedó","que quedamos","como estas",
           "cómo estás","lo ultimo que","lo último que","retoma","retomar","en que quedan",
           "listame los proyecto","lista los proyecto","listame todos los proyecto","que proyecto",
           "qué proyecto","estabamos trabajando","estábamos trabajando","en que quedan")

def classify_task(prompt):
    p = (prompt or "").strip().lower()
    if not p: return "otro"
    if _is_sistema(p): return "sistema"
    if p in _FILLERS or re.match(r"^(hola|hi|hey|buenos dias|buenas|holi)\b", p):
        return "conversacion"
    if any(k in p for k in _RECALL): return "conversacion"
    for label, kws in TASK_RULES:
        if any(re.search(r"(?<![a-z0-9áéíóúñü])"+re.escape(k), p) for k in kws):
            return label
    return "otro"

# Tarifas USD por 1M tokens: (input, output, cache_write_5m, cache_read).
# cache_write_5m = 1.25x input ; cache_read = 0.1x input.
PRICES = {
    "claude-opus-4-8":  (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-7":  (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-6":  (5.0, 25.0, 6.25, 0.50),
    "claude-sonnet-4-6":(3.0, 15.0, 3.75, 0.30),
    "claude-fable-5":   (10.0,50.0,12.50, 1.00),
    "claude-haiku-4-5": (1.0,  5.0, 1.25, 0.10),
}
def cost_usd(model, inp, cc, cr, out):
    p = PRICES.get(model)
    if not p: return 0.0
    return (inp*p[0] + out*p[1] + cc*p[2] + cr*p[3]) / 1_000_000.0

def cmd_tokens(_):
    # Hook Stop: registra uso de tokens por respuesta, agrupado por consulta.
    try: d = json.load(sys.stdin)
    except Exception: return
    p = d.get("transcript_path"); sid = d.get("session_id","")
    if not p or not os.path.exists(p): return
    c = conn(); c.executescript(TOKEN_DDL); _migrate_tokens(c)
    rows = _parse_transcript(p, sid)
    if rows:
        c.executemany("""INSERT OR IGNORE INTO token_usage(ts,session_id,msg_id,
            request_id,model,turn_uuid,prompt,input_tokens,cache_creation_tokens,
            cache_read_tokens,output_tokens,project,task_type)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
        c.commit()

def _parse_transcript(p, sid):
    # Recorre un transcript JSONL y devuelve una fila por respuesta del asistente,
    # etiquetada con proyecto (cwd) y tipo de tarea (clasificador del prompt).
    rows = []; turn = ""; prompt = ""; cwd = ""
    try:
        with open(p) as f:
            for line in f:
                try: m = json.loads(line)
                except Exception: continue
                if m.get("cwd"): cwd = m["cwd"]
                t = m.get("type")
                if t == "user" and not m.get("isSidechain"):
                    # ¿Es una consulta real del usuario (no un tool_result)?
                    content = (m.get("message") or {}).get("content")
                    txt = ""; is_tr = False
                    if isinstance(content, str): txt = content
                    elif isinstance(content, list):
                        for b in content:
                            if isinstance(b, dict):
                                if b.get("type")=="tool_result": is_tr=True
                                elif b.get("type")=="text": txt += b.get("text","")
                    if txt and not is_tr:
                        turn = m.get("uuid",""); prompt = txt.strip().replace("\n"," ")[:200]
                elif t == "assistant":
                    msg = m.get("message") or {}; u = msg.get("usage")
                    if not u or not msg.get("id") or msg.get("model")=="<synthetic>": continue
                    rows.append((m.get("timestamp",""), sid, msg["id"], m.get("requestId",""),
                        msg.get("model",""), turn, prompt, u.get("input_tokens",0),
                        u.get("cache_creation_input_tokens",0), u.get("cache_read_input_tokens",0),
                        u.get("output_tokens",0), derive_project(cwd), classify_task(prompt)))
    except Exception:
        return []
    return rows

def cmd_tokens_report(arg):
    c = conn(); c.executescript(TOKEN_DDL)
    where = "WHERE session_id=?" if arg else ""
    params = (arg,) if arg else ()
    r = c.execute(f"""SELECT COUNT(*) n, COUNT(DISTINCT session_id) s,
        SUM(input_tokens) inp, SUM(cache_creation_tokens) cc,
        SUM(cache_read_tokens) cr, SUM(output_tokens) out
        FROM token_usage {where}""", params).fetchone()
    tot_in = (r["inp"] or 0)+(r["cc"] or 0)+(r["cr"] or 0)
    print(f"Respuestas registradas: {r['n']}  |  sesiones: {r['s']}")
    print(f"Input total (incl. cache): {tot_in:,}")
    print(f"  - input nuevo:      {r['inp'] or 0:,}")
    print(f"  - cache creation:   {r['cc'] or 0:,}")
    print(f"  - cache read:       {r['cr'] or 0:,}")
    print(f"Output total:         {r['out'] or 0:,}")
    print("\nPor modelo (con costo USD):")
    total = 0.0
    for m in c.execute(f"""SELECT model, COUNT(*) n, SUM(input_tokens) inp,
        SUM(cache_creation_tokens) cc, SUM(cache_read_tokens) cr, SUM(output_tokens) out
        FROM token_usage {where} GROUP BY model ORDER BY out DESC""", params):
        usd = cost_usd(m["model"], m["inp"] or 0, m["cc"] or 0, m["cr"] or 0, m["out"] or 0)
        total += usd
        tin = (m["inp"] or 0)+(m["cc"] or 0)+(m["cr"] or 0)
        print(f"  {m['model'] or '?'}: {m['n']} resp, in {tin:,} / out {m['out'] or 0:,}  =  ${usd:,.4f}")
    print(f"\nCOSTO TOTAL ESTIMADO: ${total:,.4f}")

def cmd_tokens_detail(arg):
    # Detalle por consulta (agrupando respuestas bajo cada pregunta del usuario).
    c = conn(); c.executescript(TOKEN_DDL)
    where = "WHERE session_id=?" if arg else ""
    params = (arg,) if arg else ()
    rows = c.execute(f"""SELECT turn_uuid, MIN(ts) ts, MAX(prompt) prompt,
        COUNT(*) n, GROUP_CONCAT(DISTINCT model) models,
        SUM(input_tokens) inp, SUM(cache_creation_tokens) cc,
        SUM(cache_read_tokens) cr, SUM(output_tokens) out,
        SUM(input_tokens+cache_creation_tokens+cache_read_tokens) tin
        FROM token_usage {where} GROUP BY turn_uuid ORDER BY ts""", params).fetchall()
    print(f"{'fecha/hora':19}  {'in':>9} {'out':>7} {'USD':>9}  consulta")
    total = 0.0
    for r in rows:
        # costo por consulta: sumar por modelo dentro del turno
        usd = 0.0
        for mm in c.execute(f"""SELECT model, SUM(input_tokens) i, SUM(cache_creation_tokens) cc,
            SUM(cache_read_tokens) cr, SUM(output_tokens) o FROM token_usage
            WHERE turn_uuid=? {('AND session_id=?' if arg else '')} GROUP BY model""",
            ((r["turn_uuid"], arg) if arg else (r["turn_uuid"],))):
            usd += cost_usd(mm["model"], mm["i"] or 0, mm["cc"] or 0, mm["cr"] or 0, mm["o"] or 0)
        total += usd
        ts = (r["ts"] or "")[:19].replace("T"," ")
        print(f"{ts:19}  {r['tin'] or 0:>9,} {r['out'] or 0:>7,} ${usd:>8,.4f}  {(r['prompt'] or '(?)')[:60]}")
    print(f"\n{len(rows)} consultas  |  COSTO TOTAL: ${total:,.4f}")

def cmd_tokens_daily(arg):
    # Resumen diario con desglose por modelo, derivado del detalle.
    c = conn(); c.executescript(TOKEN_DDL)
    where = "WHERE session_id=?" if arg else ""
    params = (arg,) if arg else ()
    print(f"{'dia':10}  {'consultas':>9} {'resp':>5} {'in':>11} {'out':>9} {'USD':>9}")
    gtot = 0.0; per_model = {}
    for d in c.execute(f"""SELECT substr(ts,1,10) dia FROM token_usage {where}
        GROUP BY dia ORDER BY dia""", params):
        dia = d["dia"]
        agg = c.execute(f"""SELECT COUNT(DISTINCT turn_uuid) q, COUNT(*) n,
            SUM(input_tokens+cache_creation_tokens+cache_read_tokens) tin, SUM(output_tokens) out
            FROM token_usage WHERE substr(ts,1,10)=? {('AND session_id=?' if arg else '')}""",
            ((dia, arg) if arg else (dia,))).fetchone()
        usd = 0.0; lines = []
        for mm in c.execute(f"""SELECT model, COUNT(*) n, SUM(input_tokens) i,
            SUM(cache_creation_tokens) cc, SUM(cache_read_tokens) cr, SUM(output_tokens) o
            FROM token_usage WHERE substr(ts,1,10)=? {('AND session_id=?' if arg else '')}
            GROUP BY model ORDER BY o DESC""", ((dia, arg) if arg else (dia,))):
            mu = cost_usd(mm["model"], mm["i"] or 0, mm["cc"] or 0, mm["cr"] or 0, mm["o"] or 0)
            usd += mu; per_model[mm["model"]] = per_model.get(mm["model"],0.0)+mu
            tin = (mm["i"] or 0)+(mm["cc"] or 0)+(mm["cr"] or 0)
            lines.append(f"             - {mm['model'] or '?':18} {mm['n']:>4} resp  "
                         f"in {tin:>11,} / out {mm['o'] or 0:>8,}  ${mu:>8,.4f}")
        gtot += usd
        print(f"{dia:10}  {agg['q']:>9} {agg['n']:>5} {agg['tin'] or 0:>11,} {agg['out'] or 0:>9,} ${usd:>8,.4f}")
        for ln in lines: print(ln)
    print("\nTotal por modelo:")
    for mdl, u in sorted(per_model.items(), key=lambda x:-x[1]):
        print(f"  {mdl or '?':18} ${u:>9,.4f}")
    print(f"\nCOSTO TOTAL: ${gtot:,.4f}")

def _cmd_tokens_group(col, label, arg):
    # Reporte agrupado por una columna (project o task_type), con costo USD.
    c = conn(); c.executescript(TOKEN_DDL); _migrate_tokens(c)
    k = f"COALESCE(NULLIF({col},''),'(sin etiqueta)')"
    where = "WHERE session_id=?" if arg else ""
    params = (arg,) if arg else ()
    cost = {}
    for r in c.execute(f"""SELECT {k} g, model, SUM(input_tokens) i,
        SUM(cache_creation_tokens) cc, SUM(cache_read_tokens) cr, SUM(output_tokens) o
        FROM token_usage {where} GROUP BY g, model""", params):
        cost[r["g"]] = cost.get(r["g"], 0.0) + cost_usd(
            r["model"], r["i"] or 0, r["cc"] or 0, r["cr"] or 0, r["o"] or 0)
    print(f"{label:16} {'consultas':>9} {'resp':>5} {'in':>13} {'out':>9} {'USD':>10}")
    gtot = 0.0
    for r in c.execute(f"""SELECT {k} g, COUNT(DISTINCT turn_uuid) q, COUNT(*) n,
        SUM(input_tokens+cache_creation_tokens+cache_read_tokens) tin, SUM(output_tokens) out
        FROM token_usage {where} GROUP BY g ORDER BY out DESC""", params):
        u = cost.get(r["g"], 0.0); gtot += u
        print(f"{(r['g'] or '?')[:16]:16} {r['q']:>9} {r['n']:>5} "
              f"{r['tin'] or 0:>13,} {r['out'] or 0:>9,} ${u:>9,.4f}")
    print(f"\nCOSTO TOTAL: ${gtot:,.4f}")

def cmd_tokens_project(arg): _cmd_tokens_group("project", "proyecto", arg)
def cmd_tokens_func(arg):    _cmd_tokens_group("task_type", "funcion", arg)

def cmd_tokens_backfill(_):
    # Reetiqueta filas ya guardadas: recorre los transcripts y rellena
    # project/task_type de cada msg_id. Idempotente.
    import glob
    c = conn(); c.executescript(TOKEN_DDL); _migrate_tokens(c)
    updates = {}  # msg_id -> (project, task_type)
    base = os.path.expanduser("~/.claude/projects")
    for path in glob.glob(os.path.join(base, "*", "*.jsonl")):
        for row in _parse_transcript(path, ""):
            # row: (ts,sid,msg_id,req,model,turn,prompt,inp,cc,cr,out,project,task_type)
            updates[row[2]] = (row[11], row[12])
    n = 0
    for msg_id, (proj, tt) in updates.items():
        cur = c.execute("UPDATE token_usage SET project=?, task_type=? WHERE msg_id=?",
                        (proj, tt, msg_id))
        n += cur.rowcount
    c.commit()
    print(f"Backfill: {len(updates)} respuestas en transcripts, {n} filas actualizadas en token_usage.")

def cmd_decay(_):
    c = conn()
    for r in c.execute("SELECT * FROM semantic WHERE status='active'").fetchall():
        if eff_importance(r)<ARCHIVE_THRESHOLD and days_since(r["last_used"])>ARCHIVE_IDLE_DAYS:
            c.execute("UPDATE semantic SET status='archived' WHERE id=?",(r["id"],))
    c.commit()

if __name__=="__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "search"
    arg = " ".join(sys.argv[2:]) if len(sys.argv)>2 else None
    try:
        {"init":cmd_init,"context":cmd_context,"add":cmd_add,"log":cmd_log,
         "decay":cmd_decay,"search":cmd_search,"tokens":cmd_tokens,
         "tokens_report":cmd_tokens_report,"tokens_detail":cmd_tokens_detail,
         "tokens_daily":cmd_tokens_daily,"tokens_project":cmd_tokens_project,
         "tokens_func":cmd_tokens_func,"tokens_backfill":cmd_tokens_backfill,
         "count_pending":cmd_count_pending}.get(cmd, cmd_search)(arg)
    except Exception:
        pass  # nunca bloquear un hook
