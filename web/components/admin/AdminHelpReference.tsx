"use client";

import HelpKnowledgePanel from "@/components/help/HelpKnowledgePanel";
import HelpPipelineDiagram from "@/components/help/HelpPipelineDiagram";
import HelpUserGuideDiagram from "@/components/help/HelpUserGuideDiagram";

export default function AdminHelpReference() {
  return (
    <div className="space-y-8">
      <HelpPipelineDiagram namespace="admin.help" />
      <HelpUserGuideDiagram namespace="admin.help" />
      <HelpKnowledgePanel namespace="admin.help" searchInputId="admin-help-search" />
    </div>
  );
}
