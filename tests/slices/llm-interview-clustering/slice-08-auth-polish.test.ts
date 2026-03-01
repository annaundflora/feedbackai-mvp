// tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ─── Mock next/navigation ───────────────────────────────────────────────────
const mockReplace = vi.fn();
const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, refresh: mockRefresh }),
}));

// ─── Mock global fetch (for LoginPage which calls /api/auth/login directly) ─
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// ─── Mock clientFetch (for Client Components: DangerZone, SettingsForm, etc.)─
const mockClientFetch = vi.fn().mockResolvedValue({});
vi.mock("@/lib/client-api", () => ({
  clientFetch: (...args: unknown[]) => mockClientFetch(...args),
}));

// ─── Imports after mocks ─────────────────────────────────────────────────────
import LoginPage from "@/app/login/page";
import { UserAvatar } from "@/components/user-avatar";
import { DangerZone } from "@/components/danger-zone";
import { SettingsForm } from "@/components/settings-form";
import { SkeletonCard, SkeletonGrid } from "@/components/skeleton-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorBoundary } from "@/components/error-boundary";
import { AssignInterviewsModal } from "@/components/assign-interviews-modal";
import { InterviewsTabClient } from "@/components/interviews-tab-client";
import type { InterviewAssignment, AvailableInterview, ProjectResponse } from "@/lib/types";

// ─── Helpers ─────────────────────────────────────────────────────────────────
function mockFetchOk(data: unknown): void {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(data),
    status: 200,
  });
}

function mockFetchError(status: number, detail: string): void {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    json: () => Promise.resolve({ detail }),
    status,
  });
}

// ─── LoginPage ────────────────────────────────────────────────────────────────
describe("LoginPage", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockReplace.mockReset();
  });

  it("should disable submit button when fields are empty", () => {
    render(<LoginPage />);
    const button = screen.getByTestId("submit-button");
    expect(button).toBeDisabled();
  });

  it("should enable submit button when both fields are filled", async () => {
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "secret123");
    expect(screen.getByTestId("submit-button")).not.toBeDisabled();
  });

  it("should call POST /api/auth/login with credentials on submit", async () => {
    mockFetchOk({ success: true, user: { id: "1", email: "user@example.com" } });
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "secret123");
    await userEvent.click(screen.getByTestId("submit-button"));
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ email: "user@example.com", password: "secret123" }),
      }),
    );
  });

  it("should redirect to /projects after successful login", async () => {
    mockFetchOk({ success: true, user: { id: "1", email: "user@example.com" } });
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "secret123");
    await userEvent.click(screen.getByTestId("submit-button"));
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/projects"));
  });

  it("should display error message on 401 response", async () => {
    mockFetchError(401, "Invalid email or password");
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "wrong");
    await userEvent.click(screen.getByTestId("submit-button"));
    await waitFor(() =>
      expect(screen.getByTestId("login-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("login-error").textContent).toMatch(/Invalid credentials|Sign in failed/);
  });

  it("should show loading state during request", async () => {
    let resolve: (v: unknown) => void;
    mockFetch.mockReturnValueOnce(new Promise((r) => { resolve = r; }));
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "secret");
    await userEvent.click(screen.getByTestId("submit-button"));
    expect(screen.getByTestId("submit-button").textContent).toMatch(/Signing in/);
    resolve!({ ok: true, json: () => Promise.resolve({ success: true, user: {} }), status: 200 });
  });
});

// ─── UserAvatar ───────────────────────────────────────────────────────────────
describe("UserAvatar", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockReplace.mockReset();
  });

  it("should show initials derived from email", () => {
    render(<UserAvatar email="john.doe@example.com" />);
    expect(screen.getByTestId("user-avatar-button").textContent).toBe("JO");
  });

  it("should open dropdown on click", async () => {
    render(<UserAvatar email="user@example.com" />);
    await userEvent.click(screen.getByTestId("user-avatar-button"));
    expect(screen.getByTestId("user-menu")).toBeInTheDocument();
  });

  it("should call logout endpoint and redirect on logout click", async () => {
    mockFetchOk({ success: true });
    render(<UserAvatar email="user@example.com" />);
    await userEvent.click(screen.getByTestId("user-avatar-button"));
    await userEvent.click(screen.getByTestId("logout-button"));
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/login"));
  });
});

// ─── DangerZone ───────────────────────────────────────────────────────────────
describe("DangerZone", () => {
  beforeEach(() => {
    mockClientFetch.mockReset().mockResolvedValue({});
    mockReplace.mockReset();
  });

  it("should open confirmation modal on delete click", async () => {
    render(<DangerZone projectId="proj-1" projectName="My Project" />);
    await userEvent.click(screen.getByTestId("delete-project-button"));
    expect(screen.getByTestId("delete-confirm-modal")).toBeInTheDocument();
  });

  it("should keep delete button disabled until project name matches", async () => {
    render(<DangerZone projectId="proj-1" projectName="My Project" />);
    await userEvent.click(screen.getByTestId("delete-project-button"));
    const confirmButton = screen.getByTestId("delete-confirm-button");
    expect(confirmButton).toBeDisabled();
    await userEvent.type(screen.getByTestId("delete-confirm-input"), "My Project");
    expect(confirmButton).not.toBeDisabled();
  });

  it("should call DELETE /api/projects/{id} via clientFetch and redirect on confirmed delete", async () => {
    render(<DangerZone projectId="proj-1" projectName="My Project" />);
    await userEvent.click(screen.getByTestId("delete-project-button"));
    await userEvent.type(screen.getByTestId("delete-confirm-input"), "My Project");
    await userEvent.click(screen.getByTestId("delete-confirm-button"));
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1",
      expect.objectContaining({ method: "DELETE" }),
    );
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/projects"));
  });
});

