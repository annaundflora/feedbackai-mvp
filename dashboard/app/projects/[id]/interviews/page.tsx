// dashboard/app/projects/[id]/interviews/page.tsx
import { apiFetch } from "@/lib/api-client";
import type { InterviewAssignment } from "@/lib/types";
import { InterviewsTabClient } from "@/components/interviews-tab-client";

interface InterviewsPageProps {
  params: Promise<{ id: string }>;
}

export default async function InterviewsPage({ params }: InterviewsPageProps): Promise<JSX.Element> {
  const { id } = await params;
  const interviews = await apiFetch<InterviewAssignment[]>(`/api/projects/${id}/interviews`);

  return <InterviewsTabClient projectId={id} initialInterviews={interviews} />;
}
