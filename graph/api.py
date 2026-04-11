"""
FastAPI Graph API Server
=========================
REST API for querying the Neo4j knowledge graph.
Provides endpoints for the Next.js UI.
"""

import os
import sys
import json
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
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
    from agent.llm_client import chat_completion
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    print("Warning: LLM client not available. AI query endpoint will be disabled.")


app = FastAPI(title="Knowledge Graph API", version="1.0.0")

# CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.post("/query", response_model=CypherQueryResponse)
async def natural_language_query(request: NLQueryRequest):
    """
    Convert natural language question to Cypher query and execute it.
    Uses LLM to generate Cypher from the question.
    """
    if not HAS_LLM:
        raise HTTPException(
            status_code=501,
            detail="LLM client not available. AI query endpoint is disabled."
        )
    
    try:
        # Get schema for context
        schema = neo4j_client.get_schema()
        
        # Build prompt for LLM
        prompt = build_cypher_prompt(request.question, schema, request.company)
        
        # Generate Cypher
        messages = [
            {"role": "system", "content": "You are a Neo4j Cypher query expert."},
            {"role": "user", "content": prompt}
        ]
        
        llm_response = chat_completion(messages, temperature=0.1, max_tokens=1000)
        
        # Parse Cypher from response
        cypher = extract_cypher_from_response(llm_response)
        
        if not cypher:
            raise HTTPException(
                status_code=400,
                detail="Could not generate valid Cypher query from question"
            )
        
        # Execute Cypher (read-only safety check)
        if not is_read_only_query(cypher):
            raise HTTPException(
                status_code=403,
                detail="Only read-only queries are allowed"
            )
        
        # Execute query
        result = neo4j_client._run_query(cypher)
        
        return {
            "cypher": cypher,
            "result": {"data": result, "count": len(result)},
            "explanation": f"Executed query for: {request.question}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Helper Functions ──────────────────────────────────────

def build_cypher_prompt(question: str, schema: dict, company: Optional[str]) -> str:
    """Build prompt for LLM to generate Cypher."""
    
    company_context = ""
    if company:
        company_context = f"\nFocus on company code: {company} (filter using '$company IN n.companies' on entity nodes)"
    
    examples = """
IMPORTANT SCHEMA NOTES:
- Company nodes only have a 'code' property (e.g. 'IHCL', 'CHALET', 'EIH', 'JUNIPER', 'LEMONTREE')
- Entity nodes (TOPIC, LOCATION, BRAND, STRATEGY, PERSON, TIME_PERIOD) have: name, count, companies (list of company codes)
- To find entities for a company, use: WHERE 'IHCL' IN n.companies
- Entities are connected via CO_OCCURS relationships (not to Company nodes directly)
- Use UPPERCASE labels for entities: TOPIC, LOCATION, BRAND, STRATEGY, PERSON, TIME_PERIOD

Example 1:
Question: "Which locations are associated with IHCL?"
Cypher: MATCH (l:LOCATION) WHERE 'IHCL' IN l.companies RETURN l.name, l.count ORDER BY l.count DESC LIMIT 10

Example 2:
Question: "What are the top 5 most discussed topics?"
Cypher: MATCH (t:TOPIC) RETURN t.name, t.count ORDER BY t.count DESC LIMIT 5

Example 3:
Question: "Which companies operate in Mumbai?"
Cypher: MATCH (l:LOCATION {name: 'Mumbai'}) RETURN l.name, l.companies

Example 4:
Question: "Compare brands of IHCL and EIH"
Cypher: MATCH (b:BRAND) WHERE 'IHCL' IN b.companies OR 'EIH' IN b.companies RETURN b.name, b.companies, b.count ORDER BY b.count DESC

Example 5:
Question: "What topics are common between IHCL and CHALET?"
Cypher: MATCH (t:TOPIC) WHERE 'IHCL' IN t.companies AND 'CHALET' IN t.companies RETURN t.name, t.count ORDER BY t.count DESC LIMIT 10

Example 6:
Question: "Find strategies related to digital"
Cypher: MATCH (s:STRATEGY) WHERE toLower(s.name) CONTAINS 'digital' RETURN s.name, s.count, s.companies ORDER BY s.count DESC
"""
    
    prompt = f"""You are a Neo4j Cypher query expert. Generate a Cypher query to answer the user's question.

Graph Schema:
- Node Labels: {', '.join(schema['node_labels'])}
- Relationship Types: {', '.join(schema['relationship_types'])}
- Node Properties: {json.dumps(schema['node_properties'], indent=2)}

{examples}

User Question: {question}{company_context}

Generate ONLY the Cypher query. No explanations, no markdown fences. Just the raw Cypher.
The query must be read-only (MATCH/RETURN only, no CREATE/DELETE/SET).
Always add LIMIT 20 unless user specifies a number.
"""
    
    return prompt


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
