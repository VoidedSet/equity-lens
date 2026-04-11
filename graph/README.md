# Knowledge Graph → Neo4j Migration

This folder contains the Neo4j-powered knowledge graph system that replaces the JSON-based graph.

## Architecture

```
Data Ingestion/extracted_json/  →  build_graph.py  →  graph_data.json
                                                     ↓
                                              migrate_to_neo4j.py
                                                     ↓
                                              Neo4j Database
                                                     ↓
                                              neo4j_client.py
                                                     ↓
                                              api.py (FastAPI)
                                                     ↓
                                              Next.js UI
```

## Setup

### 1. Install Python Dependencies

```bash
cd graph
pip install -r requirements.txt
```

### 2. Start Neo4j Desktop

- Open Neo4j Desktop
- Start your database (should be running on `localhost:7687`)
- Database name: `datahack-graphdb`
- Password: `kshayik1` (or set `GRAPH_NEO4J_PASSWORD` env var)

### 3. Build the Graph (if not already done)

```bash
python graph/build_graph.py
```

This creates `graph_data.json` (~8.5MB) from all the extracted data.

### 4. Migrate to Neo4j

```bash
python graph/migrate_to_neo4j.py
```

This will:
- Load `graph_data.json`
- Create nodes and relationships in Neo4j
- Create indexes and constraints
- Verify the migration

**Expected output:**
```
Nodes: ~1000-2000
Edges: ~5000-10000
Types: Company, Topic, Brand, Location, Strategy, Person, TimePeriod
```

### 5. Start the FastAPI Server

```bash
python graph/api.py
```

Server runs on `http://localhost:8001`

### 6. Start the Next.js UI

```bash
cd ui
npm install  # if not already done
npm run dev
```

UI runs on `http://localhost:3000`

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/search?q=...` | GET | Search nodes by name |
| `/node/{id}/neighbors?depth=1` | GET | Get neighborhood subgraph |
| `/company/{code}/subgraph` | GET | Get company-centric subgraph |
| `/company/{code}/profile` | GET | Get company profile |
| `/compare?c1=...&c2=...` | GET | Compare two companies |
| `/schema` | GET | Get graph schema (for AI) |
| `/stats` | GET | Get graph statistics |
| `/query` | POST | Natural language → Cypher query |

## Usage Examples

### Python Client

```python
from graph.neo4j_client import Neo4jClient

with Neo4jClient() as client:
    # Search nodes
    results = client.search_nodes("Mumbai", limit=10)
    
    # Get company profile
    profile = client.get_company_profile("IHCL")
    print(profile["topics"][:5])
    
    # Compare companies
    comparison = client.compare_companies("IHCL", "EIH")
    print(comparison["shared"])
    
    # Get stats
    stats = client.get_stats()
    print(f"Total nodes: {stats['total_nodes']}")
```

### API Calls

```bash
# Search
curl "http://localhost:8001/search?q=Mumbai&limit=5"

# Company subgraph
curl "http://localhost:8001/company/IHCL/subgraph?max_nodes=100"

# Compare
curl "http://localhost:8001/compare?c1=IHCL&c2=EIH"

# AI Query
curl -X POST "http://localhost:8001/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Which companies operate in Mumbai?"}'
```

## UI Features

The new `KnowledgeGraph` component in the Next.js UI provides:

1. **Interactive Graph Visualization** (React Flow)
   - Drag nodes, zoom, pan
   - Color-coded by type
   - Size by mention count

2. **Search & Filter**
   - Search nodes by name
   - Filter by type/company
   - Highlight matching nodes

3. **AI Natural Language Queries**
   - Ask questions in plain English
   - AI generates Cypher queries
   - Returns relevant subgraph

4. **Company-Centric View**
   - Shows only selected company's neighborhood
   - Lazy loading (not the full 8.5MB graph)

## Environment Variables

Create a `.env` file in the `graph/` folder:

```env
GRAPH_NEO4J_URI=neo4j://127.0.0.1:7687
GRAPH_NEO4J_USER=neo4j
GRAPH_NEO4J_PASSWORD=kshayik1
GRAPH_NEO4J_DATABASE=datahack-graphdb
```

## Troubleshooting

### "Failed to connect to graph API"

Make sure the FastAPI server is running:
```bash
python graph/api.py
```

### "Company not found"

Check that the migration completed successfully:
```bash
python graph/neo4j_client.py
```

### Neo4j connection errors

1. Verify Neo4j Desktop is running
2. Check the database is started
3. Verify credentials in `.env`

### Graph is empty

Re-run the migration:
```bash
python graph/migrate_to_neo4j.py
```

## Schema

### Node Labels

- **Company**: `{code, name, count}`
- **Topic**: `{name, count, companies[]}`
- **Brand**: `{name, count, companies[]}`
- **Location**: `{name, count, companies[]}`
- **Strategy**: `{name, count, companies[]}`
- **Person**: `{name, count, companies[]}`
- **TimePeriod**: `{name, count, companies[]}`

### Relationships

- **CO_OCCURS**: `{weight, count, companies[], contexts[]}`
  - Connects any two entities that appear together in the same document chunk

## Performance

- **Migration time**: ~30-60 seconds for full graph
- **Query time**: <100ms for most queries
- **Subgraph fetch**: <200ms for 100-node subgraph
- **AI query**: 1-3 seconds (LLM generation + execution)

## Next Steps

1. Add more relationship types (e.g., COMPETES_WITH, OPERATES_IN)
2. Integrate news events graph (from `graph-db/`)
3. Add time-based filtering (show graph evolution over quarters)
4. Implement graph algorithms (PageRank, community detection)
5. Add graph export (to Gephi, Cytoscape)
