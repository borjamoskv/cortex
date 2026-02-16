#!/usr/bin/env python3
"""
CORTEX v4.0 → NotebookLM Bridge Generator
==========================================
Generates a Jupyter Notebook adapted to the REAL CORTEX v4.0 schema:
- facts (project TEXT, not project_id INT — no 'projects' table)
- agents, consensus_votes_v2, trust_edges
- sessions, transactions, heartbeats, entities, entity_relations
- DB at ~/.cortex/cortex.db

Usage:  python create_nb.py
Output: notebooks/cortex_notebooklm.ipynb
"""

import json, textwrap

def cell_md(lines: str):
    return {"cell_type": "markdown", "metadata": {}, "source": lines.split("\n")}

def cell_code(lines: str):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": textwrap.dedent(lines).strip().split("\n")}

cells = []

# ── 0. Title ──────────────────────────────────────────────────────────
cells.append(cell_md(
"# 🧠 CORTEX v4.0 → NotebookLM Bridge\n"
"\n"
"Extrae, visualiza y aplana el **grafo de conocimiento CORTEX** en un\n"
"*Master Digest* Markdown optimizado para Google NotebookLM.\n"
"\n"
"### Tablas cubiertas\n"
"| Tabla | Rol |\n"
"|---|---|\n"
"| `facts` | Hechos, decisiones, aprendizajes |\n"
"| `agents` | Agentes del Swarm + reputación |\n"
"| `consensus_votes_v2` | Votos ponderados por reputación |\n"
"| `trust_edges` | Grafo de confianza inter-agente |\n"
"| `sessions` | Sesiones de trabajo |\n"
"| `transactions` | Ledger append-only hash-chained |\n"
"| `heartbeats` | Pulsos de actividad |\n"
"| `entities` / `entity_relations` | Entidades extraídas + relaciones |\n"
))

# ── 1. Connect ────────────────────────────────────────────────────────
cells.append(cell_md("## 1. Conexión a la Matriz"))
cells.append(cell_code("""
    import sqlite3
    import pandas as pd
    import json
    from datetime import datetime
    from pathlib import Path

    DB_PATH = Path.home() / ".cortex" / "cortex.db"
    OUTPUT_DIR = Path("notebooklm_sources")
    OUTPUT_DIR.mkdir(exist_ok=True)
    MASTER_FILE = "cortex_notebooklm_digest.md"

    conn = sqlite3.connect(str(DB_PATH))
    print(f"🔌 Conectado a CORTEX: {DB_PATH}")

    # ── Quick census ──
    tables = {
        "facts": "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL",
        "agents": "SELECT COUNT(*) FROM agents",
        "transactions": "SELECT COUNT(*) FROM transactions",
        "heartbeats": "SELECT COUNT(*) FROM heartbeats",
        "consensus_votes": "SELECT COUNT(*) FROM consensus_votes_v2",
    }
    print("\\n📊 Censo de Memoria:")
    for name, q in tables.items():
        try:
            n = conn.execute(q).fetchone()[0]
            print(f"  {name:20s} → {n:,}")
        except Exception:
            print(f"  {name:20s} → (tabla no existe)")
"""))

# ── 2. DataFrames ─────────────────────────────────────────────────────
cells.append(cell_md("## 2. Extracción de Datos"))
cells.append(cell_code("""
    df_facts = pd.read_sql_query(
        "SELECT * FROM facts WHERE valid_until IS NULL ORDER BY project, created_at DESC",
        conn
    )
    df_agents = pd.read_sql_query("SELECT * FROM agents", conn)
    df_votes  = pd.read_sql_query("SELECT * FROM consensus_votes_v2", conn)
    df_tx     = pd.read_sql_query("SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 500", conn)

    # Entities & relations (may not exist on older DBs)
    try:
        df_entities  = pd.read_sql_query("SELECT * FROM entities", conn)
        df_relations = pd.read_sql_query("SELECT * FROM entity_relations", conn)
        print(f"  Entidades: {len(df_entities)}, Relaciones: {len(df_relations)}")
    except Exception:
        df_entities = pd.DataFrame()
        df_relations = pd.DataFrame()
        print("  ⚠️ Tablas entities/entity_relations no encontradas")

    projects = sorted(df_facts["project"].unique())
    print(f"\\n🗂️  {len(projects)} proyectos activos:")
    for p in projects:
        cnt = len(df_facts[df_facts["project"] == p])
        print(f"   • {p} ({cnt} facts)")
"""))

