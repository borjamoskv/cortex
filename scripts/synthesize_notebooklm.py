import sys
from pathlib import Path

# Ninja Bypass
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import sqlite3
import pandas as pd

CORTEX_DB_PATH = Path.home() / ".cortex" / "cortex.db"
OUTPUT_DIR = Path("notebooklm_sources")
OUTPUT_DIR.mkdir(exist_ok=True)


def get_connection():
    return sqlite3.connect(str(CORTEX_DB_PATH))


def run():
    with get_connection() as conn:
        df_unverified = pd.read_sql_query(
            "SELECT project, COUNT(*) as count FROM facts WHERE confidence != 'verified' AND valid_until IS NULL GROUP BY project",
            conn,
        )
        try:
            df_orphans = pd.read_sql_query(
                "SELECT name, entity_type, project, mention_count FROM entities WHERE id NOT IN (SELECT source_entity_id FROM entity_relations) AND id NOT IN (SELECT target_entity_id FROM entity_relations)",
                conn,
            )
        except (sqlite3.OperationalError, pd.errors.DatabaseError):
            df_orphans = pd.DataFrame(columns=["name", "entity_type", "project", "mention_count"])
        df = pd.read_sql_query(
            "SELECT project, fact_type, content, confidence, tags FROM facts WHERE valid_until IS NULL",
            conn,
        )

    projects = df["project"].unique()
    for project in projects:
        proj_df = df[df["project"] == project]
        filename = OUTPUT_DIR / f"{project}_knowledge.md"

        proj_orphans = (
            df_orphans[df_orphans["project"] == project]["name"].tolist()
            if not df_orphans.empty
            else []
        )
        unverified_count = (
            df_unverified[df_unverified["project"] == project][["count"]].sum().iloc[0]
            if not df_unverified.empty and project in df_unverified["project"].values
            else 0
        )

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# 🧠 CORTEX Domain: {project.upper()}\n\n")
            if unverified_count > 0 or proj_orphans:
                f.write(f"## 🔍 NOTAS DE INVESTIGACIÓN (CRÍTICO)\n")
                f.write(
                    f"> NotebookLM: He detectado las siguientes lagunas en CORTEX para este proyecto.\n"
                )
                if unverified_count > 0:
                    f.write(
                        f"- Hay **{unverified_count}** hechos sin verificar que requieren validación lógica.\n"
                    )
                if proj_orphans:
                    f.write(
                        f"- Las siguientes entidades carecen de conexiones relacionales: {', '.join(proj_orphans[:5])}.\n"
                    )
                f.write("\n")

            f.write(f"## Base de Conocimiento\n")
            for ftype in proj_df["fact_type"].unique():
                f.write(f"### {ftype.capitalize()}\n")
                type_df = proj_df[proj_df["fact_type"] == ftype]
                for _, row in type_df.iterrows():
                    f.write(f"- **{row['content']}** (Confid: {row['confidence']})\n")

        print(f"✅ {filename.name} sintetizado.")


if __name__ == "__main__":
    run()
