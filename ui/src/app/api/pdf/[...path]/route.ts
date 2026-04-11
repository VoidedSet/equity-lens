import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: segments } = await params;
  const relativePath = segments.join("/");

  // Resolve to Raw Data Extraction folder
  const RAW_DIR = path.resolve(process.cwd(), "../Raw Data Extraction");
  const filePath = path.join(RAW_DIR, relativePath);

  // Security: ensure we stay inside RAW_DIR
  const resolved = path.resolve(filePath);
  if (!resolved.startsWith(path.resolve(RAW_DIR))) {
    return NextResponse.json({ error: "Access denied" }, { status: 403 });
  }

  if (!fs.existsSync(resolved)) {
    return NextResponse.json(
      { error: `File not found: ${relativePath}` },
      { status: 404 }
    );
  }

  const ext = path.extname(resolved).toLowerCase();
  const buffer = fs.readFileSync(resolved);

  if (ext === ".pdf") {
    return new NextResponse(buffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `inline; filename="${path.basename(resolved)}"`,
        "Cache-Control": "public, max-age=3600",
      },
    });
  }

  if (ext === ".csv") {
    return new NextResponse(buffer, {
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `inline; filename="${path.basename(resolved)}"`,
      },
    });
  }

  if (ext === ".json") {
    return new NextResponse(buffer, {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": `inline; filename="${path.basename(resolved)}"`,
        "Cache-Control": "public, max-age=3600",
      },
    });
  }

  if (ext === ".txt") {
    return new NextResponse(buffer, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": `inline; filename="${path.basename(resolved)}"`,
        "Cache-Control": "public, max-age=3600",
      },
    });
  }

  return NextResponse.json({ error: "Unsupported file type" }, { status: 400 });
}
