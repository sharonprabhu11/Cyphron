import { NextResponse } from "next/server";

function backendBase(): string | null {
  const u =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() ||
    process.env.BACKEND_URL?.trim() ||
    "";
  if (!u) return null;
  return u.replace(/\/$/, "");
}

export async function GET(_request: Request, context: { params: Promise<{ alertId: string }> }) {
  const { alertId: rawId } = await context.params;
  const alertId = decodeURIComponent(rawId);
  const base = backendBase();
  if (!base) {
    return NextResponse.json({ error: "NEXT_PUBLIC_BACKEND_URL is not configured." }, { status: 503 });
  }

  const url = `${base}/api/v1/alerts/${encodeURIComponent(alertId)}/report/pdf`;
  const upstream = await fetch(url, { method: "GET", cache: "no-store" });
  if (!upstream.ok) {
    const text = await upstream.text();
    return NextResponse.json(
      { error: text || upstream.statusText },
      { status: upstream.status === 404 ? 404 : 502 }
    );
  }

  const buf = Buffer.from(await upstream.arrayBuffer());
  const cd = upstream.headers.get("content-disposition");
  const headers: Record<string, string> = {
    "Content-Type": "application/pdf",
    "Cache-Control": "private, no-store",
  };
  if (cd) headers["Content-Disposition"] = cd;

  return new NextResponse(buf, { status: 200, headers });
}
