import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { resolveAuthenticatedHome } from "@/lib/contact";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (token) {
    redirect(await resolveAuthenticatedHome(locale, token.value));
  }

  redirect(`/${locale}/welcome`);
}
