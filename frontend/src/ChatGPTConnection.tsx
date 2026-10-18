import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown, ExternalLink, LoaderCircle, LogOut, RotateCcw, X } from 'lucide-react';
import { disconnectChatGPT, getChatGPTModels, getChatGPTStatus, isChatGPTUsageLimit, loginWithChatGPT, needsChatGPTReconnect, resumeChatGPT, safeConnectionUrl, selectChatGPTModel } from './chatgptApi';
import type { ChatGPTConnectionStatus } from './chatgptApi';
import './chatgptConnection.css';

interface ChatGPTConnectionProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onStatusChange: (status: ChatGPTConnectionStatus) => void;
}

const WELCOME_KEY = 'toon-studio:chatgpt-usage-notice:v1';

function initialNoticeAccepted(): boolean {
  try { return localStorage.getItem(WELCOME_KEY) === 'accepted'; } catch { return false; }
}

function failureMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : 'ChatGPT 연결 상태를 확인하지 못했습니다.';
}

export default function ChatGPTConnection({ open, onOpenChange, onStatusChange }: ChatGPTConnectionProps) {
  const [status, setStatus] = useState<ChatGPTConnectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [authorizationUrl, setAuthorizationUrl] = useState('');
  const [noticeAccepted, setNoticeAccepted] = useState(initialNoticeAccepted);
  const [showNotice, setShowNotice] = useState(false);
  const [loginExpired, setLoginExpired] = useState(false);
  const callbacks = useRef({ onOpenChange, onStatusChange });
  const statusRef = useRef(status);
  const loadController = useRef<AbortController | null>(null);
  const actionController = useRef<AbortController | null>(null);
  const loginDeadline = useRef<number | null>(null);
  const lock = useRef(false);
  const panel = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  callbacks.current = { onOpenChange, onStatusChange };
  statusRef.current = status;

  const refresh = useCallback(async (): Promise<ChatGPTConnectionStatus | null> => {
    loadController.current?.abort();
    const controller = new AbortController();
    loadController.current = controller;
    try {
      const value = await getChatGPTStatus(controller.signal);
      if (controller.signal.aborted) return null;
      const previous = statusRef.current;
      statusRef.current = value;
      setStatus(value);
      callbacks.current.onStatusChange(value);
      if (value.blocked && !previous?.blocked) callbacks.current.onOpenChange(true);
      if (value.connected && value.sharing && !value.login_pending) {
        setAuthorizationUrl('');
        setLoginExpired(false);
        loginDeadline.current = null;
      }
      setError('');
      return value;
    } catch (reason) {
      if (!controller.signal.aborted) setError(failureMessage(reason));
      return null;
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const update = () => { void refresh(); };
    update();
    window.addEventListener('chatgpt-status-changed', update);
    return () => {
      window.removeEventListener('chatgpt-status-changed', update);
      loadController.current?.abort();
      actionController.current?.abort();
    };
  }, [refresh]);

  useEffect(() => {
    if (!status?.login_pending || loginExpired) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    loginDeadline.current ??= Date.now() + 10 * 60 * 1000;
    const poll = async () => {
      if (!active) return;
      if (Date.now() >= (loginDeadline.current ?? 0)) {
        setLoginExpired(true);
        setAuthorizationUrl('');
        return;
      }
      const value = await refresh();
      if (active && (value?.login_pending || (!value && statusRef.current?.login_pending))) timer = setTimeout(() => void poll(), 2000);
    };
    timer = setTimeout(() => void poll(), 2000);
    return () => { active = false; clearTimeout(timer); };
  }, [status?.login_pending, loginExpired, refresh]);

  useEffect(() => {
    if (!open) return;
    const keydown = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') {
        callbacks.current.onOpenChange(false);
        toggle.current?.focus();
      }
    };
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !panel.current?.contains(event.target)) callbacks.current.onOpenChange(false);
    };
    window.addEventListener('keydown', keydown);
    window.addEventListener('pointerdown', outside);
    return () => {
      window.removeEventListener('keydown', keydown);
      window.removeEventListener('pointerdown', outside);
    };
  }, [open]);

  async function act(work: (signal: AbortSignal) => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    const controller = new AbortController();
    actionController.current = controller;
    setBusy(true);
    setError('');
    setNotice('');
    try { await work(controller.signal); }
    catch (reason) { if (!controller.signal.aborted) setError(failureMessage(reason)); }
    finally {
      if (!controller.signal.aborted) setBusy(false);
      lock.current = false;
    }
  }

  async function login(accepted = false) {
    if (!noticeAccepted && !accepted) { setShowNotice(true); return; }
    if (accepted) {
      setNoticeAccepted(true);
      setShowNotice(false);
      try { localStorage.setItem(WELCOME_KEY, 'accepted'); } catch { /* The acknowledgement is still valid for this session. */ }
    }
    await act(async signal => {
      const result = await loginWithChatGPT(signal);
      if (signal.aborted) return;
      const url = safeConnectionUrl(result.authorization_url);
      if (!url) throw new Error('로그인 주소를 확인하지 못했습니다. 다시 연결해 주세요.');
      setAuthorizationUrl(url);
      loginDeadline.current = Date.now() + Math.max(1, result.expires_in) * 1000;
      setLoginExpired(false);
      window.open(url, '_blank', 'noopener,noreferrer');
      await refresh();
    });
  }

  async function changeModel(model: string) {
    await act(async signal => {
      await selectChatGPTModel(model, signal);
      if (!signal.aborted) await refresh();
    });
  }

  async function reloadModels() {
    await act(async signal => {
      await getChatGPTModels(signal);
      if (!signal.aborted) await refresh();
    });
  }

  async function disconnect() {
    await act(async signal => {
      await disconnectChatGPT(signal);
      if (signal.aborted) return;
      setAuthorizationUrl('');
      loginDeadline.current = null;
      setLoginExpired(false);
      await refresh();
    });
  }

  async function resume() {
    await act(async signal => {
      await resumeChatGPT(signal);
      if (signal.aborted) return;
      const value = await refresh();
      if (value && !value.blocked) setNotice('작업을 다시 시작할 수 있습니다. 작성한 메시지를 직접 보내 주세요.');
    });
  }

  const connected = status?.connected && status.sharing;
  const usageUrl = safeConnectionUrl(status?.manage_usage_url);
  const pending = Boolean(status?.login_pending && !loginExpired);
  const usageStopped = isChatGPTUsageLimit(status);
  const reconnectRequired = needsChatGPTReconnect(status);
  const statusLabel = status?.fixture ? '합성 테스트' : status?.blocked ? '작업 중단' : connected ? '연결됨' : '연결 필요';

  return <div className="chatgpt-connection" ref={panel}>
    <button type="button" ref={toggle} className="chatgpt-toggle" aria-expanded={open} aria-controls="chatgpt-connection-panel" onClick={() => onOpenChange(!open)}>
      <span className={`chatgpt-dot${status?.blocked ? ' blocked' : connected ? ' connected' : ''}`} aria-hidden="true" />ChatGPT 연결<ChevronDown size={13} aria-hidden="true" />
      <span className="chatgpt-sr-only">{statusLabel}</span>
    </button>
    {open ? <section id="chatgpt-connection-panel" className="chatgpt-panel" aria-labelledby="chatgpt-panel-title" aria-busy={busy || loading}>
      <header><h2 id="chatgpt-panel-title">ChatGPT 연결</h2><button type="button" className="chatgpt-icon-button" aria-label="연결 설정 닫기" onClick={() => onOpenChange(false)}><X size={16} aria-hidden="true" /></button></header>
      {loading ? <p className="chatgpt-status" role="status"><LoaderCircle size={15} className="chatgpt-spin" aria-hidden="true" />연결 확인 중</p> : null}
      {error ? <div className="chatgpt-error" role="alert"><p>{error}</p><button type="button" className="chatgpt-link-button" disabled={busy} onClick={() => void refresh()}><RotateCcw size={13} aria-hidden="true" />다시 확인</button></div> : null}
      {notice ? <p className="chatgpt-notice" role="status">{notice}</p> : null}
      {status?.fixture ? <p className="chatgpt-status">합성 테스트 실행 중</p> : status ? <>
        <p className="chatgpt-status">{pending ? '로그인 완료를 기다리고 있습니다.' : connected ? 'ChatGPT 구독 사용 중' : status.connected ? '구독 사용 권한 확인 필요' : 'ChatGPT가 연결되지 않았습니다.'}</p>
        {connected && status.account_label ? <p className="chatgpt-account">{status.account_label}</p> : null}
        {showNotice ? <div className="chatgpt-welcome"><p>연결하면 이 앱의 AI 작업에 ChatGPT 구독 사용량이 사용됩니다.</p><div className="chatgpt-action-row"><button type="button" className="chatgpt-link-button" onClick={() => setShowNotice(false)}>취소</button><button type="button" className="chatgpt-button primary" disabled={busy} onClick={() => void login(true)}>Continue with ChatGPT</button></div></div> : null}
        {status.blocked ? <div className="chatgpt-limit" role="alert"><strong>{usageStopped ? '사용 한도로 작업을 중단했습니다.' : 'ChatGPT 작업을 중단했습니다.'}</strong><p>{reconnectRequired ? '계정과 구독 사용 권한을 확인하려면 다시 연결해 주세요.' : usageStopped ? '사용량을 확인한 뒤 직접 재개해 주세요.' : '연결 상태를 확인한 뒤 다시 시작해 주세요.'}</p>
          <div className="chatgpt-action-row">{usageUrl ? <a href={usageUrl} target="_blank" rel="noopener noreferrer">사용량 관리<ExternalLink size={12} aria-hidden="true" /></a> : null}<button type="button" className="chatgpt-button" disabled={busy || pending || showNotice} onClick={() => void (reconnectRequired ? login() : resume())}>{reconnectRequired ? '다시 연결' : usageStopped ? '한도 확인 후 재개' : '상태 확인 후 재개'}</button></div>
        </div> : null}
        {authorizationUrl && pending ? <a className="chatgpt-login-fallback" href={authorizationUrl} target="_blank" rel="noopener noreferrer">로그인 창 열기<ExternalLink size={12} aria-hidden="true" /></a> : null}
        {connected ? <>
          <label className="chatgpt-model-label" htmlFor="chatgpt-model">사용 모델<select id="chatgpt-model" value={status.model ?? ''} disabled={busy || pending || status.models.length === 0} onChange={event => void changeModel(event.target.value)}>
            {!status.model ? <option value="" disabled>모델 선택</option> : null}
            {status.model && !status.models.some(model => model.slug === status.model) ? <option value={status.model} disabled>현재 모델 확인 필요</option> : null}
            {status.models.map(model => <option value={model.slug} key={model.slug}>{model.display_name}</option>)}
          </select></label>
          {status.models.length === 0 ? <button type="button" className="chatgpt-link-button chatgpt-model-retry" disabled={busy} onClick={() => void reloadModels()}><RotateCcw size={13} aria-hidden="true" />모델 목록 다시 불러오기</button> : null}
          <div className="chatgpt-footer-actions">{usageUrl ? <a href={usageUrl} target="_blank" rel="noopener noreferrer">사용량 관리<ExternalLink size={12} aria-hidden="true" /></a> : null}<button type="button" className="chatgpt-link-button" disabled={busy} onClick={() => void disconnect()}><LogOut size={13} aria-hidden="true" />연결 해제</button></div>
        </> : <>
          {loginExpired ? <p className="chatgpt-notice" role="status">로그인 대기 시간이 지났습니다. 다시 연결해 주세요.</p> : null}
          <p className="chatgpt-credit-setting">ChatGPT 사용량 설정에서 한도 후 추가 크레딧 사용을 꺼주세요.{usageUrl ? <> <a href={usageUrl} target="_blank" rel="noopener noreferrer">사용량 관리<ExternalLink size={12} aria-hidden="true" /></a></> : null}</p>
          {!showNotice && !reconnectRequired ? <button type="button" className="chatgpt-button primary chatgpt-login" disabled={busy || pending} onClick={() => void login()}>{busy ? <LoaderCircle size={15} className="chatgpt-spin" aria-hidden="true" /> : null}Continue with ChatGPT</button> : null}
          {status.connected ? <button type="button" className="chatgpt-link-button chatgpt-disconnect" disabled={busy} onClick={() => void disconnect()}>연결 해제</button> : null}
        </>}
      </> : null}
    </section> : null}
  </div>;
}
