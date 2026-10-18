import type { CharacterDecisionInput, CharacterState, CharacterTurnInput } from './characterTypes';

let csrfToken = '';
let csrfRequest: Promise<string> | null = null;

export class CharacterApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'CharacterApiError';
  }
}

function detailMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(item => item && typeof item === 'object' && 'msg' in item ? String(item.msg) : String(item)).join(' · ');
  }
  if (detail && typeof detail === 'object' && 'message' in detail) return String(detail.message);
  return '요청을 완료하지 못했습니다. 다시 시도해 주세요.';
}

async function readResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const value = await response.json().catch(() => ({}));
    throw new CharacterApiError(detailMessage(value.detail), response.status);
  }
  return response.json() as Promise<T>;
}

export async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  if (!csrfRequest) {
    csrfRequest = fetch('/api/bootstrap', { credentials: 'same-origin' })
      .then(response => readResponse<{ csrf_token: string }>(response))
      .then(value => {
        csrfToken = value.csrf_token;
        return csrfToken;
      })
      .finally(() => { csrfRequest = null; });
  }
  return csrfRequest;
}

export function resetCsrfToken(): void {
  csrfToken = '';
}

function characterPath(projectId: string): string {
  return `/api/studio/projects/${encodeURIComponent(projectId)}/character`;
}

export async function getCharacter(projectId: string, signal?: AbortSignal): Promise<CharacterState> {
  return readResponse(await fetch(characterPath(projectId), { signal, credentials: 'same-origin' }));
}

async function mutateCharacter(projectId: string, action: string, body: CharacterTurnInput | CharacterDecisionInput, signal?: AbortSignal): Promise<CharacterState> {
  try {
    const token = await getCsrfToken();
    const response = await fetch(`${characterPath(projectId)}/${action}`, {
      method: 'POST',
      signal,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
      body: JSON.stringify(body),
    });
    if (response.status === 403) resetCsrfToken();
    return await readResponse(response);
  } finally {
    window.dispatchEvent(new Event('chatgpt-status-changed'));
  }
}

export function sendCharacterTurn(projectId: string, input: CharacterTurnInput, signal?: AbortSignal): Promise<CharacterState> {
  return mutateCharacter(projectId, 'turns', input, signal);
}

export function confirmCharacterDirection(projectId: string, input: CharacterDecisionInput, signal?: AbortSignal): Promise<CharacterState> {
  return mutateCharacter(projectId, 'confirm', input, signal);
}

export function reopenCharacterDirection(projectId: string, input: CharacterDecisionInput, signal?: AbortSignal): Promise<CharacterState> {
  return mutateCharacter(projectId, 'reopen', input, signal);
}

export const getCharacterState = getCharacter;
export const submitCharacterTurn = sendCharacterTurn;

export function hasAppliedCharacterTurn(before: CharacterState, after: CharacterState): boolean {
  return before.project_id === after.project_id && Boolean(after.brief &&
    (after.brief.version !== before.brief?.version || after.versions.length > before.versions.length));
}

export function hasAppliedCharacterMessage(state: CharacterState, message: string): boolean {
  return state.messages.some((item, index) => {
    if (item.role !== 'user' || item.content !== message.trim()) return false;
    const response = state.messages[index + 1];
    return response?.role === 'assistant' && Boolean(response.version && state.versions.some(brief => brief.version === response.version));
  });
}
