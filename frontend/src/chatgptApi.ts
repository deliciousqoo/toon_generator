import { getCsrfToken, resetCsrfToken } from './characterApi';

export interface ChatGPTModel {
  slug: string;
  display_name: string;
}

export interface ChatGPTConnectionStatus {
  connected: boolean;
  sharing: boolean;
  login_pending: boolean;
  blocked: boolean;
  reason?: string;
  account_label?: string | null;
  model?: string | null;
  models: ChatGPTModel[];
  manage_usage_url: string;
  fixture: boolean;
}

export interface ChatGPTLogin {
  authorization_url: string;
  expires_in: number;
}

export class ChatGPTApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'ChatGPTApiError';
  }
}

async function connectionRequest<T>(action = '', body?: unknown, signal?: AbortSignal): Promise<T> {
  const method = body === undefined ? 'GET' : 'POST';
  const token = body === undefined ? '' : await getCsrfToken();
  const response = await fetch(`/api/studio/chatgpt${action}`, {
    method, signal, credentials: 'same-origin',
    headers: method === 'GET' ? {} : { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 403) resetCsrfToken();
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = typeof error.detail === 'string' ? error.detail : 'ChatGPT 연결 요청을 완료하지 못했습니다.';
    throw new ChatGPTApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function getChatGPTStatus(signal?: AbortSignal): Promise<ChatGPTConnectionStatus> {
  return connectionRequest('', undefined, signal);
}

export function loginWithChatGPT(signal?: AbortSignal): Promise<ChatGPTLogin> {
  return connectionRequest('/login', {}, signal);
}

export function disconnectChatGPT(signal?: AbortSignal): Promise<unknown> {
  return connectionRequest('/disconnect', {}, signal);
}

export function selectChatGPTModel(model: string, signal?: AbortSignal): Promise<unknown> {
  return connectionRequest('/model', { model }, signal);
}

export function getChatGPTModels(signal?: AbortSignal): Promise<{ models: ChatGPTModel[] }> {
  return connectionRequest('/models', undefined, signal);
}

export function resumeChatGPT(signal?: AbortSignal): Promise<unknown> {
  return connectionRequest('/resume', {}, signal);
}

export function canUseChatGPT(status: ChatGPTConnectionStatus | null | undefined): boolean {
  return Boolean(status?.fixture || (status?.connected && status.sharing && !status.blocked && status.model && status.models.some(model => model.slug === status.model)));
}

const USAGE_REASONS = new Set([
  'subscription_limit', 'subscription_sharing_usage_limit_exceeded', 'subscription_sharing_usage_unavailable',
  'subscription_sharing_user_unavailable', 'rate_limit_exceeded', 'insufficient_quota', 'character_call_limit',
]);

const RECONNECT_REASONS = new Set([
  'authentication_required', 'subscription_sharing_invalid_user', 'sharing_not_authorized',
  'chatpass_v2_scope_not_authorized', 'chatpass_v2_invalid_authorization_context',
  'subscription_sharing_user_not_eligible', 'permission_denied', 'invalid_grant', 'invalid_refresh_token',
  'token_expired', 'refresh_token_expired', 'refresh_token_invalidated', 'refresh_token_reused',
]);

export function isChatGPTUsageLimit(status: ChatGPTConnectionStatus | null | undefined): boolean {
  return Boolean(status?.blocked && status.reason && USAGE_REASONS.has(status.reason));
}

export function needsChatGPTReconnect(status: ChatGPTConnectionStatus | null | undefined): boolean {
  return Boolean(status?.blocked && status.reason && RECONNECT_REASONS.has(status.reason));
}

export function safeConnectionUrl(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' ? url.href : undefined;
  } catch { return undefined; }
}
