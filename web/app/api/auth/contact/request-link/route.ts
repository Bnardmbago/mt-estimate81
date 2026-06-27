import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://api:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${API_URL}/auth/contact/request-link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
