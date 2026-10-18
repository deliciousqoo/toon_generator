import { CharacterApiError, getCsrfToken, resetCsrfToken } from './characterApi';
import type { CharacterState } from './characterTypes';
import type { VisualMutation, VisualJobInput, VisualSelectionInput, VisualCoverageInput, VisualComponentInput, VisualSheetBuildInput, VisualSheetDecisionInput, VisualProvenance } from './characterVisualTypes';

function basePath(projectId: string) { return `/api/studio/projects/${encodeURIComponent(projectId)}/character/visual`; }

async function mutate(projectId: string, action: string, body: object | FormData, signal?: AbortSignal): Promise<CharacterState> {
  const token = await getCsrfToken();
  const multipart = body instanceof FormData;
  const response = await fetch(`${basePath(projectId)}/${action}`, {
    method: 'POST', credentials: 'same-origin', signal,
    headers: { 'X-CSRF-Token': token, ...(multipart ? {} : { 'Content-Type': 'application/json' }) },
    body: multipart ? body : JSON.stringify(body),
  });
  if (response.status === 403) {
    resetCsrfToken();
    throw new CharacterApiError('연결 세션이 갱신됐습니다. 작성한 내용은 보관했습니다. 다시 시도해 주세요.', 403);
  }
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    const detail: unknown = result.detail;
    const message = typeof detail === 'string' ? detail : detail && typeof detail === 'object' && 'message' in detail
      ? String(detail.message) : '이미지 작업을 반영하지 못했습니다. 입력한 내용은 보관했습니다.';
    throw new CharacterApiError(message, response.status);
  }
  return response.json() as Promise<CharacterState>;
}

export const requestVisualJob = (projectId: string, input: VisualJobInput, signal?: AbortSignal) => mutate(projectId, 'jobs', input, signal);
export const selectVisualCandidate = (projectId: string, input: VisualSelectionInput, signal?: AbortSignal) => mutate(projectId, 'select', input, signal);
export const saveVisualCoverage = (projectId: string, input: VisualCoverageInput, signal?: AbortSignal) => mutate(projectId, 'coverage', input, signal);
export const attachVisualComponent = (projectId: string, componentId: string, input: VisualComponentInput, signal?: AbortSignal) => mutate(projectId, `components/${encodeURIComponent(componentId)}/attach`, input, signal);
export const buildVisualSheet = (projectId: string, input: VisualSheetBuildInput, signal?: AbortSignal) => mutate(projectId, 'sheet/build', input, signal);
export const confirmVisualSheet = (projectId: string, input: VisualSheetDecisionInput, signal?: AbortSignal) => mutate(projectId, 'sheet/confirm', input, signal);
export const reopenVisualSheet = (projectId: string, input: VisualSheetDecisionInput, signal?: AbortSignal) => mutate(projectId, 'sheet/reopen', input, signal);
export const cancelVisualJob = (projectId: string, jobId: string, input: VisualMutation, signal?: AbortSignal) => mutate(projectId, `jobs/${encodeURIComponent(jobId)}/cancel`, input, signal);

export function uploadVisualImage(projectId: string, jobId: string, input: VisualMutation, file: File, provenance: VisualProvenance, signal?: AbortSignal) {
  const data = new FormData();
  data.append('request', JSON.stringify({ ...input, provenance }));
  data.append('file', file);
  return mutate(projectId, `jobs/${encodeURIComponent(jobId)}/image`, data, signal);
}

export function visualAssetUrl(projectId: string, assetId: string, url: string): string | undefined {
  const expected = `${basePath(projectId)}/assets/${encodeURIComponent(assetId)}`;
  return url === expected ? expected : undefined;
}

export function visualSheetExportUrl(projectId: string): string {
  return `${basePath(projectId)}/sheet/export`;
}

export async function downloadVisualSheet(projectId: string, signal?: AbortSignal): Promise<Blob> {
  const response = await fetch(visualSheetExportUrl(projectId), { credentials: 'same-origin', redirect: 'error', signal });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    const message = typeof result.detail === 'string' ? result.detail : '시트를 내려받지 못했습니다. 현재 시트와 이미지 상태를 다시 확인해 주세요.';
    throw new CharacterApiError(message, response.status);
  }
  if (response.headers.get('Content-Type')?.split(';')[0].trim() !== 'application/zip') {
    throw new Error('시트 파일을 확인하지 못했습니다. 다시 불러온 뒤 시도해 주세요.');
  }
  return response.blob();
}