// ─── EmptyState ───────────────────────────────────────────────────────────────
describe("EmptyState", () => {
  it("should render projects variant with CTA", () => {
    const onAction = vi.fn();
    render(<EmptyState variant="projects" onAction={onAction} />);
    expect(screen.getByTestId("empty-state-projects")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-projects-action")).toBeInTheDocument();
  });

  it("should call onAction when CTA is clicked", async () => {
    const onAction = vi.fn();
    render(<EmptyState variant="clusters" onAction={onAction} />);
    await userEvent.click(screen.getByTestId("empty-state-clusters-action"));
    expect(onAction).toHaveBeenCalledOnce();
  });

  it("should not render action button for facts variant (no action)", () => {
    render(<EmptyState variant="facts" />);
    expect(screen.queryByTestId("empty-state-facts-action")).toBeNull();
  });
});

// ─── SkeletonCard ─────────────────────────────────────────────────────────────
describe("SkeletonCard", () => {
  it("should render project skeleton", () => {
    render(<SkeletonCard variant="project" />);
    expect(screen.getByTestId("skeleton-project")).toBeInTheDocument();
  });

  it("should render cluster skeleton", () => {
    render(<SkeletonCard variant="cluster" />);
    expect(screen.getByTestId("skeleton-cluster")).toBeInTheDocument();
  });

  it("should render N skeleton cards in SkeletonGrid", () => {
    render(<SkeletonGrid count={4} variant="project" />);
    expect(screen.getAllByTestId("skeleton-project")).toHaveLength(4);
  });
});

// ─── ErrorBoundary ────────────────────────────────────────────────────────────
describe("ErrorBoundary", () => {
  // Suppress console.error from React for expected error
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }): JSX.Element {
    if (shouldThrow) throw new Error("Test error");
    return <div>OK</div>;
  }

  it("should render children when no error", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  it("should render fallback UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("error-boundary-fallback")).toBeInTheDocument();
    expect(screen.getByTestId("error-boundary-retry")).toBeInTheDocument();
  });
});

// ─── SettingsForm ─────────────────────────────────────────────────────────────
describe("SettingsForm", () => {
  const mockProject: ProjectResponse = {
    id: "proj-1",
    name: "My Research Project",
    research_goal: "Understand user pain points",
    prompt_context: null,
    extraction_source: "summary",
    extraction_source_locked: false,
    interview_count: 0,
    cluster_count: 0,
    fact_count: 0,
    model_interviewer: "openai/gpt-4o",
    model_extraction: "openai/gpt-4o-mini",
    model_clustering: "openai/gpt-4o-mini",
    model_summary: "openai/gpt-4o-mini",
    created_at: "2026-02-28T10:00:00Z",
    updated_at: "2026-02-28T10:00:00Z",
  };

  const lockedProject: ProjectResponse = {
    ...mockProject,
    extraction_source_locked: true,
    fact_count: 47,
  };

  beforeEach(() => {
    mockClientFetch.mockReset().mockResolvedValue({});
    mockRefresh.mockReset();
  });

  it("should render settings form with inputs", () => {
    render(<SettingsForm project={mockProject} />);
    expect(screen.getByTestId("settings-form")).toBeInTheDocument();
    expect(screen.getByTestId("settings-name-input")).toHaveValue("My Research Project");
    expect(screen.getByTestId("settings-research-goal-input")).toHaveValue(
      "Understand user pain points",
    );
  });

  it("should keep save button disabled when form is pristine", () => {
    render(<SettingsForm project={mockProject} />);
    expect(screen.getByTestId("settings-save-button")).toBeDisabled();
  });

  it("should enable save button after editing name and call clientFetch PUT on save", async () => {
    render(<SettingsForm project={mockProject} />);
    await userEvent.clear(screen.getByTestId("settings-name-input"));
    await userEvent.type(screen.getByTestId("settings-name-input"), "Updated Name");
    const saveBtn = screen.getByTestId("settings-save-button");
    expect(saveBtn).not.toBeDisabled();
    await userEvent.click(saveBtn);
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1",
      expect.objectContaining({ method: "PUT" }),
    );
  });

  it("should show locked source display when extraction_source_locked is true (AC-8)", () => {
    render(<SettingsForm project={lockedProject} />);
    expect(screen.getByTestId("extraction-source-locked")).toBeInTheDocument();
    expect(screen.getByTestId("reset-source-link")).toBeInTheDocument();
    expect(screen.queryByTestId("extraction-source-select")).toBeNull();
  });

  it("should open ResetSourceModal when reset link is clicked", async () => {
    render(<SettingsForm project={lockedProject} />);
    await userEvent.click(screen.getByTestId("reset-source-link"));
    expect(screen.getByTestId("reset-source-modal")).toBeInTheDocument();
  });

  it("should call clientFetch PUT extraction-source with new source via ResetSourceModal", async () => {
    render(<SettingsForm project={lockedProject} />);
    await userEvent.click(screen.getByTestId("reset-source-link"));
    // Default newSource is "transcript" (opposite of locked "summary")
    await userEvent.click(screen.getByTestId("reset-source-confirm"));
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1/extraction-source",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ extraction_source: "transcript", re_extract: false }),
      }),
    );
  });
});

