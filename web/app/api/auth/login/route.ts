import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://api:8000";

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid request body", code: "VALIDATION_ERROR" },
      { status: 400 },
    );
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (error) {
    console.error("Login API unreachable:", error);
    return NextResponse.json(
      { error: "Could not reach the authentication server", code: "API_UNREACHABLE" },
      { status: 502 },
    );
  }

  let data: { access_token?: string; user?: unknown; error?: string; code?: string };
  try {
    data = await backendResponse.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid response from authentication server", code: "API_INVALID_RESPONSE" },
      { status: 502 },
    );
  }

  if (!backendResponse.ok) {
    return NextResponse.json(data, { status: backendResponse.status });
  }

  if (typeof data.access_token !== "string") {
    return NextResponse.json(
      { error: "Invalid response from authentication server", code: "API_INVALID_RESPONSE" },
      { status: 502 },
    );
  }

  const response = NextResponse.json({ user: data.user });
  const cookieSecure = process.env.COOKIE_SECURE === "true";
  response.cookies.set("access_token", data.access_token, {
    httpOnly: true,
    secure: cookieSecure,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 8,
  });

  return response;
}
