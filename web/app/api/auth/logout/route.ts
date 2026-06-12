import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  const cookieSecure = process.env.COOKIE_SECURE === "true";

  response.cookies.set("access_token", "", {
    httpOnly: true,
    secure: cookieSecure,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });

  return response;
}
