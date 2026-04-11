"""
Knowledge Graph Builder
=======================
Orchestrates text preprocessing + entity extraction ->
builds NetworkX graph -> serializes to graph_data.json.
"""

import os
import sys
import json
import math
from collections import defaultdict

# Add project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    import networkx as nx
except ImportError:
    print("Installing networkx...")
    os.system(f"{sys.executable} -m pip install networkx")
    import networkx as nx

from graph.text_preprocessor import load_all_data, COMPANIES
from graph.entity_extractor import (
    extract_entities_from_chunk,
    extract_cooccurrences,
    get_recency_score,
    COMPANY_NAMES,
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
GRAPH_JSON_PATH = os.path.join(OUTPUT_DIR, "graph_data.json")


def build_graph():
    """Main pipeline: load data -> extract entities -> build graph."""

    print("=" * 60)
    print("  Knowledge Graph Builder")
    print("=" * 60)

    # Step 1: Load all text data
    print("\n[1/4] Loading textual data...")
    all_chunks = load_all_data()
    print(f"  Total chunks: {len(all_chunks)}")

    # Step 2: Extract entities + co-occurrences from each chunk
    print("\n[2/4] Extracting entities...")

    # Track node occurrences and edge co-occurrences
    node_data = defaultdict(lambda: {
        "type": "",
        "count": 0,
        "companies": set(),
        "doc_types": set(),
        "periods": set(),
        "sources": [],
    })

    edge_data = defaultdict(lambda: {
        "count": 0,
        "weight": 0.0,
        "companies": set(),
        "doc_types": set(),
        "sample_contexts": [],
    })

    chunk_count = 0
    for chunk in all_chunks:
        entities = extract_entities_from_chunk(chunk)
        cooccurrences = extract_cooccurrences(entities)

        company = chunk.get("company", "")
        doc_type = chunk.get("doc_type", "")
        period = chunk.get("period", "")
        recency = get_recency_score(period)

        # Register nodes
        for etype, elist in entities.items():
            for ename, emeta in elist:
                node_key = f"{etype}::{ename}"
                nd = node_data[node_key]
                nd["type"] = etype
                nd["count"] += 1
                if company:
                    nd["companies"].add(company)
                if doc_type:
                    nd["doc_types"].add(doc_type)
                if period:
                    nd["periods"].add(period)

        # Register edges
        for edge in cooccurrences:
            src_type, src_name = edge["source"]
            tgt_type, tgt_name = edge["target"]
            src_key = f"{src_type}::{src_name}"
            tgt_key = f"{tgt_type}::{tgt_name}"
            edge_key = tuple(sorted([src_key, tgt_key]))

            ed = edge_data[edge_key]
            ed["count"] += 1
            ed["weight"] += recency  # weight by recency
            if company:
                ed["companies"].add(company)
            if doc_type:
                ed["doc_types"].add(doc_type)

            # Store sample context (first 3)
            if len(ed["sample_contexts"]) < 3:
                ed["sample_contexts"].append(chunk["text"][:200])

        chunk_count += 1
        if chunk_count % 500 == 0:
            print(f"  Processed {chunk_count}/{len(all_chunks)} chunks...")

    print(f"  Raw nodes: {len(node_data)}")
    print(f"  Raw edges: {len(edge_data)}")

    # Step 3: Build NetworkX graph (filter low-signal nodes/edges)
    print("\n[3/4] Building graph (filtering noise)...")

    G = nx.Graph()

    # Add nodes - filter METRIC nodes (too noisy), keep rest with count >= 2
    node_filter_counts = {"COMPANY": 1, "PERSON": 2, "TOPIC": 2, "BRAND": 2,
                          "LOCATION": 2, "STRATEGY": 2, "TIME_PERIOD": 3}

    for node_key, nd in node_data.items():
        ntype = nd["type"]
        if ntype == "METRIC":
            continue  # skip raw metrics in graph (too many)
        min_count = node_filter_counts.get(ntype, 3)
        if nd["count"] < min_count:
            continue

        G.add_node(node_key, **{
            "label": node_key.split("::")[-1],
            "type": ntype,
            "count": nd["count"],
            "companies": list(nd["companies"]),
            "doc_types": list(nd["doc_types"]),
            "num_companies": len(nd["companies"]),
        })

    # Add edges - only between existing nodes, weight >= 1.5
    graph_nodes = set(G.nodes())
    for edge_key, ed in edge_data.items():
        src, tgt = edge_key
        if src not in graph_nodes or tgt not in graph_nodes:
            continue

        # Calculate final weight
        freq_score = math.log(1 + ed["count"])
        weight = freq_score * (ed["weight"] / max(ed["count"], 1))

        if weight < 0.3:
            continue

        G.add_edge(src, tgt, **{
            "weight": round(weight, 3),
            "count": ed["count"],
            "companies": list(ed["companies"]),
            "doc_types": list(ed["doc_types"]),
            "sample_contexts": ed["sample_contexts"][:2],
        })

    print(f"  Final nodes: {G.number_of_nodes()}")
    print(f"  Final edges: {G.number_of_edges()}")

    # Print breakdown by type
    type_counts = defaultdict(int)
    for _, data in G.nodes(data=True):
        type_counts[data["type"]] += 1
    for ntype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {ntype}: {count}")

    # Step 4: Serialize to JSON for D3.js visualization
    print("\n[4/4] Serializing graph...")

    graph_json = {
        "nodes": [],
        "edges": [],
        "stats": {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "type_counts": dict(type_counts),
            "companies": list(COMPANY_NAMES.values()),
        },
    }

    for node_id, data in G.nodes(data=True):
        graph_json["nodes"].append({
            "id": node_id,
            "label": data["label"],
            "type": data["type"],
            "count": data["count"],
            "companies": data["companies"],
            "num_companies": data["num_companies"],
        })

    for src, tgt, data in G.edges(data=True):
        graph_json["edges"].append({
            "source": src,
            "target": tgt,
            "weight": data["weight"],
            "count": data["count"],
            "companies": data["companies"],
            "contexts": data.get("sample_contexts", []),
        })

    with open(GRAPH_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(graph_json, f, indent=2, ensure_ascii=False)

    print(f"  Saved -> {GRAPH_JSON_PATH}")
    print(f"  File size: {os.path.getsize(GRAPH_JSON_PATH) / 1024:.1f} KB")

    print(f"\n{'='*60}")
    print(f"  [OK] Graph built successfully!")
    print(f"{'='*60}\n")

    return G


if __name__ == "__main__":
    G = build_graph()
