#!/bin/bash

# Start the Knowledge Graph API Server
# Make sure Neo4j Desktop is running first!

echo "=========================================="
echo "  Knowledge Graph API Server"
echo "=========================================="
echo ""

# Check if Neo4j is running
echo "Checking Neo4j connection..."
python3 -c "
from neo4j import GraphDatabase
import os
import sys

uri = os.getenv('GRAPH_NEO4J_URI', 'neo4j://127.0.0.1:7687')
user = os.getenv('GRAPH_NEO4J_USER', 'neo4j')
password = os.getenv('GRAPH_NEO4J_PASSWORD', 'kshayik1')

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        session.run('RETURN 1')
    driver.close()
    print('✓ Neo4j is running')
except Exception as e:
    print(f'✗ Neo4j connection failed: {e}')
    print('')
    print('Please start Neo4j Desktop first!')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "Starting FastAPI server on http://localhost:8001..."
echo ""

# Start the API server
python3 api.py
