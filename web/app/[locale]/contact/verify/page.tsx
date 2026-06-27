import { Suspense } from "react";
import ContactVerifyClient from "@/components/contact/ContactVerifyClient";

export default function ContactVerifyPage() {
  return (
    <Suspense
      fallback={<div className="mx-auto max-w-md text-center text-sm text-gray-500">...</div>}
    >
      <ContactVerifyClient />
    </Suspense>
  );
}
