import { Suspense } from 'react'
import Link from 'next/link'
import { cache } from 'react'
import { apiClient } from '@/lib/api-client'
import { InterviewDetailSkeleton } from '@/components/interview-detail-skeleton'
import { InterviewDetailClient } from '@/components/interview-detail-client'

const getInterviewDetail = cache(
  (projectId: string, interviewId: string) =>
    apiClient.getInterviewDetail(projectId, interviewId)
)

interface InterviewDetailContentProps {
  projectId: string
  interviewId: string
}

async function InterviewDetailContent({
  projectId,
  interviewId,
}: InterviewDetailContentProps) {
  const interview = await getInterviewDetail(projectId, interviewId)

  return (
    <InterviewDetailClient
      projectId={projectId}
      interview={interview}
    />
  )
}

interface Props {
  params: Promise<{ id: string; interview_id: string }>
}

export default async function InterviewDetailPage({ params }: Props) {
  const { id, interview_id } = await params

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      {/* Back navigation */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          href={`/projects/${id}`}
          data-testid="back-to-interviews"
          aria-label="Back to project interviews"
          className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          &larr; Back to Interviews
        </Link>
      </div>

      <Suspense fallback={<InterviewDetailSkeleton />}>
        <InterviewDetailContent projectId={id} interviewId={interview_id} />
      </Suspense>
    </main>
  )
}