# ── 3. Knowledge Graph ────────────────────────────────────────────────
cells.append(cell_md(
    "## 3. Visualización Topológica del Grafo de Conocimiento\n"
    "Rojo = Proyectos (hubs) · Azul = Facts · Verde = Agentes · Naranja = Entidades"
))
cells.append(cell_code("""
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams["figure.dpi"] = 120

    G = nx.Graph()

    # ── Project hubs (Rojo) ──
    for p in projects:
        G.add_node(f"proj:{p}", label=p, ntype="project")

    # ── Fact nodes (Azul) — solo mostramos los últimos 80 para legibilidad ──
    sample_facts = df_facts.head(80)
    for _, r in sample_facts.iterrows():
        lbl = str(r["content"])[:25] + "…"
        G.add_node(f"fact:{r['id']}", label=lbl, ntype="fact")
        G.add_edge(f"fact:{r['id']}", f"proj:{r['project']}")

    # ── Agent nodes (Verde) ──
    for _, a in df_agents.iterrows():
        G.add_node(f"agent:{a['id']}", label=a.get("name", a["id"])[:15], ntype="agent")

    # ── Consensus edges (Agent → Fact via vote) ──
    for _, v in df_votes.iterrows():
        src = f"agent:{v['agent_id']}"
        tgt = f"fact:{v['fact_id']}"
        if src in G and tgt in G:
            G.add_edge(src, tgt, style="dotted")

    # ── Draw ──
    color_map = {"project": "#FF6B6B", "fact": "#4D96FF", "agent": "#51CF66", "entity": "#FFA94D"}
    size_map  = {"project": 1400, "fact": 200, "agent": 600, "entity": 250}

    colors = [color_map.get(G.nodes[n].get("ntype", "fact"), "#aaa") for n in G]
    sizes  = [size_map.get(G.nodes[n].get("ntype", "fact"), 300) for n in G]

    fig, ax = plt.subplots(figsize=(16, 11))
    pos = nx.spring_layout(G, k=0.4, iterations=60, seed=42)
    nx.draw(G, pos, node_color=colors, node_size=sizes,
            with_labels=False, alpha=0.85, edge_color="#cccccc", ax=ax)

    # Labels solo para projects + agents
    hub_labels = {n: G.nodes[n]["label"] for n in G
                  if G.nodes[n].get("ntype") in ("project", "agent")}
    nx.draw_networkx_labels(G, pos, labels=hub_labels, font_size=7,
                            font_weight="bold", ax=ax)

    ax.set_title("🕸️ CORTEX Knowledge Graph  (🔴 Proyectos · 🔵 Facts · 🟢 Agentes)",
                 fontsize=14, pad=15)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig("cortex_knowledge_graph.png", dpi=150, bbox_inches="tight")
    plt.show()
    print("📸 Grafo guardado como cortex_knowledge_graph.png")
"""))

# ── 4. Consensus Heatmap ──────────────────────────────────────────────
cells.append(cell_md("## 4. Mapa de Calor — Reputación de Agentes y Votos"))
cells.append(cell_code("""
    if not df_agents.empty and "reputation_score" in df_agents.columns:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 4a. Reputación de agentes
        top = df_agents.sort_values("reputation_score", ascending=True).tail(15)
        axes[0].barh(top["name"], top["reputation_score"], color="#51CF66")
        axes[0].set_title("Top 15 Agentes por Reputación")
        axes[0].set_xlim(0, 1)

        # 4b. Distribución de votos por agente
        if not df_votes.empty:
            vote_counts = df_votes.groupby("agent_id").size().sort_values(ascending=True).tail(15)
            agent_names = {a["id"]: a["name"] for _, a in df_agents.iterrows()}
            labels = [agent_names.get(aid, aid)[:15] for aid in vote_counts.index]
            axes[1].barh(labels, vote_counts.values, color="#4D96FF")
            axes[1].set_title("Votos emitidos por Agente")

        plt.tight_layout()
        plt.show()
    else:
        print("ℹ️ No hay datos de agentes/reputación para visualizar")
"""))

