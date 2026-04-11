import json
import os
import sys
from pathlib import Path
from typing import List

from neo4j import GraphDatabase


UPSERT_QUERY = """
UNWIND $events AS e
MERGE (ev:Event {event_id: e.event_id})
  ON CREATE SET ev.created_at = datetime()
SET ev.title = e.title,
    ev.summary = e.summary,
    ev.url = e.url,
    ev.published_date = e.published_date,
    ev.as_of_date = e.as_of_date,
    ev.event_type = e.event_type,
    ev.sentiment = e.sentiment,
    ev.market_scope = e.market_scope,
    ev.dimension_primary = e.dimension_primary,
    ev.relevance_score = e.relevance_score,
    ev.stage2_confidence = e.stage2_confidence,
    ev.graph_confidence = e.graph_confidence,
    ev.quality = e.quality,
    ev.updated_at = datetime()

MERGE (s:Source {name: e.source})
MERGE (sb:SourceBucket {name: e.source_bucket})
MERGE (d:Dimension {name: e.dimension_primary})
MERGE (ev)-[:FROM_SOURCE]->(s)
MERGE (ev)-[:IN_SOURCE_BUCKET]->(sb)
MERGE (ev)-[:ALIGNS_WITH]->(d)

FOREACH (c IN e.companies |
  MERGE (co:Company {code: c})
  MERGE (co)-[rel:AFFECTED_BY {event_id: e.event_id}]->(ev)
  SET rel.confidence = e.graph_confidence,
      rel.quality = e.quality,
      rel.sentiment = e.sentiment,
      rel.dimension_primary = e.dimension_primary,
      rel.published_date = e.published_date,
      rel.as_of_date = e.as_of_date,
      rel.url = e.url
)

FOREACH (m IN e.metrics |
  MERGE (metric:Metric {name: m})
  MERGE (ev)-[:IMPACTS_METRIC]->(metric)
)

MERGE (t:Topic {name: e.event_type})
MERGE (ev)-[:TAGGED_AS]->(t)
"""


def load_events(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        raise ValueError("Graph payload must be a JSON list")
    return payload


def run_import(graph_events_path: Path) -> int:
    uri = os.getenv("GRAPH_NEO4J_URI", "neo4j://127.0.0.1:7687").strip()
    user = os.getenv("GRAPH_NEO4J_USER", "neo4j").strip()
    password = os.getenv("GRAPH_NEO4J_PASSWORD", "kshayik1").strip()
    database = os.getenv("GRAPH_NEO4J_DATABASE", "datahack-graphdb").strip() or None

    if not password:
        print("[error] GRAPH_NEO4J_PASSWORD missing")
        return 1

    if not graph_events_path.exists():
        print(f"[error] graph events file not found: {graph_events_path}")
        return 1

    events = load_events(graph_events_path)
    if not events:
        print("[warn] no events to import")
        return 0

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) if database else driver.session() as session:
            session.run("CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE")
            session.run("CREATE CONSTRAINT company_code_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.code IS UNIQUE")
            session.run("CREATE CONSTRAINT source_name_unique IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE")
            session.run(UPSERT_QUERY, events=events)
        print(f"[done] imported {len(events)} graph events")
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        payload_arg = Path(sys.argv[1])
    else:
        output_dir = Path("../worflow_news/output")
        candidates = sorted(output_dir.glob("graph_events_*.json"))
        if not candidates:
            print("[error] no graph_events_*.json found. run news pipeline first or pass file path")
            sys.exit(1)
        payload_arg = candidates[-1]
    sys.exit(run_import(payload_arg))