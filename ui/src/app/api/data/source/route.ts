import { NextRequest, NextResponse } from "next/server";
import { resolveSource } from "@/lib/db";
import { isS3Configured, presignS3GetUrl } from "@/lib/s3";

export const dynamic = "force-dynamic";

function extractS3Key(ref: string | null, explicitKey: string | null): string | null {
  if (explicitKey && explicitKey.trim()) {
    return explicitKey.trim().replace(/^\/+/, "");
  }
  if (!ref) return null;
  const trimmed = ref.trim();
  if (trimmed.startsWith("s3://")) {
    const withoutScheme = trimmed.slice("s3://".length);
    const slashIdx = withoutScheme.indexOf("/");
    return slashIdx >= 0 ? withoutScheme.slice(slashIdx + 1) : null;
  }
  if (trimmed.startsWith("raw/") || trimmed.startsWith("processed/") || trimmed.startsWith("curated/")) {
    return trimmed;
  }
  return null;
}

export async function GET(request: NextRequest) {
  const ref = request.nextUrl.searchParams.get("ref");
  const s3KeyParam = request.nextUrl.searchParams.get("s3Key");
  const company = request.nextUrl.searchParams.get("company") || "IHCL";
  const pageParam = request.nextUrl.searchParams.get("page");

  if (!ref && !s3KeyParam) {
    return NextResponse.json({ error: "Missing ?ref= or ?s3Key= parameter" }, { status: 400 });
  }

  const s3Key = extractS3Key(ref, s3KeyParam);
  if (s3Key && isS3Configured()) {
    const presignedUrl = presignS3GetUrl(s3Key, { expiresIn: 900 });
    const isPdf = s3Key.toLowerCase().endsWith(".pdf");
    const fileName = s3Key.split("/").pop() || s3Key;
    return NextResponse.json({
      type: isPdf ? "pdf" : "csv",
      relativePath: s3Key,
      page: pageParam ? parseInt(pageParam, 10) : null,
      searchText: null,
      label: fileName,
      pdfUrl: isPdf ? presignedUrl : null,
      csvUrl: isPdf ? null : presignedUrl,
      source: "s3",
    });
  }

  if (!ref) {
    return NextResponse.json(
      { error: "S3 presigning is not configured and no ?ref= fallback was provided" },
      { status: 404 }
    );
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
    source: "local",
  });
}
