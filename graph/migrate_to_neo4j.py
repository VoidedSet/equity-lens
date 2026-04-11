"""
Migrate Knowledge Graph to Neo4j
=================================
One-time migration script to load graph_data.json into Neo4j.
"""

import os
import sys
import json
from neo4j import GraphDatabase

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

GRAPH_JSON_PATH = os.path.join(os.path.dirname(__file__), "graph_data.json")

NEO4J_URI = os.getenv("GRAPH_NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("GRAPH_NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("GRAPH_NEO4J_PASSWORD", "kshayik1")
NEO4J_DATABASE = os.getenv("GRAPH_NEO4J_DATABASE", "datahack-graphdb")


def load_graph_json():
    """Load the graph_data.json file."""
    print(f"Loading graph from: {GRAPH_JSON_PATH}")
    with open(GRAPH_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"  Nodes: {len(data['nodes'])}")
    print(f"  Edges: {len(data['edges'])}")
    return data


def clear_existing_graph(driver, database):
    """Clear existing knowledge graph nodes (keep news events)."""
    print("\nClearing existing knowledge graph nodes...")
    
    with driver.session(database=database) as session:
        # Delete only knowledge graph nodes (not Event nodes from news)
        result = session.run("""
            MATCH (n)
            WHERE n:Company OR n:Topic OR n:Brand OR n:Location 
               OR n:Strategy OR n:Person OR n:TimePeriod
            DETACH DELETE n
            RETURN count(n) as deleted
        """)
        deleted = result.single()["deleted"]
        print(f"  Deleted {deleted} knowledge graph nodes")


def create_constraints(driver, database):
    """Create constraints and indexes."""
    print("\nCreating constraints and indexes...")
    
    constraints = [
        "CREATE CONSTRAINT company_code_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.code IS UNIQUE",
        "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
        "CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.name)",
        "CREATE INDEX brand_name IF NOT EXISTS FOR (b:Brand) ON (b.name)",
        "CREATE INDEX location_name IF NOT EXISTS FOR (l:Location) ON (l.name)",
        "CREATE INDEX strategy_name IF NOT EXISTS FOR (s:Strategy) ON (s.name)",
        "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
    ]
    
    with driver.session(database=database) as session:
        for constraint in constraints:
            try:
                session.run(constraint)
                print(f"  ✓ {constraint.split()[1]}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  ✗ {constraint.split()[1]}: {e}")


def migrate_nodes(driver, database, nodes):
    """Migrate nodes to Neo4j."""
    print(f"\nMigrating {len(nodes)} nodes...")
    
    # Group nodes by type for batch processing
    nodes_by_type = {}
    for node in nodes:
        node_type = node["type"]
        if node_type not in nodes_by_type:
            nodes_by_type[node_type] = []
        nodes_by_type[node_type].append(node)
    
    with driver.session(database=database) as session:
        for node_type, type_nodes in nodes_by_type.items():
            print(f"  Processing {len(type_nodes)} {node_type} nodes...")
            
            # Batch insert
            batch_size = 500
            for i in range(0, len(type_nodes), batch_size):
                batch = type_nodes[i:i+batch_size]
                
                # Build Cypher query based on node type
                if node_type == "COMPANY":
                    query = f"""
                    UNWIND $nodes AS node
                    MERGE (n:Company {{code: split(node.id, '::')[1]}})
                    SET n.name = node.label,
                        n.count = node.count,
                        n.companies = node.companies
                    """
                else:
                    query = f"""
                    UNWIND $nodes AS node
                    MERGE (n:{node_type} {{name: node.label}})
                    SET n.count = node.count,
                        n.companies = node.companies,
                        n.num_companies = node.num_companies
                    """
                
                session.run(query, nodes=batch)
            
            print(f"    ✓ {len(type_nodes)} {node_type} nodes created")


def migrate_edges(driver, database, edges, nodes):
    """Migrate edges to Neo4j."""
    print(f"\nMigrating {len(edges)} edges...")
    
    # Create a mapping from node id to (type, label)
    node_map = {}
    for node in nodes:
        node_type = node["type"]
        label = node["label"]
        if node_type == "COMPANY":
            # Company nodes use code as identifier
            code = node["id"].split("::")[-1]
            node_map[node["id"]] = ("Company", code, "code")
        else:
            node_map[node["id"]] = (node_type, label, "name")
    
    with driver.session(database=database) as session:
        batch_size = 500
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i+batch_size]
            
            # Prepare edge data with node type info
            edge_data = []
            for edge in batch:
                source_id = edge["source"]
                target_id = edge["target"]
                
                if source_id not in node_map or target_id not in node_map:
                    continue
                
                source_type, source_val, source_prop = node_map[source_id]
                target_type, target_val, target_prop = node_map[target_id]
                
                edge_data.append({
                    "source_type": source_type,
                    "source_val": source_val,
                    "source_prop": source_prop,
                    "target_type": target_type,
                    "target_val": target_val,
                    "target_prop": target_prop,
                    "weight": edge.get("weight", 1.0),
                    "count": edge.get("count", 1),
                    "companies": edge.get("companies", []),
                    "contexts": edge.get("contexts", [])
                })
            
            # Create relationships
            query = """
            UNWIND $edges AS edge
            CALL {
                WITH edge
                MATCH (source)
                WHERE edge.source_type IN labels(source)
                  AND source[edge.source_prop] = edge.source_val
                MATCH (target)
                WHERE edge.target_type IN labels(target)
                  AND target[edge.target_prop] = edge.target_val
                MERGE (source)-[r:CO_OCCURS]-(target)
                SET r.weight = edge.weight,
                    r.count = edge.count,
                    r.companies = edge.companies,
                    r.contexts = edge.contexts
            } IN TRANSACTIONS OF 100 ROWS
            """
            
            try:
                session.run(query, edges=edge_data)
            except Exception as e:
                # Fallback without transactions
                query_simple = """
                UNWIND $edges AS edge
                MATCH (source)
                WHERE edge.source_type IN labels(source)
                  AND source[edge.source_prop] = edge.source_val
                MATCH (target)
                WHERE edge.target_type IN labels(target)
                  AND target[edge.target_prop] = edge.target_val
                MERGE (source)-[r:CO_OCCURS]-(target)
                SET r.weight = edge.weight,
                    r.count = edge.count,
                    r.companies = edge.companies,
                    r.contexts = edge.contexts
                """
                session.run(query_simple, edges=edge_data)
            
            print(f"  Progress: {min(i+batch_size, len(edges))}/{len(edges)} edges")
    
    print(f"  ✓ {len(edges)} edges created")


