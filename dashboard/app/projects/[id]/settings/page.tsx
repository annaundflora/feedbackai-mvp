// dashboard/app/projects/[id]/settings/page.tsx
import { apiFetch } from "@/lib/api-client";
import type { ProjectResponse } from "@/lib/types";
import { SettingsForm } from "@/components/settings-form";
import { ModelConfigForm } from "@/components/model-config-form";
import { DangerZone } from "@/components/danger-zone";

interface SettingsPageProps {
  params: Promise<{ id: string }>;
}

export default async function SettingsPage({ params }: SettingsPageProps): Promise<JSX.Element> {
  const { id } = await params;
  const project = await apiFetch<ProjectResponse>(`/api/projects/${id}`);

  return (
    <div className="space-y-10 max-w-2xl">
      <section>
        <h2 className="text-base font-semibold text-gray-900 mb-4">General</h2>
        <SettingsForm project={project} />
      </section>

      <hr className="border-gray-200" />

      <section>
        <h2 className="text-base font-semibold text-gray-900 mb-1">
          Model Configuration (OpenRouter)
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Configure the LLM model slug for each task. Format: provider/model-name
        </p>
        <ModelConfigForm project={project} />
      </section>

      <hr className="border-gray-200" />

      <section>
        <h2 className="text-base font-semibold text-red-600 mb-4">Danger Zone</h2>
        <DangerZone projectId={id} projectName={project.name} />
      </section>
    </div>
  );
}
