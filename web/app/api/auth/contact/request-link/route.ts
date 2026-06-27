import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://api:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const proxyHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const host = request.headers.get("host");
  const forwardedProto = request.headers.get("x-forwarded-proto");
  const proto =
    forwardedProto ??
    (request.nextUrl.protocol === "https:" ? "https" : "http");
  if (host) {
    proxyHeaders["X-Forwarded-Host"] = host;
    proxyHeaders["X-Forwarded-Proto"] = proto;
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${API_URL}/auth/contact/request-link`, {
      method: "POST",
      headers: proxyHeaders,
      body: JSON.stringify(body),
    });
  } catch {
    return NextResponse.json(
      {
        error: "Could not reach the API server.",
        code: "API_UNREACHABLE",
      },
      { status: 502 },
    );
  }

  if (!backendResponse.ok) {
    const data = await backendResponse.json().catch(() => ({
      error: "The API server returned an unexpected response.",
      code: "API_BAD_RESPONSE",
    }));
    return NextResponse.json(data, { status: backendResponse.status });
  }

  return new NextResponse(null, { status: 204 });
}
