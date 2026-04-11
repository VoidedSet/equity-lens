import { NextRequest, NextResponse } from "next/server";
import { resolveSource } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const ref = request.nextUrl.searchParams.get("ref");
  const company = request.nextUrl.searchParams.get("company") || "IHCL";

  if (!ref) {
    return NextResponse.json({ error: "Missing ?ref= parameter" }, { status: 400 });
  }

  const resolution = resolveSource(ref, company);

  if (!resolution) {
    return NextResponse.json(
      { error: `Could not resolve source: "${ref}"`, ref, company },
      { status: 404 }
    );
  }

  return NextResponse.json({
    type: resolution.type,
    relativePath: resolution.relativePath,
    page: resolution.page,
    searchText: resolution.searchText,
    label: resolution.label,
    pdfUrl: resolution.type === "pdf" ? `/api/pdf/${resolution.relativePath}` : null,
    csvUrl: resolution.type === "csv" ? `/api/pdf/${resolution.relativePath}` : null,
  });
}
