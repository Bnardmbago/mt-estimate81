"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import DocumentUpload from "@/components/DocumentUpload";
import EstimateExtraction from "@/components/EstimateExtraction";
import EstimateForm, { type EstimateFormHandle } from "@/components/EstimateForm";
import type { EstimateDetail, EstimateDocument } from "@/lib/estimate";

type EstimateDetailContentProps = {
  estimate: EstimateDetail;
};

export default function EstimateDetailContent({
  estimate,
}: EstimateDetailContentProps) {
  const formRef = useRef<EstimateFormHandle>(null);
  const [hasUploadedDocuments, setHasUploadedDocuments] = useState(
    (estimate.documents ?? []).length > 0,
  );

  const handleDocumentsChange = useCallback((documents: EstimateDocument[]) => {
    setHasUploadedDocuments(documents.length > 0);
  }, []);

  useEffect(() => {
    setHasUploadedDocuments((estimate.documents ?? []).length > 0);
  }, [estimate.documents]);

  return (
    <>
      <EstimateForm
        ref={formRef}
        estimate={estimate}
        hasUploadedDocuments={hasUploadedDocuments}
      />
      <DocumentUpload
        estimateId={estimate.id}
        initialDocuments={estimate.documents ?? []}
        onDocumentsChange={handleDocumentsChange}
      />
      <EstimateExtraction estimate={estimate} formRef={formRef} />
    </>
  );
}
