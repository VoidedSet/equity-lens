"""
Neo4j Client for Knowledge Graph
=================================
Query interface for the migrated knowledge graph in Neo4j.
"""

import os
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase


class Neo4jClient:
    def __init__(self, uri: str = None, user: str = None, password: str = None, database: str = None):
        self.uri = uri or os.getenv("GRAPH_NEO4J_URI", "neo4j://127.0.0.1:7687")
        self.user = user or os.getenv("GRAPH_NEO4J_USER", "neo4j")
        self.password = password or os.getenv("GRAPH_NEO4J_PASSWORD", "kshayik1")
        self.database = database or os.getenv("GRAPH_NEO4J_DATABASE", "datahack-graphdb")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _run_query(self, query: str, params: dict = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results as list of dicts."""
        with self.driver.session(database=self.database) as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    def get_schema(self) -> Dict[str, Any]:
        """Get graph schema for AI context."""
        node_labels_query = "CALL db.labels() YIELD label RETURN collect(label) as labels"
        rel_types_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
        
        node_labels = self._run_query(node_labels_query)[0]["labels"]
        rel_types = self._run_query(rel_types_query)[0]["types"]
        
        # Get sample properties for each node type
        node_schemas = {}
        for label in node_labels:
            sample_query = f"""
            MATCH (n:{label})
            WITH n LIMIT 1
            RETURN keys(n) as properties
            """
            props = self._run_query(sample_query)
            node_schemas[label] = props[0]["properties"] if props else []
        
        return {
            "node_labels": node_labels,
            "relationship_types": rel_types,
            "node_properties": node_schemas,
        }

    def search_nodes(
        self,
        query: str = "",
        node_type: str = None,
        company_filter: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search nodes by name with optional filters."""
        cypher = """
        MATCH (n)
        WHERE ($query = '' OR toLower(n.name) CONTAINS toLower($query) OR toLower(n.label) CONTAINS toLower($query))
        """
        
        params = {"query": query, "limit": limit}
        
        if node_type:
            cypher += f" AND '{node_type}' IN labels(n)"
        
        if company_filter:
            cypher += """
            AND (
                n.code = $company 
                OR $company IN n.companies
            )
            """
            params["company"] = company_filter
        
        cypher += """
        RETURN 
            elementId(n) as id,
            labels(n)[0] as type,
            coalesce(n.name, n.label, n.code) as name,
            coalesce(n.count, 0) as count,
            coalesce(n.companies, []) as companies
        ORDER BY count DESC
        LIMIT $limit
        """
        
        return self._run_query(cypher, params)

    def get_node_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        max_nodes: int = 100
    ) -> Dict[str, Any]:
        """Get neighborhood subgraph around a node."""
        cypher_simple = """
        MATCH (start)
        WHERE elementId(start) = $node_id
        OPTIONAL MATCH (start)-[r]-(neighbor)
        WITH start, collect(DISTINCT neighbor)[0..$max_nodes] as neighbors
        UNWIND neighbors as n
        OPTIONAL MATCH (n)-[r2]-(m)
        WHERE m = start OR m IN neighbors
        WITH start, neighbors, collect(DISTINCT r2) as rels
        UNWIND neighbors as n
        RETURN 
            collect(DISTINCT {
                id: elementId(n),
                type: labels(n)[0],
                name: coalesce(n.name, n.label, n.code),
                count: coalesce(n.count, 0),
                companies: coalesce(n.companies, [])
            })[0..$max_nodes] as nodes,
            [rel in rels | {
                source: elementId(startNode(rel)),
                target: elementId(endNode(rel)),
                type: type(rel),
                weight: coalesce(rel.weight, 1),
                count: coalesce(rel.count, 0)
            }][0..$max_nodes] as edges
        """
        
        params = {"node_id": node_id, "depth": depth, "max_nodes": max_nodes}
        result = self._run_query(cypher_simple, params)
        
        if result:
            return {
                "nodes": result[0].get("nodes", []),
                "edges": result[0].get("edges", [])
            }
        return {"nodes": [], "edges": []}

    def get_company_subgraph(self, company_code: str, max_nodes: int = 100) -> Dict[str, Any]:
        """Get all nodes associated with a company."""
        # Step 1: Collect the Company node + all entity nodes whose companies array contains the code
        node_cypher = """
        MATCH (c:Company {code: $code})
        WITH c
        OPTIONAL MATCH (entity)
        WHERE entity <> c AND $code IN entity.companies
        WITH c, collect(DISTINCT entity)[0..$max_nodes] as entities
        RETURN
            [{
                id: elementId(c),
                type: 'Company',
                name: coalesce(c.name, c.code),
                code: c.code,
                count: coalesce(c.count, 0)
            }] + [e in entities | {
                id: elementId(e),
                type: labels(e)[0],
                name: coalesce(e.name, e.label),
                count: coalesce(e.count, 0),
                companies: coalesce(e.companies, [])
            }] as nodes,
            [e in entities | elementId(e)] as entity_ids,
            elementId(c) as company_id
        """
        
        params = {"code": company_code, "max_nodes": max_nodes}
        node_result = self._run_query(node_cypher, params)
        
        if not node_result:
            return {"nodes": [], "edges": []}
        
        nodes = node_result[0].get("nodes", [])
        entity_ids = node_result[0].get("entity_ids", [])
        company_id = node_result[0].get("company_id")
        
        all_ids = entity_ids + ([company_id] if company_id else [])
        
        # Step 2: Get edges between the collected nodes
        edges = []
        if len(all_ids) > 1:
            edge_cypher = """
            MATCH (a)-[r]-(b)
            WHERE elementId(a) IN $ids AND elementId(b) IN $ids
              AND elementId(a) < elementId(b)
            RETURN DISTINCT
                elementId(startNode(r)) as source,
                elementId(endNode(r)) as target,
                type(r) as type,
                coalesce(r.weight, 1) as weight,
                coalesce(r.count, 0) as count,
                coalesce(r.companies, []) as companies
            LIMIT $max_edges
            """
            edge_result = self._run_query(edge_cypher, {"ids": all_ids, "max_edges": max_nodes * 3})
            edges = edge_result if edge_result else []
        
        return {"nodes": nodes, "edges": edges}

    def get_company_profile(self, company_name: str) -> Dict[str, Any]:
        """Get complete profile of a company from graph."""
        cypher = """
        MATCH (c:Company)
        WHERE c.code = $code OR toLower(c.name) CONTAINS toLower($name)
        OPTIONAL MATCH (c)-[r]-(entity)
        WHERE c.code IN entity.companies
        WITH c, entity, labels(entity)[0] as entityType
        RETURN 
            c.name as company,
            c.code as code,
            collect(DISTINCT {
                type: entityType,
                name: coalesce(entity.name, entity.label),
                count: coalesce(entity.count, 0)
            }) as connections,
            count(DISTINCT entity) as total_connections
        """
        
        params = {"code": company_name.upper(), "name": company_name}
        result = self._run_query(cypher, params)
        
        if not result:
            return {"error": "Company not found"}
        
        data = result[0]
        profile = {
            "company": data["company"],
            "code": data["code"],
            "total_connections": data["total_connections"],
            "topics": [],
            "brands": [],
            "locations": [],
            "strategies": [],
            "people": []
        }
        
        for conn in data["connections"]:
            entity_type = conn["type"]
            entry = {"name": conn["name"], "mentions": conn["count"]}
            
            if entity_type == "Topic":
                profile["topics"].append(entry)
            elif entity_type == "Brand":
                profile["brands"].append(entry)
            elif entity_type == "Location":
                profile["locations"].append(entry)
            elif entity_type == "Strategy":
                profile["strategies"].append(entry)
            elif entity_type == "Person":
                profile["people"].append(entry)
        
        for key in ["topics", "brands", "locations", "strategies", "people"]:
            profile[key] = sorted(profile[key], key=lambda x: -x["mentions"])
        
        return profile

    def compare_companies(self, company1: str, company2: str) -> Dict[str, Any]:
        """Compare two companies: shared and unique entities."""
        cypher = """
        MATCH (c1:Company), (c2:Company)
        WHERE (c1.code = $code1 OR toLower(c1.name) CONTAINS toLower($name1))
          AND (c2.code = $code2 OR toLower(c2.name) CONTAINS toLower($name2))
        OPTIONAL MATCH (c1)--(e1)
        WHERE c1.code IN e1.companies AND labels(e1)[0] IN ['Topic', 'Brand', 'Location', 'Strategy']
        OPTIONAL MATCH (c2)--(e2)
        WHERE c2.code IN e2.companies AND labels(e2)[0] IN ['Topic', 'Brand', 'Location', 'Strategy']
        WITH c1, c2,
             collect(DISTINCT {type: labels(e1)[0], name: coalesce(e1.name, e1.label)}) as entities1,
             collect(DISTINCT {type: labels(e2)[0], name: coalesce(e2.name, e2.label)}) as entities2
        RETURN 
            c1.name as company1,
            c2.name as company2,
            entities1,
            entities2
        """
        
        params = {
            "code1": company1.upper(), "name1": company1,
            "code2": company2.upper(), "name2": company2
        }
        result = self._run_query(cypher, params)
        
        if not result:
            return {"error": "Companies not found"}
        
        data = result[0]
        e1_set = {(e["type"], e["name"]) for e in data["entities1"] if e["type"]}
        e2_set = {(e["type"], e["name"]) for e in data["entities2"] if e["type"]}
        
        shared = e1_set & e2_set
        unique1 = e1_set - e2_set
        unique2 = e2_set - e1_set
        
        result_dict = {
            "company1": data["company1"],
            "company2": data["company2"],
            "shared": {},
            "unique_to_1": {},
            "unique_to_2": {},
            "similarity_score": 0.0
        }
        
        for entity_type, name in shared:
            if entity_type not in result_dict["shared"]:
                result_dict["shared"][entity_type] = []
            result_dict["shared"][entity_type].append(name)
        
        for entity_type, name in unique1:
            if entity_type not in result_dict["unique_to_1"]:
                result_dict["unique_to_1"][entity_type] = []
            result_dict["unique_to_1"][entity_type].append(name)
        
        for entity_type, name in unique2:
            if entity_type not in result_dict["unique_to_2"]:
                result_dict["unique_to_2"][entity_type] = []
            result_dict["unique_to_2"][entity_type].append(name)
        
        total_union = len(e1_set | e2_set)
        if total_union > 0:
            result_dict["similarity_score"] = round(len(shared) / total_union * 100, 1)
        
        return result_dict

    def find_connections(self, term1: str, term2: str) -> Dict[str, Any]:
        """Find shortest path between two entities."""
        cypher = """
        MATCH (n1), (n2)
        WHERE (toLower(coalesce(n1.name, n1.label)) CONTAINS toLower($term1))
          AND (toLower(coalesce(n2.name, n2.label)) CONTAINS toLower($term2))
        WITH n1, n2 LIMIT 1
        MATCH path = shortestPath((n1)-[*..5]-(n2))
        RETURN 
            coalesce(n1.name, n1.label) as term1,
            coalesce(n2.name, n2.label) as term2,
            [node in nodes(path) | coalesce(node.name, node.label)] as path,
            length(path) as path_length
        """
        
        params = {"term1": term1, "term2": term2}
        result = self._run_query(cypher, params)
        
        if not result:
            return {"error": f"Could not find nodes for: {term1}, {term2}"}
        
        data = result[0]
        return {
            "term1": data["term1"],
            "term2": data["term2"],
            "shortest_path": data["path"],
            "path_length": data["path_length"],
            "directly_connected": data["path_length"] == 1
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get overall graph statistics."""
        cypher = """
        MATCH (n)
        WITH labels(n)[0] as type, count(*) as count
        RETURN collect({type: type, count: count}) as type_counts
        """
        
        type_data = self._run_query(cypher)[0]["type_counts"]
        
        edge_cypher = "MATCH ()-[r]->() RETURN count(r) as edge_count"
        edge_count = self._run_query(edge_cypher)[0]["edge_count"]
        
        total_nodes = sum(t["count"] for t in type_data)
        
        return {
            "total_nodes": total_nodes,
            "total_edges": edge_count,
            "type_breakdown": {t["type"]: t["count"] for t in type_data}
        }


if __name__ == "__main__":
    # Test queries
    with Neo4jClient() as client:
        print("=== Graph Stats ===")
        stats = client.get_stats()
        print(f"Nodes: {stats['total_nodes']}, Edges: {stats['total_edges']}")
        print(f"Types: {stats['type_breakdown']}")
        
        print("\n=== Search 'Mumbai' ===")
        results = client.search_nodes("Mumbai", limit=5)
        for r in results:
            print(f"  {r['type']}: {r['name']} (count: {r['count']})")
        
        print("\n=== Company Profile: IHCL ===")
        profile = client.get_company_profile("IHCL")
        print(f"  Company: {profile.get('company')}")
        print(f"  Topics: {len(profile.get('topics', []))}")
        print(f"  Brands: {len(profile.get('brands', []))}")
