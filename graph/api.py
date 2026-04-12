"""
FastAPI Graph API Server
=========================
REST API for querying the Neo4j knowledge graph.
Provides endpoints for the Next.js UI.
"""

import os
import sys
import json
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load graph/.env before anything else
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from graph.neo4j_client import Neo4jClient

# Import LLM client for AI queries
try:
    from agent.llm_client import groq_chat_completion
    from agent.agent import process_query_stream
    HAS_LLM = True
except ImportError:
    try:
         import requests as _req
         HAS_LLM = True
         groq_chat_completion = None
         process_query_stream = None
    except ImportError:
         HAS_LLM = False
    print("Warning: agent module not found; will use inline Groq call.")


import requests as _requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _groq_call(messages: list, temperature: float = 0.1, max_tokens: int = 1024) -> str:
    """Inline Groq call — used if agent module is unavailable."""
    if not GROQ_API_KEY:
        return "[LLM Error] GROQ_API_KEY not set in graph/.env"
    try:
        resp = _requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"[LLM Error] Groq {resp.status_code}: {resp.text[:300]}"
    except Exception as exc:
        return f"[LLM Error] {exc}"


def _call_llm(messages: list, temperature: float = 0.1, max_tokens: int = 1024) -> str:
    """Route to agent module if available, else use inline Groq call."""
    if groq_chat_completion is not None:
        return groq_chat_completion(messages, temperature, max_tokens)
    return _groq_call(messages, temperature, max_tokens)


app = FastAPI(title="Knowledge Graph API", version="1.0.0")

# CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the output directory
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
if os.path.exists(OUTPUT_DIR):
    app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")


# Global Neo4j client
neo4j_client = None


@app.on_event("startup")
async def startup_event():
    global neo4j_client
    neo4j_client = Neo4jClient()
    print("✓ Neo4j client initialized")


@app.on_event("shutdown")
async def shutdown_event():
    if neo4j_client:
        neo4j_client.close()
    print("✓ Neo4j client closed")


# ─── Request/Response Models ───────────────────────────────

class NodeSearchResponse(BaseModel):
    nodes: List[dict]
    total: int


class SubgraphResponse(BaseModel):
    nodes: List[dict]
    edges: List[dict]


class NLQueryRequest(BaseModel):
    question: str
    company: Optional[str] = None


class AgentStreamRequest(BaseModel):
    query: str
    history: List[Dict[str, Any]] = []


class CypherQueryResponse(BaseModel):
    cypher: str
    result: dict
    explanation: str


# ─── API Endpoints ─────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "Knowledge Graph API",
        "version": "1.0.0",
        "endpoints": [
            "/search",
            "/node/{node_id}/neighbors",
            "/company/{code}/subgraph",
            "/company/{code}/profile",
            "/compare",
            "/schema",
            "/stats",
            "/query (POST)"
        ]
    }