# ── 5. Activity Timeline ─────────────────────────────────────────────
cells.append(cell_md("## 5. Timeline de Actividad (Heartbeats)"))
cells.append(cell_code("""
    hb_query = "SELECT date(timestamp) as day, project, COUNT(*) as pulses FROM heartbeats GROUP BY day, project ORDER BY day"
    df_hb = pd.read_sql_query(hb_query, conn)

    if not df_hb.empty:
        pivot = df_hb.pivot_table(index="day", columns="project", values="pulses", fill_value=0)
        # Top 8 projects by total pulses
        top_projects = pivot.sum().sort_values(ascending=False).head(8).index
        fig, ax = plt.subplots(figsize=(14, 5))
        pivot[top_projects].plot.area(ax=ax, alpha=0.7)
        ax.set_title("⏱️ Heartbeats por Proyecto (Timeline)")
        ax.set_ylabel("Pulsos")
        ax.legend(loc="upper left", fontsize=7)
        plt.tight_layout()
        plt.show()
    else:
        print("ℹ️ Sin heartbeats registrados")
"""))

# ── 6. Master Digest Generator ───────────────────────────────────────
cells.append(cell_md(
    "## 6. 🎯 Generación del Master Digest para NotebookLM\n"
    "Transforma toda la base relacional en un Markdown narrativo jerárquico\n"
    "optimizado para RAG."
))
cells.append(cell_code("""
    def generate_master_digest():
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc = []
        doc.append(f"# 🧠 CORTEX MASTER KNOWLEDGE DIGEST\\n")
        doc.append(f"> *Auto-generado: {ts}*\\n\\n")

        doc.append("## INTRODUCCIÓN Y CONTEXTO DEL SISTEMA\\n")
        doc.append("CORTEX v4.0 es un motor de memoria soberano con capacidades de ")
        doc.append("Reputation-Weighted Consensus (RWC), embeddings vectoriales (sqlite-vec), ")
        doc.append("y ledger append-only hash-chained. Este documento contiene el vaciado ")
        doc.append("completo del conocimiento activo, organizado por proyecto.\\n\\n")

        # ── Stats block ──
        doc.append("### Estadísticas Globales\\n")
        doc.append(f"- **Facts activos:** {len(df_facts)}\\n")
        doc.append(f"- **Agentes registrados:** {len(df_agents)}\\n")
        doc.append(f"- **Votos de consenso:** {len(df_votes)}\\n")
        doc.append(f"- **Transacciones:** {len(df_tx)}\\n")
        doc.append(f"- **Proyectos:** {len(projects)}\\n\\n")

        # ── Per-project sections ──
        doc.append("---\\n\\n")
        doc.append("## 📁 DIRECTORIO DE PROYECTOS\\n\\n")

        for proj in projects:
            proj_facts = df_facts[df_facts["project"] == proj]
            doc.append(f"### Proyecto: {proj}\\n")
            doc.append(f"*{len(proj_facts)} hechos activos*\\n\\n")

            # Group by fact_type
            for ft in sorted(proj_facts["fact_type"].unique()):
                doc.append(f"#### {ft.capitalize()}\\n")
                ft_facts = proj_facts[proj_facts["fact_type"] == ft]
                for _, f in ft_facts.iterrows():
                    conf = f.get("confidence", "stated")
                    tags = f.get("tags", "[]")
                    line = f"- {f['content']}"
                    if conf != "stated":
                        line += f" *(confianza: {conf})*"
                    if tags and tags != "[]":
                        try:
                            tag_list = json.loads(tags) if isinstance(tags, str) else tags
                            if tag_list:
                                line += f" `{', '.join(tag_list)}`"
                        except Exception:
                            pass
                    doc.append(line + "\\n")
                doc.append("\\n")

            # Unverified warning
            unverified = proj_facts[proj_facts["confidence"] != "verified"]
            if len(unverified) > 0:
                doc.append(f"> ⚠️ **Data Gap:** {len(unverified)} de {len(proj_facts)} ")
                doc.append(f"hechos en '{proj}' no están verificados.\\n")

            doc.append("\\n---\\n\\n")

        # ── Agents section ──
        doc.append("## 🤖 DIRECTORIO DE AGENTES (Neural Swarm)\\n\\n")
        if not df_agents.empty:
            for _, a in df_agents.sort_values("reputation_score", ascending=False).iterrows():
                name = a.get("name", a["id"])
                rep = a.get("reputation_score", 0.5)
                atype = a.get("agent_type", "ai")
                doc.append(f"- **{name}** — Rep: {rep:.2f} | Type: {atype}")
                tv = a.get("total_votes", 0)
                sv = a.get("successful_votes", 0)
                if tv > 0:
                    doc.append(f" | Votos: {sv}/{tv}")
                doc.append("\\n")
        doc.append("\\n")

        # ── Consensus highlights ──
        if not df_votes.empty:
            doc.append("## 🗳️ CONSENSO — Hechos Más Disputados\\n\\n")
            vote_summary = df_votes.groupby("fact_id").agg(
                total_votes=("vote", "count"),
                avg_weight=("vote_weight", "mean"),
            ).sort_values("total_votes", ascending=False).head(10)

            for fid, row in vote_summary.iterrows():
                fact_content = df_facts[df_facts["id"] == fid]["content"]
                content = fact_content.iloc[0] if not fact_content.empty else f"Fact #{fid}"
                doc.append(f"- **Fact #{fid}** ({int(row['total_votes'])} votos, ")
                doc.append(f"peso medio: {row['avg_weight']:.2f}): {content}\\n")
            doc.append("\\n")

        # ── Transaction ledger summary ──
        if not df_tx.empty:
            doc.append("## 📒 ÚLTIMAS TRANSACCIONES (Ledger)\\n\\n")
            for _, t in df_tx.head(20).iterrows():
                doc.append(f"- [{t.get('timestamp','')}] **{t['project']}** → ")
                doc.append(f"{t['action']}: {(t.get('detail','') or '')[:80]}\\n")

        return "".join(doc)

    # Generate & save
    content = generate_master_digest()
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\\n🎯 Master Digest generado: {MASTER_FILE}")
    print(f"   Tamaño: {len(content):,} caracteres")
    print(f"\\n📋 Siguiente paso:")
    print(f"   1. Ve a https://notebooklm.google.com/")
    print(f"   2. Crea un cuaderno 'CORTEX Brain'")
    print(f"   3. Sube '{MASTER_FILE}' como fuente")
    print(f"   4. ¡Dale a 'Generate Audio Overview'! 🎧")
"""))

# ── 7. Close ──────────────────────────────────────────────────────────
cells.append(cell_md("## 7. Limpieza"))
cells.append(cell_code("""
    conn.close()
    print("🔌 Conexión cerrada. ¡A NotebookLM!")
"""))

# ── Assemble notebook ────────────────────────────────────────────────
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py", "mimetype": "text/x-python",
            "name": "python", "nbformat_minor": 4,
            "pygments_lexer": "ipython3", "version": "3.11.0",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 4,
}

from pathlib import Path as _Path
out_path = _Path("notebooks/cortex_notebooklm.ipynb")
out_path.parent.mkdir(exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"✅ Notebook generado: {out_path}")
print("   Ábrelo en VSCode/Cursor y ejecuta todas las celdas.")
