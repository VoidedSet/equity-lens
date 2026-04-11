import { NextRequest, NextResponse } from "next/server";

const GRAPH_API_URL = process.env.GRAPH_API_URL || "http://localhost:8001";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = path.join("/");
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${GRAPH_API_URL}/${apiPath}${searchParams ? `?${searchParams}` : ""}`;

  try {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const text = await response.text();
      return NextResponse.json(
        { error: text || response.statusText },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error(`Graph API proxy error [GET /${apiPath}]:`, error.message);
    return NextResponse.json(
      { error: `Graph API unreachable: ${error.message}` },
      { status: 502 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: segments } = await params;
  const apiPath = segments.join("/");
  const url = `${GRAPH_API_URL}/${apiPath}`;

  try {
    const body = await request.json();
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      return NextResponse.json(
        { error: text || response.statusText },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error(`Graph API proxy error [POST /${apiPath}]:`, error.message);
    return NextResponse.json(
      { error: `Graph API unreachable: ${error.message}` },
      { status: 502 }
    );
  }
}
