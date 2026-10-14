let csrf = '';
export function setCsrf(value: string) { csrf = value; }
function message(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(v => typeof v === 'object' && v !== null && 'msg' in v ? String(v.msg) : String(v)).join(' · ');
  return '요청을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.';
}
export async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const isForm = body instanceof FormData;
  if (method !== 'GET') headers['X-CSRF-Token'] = csrf;
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : isForm ? body : JSON.stringify(body) });
  if (!response.ok) { const error = await response.json().catch(() => ({})); throw new Error(message(error.detail)); }
  return response.json() as Promise<T>;
}
type SavePicker = (options: { suggestedName: string; types: { description: string; accept: Record<string, string[]> }[] }) => Promise<{ createWritable(): Promise<{ write(data: Blob): Promise<void>; close(): Promise<void> }> }>;
export async function exportBackup(projectId: string, encrypted: boolean, passphrase: string): Promise<void> {
  const filename = `${projectId}${encrypted ? '.toonbackup.age' : '.toonbackup'}`;
  const picker = (window as unknown as { showSaveFilePicker?: SavePicker }).showSaveFilePicker;
  if (!picker) {
    const saved = await request<{ saved: boolean; cancelled: boolean; filename?: string }>(`/projects/${encodeURIComponent(projectId)}/backup/save`, 'POST', { encrypted, ...(encrypted ? { passphrase } : {}) });
    if (saved.cancelled) throw new DOMException('저장을 취소했습니다.', 'AbortError');
    if (!saved.saved) throw new Error('백업 저장을 완료하지 못했습니다. 다시 시도해 주세요.');
    return;
  }
  // Open the location picker during the direct user gesture, before awaiting the server.
  const handle = await picker({ suggestedName: filename, types: [{ description: encrypted ? '암호화 프로젝트 백업' : '프로젝트 백업', accept: { 'application/octet-stream': [encrypted ? '.age' : '.toonbackup'] } }] });
  const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/backup`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify({ encrypted, ...(encrypted ? { passphrase } : {}) }) });
  if (!response.ok) { const error = await response.json().catch(() => ({})); throw new Error(message(error.detail)); }
  const blob = await response.blob();
  const writable = await handle.createWritable(); await writable.write(blob); await writable.close();
}
