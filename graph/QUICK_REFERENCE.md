# Knowledge Graph — Quick Reference

## 🚀 Quick Start

```bash
# 1. Install dependencies
cd graph && pip install -r requirements.txt

# 2. Migrate to Neo4j (one-time)
python migrate_to_neo4j.py

# 3. Start API server
./start_graph_api.sh

# 4. Start UI (in another terminal)
cd ../ui && npm run dev
```

---

## 🔍 Common Queries

### Python

```python
from graph.neo4j_client import Neo4jClient

with Neo4jClient() as client:
    # Search
    client.search_nodes("Mumbai", limit=10)
    
    # Company profile
    client.get_company_profile("IHCL")
    
    # Compare
    client.compare_companies("IHCL", "EIH")
    
    # Stats
    client.get_stats()
    
    # Subgraph
    client.get_company_subgraph("IHCL", max_nodes=100)
```

### API (curl)

```bash
# Stats
curl http://localhost:8001/stats

# Search
curl "http://localhost:8001/search?q=Mumbai&limit=10"

# Company subgraph
curl "http://localhost:8001/company/IHCL/subgraph?max_nodes=100"

# Compare
curl "http://localhost:8001/compare?c1=IHCL&c2=EIH"

# AI query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which companies operate in Mumbai?"}'
```

### Cypher (Neo4j Browser)

```cypher
// Get all companies
MATCH (c:Company) RETURN c

// Find topics related to IHCL
MATCH (c:Company {code: 'IHCL'})-[r]-(t:Topic)
RETURN t.name, r.count
ORDER BY r.count DESC
LIMIT 10

// Find shared topics between IHCL and EIH
MATCH (c1:Company {code: 'IHCL'})--(t:Topic)--(c2:Company {code: 'EIH'})
RETURN DISTINCT t.name, t.count
ORDER BY t.count DESC

// Get all locations
MATCH (l:Location)
RETURN l.name, l.count
ORDER BY l.count DESC

// Find path between two entities
MATCH path = shortestPath(
  (a {name: 'Mumbai'})-[*..5]-(b {name: 'Luxury'})
)
RETURN path
```

---

## 📊 Useful Stats Queries

```python
from graph.neo4j_client import Neo4jClient

with Neo4jClient() as client:
    stats = client.get_stats()
    
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")
    
    for node_type, count in stats['type_breakdown'].items():
        print(f"  {node_type}: {count}")
```

---

## 🎨 UI Features

### Search
- Type in search box: "Mumbai", "Revenue", "Taj"
- Press Enter or click Search
- Matching nodes are highlighted

### Filters
- Type filter: Show only Topics, Brands, etc.
- Company filter: Show only nodes for a specific company

### AI Queries
Examples:
- "Which companies operate in Mumbai?"
- "What are the top topics for IHCL?"
- "Find connections between luxury segment and Mumbai"
- "Compare IHCL and EIH brands"

### Node Interaction
- **Click** — Show node details
- **Drag** — Move nodes
- **Scroll** — Zoom in/out
- **Pan** — Click and drag background

---

## 🔧 Troubleshooting

### API not responding
```bash
# Check if server is running
curl http://localhost:8001/

# Restart server
./graph/start_graph_api.sh
```

### Neo4j connection error
```bash
# Test connection
python -c "from neo4j import GraphDatabase; \
  driver = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j', 'kshayik1')); \
  driver.verify_connectivity(); print('✓ Connected')"
```

### Empty graph
```bash
# Re-run migration
python graph/migrate_to_neo4j.py
```

### UI not loading graph
1. Check API is running: `curl http://localhost:8001/stats`
2. Check browser console for errors
3. Verify company code is correct

---

## 📝 Environment Variables

Create `graph/.env`:
```env
GRAPH_NEO4J_URI=neo4j://127.0.0.1:7687
GRAPH_NEO4J_USER=neo4j
GRAPH_NEO4J_PASSWORD=kshayik1
GRAPH_NEO4J_DATABASE=datahack-graphdb
```

Create `ui/.env.local`:
```env
GRAPH_API_URL=http://localhost:8001
```

---

## 🔗 Useful Links

- **API Docs**: http://localhost:8001/docs
- **Neo4j Browser**: http://localhost:7474
- **UI**: http://localhost:3000
- **Full Docs**: See `graph/README.md`
- **Setup Guide**: See `GRAPH_MIGRATION_GUIDE.md`

---

## 📞 Quick Commands

```bash
# Start everything
./graph/start_graph_api.sh &
cd ui && npm run dev

# Stop everything
pkill -f "python.*api.py"
pkill -f "next dev"

# Check status
curl http://localhost:8001/stats
curl http://localhost:3000

# View logs
tail -f graph/api.log  # if logging is enabled
```

---

## 🎯 Common Use Cases

### 1. Explore a company's knowledge graph
```python
client.get_company_subgraph("IHCL", max_nodes=150)
```

### 2. Find competitive overlaps
```python
client.compare_companies("IHCL", "EIH")
```

### 3. Search for specific topics
```python
client.search_nodes("Revenue", node_type="Topic")
```

### 4. Get company profile
```python
profile = client.get_company_profile("IHCL")
print(f"Top topics: {[t['name'] for t in profile['topics'][:5]]}")
```

### 5. Find connections
```python
client.find_connections("IHCL", "Mumbai")
```

---

**For detailed documentation, see `graph/README.md`**
