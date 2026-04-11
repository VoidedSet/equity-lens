"""
Graph Analyzer
==============
Query and compare functions for the knowledge graph.
Loads graph_data.json, provides structured analysis.
"""

import os
import sys
import json
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    import networkx as nx
except ImportError:
    os.system(f"{sys.executable} -m pip install networkx")
    import networkx as nx

GRAPH_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph_data.json")

COMPANY_CODE_MAP = {
    "chalet": "CHALET", "chalet hotels": "CHALET", "chalet_hotels": "CHALET",
    "eih": "EIH", "eih limited": "EIH", "eih_limited": "EIH", "oberoi": "EIH",
    "ihcl": "IHCL", "indian hotels": "IHCL", "indian_hotels": "IHCL", "taj": "IHCL",
    "juniper": "JUNIPER", "juniper hotels": "JUNIPER", "juniper_hotels": "JUNIPER",
    "lemontree": "LEMONTREE", "lemon tree": "LEMONTREE", "lemon_tree_hotels": "LEMONTREE",
    "lemon tree hotels": "LEMONTREE",
}


def load_graph():
    """Load graph from JSON."""
    if not os.path.exists(GRAPH_JSON_PATH):
        print(f"Graph not found. Run: python graph/build_graph.py first")
        return None

    with open(GRAPH_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    G = nx.Graph()
    for node in data["nodes"]:
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
    for edge in data["edges"]:
        G.add_edge(edge["source"], edge["target"], **{
            k: v for k, v in edge.items() if k not in ("source", "target")
        })
    return G


def resolve_company(name: str) -> str:
    """Resolve company alias to code."""
    return COMPANY_CODE_MAP.get(name.lower().strip(), name.upper())


def get_company_profile(company_name: str) -> dict:
    """Get complete profile of a company from graph."""
    G = load_graph()
    if G is None:
        return {"error": "Graph not built"}

    code = resolve_company(company_name)
    company_node = f"COMPANY::{code}"

    # Find display name
    display_names = {
        "CHALET": "Chalet Hotels", "EIH": "EIH Limited",
        "IHCL": "Indian Hotels", "JUNIPER": "Juniper Hotels",
        "LEMONTREE": "Lemon Tree Hotels",
    }
    display = display_names.get(code, code)

    # Find all nodes connected to this company
    profile = {
        "company": display,
        "topics": [],
        "brands": [],
        "locations": [],
        "strategies": [],
        "people": [],
        "total_connections": 0,
    }

    # Find nodes where this company code appears in companies list
    for node_id, data in G.nodes(data=True):
        if code in data.get("companies", []):
            ntype = data.get("type", "")
            label = data.get("label", "")
            count = data.get("count", 0)

            entry = {"name": label, "mentions": count}

            if ntype == "TOPIC":
                profile["topics"].append(entry)
            elif ntype == "BRAND":
                profile["brands"].append(entry)
            elif ntype == "LOCATION":
                profile["locations"].append(entry)
            elif ntype == "STRATEGY":
                profile["strategies"].append(entry)
            elif ntype == "PERSON":
                profile["people"].append(entry)

    # Sort by mentions
    for key in ["topics", "brands", "locations", "strategies", "people"]:
        profile[key] = sorted(profile[key], key=lambda x: -x["mentions"])
        profile["total_connections"] += len(profile[key])

    return profile


def compare_companies(company1: str, company2: str) -> dict:
    """Compare two companies: shared topics, unique topics, common strategies."""
    G = load_graph()
    if G is None:
        return {"error": "Graph not built"}

    code1 = resolve_company(company1)
    code2 = resolve_company(company2)

    display_names = {
        "CHALET": "Chalet Hotels", "EIH": "EIH Limited",
        "IHCL": "Indian Hotels", "JUNIPER": "Juniper Hotels",
        "LEMONTREE": "Lemon Tree Hotels",
    }

    # Collect entities per company
    entities1 = defaultdict(set)
    entities2 = defaultdict(set)

    for node_id, data in G.nodes(data=True):
        companies = data.get("companies", [])
        ntype = data.get("type", "")
        label = data.get("label", "")

        if ntype in ("COMPANY", "TIME_PERIOD", "METRIC"):
            continue

        if code1 in companies:
            entities1[ntype].add(label)
        if code2 in companies:
            entities2[ntype].add(label)

    # Calculate shared and unique
    result = {
        "company1": display_names.get(code1, code1),
        "company2": display_names.get(code2, code2),
        "shared": {},
        "unique_to_1": {},
        "unique_to_2": {},
        "similarity_score": 0.0,
    }

    total_shared = 0
    total_union = 0

    for ntype in set(list(entities1.keys()) + list(entities2.keys())):
        s1 = entities1.get(ntype, set())
        s2 = entities2.get(ntype, set())
        shared = s1 & s2
        only1 = s1 - s2
        only2 = s2 - s1

        if shared:
            result["shared"][ntype] = sorted(list(shared))
        if only1:
            result["unique_to_1"][ntype] = sorted(list(only1))
        if only2:
            result["unique_to_2"][ntype] = sorted(list(only2))

        total_shared += len(shared)
        total_union += len(s1 | s2)

    # Jaccard similarity
    if total_union > 0:
        result["similarity_score"] = round(total_shared / total_union * 100, 1)

    return result


def get_topic_leaders(topic: str) -> dict:
    """Which company discusses a topic most?"""
    G = load_graph()
    if G is None:
        return {"error": "Graph not built"}

    # Find the topic node
    topic_node = None
    for node_id, data in G.nodes(data=True):
        if data.get("type") == "TOPIC" and data.get("label", "").lower() == topic.lower():
            topic_node = node_id
            break

    if not topic_node:
        # Try partial match
        for node_id, data in G.nodes(data=True):
            if data.get("type") == "TOPIC" and topic.lower() in data.get("label", "").lower():
                topic_node = node_id
                break

    if not topic_node:
        return {"error": f"Topic '{topic}' not found", "available_topics": get_all_topics(G)}

    node_data = G.nodes[topic_node]
    companies = node_data.get("companies", [])

    # Count mentions per company by looking at connected edges
    company_scores = {}
    for neighbor in G.neighbors(topic_node):
        ndata = G.nodes[neighbor]
        if ndata.get("type") == "COMPANY":
            edge_data = G.edges[topic_node, neighbor]
            company_scores[ndata["label"]] = {
                "weight": edge_data.get("weight", 0),
                "mentions": edge_data.get("count", 0),
            }

    return {
        "topic": node_data["label"],
        "total_mentions": node_data["count"],
        "companies_discussing": companies,
        "company_scores": company_scores,
    }


def get_all_topics(G=None) -> list:
    """Get all topic nodes."""
    if G is None:
        G = load_graph()
    if G is None:
        return []
    return sorted([
        data["label"] for _, data in G.nodes(data=True)
        if data.get("type") == "TOPIC"
    ])


def find_connections(term1: str, term2: str) -> dict:
    """Find connections between two entities."""
    G = load_graph()
    if G is None:
        return {"error": "Graph not built"}

    # Find nodes matching terms
    node1 = None
    node2 = None
    for node_id, data in G.nodes(data=True):
        label = data.get("label", "").lower()
        if term1.lower() in label and node1 is None:
            node1 = node_id
        if term2.lower() in label and node2 is None:
            node2 = node_id

    if not node1 or not node2:
        return {"error": f"Could not find nodes for: {term1}, {term2}"}

    result = {
        "term1": G.nodes[node1]["label"],
        "term2": G.nodes[node2]["label"],
        "directly_connected": G.has_edge(node1, node2),
    }

    # Find shortest path
    try:
        path = nx.shortest_path(G, node1, node2)
        result["shortest_path"] = [G.nodes[n]["label"] for n in path]
        result["path_length"] = len(path) - 1
    except nx.NetworkXNoPath:
        result["shortest_path"] = None
        result["path_length"] = -1

    # If directly connected, show edge data
    if result["directly_connected"]:
        edge_data = G.edges[node1, node2]
        result["edge_weight"] = edge_data.get("weight", 0)
        result["co_occurrences"] = edge_data.get("count", 0)
        result["contexts"] = edge_data.get("contexts", [])

    return result


def get_graph_summary() -> dict:
    """Get overall graph statistics."""
    G = load_graph()
    if G is None:
        return {"error": "Graph not built"}

    type_counts = defaultdict(int)
    for _, data in G.nodes(data=True):
        type_counts[data.get("type", "UNKNOWN")] += 1

    # Top nodes by degree
    top_nodes = sorted(G.degree(), key=lambda x: -x[1])[:15]
    top_list = []
    for node_id, degree in top_nodes:
        data = G.nodes[node_id]
        top_list.append({
            "label": data["label"],
            "type": data["type"],
            "connections": degree,
        })

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "type_breakdown": dict(type_counts),
        "most_connected": top_list,
        "density": round(nx.density(G), 4),
        "components": nx.number_connected_components(G),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Query the knowledge graph")
    parser.add_argument("action", choices=["summary", "profile", "compare", "topic", "connect"])
    parser.add_argument("--company", "-c", help="Company name")
    parser.add_argument("--company2", "-c2", help="Second company (for compare)")
    parser.add_argument("--topic", "-t", help="Topic name")
    parser.add_argument("--term1", help="First term (for connect)")
    parser.add_argument("--term2", help="Second term (for connect)")
    args = parser.parse_args()

    if args.action == "summary":
        result = get_graph_summary()
    elif args.action == "profile":
        result = get_company_profile(args.company or "IHCL")
    elif args.action == "compare":
        result = compare_companies(args.company or "IHCL", args.company2 or "EIH")
    elif args.action == "topic":
        result = get_topic_leaders(args.topic or "Revenue")
    elif args.action == "connect":
        result = find_connections(args.term1 or "Expansion", args.term2 or "Goa")
    else:
        result = {"error": "Unknown action"}

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