def verify_migration(driver, database):
    """Verify the migration."""
    print("\nVerifying migration...")
    
    with driver.session(database=database) as session:
        # Count nodes by type
        result = session.run("""
            MATCH (n)
            WHERE n:Company OR n:Topic OR n:Brand OR n:Location 
               OR n:Strategy OR n:Person OR n:TimePeriod
            WITH labels(n)[0] as type, count(*) as count
            RETURN type, count
            ORDER BY count DESC
        """)
        
        print("  Node counts:")
        total_nodes = 0
        for record in result:
            print(f"    {record['type']}: {record['count']}")
            total_nodes += record['count']
        print(f"  Total knowledge graph nodes: {total_nodes}")
        
        # Count edges
        edge_result = session.run("""
            MATCH ()-[r:CO_OCCURS]-()
            RETURN count(r) as count
        """)
        edge_count = edge_result.single()["count"]
        print(f"  Total CO_OCCURS edges: {edge_count}")


def main():
    """Main migration flow."""
    print("=" * 60)
    print("  Knowledge Graph → Neo4j Migration")
    print("=" * 60)
    
    if not os.path.exists(GRAPH_JSON_PATH):
        print(f"\n❌ Error: graph_data.json not found at {GRAPH_JSON_PATH}")
        print("   Please run: python graph/build_graph.py first")
        return 1
    
    # Load graph data
    graph_data = load_graph_json()
    
    # Connect to Neo4j
    print(f"\nConnecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # Test connection
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("RETURN 1 as test")
            result.single()
        print("  ✓ Connected successfully")
        
        # Clear existing graph (optional - comment out to keep existing data)
        # clear_existing_graph(driver, NEO4J_DATABASE)
        
        # Create constraints
        create_constraints(driver, NEO4J_DATABASE)
        
        # Migrate nodes
        migrate_nodes(driver, NEO4J_DATABASE, graph_data["nodes"])
        
        # Migrate edges
        migrate_edges(driver, NEO4J_DATABASE, graph_data["edges"], graph_data["nodes"])
        
        # Verify
        verify_migration(driver, NEO4J_DATABASE)
        
        print("\n" + "=" * 60)
        print("  ✓ Migration completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        driver.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
