import { request, setCsrf } from './api';
import type { StudioAction, StudioInputKind, StudioProject, StudioProjectInput, StudioProjectSnapshot, StudioRun } from './studioTypes';

let studioCsrf = '';

export class StudioApiError extends Error {
  constructor(message: string, public status: number) { super(message); this.name = 'StudioApiError'; }
}

function detailMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(value => value && typeof value === 'object' && 'msg' in value ? String(value.msg) : String(value)).join(' · ');
  if (detail && typeof detail === 'object' && 'message' in detail) return String(detail.message);
  return '요청을 완료하지 못했습니다. 다시 시도해 주세요.';
}

async function studioRequest<T>(path: string, options: { method?: string; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  const method = options.method ?? 'GET';
  const response = await fetch(`/api/studio${path}`, {
    method,
    signal: options.signal,
    headers: { ...(method === 'GET' ? {} : { 'X-CSRF-Token': studioCsrf }), ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new StudioApiError(detailMessage(error.detail), response.status);
  }
  return response.json() as Promise<T>;
}

export async function initializeStudio(): Promise<StudioProject[]> {
  const [bootstrap, collection] = await Promise.all([
    request<{ csrf_token: string }>('/bootstrap'),
    studioRequest<{ projects: StudioProject[] }>('/projects'),
  ]);
  studioCsrf = bootstrap.csrf_token;
  setCsrf(studioCsrf);
  return collection.projects;
}

export function createStudioProject(input: StudioProjectInput): Promise<StudioProject> {
  return studioRequest('/projects', { method: 'POST', body: input });
}
export function createCharacterProject(name: string): Promise<StudioProject> {
  return studioRequest('/character-projects', { method: 'POST', body: { name: name.trim() || '새 캐릭터', synthetic_confirmed: true } });
}
export function getStudioProject(id: string, signal?: AbortSignal): Promise<StudioProjectSnapshot> {
  return studioRequest(`/projects/${encodeURIComponent(id)}`, { signal });
}
export function startStudioRun(id: string, idea: string, inputKind: StudioInputKind): Promise<StudioRun> {
  return studioRequest(`/projects/${encodeURIComponent(id)}/runs`, { method: 'POST', body: { idea, input_kind: inputKind } });
}
export function getStudioRun(projectId: string, id: string, signal?: AbortSignal): Promise<StudioRun> {
  return studioRequest(`/projects/${encodeURIComponent(projectId)}/runs/${encodeURIComponent(id)}`, { signal });
}
export function actOnStudioRun(run: StudioRun, action: StudioAction, feedback?: string, targetIds?: string[]): Promise<StudioRun> {
  return studioRequest(`/projects/${encodeURIComponent(run.project_id)}/runs/${encodeURIComponent(run.id)}/actions`, { method: 'POST', body: { action, expected_revision: run.revision, ...(feedback ? { feedback } : {}), ...(targetIds?.length ? { target_ids: targetIds } : {}) } });
}
