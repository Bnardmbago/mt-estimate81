import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { resolveReturnPath } from "@/lib/authRedirect";
import LoginForm from "./LoginForm";

export default async function LoginPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ next?: string }>;
}) {
  const { locale } = await params;
  const { next } = await searchParams;
  const cookieStore = await cookies();

  if (cookieStore.get("access_token")) {
    redirect(resolveReturnPath(locale, next));
  }

  return (
    <Suspense fallback={<div className="mx-auto max-w-md text-sm text-gray-500">...</div>}>
      <LoginForm />
    </Suspense>
  );
}