// ─── InterviewsTabClient ─────────────────────────────────────────────────────
describe("InterviewsTabClient", () => {
  const mockInterviews: InterviewAssignment[] = [
    {
      interview_id: "iv-1",
      date: "2026-02-28T10:00:00Z",
      summary_preview: "User had issues with navigation",
      fact_count: 4,
      extraction_status: "completed",
      clustering_status: "completed",
    },
    {
      interview_id: "iv-2",
      date: "2026-02-27T09:00:00Z",
      summary_preview: "Pricing was confusing",
      fact_count: 0,
      extraction_status: "failed",
      clustering_status: "failed",
    },
  ];

  beforeEach(() => {
    mockClientFetch.mockReset().mockResolvedValue({});
    mockRefresh.mockReset();
  });

  it("should render interview table with status badges", () => {
    render(<InterviewsTabClient projectId="proj-1" initialInterviews={mockInterviews} />);
    expect(screen.getByTestId("interviews-table")).toBeInTheDocument();
    expect(screen.getByTestId("interview-status-iv-1").textContent).toBe("analyzed");
    expect(screen.getByTestId("interview-status-iv-2").textContent).toBe("failed");
  });

  it("should show retry button for failed interviews", () => {
    render(<InterviewsTabClient projectId="proj-1" initialInterviews={mockInterviews} />);
    expect(screen.getByTestId("retry-button-iv-2")).toBeInTheDocument();
    expect(screen.queryByTestId("retry-button-iv-1")).toBeNull();
  });

  it("should call retry endpoint via clientFetch and refresh on retry click", async () => {
    render(<InterviewsTabClient projectId="proj-1" initialInterviews={mockInterviews} />);
    await userEvent.click(screen.getByTestId("retry-button-iv-2"));
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1/interviews/iv-2/retry",
      expect.objectContaining({ method: "POST" }),
    );
    await waitFor(() => expect(mockRefresh).toHaveBeenCalled());
  });

  it("should show empty state when no interviews", () => {
    render(<InterviewsTabClient projectId="proj-1" initialInterviews={[]} />);
    expect(screen.getByTestId("empty-state-interviews")).toBeInTheDocument();
  });
});

// ─── AssignInterviewsModal ───────────────────────────────────────────────────
describe("AssignInterviewsModal", () => {
  const mockAvailable: AvailableInterview[] = [
    { session_id: "sess-1", created_at: "2026-02-28T10:00:00Z", summary_preview: "Preview 1" },
    { session_id: "sess-2", created_at: "2026-02-27T09:00:00Z", summary_preview: "Preview 2" },
  ];

  beforeEach(() => {
    mockClientFetch.mockReset();
  });

  it("should load and display available interviews", async () => {
    mockClientFetch.mockResolvedValueOnce(mockAvailable);
    render(
      <AssignInterviewsModal projectId="proj-1" onClose={vi.fn()} onAssigned={vi.fn()} />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("assign-checkbox-sess-1")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("assign-checkbox-sess-2")).toBeInTheDocument();
  });

  it("should keep assign button disabled until at least 1 is selected", async () => {
    mockClientFetch.mockResolvedValueOnce(mockAvailable);
    render(
      <AssignInterviewsModal projectId="proj-1" onClose={vi.fn()} onAssigned={vi.fn()} />,
    );
    await waitFor(() => screen.getByTestId("assign-checkbox-sess-1"));
    expect(screen.getByTestId("assign-modal-confirm")).toBeDisabled();
    await userEvent.click(screen.getByTestId("assign-checkbox-sess-1"));
    expect(screen.getByTestId("assign-modal-confirm")).not.toBeDisabled();
  });

  it("should call POST interviews with selected IDs on confirm via clientFetch", async () => {
    mockClientFetch.mockResolvedValueOnce(mockAvailable).mockResolvedValueOnce({});
    const onAssigned = vi.fn();
    render(
      <AssignInterviewsModal projectId="proj-1" onClose={vi.fn()} onAssigned={onAssigned} />,
    );
    await waitFor(() => screen.getByTestId("assign-checkbox-sess-1"));
    await userEvent.click(screen.getByTestId("assign-checkbox-sess-1"));
    await userEvent.click(screen.getByTestId("assign-modal-confirm"));
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1/interviews",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ interview_ids: ["sess-1"] }),
      }),
    );
    await waitFor(() => expect(onAssigned).toHaveBeenCalled());
  });
});
