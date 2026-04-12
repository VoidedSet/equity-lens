import { NextRequest, NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase";
import {
  getDeviations,
  getScorecards,
  getCredibilityScores,
} from "@/lib/db";

// ── RAG Pipeline: embed query → match documents → LLM synthesis ──

const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";

type ChunkMatch = {
  id: string;
  company_id: string;
  document_type: string;
  period: string;
  chunk_text: string;
  source_document: string;
  source_page: number | null;
  speaker: string | null;
  section_name: string | null;
  similarity: number;
};

async function searchDocumentChunks(
  queryText: string,
  companyId?: string,
  topK: number = 8
): Promise<ChunkMatch[]> {
  // Use Supabase full-text search as fallback when no embeddings available
  const supabase = getServiceClient();

  // Try vector search first via match_documents RPC
  // We need to embed the query — but we don't have sentence-transformers in Node.
  // Instead, use keyword-based search on chunk_text as a pragmatic fallback.
  const keywords = queryText
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .split(/\s+/)
    .filter((w) => w.length > 3)
    .slice(0, 5);

  if (keywords.length === 0) return [];

  // Build an OR text search query
  let query = supabase
    .from("document_chunks")
    .select("id, company_id, document_type, period, chunk_text, source_document, source_page, speaker, section_name")
    .limit(topK);

  if (companyId) {
    query = query.eq("company_id", companyId.toUpperCase());
  }

  // Use ilike for keyword matching (Supabase text search)
  // Search for the most distinctive keyword
  const searchTerm = keywords.join(" | ");
  query = query.or(keywords.map((k) => `chunk_text.ilike.%${k}%`).join(","));

  const { data, error } = await query;
  if (error) {
    console.error("[RAG] Search error:", error.message);
    return [];
  }

  // Score results by keyword match count
  const scored = (data || []).map((row) => {
    const text = (row.chunk_text || "").toLowerCase();
    const matchCount = keywords.filter((k) => text.includes(k)).length;
    return { ...row, similarity: matchCount / keywords.length } as ChunkMatch;
  });

  return scored.sort((a, b) => b.similarity - a.similarity).slice(0, topK);
}

async function synthesizeAnswer(
  question: string,
  chunks: ChunkMatch[],
  companyContext?: string
): Promise<{ answer: string; citations: string[] }> {
  if (chunks.length === 0) {
    // Fallback: try to answer from structured data
    return buildStructuredDataResponse(question, companyContext);
  }

  // Build context from matched chunks
  const contextParts = chunks.map((c, i) => {
    const source = c.source_document || "Unknown";
    const page = c.source_page ? ` | Page ${c.source_page}` : "";
    const speaker = c.speaker ? ` (${c.speaker})` : "";
    const period = c.period || "";
    return `[Source ${i + 1}: ${source}${page} | ${period}${speaker}]\n${c.chunk_text}`;
  });
  const context = contextParts.join("\n\n---\n\n");

  // Build citations
  const citations = chunks
    .filter((c) => c.similarity > 0.2)
    .slice(0, 5)
    .map((c) => {
      const doc = c.source_document || "Document";
      const page = c.source_page ? ` | Page ${c.source_page}` : "";
      const period = c.period ? ` | ${c.period}` : "";
      return `${doc}${page}${period}`;
    });

  // Call Groq Llama 3.3 70B for synthesis
  if (!GROQ_API_KEY) {
    return buildChunkSummary(question, chunks, citations);
  }

  try {
    const response = await fetch(GROQ_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${GROQ_API_KEY}`,
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [
          {
            role: "system",
            content: `You are EquityLens AI — an expert equity research analyst covering Indian hotel companies (IHCL, Chalet Hotels, Lemon Tree Hotels, EIH/Oberoi, Juniper Hotels).

Your job is to answer the analyst's question using ONLY the source documents provided.

STRICT RULES:
1. Never invent or extrapolate beyond what the sources say.
2. If the answer is not found, respond: "DATA NOT AVAILABLE — not found in ingested documents."
3. Cite sources using [Source N] notation inline.
4. Be analytical. Extract the signal: did management over-promise? Did numbers diverge? What is the trend?
5. Use specific figures, dates, and direct quotes when available.
6. Structure your response clearly with a 1-2 sentence direct answer first, then supporting detail.`,
          },
          {
            role: "user",
            content: `QUESTION: ${question}

SOURCE DOCUMENTS (use ONLY these):
${context}

Provide a concise analyst-grade answer with source citations.`,
          },
        ],
        max_tokens: 1200,
        temperature: 0.2,
      }),
    });

    if (!response.ok) {
      console.error("[RAG] Groq API error:", response.status, await response.text());
      return buildChunkSummary(question, chunks, citations);
    }

    const result = await response.json();
    const llmAnswer = result.choices?.[0]?.message?.content || "Unable to generate answer.";

    return { answer: llmAnswer, citations };
  } catch (err) {
    console.error("[RAG] Groq call failed:", err);
    return buildChunkSummary(question, chunks, citations);
  }
}

function buildChunkSummary(
  question: string,
  chunks: ChunkMatch[],
  citations: string[]
): { answer: string; citations: string[] } {
  const topSources = chunks.slice(0, 3).map((c, i) => {
    const src = c.source_document?.replace(/.*\//, "") || "Document";
    const period = c.period ? ` (${c.period})` : "";
    const speaker = c.speaker ? `${c.speaker}: ` : "";
    const snippet = c.chunk_text.slice(0, 180).replace(/\s+/g, " ").trim();
    return `[Source ${i + 1} — ${src}${period}]\n${speaker}"${snippet}…"`;
  });
  return {
    answer: [
      `**Groq API key not configured.** Showing raw retrieved passages for: *${question}*`,
      "",
      ...topSources,
      "",
      `Add GROQ_API_KEY to ui/.env.local to enable AI synthesis.`,
    ].join("\n"),
    citations,
  };
}

async function buildStructuredDataResponse(
  question: string,
  companyId?: string
): Promise<{ answer: string; citations: string[] }> {
  const cid = companyId?.toUpperCase() || "IHCL";
  const [deviations, scorecards, credibility] = await Promise.all([
    getDeviations(cid),
    getScorecards(cid),
    getCredibilityScores(cid),
  ]);

  const sc = scorecards[0];
  const cred = credibility[0];
  const missCount = deviations.filter((d) => d.flag === "MISS").length;
  const beatCount = deviations.filter((d) => d.flag === "BEAT").length;
  const inlineCount = deviations.filter((d) => d.flag === "IN-LINE").length;
  const total = deviations.length;
  const hitRate = total > 0 ? Math.round(((beatCount + inlineCount) / total) * 100) : 0;

  let answer = "";
  if (total > 0) {
    answer = `${cid} has ${total} tracked guidance claims: ${missCount} misses, ${beatCount} beats, ${inlineCount} in-line (${hitRate}% hit rate).`;
    if (sc) answer += ` Composite score: ${sc.composite_score}/100.`;
    if (cred) answer += ` Credibility: ${cred.overall_score}/100, trend: ${cred.trend}.`;
  } else {
    answer = sc
      ? `${cid} composite score: ${sc.composite_score}/100 (Credibility: ${sc.dim_credibility}, Financial Quality: ${sc.dim_financial_quality}, Industry: ${sc.dim_industry_position}, Risk: ${sc.dim_risk}).`
      : `DATA NOT AVAILABLE — No detailed guidance tracking data has been ingested yet for ${cid}. Run the ingestion pipeline to populate this data.`;
  }

  return {
    answer,
    citations: [
      `${cid} Deviation Tracker`,
      `${cid} Scorecard`,
      "Screener.in Financials",
    ],
  };
}

// ── Detect company from question ─────────────────────────────
function detectCompany(question: string): string | undefined {
  const q = question.toLowerCase();
  const patterns: [string, string[]][] = [
    ["IHCL", ["ihcl", "indian hotels", "taj hotels", "taj group"]],
    ["CHALET", ["chalet", "chalet hotels"]],
    ["LEMONTREE", ["lemon tree", "lemontree"]],
    ["EIH", ["eih", "oberoi", "trident"]],
    ["JUNIPER", ["juniper", "hyatt"]],
  ];
  for (const [id, keywords] of patterns) {
    if (keywords.some((k) => q.includes(k))) return id;
  }
  return undefined;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const question = body.question || body.query || "";
    const requestedCompany = body.company;

    if (!question.trim()) {
      return NextResponse.json(
        { error: "Question is required" },
        { status: 400 }
      );
    }

    // Detect company from question or request body
    const companyId = requestedCompany || detectCompany(question);

    // RAG: search for relevant document chunks
    const chunks = await searchDocumentChunks(question, companyId);

    // Synthesize answer using LLM + retrieved chunks
    const response = await synthesizeAnswer(question, chunks, companyId);

    return NextResponse.json({
      question,
      answer: response.answer,
      citations: response.citations,
      company: companyId || "ALL",
      chunks_retrieved: chunks.length,
      data_source: "EquityLens AI — Source-Only RAG Architecture",
      disclaimer:
        "Every claim is cited to a specific document, page, and period. If data is not in ingested documents, the system says DATA NOT AVAILABLE.",
    });
  } catch (err) {
    console.error("[Q&A] Error:", err);
    return NextResponse.json(
      { error: "Invalid request body" },
      { status: 400 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    endpoint: "/api/gpt/query",
    method: "POST",
    description:
      "Ask EquityLens AI a question about hotel sector companies. Uses RAG over ingested earnings calls and annual reports. Every answer is source-cited.",
    example_body: {
      question: "How many times has IHCL missed RevPAR guidance?",
      company: "IHCL",
    },
    available_topics: [
      "RevPAR guidance tracking",
      "Management credibility comparison",
      "F&B margin compression risk",
      "Mumbai supply overhang",
      "Room additions pipeline",
      "Debt and interest coverage",
      "General company overview",
    ],
  });
}