@app.get("/search", response_model=NodeSearchResponse)
async def search_nodes(
    q: str = Query("", description="Search query"),
    type: Optional[str] = Query(None, description="Node type filter"),
    company: Optional[str] = Query(None, description="Company filter"),
    limit: int = Query(50, ge=1, le=200)
):
    """Search nodes by name with optional filters."""
    try:
        results = neo4j_client.search_nodes(
            query=q,
            node_type=type,
            company_filter=company,
            limit=limit
        )
        return {"nodes": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/node/{node_id}/neighbors", response_model=SubgraphResponse)
async def get_node_neighbors(
    node_id: str,
    depth: int = Query(1, ge=1, le=3),
    max_nodes: int = Query(100, ge=10, le=500)
):
    """Get neighborhood subgraph around a node."""
    try:
        result = neo4j_client.get_node_neighbors(node_id, depth, max_nodes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/company/{code}/subgraph", response_model=SubgraphResponse)
async def get_company_subgraph(
    code: str,
    max_nodes: int = Query(100, ge=10, le=500)
):
    """Get all nodes associated with a company."""
    try:
        result = neo4j_client.get_company_subgraph(code.upper(), max_nodes)
        if not result["nodes"]:
            raise HTTPException(status_code=404, detail=f"Company {code} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/company/{code}/profile")
async def get_company_profile(code: str):
    """Get company profile with all connections."""
    try:
        result = neo4j_client.get_company_profile(code)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/compare")
async def compare_companies(
    c1: str = Query(..., description="First company code"),
    c2: str = Query(..., description="Second company code")
):
    """Compare two companies."""
    try:
        result = neo4j_client.compare_companies(c1, c2)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema")
async def get_schema():
    """Get graph schema for AI context."""
    try:
        schema = neo4j_client.get_schema()
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get graph statistics."""
    try:
        stats = neo4j_client.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def natural_language_query(request: NLQueryRequest):
    """
    Convert natural language question to Cypher query via Groq Llama 3.3 70B,
    execute it, and return both tabular results AND graph-renderable nodes/edges.
    """
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=501,
            detail="GROQ_API_KEY not set. Add it to graph/.env to enable AI queries."
        )
    
    try:
        # Get schema for context
        schema = neo4j_client.get_schema()
        
        # Build prompt
        prompt = build_cypher_prompt(request.question, schema, request.company)
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Neo4j Cypher query expert for an Indian hotel sector knowledge graph. "
                    "Generate precise, read-only Cypher queries. Output ONLY the raw Cypher, no markdown, no explanation."
                )
            },
            {"role": "user", "content": prompt}
        ]
        
        llm_response = _call_llm(messages, temperature=0.05, max_tokens=512)
        
        if llm_response.startswith("[LLM Error]"):
            raise HTTPException(status_code=502, detail=llm_response)
        
        # Parse Cypher from response
        cypher = extract_cypher_from_response(llm_response)
        
        if not cypher:
            raise HTTPException(
                status_code=400,
                detail=f"Could not parse valid Cypher from LLM response: {llm_response[:200]}"
            )
        
        # Safety check
        if not is_read_only_query(cypher):
            raise HTTPException(status_code=403, detail="Only read-only queries are allowed")
        
        # Execute query
        raw_result = neo4j_client._run_query(cypher)
        
        # Build graph-renderable nodes + edges from the result rows
        graph_nodes, graph_edges = extract_graph_from_result(raw_result, request.company)
        
        return {
            "cypher": cypher,
            "result": {"data": raw_result, "count": len(raw_result)},
            "graph": {"nodes": graph_nodes, "edges": graph_edges},
            "explanation": f"Groq (Llama 3.3 70B) answered: {request.question}",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/stream")
async def agent_stream(request: AgentStreamRequest):
    """
    Stream agent thoughts and tool execution to the frontend using SSE.
    """
    if process_query_stream is None:
        raise HTTPException(status_code=501, detail="Agent module not available")

    async def event_generator():
        try:
            for event in process_query_stream(request.query, request.history):
                # Format as Server-Sent Events (SSE)
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─── Helper Functions ──────────────────────────────────────

def build_cypher_prompt(question: str, schema: dict, company: Optional[str]) -> str:
    """Build a rich prompt for Groq Llama 3.3 70B to generate Cypher."""

    company_context = ""
    if company:
        company_context = (
            f"\nACTIVE COMPANY FILTER: {company}. "
            f"When relevant, scope results to this company using: WHERE '{company}' IN n.companies"
        )

    examples = """
=== SCHEMA RULES (READ CAREFULLY) ===
- Company nodes: label=Company, property: code (e.g. 'IHCL', 'CHALET', 'EIH', 'JUNIPER', 'LEMONTREE')
- Entity nodes: labels TOPIC, LOCATION, BRAND, STRATEGY, PERSON, TIME_PERIOD
  Properties on entity nodes: name (string), count (int = mention frequency), companies (list of codes)
- Relationships: CO_OCCURS connects entities to entities. Company nodes do NOT have direct edges to entities.
- To find entities for a company: WHERE 'IHCL' IN n.companies
- ALWAYS use UPPERCASE labels: TOPIC not Topic, LOCATION not Location, etc.

=== EXAMPLES ===

Q: Which locations are associated with IHCL?
A: MATCH (l:LOCATION) WHERE 'IHCL' IN l.companies RETURN elementId(l) as id, labels(l)[0] as type, l.name as name, l.count as count, l.companies as companies ORDER BY l.count DESC LIMIT 15

Q: Top discussed topics across all companies
A: MATCH (t:TOPIC) RETURN elementId(t) as id, labels(t)[0] as type, t.name as name, t.count as count, t.companies as companies ORDER BY t.count DESC LIMIT 20

Q: Which companies operate in Mumbai?
A: MATCH (l:LOCATION) WHERE toLower(l.name) CONTAINS 'mumbai' RETURN elementId(l) as id, labels(l)[0] as type, l.name as name, l.count as count, l.companies as companies

Q: Compare brands of IHCL and EIH
A: MATCH (b:BRAND) WHERE 'IHCL' IN b.companies OR 'EIH' IN b.companies RETURN elementId(b) as id, labels(b)[0] as type, b.name as name, b.count as count, b.companies as companies ORDER BY b.count DESC LIMIT 20

Q: What topics are common between IHCL and CHALET?
A: MATCH (t:TOPIC) WHERE 'IHCL' IN t.companies AND 'CHALET' IN t.companies RETURN elementId(t) as id, labels(t)[0] as type, t.name as name, t.count as count, t.companies as companies ORDER BY t.count DESC LIMIT 15

Q: Strategies related to expansion
A: MATCH (s:STRATEGY) WHERE toLower(s.name) CONTAINS 'expan' RETURN elementId(s) as id, labels(s)[0] as type, s.name as name, s.count as count, s.companies as companies ORDER BY s.count DESC LIMIT 15

Q: Find connections between revenue and Mumbai
A: MATCH (a)-[r:CO_OCCURS]-(b) WHERE (toLower(a.name) CONTAINS 'revenue' OR toLower(a.name) CONTAINS 'revpar') AND (toLower(b.name) CONTAINS 'mumbai') RETURN elementId(a) as id, labels(a)[0] as type, a.name as name, a.count as count, a.companies as companies UNION MATCH (a)-[r:CO_OCCURS]-(b) WHERE (toLower(a.name) CONTAINS 'revenue' OR toLower(a.name) CONTAINS 'revpar') AND (toLower(b.name) CONTAINS 'mumbai') RETURN elementId(b) as id, labels(b)[0] as type, b.name as name, b.count as count, b.companies as companies LIMIT 20

Q: Key persons mentioned for Lemon Tree
A: MATCH (p:PERSON) WHERE 'LEMONTREE' IN p.companies RETURN elementId(p) as id, labels(p)[0] as type, p.name as name, p.count as count, p.companies as companies ORDER BY p.count DESC LIMIT 10

=== OUTPUT FORMAT REQUIREMENT ===
Always RETURN these columns when possible: elementId(n) as id, labels(n)[0] as type, n.name as name, n.count as count, n.companies as companies
This enables the frontend to render the results as a knowledge graph visualization.
"""

    prompt = f"""Graph Schema:
- Node Labels: {', '.join(schema.get('node_labels', []))}
- Relationship Types: {', '.join(schema.get('relationship_types', []))}

{examples}

User Question: {question}{company_context}

Output ONLY the raw Cypher query. No markdown. No explanation. No code fences.
Must be read-only (MATCH/RETURN only). Add LIMIT 25 if not already specified.
"""
    return prompt


def extract_graph_from_result(rows: list, company: Optional[str]) -> tuple:
    """
    Convert raw Cypher result rows into graph-renderable nodes and edges.
    Looks for 'id', 'type', 'name', 'count', 'companies' columns.
    Then fetches edges between returned node IDs.
    """
    nodes = []
    seen_ids = set()

    for row in rows:
        node_id = row.get("id")
        if not node_id or node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        nodes.append({
            "id": str(node_id),
            "type": str(row.get("type", "TOPIC")),
            "name": str(row.get("name", "")),
            "count": int(row.get("count", 0) or 0),
            "companies": list(row.get("companies") or []),
        })

    # Fetch edges between the returned nodes
    edges = []
    if len(seen_ids) > 1 and neo4j_client:
        try:
            id_list = list(seen_ids)
            edge_cypher = """
            MATCH (a)-[r]-(b)
            WHERE elementId(a) IN $ids AND elementId(b) IN $ids
              AND elementId(a) < elementId(b)
            RETURN DISTINCT
                elementId(startNode(r)) as source,
                elementId(endNode(r)) as target,
                type(r) as type,
                coalesce(r.weight, 1) as weight
            LIMIT 100
            """
            edge_rows = neo4j_client._run_query(edge_cypher, {"ids": id_list})
            edges = [
                {"source": str(e["source"]), "target": str(e["target"]),
                 "type": e["type"], "weight": e.get("weight", 1)}
                for e in edge_rows
            ]
        except Exception:
            pass

    return nodes, edges


def extract_cypher_from_response(response: str) -> Optional[str]:
    """Extract Cypher query from LLM response."""
    text = response.strip()
    
    # Try to find code block
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            clean = part.strip()
            if clean.lower().startswith(("cypher", "cql", "neo4j")):
                clean = "\n".join(clean.split("\n")[1:]).strip()
            if "MATCH" in clean.upper() and "RETURN" in clean.upper():
                return clean
    
    # Try to find MATCH...RETURN/LIMIT pattern in raw text
    lines = text.split("\n")
    cypher_lines = []
    in_query = False
    
    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("MATCH") or upper.startswith("WITH") or upper.startswith("OPTIONAL"):
            in_query = True
        if in_query:
            cypher_lines.append(stripped)
            if "LIMIT" in upper or (upper.startswith("RETURN") and "LIMIT" not in " ".join(cypher_lines).upper()):
                # Keep collecting if RETURN but no LIMIT yet; break at LIMIT
                if "LIMIT" in upper:
                    break
    
    if cypher_lines:
        query = " ".join(cypher_lines)
        if "MATCH" in query.upper() and "RETURN" in query.upper():
            return query
    
    return None


def is_read_only_query(cypher: str) -> bool:
    """Check if Cypher query is read-only."""
    cypher_upper = cypher.upper()
    write_keywords = ["CREATE", "DELETE", "SET", "REMOVE", "MERGE", "DROP"]
    return not any(keyword in cypher_upper for keyword in write_keywords)


# ─── Run Server ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
