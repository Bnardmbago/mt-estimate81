import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://api:8000";
const CONTACT_COOKIE_MAX_AGE = 60 * 60 * 72;

export async function POST(request: NextRequest) {
  const body = await request.json();

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${API_URL}/auth/contact/verify`, {
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

  const data = await backendResponse.json().catch(() => ({
    error: "The API server returned an unexpected response.",
    code: "API_BAD_RESPONSE",
  }));

  if (!backendResponse.ok) {
    return NextResponse.json(data, { status: backendResponse.status });
  }

  const response = NextResponse.json({
    estimate_id: data.estimate_id,
    user: data.user,
  });
  const cookieSecure = process.env.COOKIE_SECURE === "true";
  response.cookies.set("access_token", data.access_token, {
    httpOnly: true,
    secure: cookieSecure,
    sameSite: "lax",
    path: "/",
    maxAge: CONTACT_COOKIE_MAX_AGE,
  });

  return response;
}
