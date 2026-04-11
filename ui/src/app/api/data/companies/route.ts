import { NextResponse } from "next/server";
import { getCompanies } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const companies = await getCompanies();
  return NextResponse.json(companies);
}
