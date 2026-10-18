import { getCsrfToken, resetCsrfToken } from './characterApi';
import type { VisualProvenance } from './characterVisualTypes';
import type { EpisodeCreateInput, EpisodeDecisionInput, EpisodeFormatInput, EpisodeRequest, EpisodeRoughJobInput, EpisodeRoughUploadInput, EpisodeState, EpisodeTurnInput } from './episodeTypes';

export class EpisodeApiError extends Error {
  constructor(message: string, public status: number) { super(message); this.name = 'EpisodeApiError'; }
}

function basePath(projectId: string) { return `/api/studio/projects/${encodeURIComponent(projectId)}/episodes`; }
function episodePath(projectId: string, episodeId: string) { return `${basePath(projectId)}/${encodeURIComponent(episodeId)}`; }
function detailMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(value => value && typeof value === 'object' && 'msg' in value ? String(value.msg) : String(value)).join(' · ');
  if (detail && typeof detail === 'object' && 'message' in detail) return String(detail.message);
  return '작업을 반영하지 못했습니다. 작성한 내용은 보관했습니다.';
}
async function readResponse<T>(response: Response): Promise<T> {
  if (response.status === 403) resetCsrfToken();
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new EpisodeApiError(detailMessage(result.detail), response.status);
  }
  return response.json() as Promise<T>;
}
async function post(path: string, body: object | FormData, signal?: AbortSignal): Promise<EpisodeState> {
  try {
    const token = await getCsrfToken();
    const multipart = body instanceof FormData;
    return await readResponse(await fetch(path, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: { 'X-CSRF-Token': token, ...(multipart ? {} : { 'Content-Type': 'application/json' }) },
      body: multipart ? body : JSON.stringify(body),
    }));
  } finally { window.dispatchEvent(new Event('chatgpt-status-changed')); }
}
export async function listEpisodes(projectId: string, signal?: AbortSignal): Promise<EpisodeState[]> {
  const result = await readResponse<{ episodes: EpisodeState[] }>(await fetch(basePath(projectId), { credentials: 'same-origin', signal }));
  return result.episodes;
}
export async function getEpisode(projectId: string, episodeId: string, signal?: AbortSignal): Promise<EpisodeState> {
  return readResponse(await fetch(episodePath(projectId, episodeId), { credentials: 'same-origin', signal }));
}
export const createEpisode = (projectId: string, input: EpisodeCreateInput, signal?: AbortSignal) => post(basePath(projectId), input, signal);
export const sendEpisodeTurn = (projectId: string, episodeId: string, input: EpisodeTurnInput, signal?: AbortSignal) => post(`${episodePath(projectId, episodeId)}/turns`, input, signal);
export const decideEpisode = (projectId: string, episodeId: string, input: EpisodeDecisionInput, signal?: AbortSignal) => post(`${episodePath(projectId, episodeId)}/decisions`, input, signal);
export const saveEpisodeFormat = (projectId: string, episodeId: string, input: EpisodeFormatInput, signal?: AbortSignal) => post(`${episodePath(projectId, episodeId)}/format`, input, signal);
export const requestEpisodeRough = (projectId: string, episodeId: string, input: EpisodeRoughJobInput, signal?: AbortSignal) => post(`${episodePath(projectId, episodeId)}/rough/jobs`, input, signal);
export const cancelEpisodeRough = (projectId: string, episodeId: string, jobId: string, input: EpisodeRequest, signal?: AbortSignal) => post(`${episodePath(projectId, episodeId)}/rough/jobs/${encodeURIComponent(jobId)}/cancel`, input, signal);
export function uploadEpisodeRough(projectId: string, episodeId: string, jobId: string, input: EpisodeRoughUploadInput, file: File, provenance: VisualProvenance, signal?: AbortSignal) {
  const data = new FormData();
  data.append('request', JSON.stringify({ ...input, provenance }));
  data.append('file', file);
  return post(`${episodePath(projectId, episodeId)}/rough/jobs/${encodeURIComponent(jobId)}/image`, data, signal);
}
export function roughAssetUrl(projectId: string, episodeId: string, assetId: string, url: string): string | undefined {
  const expected = `${episodePath(projectId, episodeId)}/rough/assets/${encodeURIComponent(assetId)}`;
  return url === expected ? expected : undefined;
}
export async function downloadEpisode(projectId: string, episodeId: string, signal?: AbortSignal): Promise<Blob> {
  const response = await fetch(`${episodePath(projectId, episodeId)}/export`, { credentials: 'same-origin', redirect: 'error', signal });
  if (!response.ok) return readResponse(response);
  if (response.headers.get('Content-Type')?.split(';')[0].trim() !== 'application/zip') throw new Error('콘티 파일을 확인하지 못했습니다. 결과를 다시 불러온 뒤 시도해 주세요.');
  return response.blob();
}
