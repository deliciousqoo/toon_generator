import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowRight, LoaderCircle, Plus } from 'lucide-react';
import CharacterWorkspace from './CharacterWorkspace';
import EpisodeWorkspace from './EpisodeWorkspace';
import ChatGPTConnection from './ChatGPTConnection';
import { getCharacterState, hasAppliedCharacterMessage, hasAppliedCharacterTurn, submitCharacterTurn } from './characterApi';
import { canUseChatGPT, isChatGPTUsageLimit, safeConnectionUrl } from './chatgptApi';
import type { ChatGPTConnectionStatus } from './chatgptApi';
import { createCharacterProject, initializeStudio } from './studioApi';
import type { StudioProject } from './studioTypes';
import type { CharacterState } from './characterTypes';
import './studioEntry.css';

export default function StudioWorkspace() {
  const [projects, setProjects] = useState<StudioProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [initialDraft, setInitialDraft] = useState('');
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<ChatGPTConnectionStatus | null>(null);
  const [connectionOpen, setConnectionOpen] = useState(false);
  const [character, setCharacter] = useState<CharacterState | null>(null);
  const [workspace, setWorkspace] = useState<'character' | 'episode'>('character');
  const [characterBusy, setCharacterBusy] = useState(false);
  const [episodeBusy, setEpisodeBusy] = useState(false);
  const lock = useRef(false);
  const connectionReady = canUseChatGPT(connectionStatus);
  const usageUrl = safeConnectionUrl(connectionStatus?.manage_usage_url);
  const usageStopped = isChatGPTUsageLimit(connectionStatus);
  const workspaceBusy = characterBusy || episodeBusy;
  const controlsLocked = busy || loading || workspaceBusy;

  useEffect(() => { setCharacter(null); setWorkspace('character'); setCharacterBusy(false); setEpisodeBusy(false); }, [projectId]);

  useEffect(() => {
    let current = true;
    setLoading(true);
    void initializeStudio().then(items => {
      if (!current) return;
      setProjects(items);
      setProjectId(previous => items.some(item => item.id === previous) ? previous : items[0]?.id ?? '');
      setCreating(items.length === 0);
      setError('');
    }).catch(reason => {
      if (current) setError(reason instanceof Error ? reason.message : '프로젝트를 불러오지 못했습니다.');
    }).finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [reload]);

  async function start(event: FormEvent) {
    event.preventDefault();
    if (lock.current || !message.trim()) return;
    if (!connectionReady) { setConnectionOpen(true); return; }
    lock.current = true;
    setBusy(true);
    setError('');
    let created: StudioProject | null = null;
    try {
      created = await createCharacterProject(name);
      // Keep a successfully created project even when its first worker fails.
      setProjects(items => [created!, ...items]);
      const state = await getCharacterState(created.id);
      const result = await submitCharacterTurn(created.id, {
        request_id: crypto.randomUUID(), expected_revision: state.revision,
        message: message.trim(), synthetic_confirmed: true,
      });
      const applied = hasAppliedCharacterTurn(state, result);
      setInitialDraft(applied ? '' : message);
      if (applied) setMessage('');
      else setError(result.issues.find(issue => issue.severity === 'blocker')?.message || '첫 입력을 반영하지 못했습니다. 작성한 내용은 보관했습니다.');
      setName('');
      setProjectId(created.id);
      setCreating(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '캐릭터 대화를 시작하지 못했습니다.');
      if (created) {
        // An HTTP response can be lost after the turn was durably committed.
        const latest = await getCharacterState(created.id).catch(() => null);
        const saved = latest && hasAppliedCharacterMessage(latest, message);
        setInitialDraft(saved ? '' : message);
        setProjectId(created.id);
        setCreating(false);
      }
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  return <div className="character-app">
    <header className="character-app-header with-chatgpt">
      <span className="character-app-brand">Toon Studio</span>
      <div className="character-app-projects">
        {projects.length > 0 && <select aria-label="프로젝트 선택" value={projectId} disabled={controlsLocked}
          onChange={event => { setProjectId(event.target.value); setCreating(false); setInitialDraft(''); setError(''); }}>
          {projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}
        </select>}
        {projects.length > 0 && <button type="button" className="character-app-new" disabled={controlsLocked}
          onClick={() => { setCreating(true); setError(''); }}><Plus size={16} aria-hidden="true" />새 프로젝트</button>}
        <ChatGPTConnection open={connectionOpen} onOpenChange={setConnectionOpen} onStatusChange={setConnectionStatus} />
      </div>
    </header>
    <main className="character-app-main">
      {error && <div className="character-app-error" role="alert"><span>{error}</span>
        {connectionStatus?.blocked && usageUrl ? <a className="character-usage-link" href={usageUrl} target="_blank" rel="noopener noreferrer">사용량 관리</a> : null}
        {loading || projects.length === 0 ? <button type="button" disabled={busy} onClick={() => setReload(value => value + 1)}>다시 불러오기</button>
          : <button type="button" onClick={() => setError('')}>닫기</button>}</div>}
      {loading ? <p className="character-app-loading" role="status"><LoaderCircle size={18} aria-hidden="true" />불러오는 중</p> : null}
      {!loading && creating ? <section className="character-start" aria-labelledby="character-start-title">
          <div className="character-start-heading"><span className="character-app-mode">{connectionStatus?.fixture ? '합성 테스트' : connectionReady ? 'ChatGPT 구독 사용 중' : 'ChatGPT 연결 필요'}</span><h1 id="character-start-title">어떤 캐릭터를 만들까요?</h1></div>
          <form onSubmit={start}>
            <label className="character-start-name">프로젝트 이름 <span>선택</span><input value={name} maxLength={120} disabled={busy}
              onChange={event => setName(event.target.value)} placeholder="새 캐릭터" /></label>
            <label className="character-start-message">캐릭터 특징·성격<textarea value={message} maxLength={3000} rows={6} required disabled={busy}
              onChange={event => setMessage(event.target.value)} placeholder={connectionStatus?.fixture ? '가상 캐릭터의 외형이나 성격을 자유롭게 적어 주세요.' : '캐릭터의 외형이나 성격을 자유롭게 적어 주세요.'} /></label>
            {!connectionReady ? <div className="character-connection-required"><span>{usageStopped ? '사용 한도로 작업이 중단됐습니다.' : connectionStatus ? 'ChatGPT 연결 후 대화를 시작할 수 있습니다.' : 'ChatGPT 연결을 확인하고 있습니다.'}</span><button type="button" className="character-app-new" onClick={() => setConnectionOpen(true)}>{usageStopped ? '사용량·재개 설정' : 'ChatGPT 연결'}</button></div> : null}
            <div className="character-start-actions">
              {projectId ? <button type="button" className="character-app-new" disabled={busy} onClick={() => setCreating(false)}>취소</button> : <span />}
              <button type="submit" className="character-start-submit" disabled={busy || !message.trim() || !connectionReady}>
                {busy ? <LoaderCircle size={17} className="character-app-spin" aria-hidden="true" /> : null}{busy ? '대화 준비 중' : '대화 시작'}<ArrowRight size={17} aria-hidden="true" />
              </button>
            </div>
          </form>
        </section> : null}
      {!loading && projectId ? <div key={projectId} hidden={creating}>
          <nav className="character-flow-tabs" aria-label="프로젝트 작업"><button type="button" aria-pressed={workspace === 'character'} disabled={workspaceBusy} onClick={() => setWorkspace('character')}>캐릭터</button><button type="button" aria-pressed={workspace === 'episode'} disabled={workspaceBusy || (!character?.sheet_approved && workspace !== 'episode')} onClick={() => setWorkspace('episode')}>이야기·콘티<ArrowRight size={13} aria-hidden="true" /></button></nav>
          <div className="character-flow-panel" hidden={workspace !== 'character'}><CharacterWorkspace projectId={projectId} initialDraft={initialDraft} connectionStatus={connectionStatus}
            onConnectionNeeded={() => setConnectionOpen(true)} onStateChange={value => { setCharacter(value); window.dispatchEvent(new Event('chatgpt-status-changed')); }} onBusyChange={setCharacterBusy} /></div>
          <div className="character-flow-panel" hidden={workspace !== 'episode'}><EpisodeWorkspace projectId={projectId} character={character} active={workspace === 'episode'} connectionStatus={connectionStatus} onConnectionNeeded={() => setConnectionOpen(true)} onBusyChange={setEpisodeBusy} /></div>
        </div> : null}
    </main>
  </div>;
}
