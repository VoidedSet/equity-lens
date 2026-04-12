import { NextResponse } from "next/server";
import { parseCSV, getCompanyCSVPath } from "@/lib/csv-parser";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const companyId = searchParams.get("companyId");
  const fileName = searchParams.get("fileName");

  if (!companyId || !fileName) {
    return NextResponse.json({ error: "Missing companyId or fileName" }, { status: 400 });
  }

  try {
    const csvPath = getCompanyCSVPath(companyId, fileName);
    if (!csvPath) {
      return NextResponse.json({ error: "Company path not found" }, { status: 404 });
    }

    const data = parseCSV(csvPath);
    return NextResponse.json({ data });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
