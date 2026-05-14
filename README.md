# EquityLens AI

EquityLens AI is an agentic intelligence system for Indian hotel companies.
It ingests PDFs and news, stores cited facts in Supabase, and scores management credibility.
The Next.js dashboard presents scorecards, comparisons, and the knowledge graph.
The system does not answer without source citations.

## Install

1. Install Python dependencies in each service folder that has a requirements file.
2. Install UI dependencies with:

```bash
cd ui
npm install
```

3. Configure environment files for Supabase and Neo4j as described in the docs.

## Docs

See the docs folder for detailed guides and prompts:

- [docs/overview/PRD.md](docs/overview/PRD.md)
- [docs/overview/IMPLEMENTATION_SUMMARY.md](docs/overview/IMPLEMENTATION_SUMMARY.md)
- [docs/graph/README.md](docs/graph/README.md)
- [docs/graph/GRAPH_MIGRATION_GUIDE.md](docs/graph/GRAPH_MIGRATION_GUIDE.md)
- [docs/ingestion/README.md](docs/ingestion/README.md)
- [docs/news/README.md](docs/news/README.md)
- [docs/ui/README.md](docs/ui/README.md)
- [docs/sector/hotel_sector_analysis.md](docs/sector/hotel_sector_analysis.md)
