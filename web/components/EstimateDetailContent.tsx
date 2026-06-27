"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import DocumentUpload from "@/components/DocumentUpload";
import EstimateAiSpecPanel from "@/components/EstimateAiSpecPanel";
import EstimateFormTemplateSelect from "@/components/EstimateFormTemplateSelect";
import EstimateExtraction from "@/components/EstimateExtraction";
import EstimateForm, { type EstimateFormHandle } from "@/components/EstimateForm";
import EstimateRateCardPanel from "@/components/EstimateRateCardPanel";
import type { EstimateDetail, EstimateDocument } from "@/lib/estimate";

type EstimateDetailContentProps = {
  estimate: EstimateDetail;
  isContactUser?: boolean;
};

export default function EstimateDetailContent({
  estimate,
  isContactUser = false,
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

  const isDraft = estimate.status === "draft";

  return (
    <>
      {isDraft ? <EstimateFormTemplateSelect estimate={estimate} /> : null}
      <EstimateForm
        ref={formRef}
        estimate={estimate}
        hasUploadedDocuments={hasUploadedDocuments}
      >
        {isDraft ? (
          <EstimateAiSpecPanel
            estimateId={estimate.id}
            estimate={estimate}
            formRef={formRef}
          />
        ) : null}
      </EstimateForm>
      <DocumentUpload
        estimateId={estimate.id}
        initialDocuments={estimate.documents ?? []}
        onDocumentsChange={handleDocumentsChange}
      />
      {isDraft && !isContactUser ? (
        <section className="mt-8 border-t border-gray-200 pt-8">
          <EstimateRateCardPanel
            estimateId={estimate.id}
            rateCardId={estimate.rate_card_id}
            rateCardName={estimate.rate_card_name}
            complexityProfile={estimate.complexity_profile ?? null}
            rateCardAutoTuned={estimate.rate_card_auto_tuned ?? false}
            rateCardTuneRecommended={estimate.rate_card_tune_recommended ?? false}
            rateCardAutoTuneEnabled={estimate.rate_card_auto_tune_enabled ?? true}
          />
        </section>
      ) : null}
      <EstimateExtraction
        estimate={estimate}
        formRef={formRef}
        hideDraftRateCard={isDraft}
        isContactUser={isContactUser}
      />
    </>
  );
}
