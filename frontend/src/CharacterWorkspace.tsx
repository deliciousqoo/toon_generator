import { useEffect, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { ArrowRight, Check, CircleAlert, Image, LoaderCircle, Pencil, RotateCcw, Send, X } from 'lucide-react';
import { CharacterApiError, confirmCharacterDirection, getCharacter, reopenCharacterDirection, sendCharacterTurn } from './characterApi';
import type { CharacterBrief, CharacterFieldUpdates, CharacterState } from './characterTypes';
import './characterStyles.css';

interface CharacterWorkspaceProps {
  projectId: string;
  initialDraft?: string;
  onStateChange?: (state: CharacterState) => void;
}

interface BriefFields {
  appearance: string;
  personality: string;
  desired_feeling: string;
  voice: string;
  identity_invariants: string;
  avoid_elements: string;
}

type ChatField = 'appearance' | 'personality' | 'desired_feeling' | 'voice';

const FIELD_QUESTIONS: Record<ChatField, string> = {
  appearance: '외형이나 특징을 어떻게 정할까요?',
  personality: '어떤 성격과 행동을 가진 캐릭터인가요?',
  desired_feeling: '캐릭터에게서 어떤 느낌이 나면 좋을까요?',
  voice: '어떤 말투를 쓰는 캐릭터인가요?',
};

const FIELD_LABELS: Record<keyof BriefFields, string> = {
  appearance: '외형과 특징',
  personality: '성격과 행동',
  desired_feeling: '원하는 느낌',
  voice: '말투',
  identity_invariants: '계속 유지할 특징',
  avoid_elements: '피하고 싶은 요소',
};

function editableFields(brief: CharacterBrief): BriefFields {
  return {
    appearance: brief.appearance,
    personality: brief.personality,
    desired_feeling: brief.desired_feeling,
    voice: brief.voice,
    identity_invariants: brief.identity_invariants.join('\n'),
    avoid_elements: brief.avoid_elements.join('\n'),
  };
}

function errorMessage(reason: unknown): string {
  if (reason instanceof TypeError) return '서버에 연결하지 못했습니다. 연결을 확인한 뒤 다시 시도해 주세요.';
  return reason instanceof Error ? reason.message : '처리하지 못했습니다. 다시 시도해 주세요.';
}

function versionLabel(version: string): string {
  return `v${version}`;
}

export default function CharacterWorkspace({ projectId, initialDraft = '', onStateChange }: CharacterWorkspaceProps) {
  const [state, setState] = useState<CharacterState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState('');
  const [chatField, setChatField] = useState<ChatField | ''>('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editDraft, setEditDraft] = useState<BriefFields | null>(null);
  const [editBase, setEditBase] = useState<BriefFields | null>(null);
  const [editError, setEditError] = useState('');
  const connection = useRef<AbortController | null>(null);
  const mutationLock = useRef(false);
  const requestIdentity = useRef<{ signature: string; id: string } | null>(null);
  const chatLog = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const changeHandler = useRef(onStateChange);
  const startingDraft = useRef(initialDraft);
  const initialDraftRecovery = useRef({ text: initialDraft.trim(), active: Boolean(initialDraft.trim()) });
  changeHandler.current = onStateChange;

  useEffect(() => {
    const controller = new AbortController();
    connection.current = controller;
    setState(null);
    setLoading(true);
    setBusy(false);
    setDraft(startingDraft.current);
    initialDraftRecovery.current = { text: startingDraft.current.trim(), active: Boolean(startingDraft.current.trim()) };
    setChatField('');
    setError('');
    setNotice('');
    setEditDraft(null);
    setEditBase(null);
    setEditError('');
    mutationLock.current = false;
    requestIdentity.current = null;
    void getCharacter(projectId, controller.signal).then(value => {
      if (!controller.signal.aborted) setState(value);
    }).catch(reason => {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [projectId]);

  useEffect(() => {
    if (state?.project_id === projectId) changeHandler.current?.(state);
  }, [state, projectId]);

  useEffect(() => {
    const recovery = initialDraftRecovery.current;
    if (!recovery.active || state?.project_id !== projectId) return;
    if (!state.messages.some(message => message.role === 'user' && message.content === recovery.text)) return;
    // Only the untouched first-turn recovery input can be reconciled with a saved message.
    // A draft the user has edited must survive every subsequent load or conflict refresh.
    recovery.active = false;
    setDraft(current => current.trim() === recovery.text ? '' : current);
    setNotice('첫 메시지가 이미 반영된 것을 확인했습니다.');
  }, [state, projectId]);

  useEffect(() => {
    const log = chatLog.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [state?.messages.length]);

  function requestId(action: string, payload: unknown): string {
    const signature = JSON.stringify({ projectId, action, payload });
    if (requestIdentity.current?.signature !== signature) {
      requestIdentity.current = { signature, id: crypto.randomUUID() };
    }
    return requestIdentity.current.id;
  }

  async function reload() {
    const controller = connection.current;
    if (!controller || controller.signal.aborted || mutationLock.current) return;
    setLoading(true);
    setError('');
    try {
      const value = await getCharacter(projectId, controller.signal);
      if (!controller.signal.aborted) {
        setState(value);
        setNotice('현재 결과를 다시 불러왔습니다. 작성 중인 내용은 보관했습니다.');
      }
    } catch (reason) {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  async function mutate(work: (signal: AbortSignal) => Promise<CharacterState>): Promise<boolean> {
    const controller = connection.current;
    if (!controller || controller.signal.aborted || mutationLock.current) return false;
    mutationLock.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const value = await work(controller.signal);
      if (controller.signal.aborted) return false;
      setState(value);
      requestIdentity.current = null;
      return true;
    } catch (reason) {
      if (controller.signal.aborted) return false;
      if (reason instanceof CharacterApiError && reason.status === 409) {
        try {
          const latest = await getCharacter(projectId, controller.signal);
          if (!controller.signal.aborted) {
            setState(latest);
            setError('다른 곳에서 변경된 최신 결과를 불러왔습니다. 작성한 내용은 보관했습니다. 결과를 확인한 뒤 다시 보내 주세요.');
          }
        } catch {
          if (!controller.signal.aborted) setError('결과가 변경되어 요청을 적용하지 못했습니다. 작성한 내용은 보관했습니다. 다시 불러온 뒤 보내 주세요.');
        }
      } else setError(errorMessage(reason));
      return false;
    } finally {
      if (!controller.signal.aborted) {
        mutationLock.current = false;
        setBusy(false);
      }
    }
  }

  async function submitTurn(event?: FormEvent) {
    event?.preventDefault();
    if (!state || !draft.trim() || busy || loading || state.direction_confirmed || editDraft) return;
    const message = draft.trim();
    if (message.length > (chatField === 'voice' ? 2000 : 3000)) {
      setError(chatField === 'voice' ? '말투는 2,000자까지 작성해 주세요.' : '대화는 한 번에 3,000자까지 작성해 주세요.');
      return;
    }
    const payload = {
      expected_revision: state.revision, message, synthetic_confirmed: true as const,
      ...(chatField ? { field_updates: { [chatField]: message } } : {}),
    };
    const sent = await mutate(signal => sendCharacterTurn(projectId, {
      ...payload, request_id: requestId('turn', payload),
    }, signal));
    if (sent) {
      setDraft(current => current.trim() === message ? '' : current);
      setChatField('');
      composer.current?.focus();
    }
  }

  function handleComposerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void submitTurn();
    }
  }

  function startEditing() {
    if (!state?.brief) return;
    const values = editableFields(state.brief);
    setEditBase(values);
    setEditDraft(values);
    setEditError('');
  }

  async function saveEdits(event: FormEvent) {
    event.preventDefault();
    if (!state || !editDraft || !editBase || busy || loading) return;
    const updates: CharacterFieldUpdates = {};
    for (const field of Object.keys(editDraft) as (keyof BriefFields)[]) {
      if (editDraft[field] === editBase[field]) continue;
      if (field === 'identity_invariants' || field === 'avoid_elements') {
        const items = editDraft[field].split('\n').map(value => value.trim()).filter(Boolean);
        if (items.length > 20 || items.some(value => value.length > 1000)) {
          setEditError('목록은 20개까지, 각 항목은 1,000자까지 작성해 주세요.');
          return;
        }
        updates[field] = items;
      } else updates[field] = editDraft[field].trim();
    }
    if (Object.keys(updates).length === 0) {
      setEditDraft(null);
      setEditBase(null);
      return;
    }
    const payload = {
      expected_revision: state.revision,
      message: '캐릭터 방향 카드에서 수정한 내용을 반영해 주세요.',
      field_updates: updates,
      synthetic_confirmed: true as const,
    };
    const saved = await mutate(signal => sendCharacterTurn(projectId, {
      ...payload, request_id: requestId('edit', payload),
    }, signal));
    if (saved) {
      setEditDraft(null);
      setEditBase(null);
      setEditError('');
      setNotice('수정한 캐릭터 방향을 확인해 주세요.');
    }
  }

  async function decide(action: 'confirm' | 'reopen') {
    if (!state?.brief || busy || loading || (action === 'confirm' && (editDraft || draft.trim()))) return;
    const payload = { expected_revision: state.revision, expected_version: state.brief.version };
    const handler = action === 'confirm' ? confirmCharacterDirection : reopenCharacterDirection;
    const saved = await mutate(signal => handler(projectId, {
      ...payload, request_id: requestId(action, payload),
    }, signal));
    if (saved) setNotice(action === 'confirm' ? '캐릭터 방향을 확인했습니다.' : '캐릭터 방향을 다시 수정할 수 있습니다.');
  }

  const locked = loading || busy;
  const confirmed = state?.direction_confirmed ?? false;
  const currentStage = confirmed ? 1 : 0;

  return <section className="character-workspace" aria-labelledby="character-title" aria-busy={loading || busy}>
    <header className="character-heading">
      <h1 id="character-title">{confirmed ? '캐릭터 후보' : '캐릭터부터 정해 볼까요?'}</h1>
      {state?.fixture ? <span className="character-test-badge" title="정해진 규칙을 사용하는 합성 테스트입니다.">테스트 · AI 미연결</span> : null}
    </header>

    <nav aria-label="캐릭터 제작 단계">
      <ol className="character-steps">
        {['캐릭터 방향', '시각 후보', '캐릭터 시트'].map((label, index) => <li key={label}
          className={index === currentStage ? 'current' : index < currentStage ? 'done' : ''}
          aria-current={index === currentStage ? 'step' : undefined}>
          <span className="character-step-number" aria-hidden="true">{index < currentStage ? <Check size={14} /> : index + 1}</span>
          <span>{label}</span>
        </li>)}
      </ol>
    </nav>

    {error ? <div className="character-error" role="alert">
      <CircleAlert size={17} aria-hidden="true" /><p>{error}</p>
      <button className="character-button subtle" type="button" disabled={locked} onClick={() => void reload()}><RotateCcw size={14} aria-hidden="true" />다시 불러오기</button>
    </div> : null}
    <p className="character-announcement" role="status">{busy ? '입력한 내용을 반영하고 있습니다.' : loading && state ? '현재 결과를 다시 불러오는 중입니다.' : notice}</p>

    {loading && !state ? <div className="character-loading" role="status"><LoaderCircle className="character-spin" size={19} aria-hidden="true" />캐릭터 작업을 불러오는 중입니다.</div> : null}

    {state ? <div className="character-columns">
      <section className="character-conversation" aria-labelledby="character-chat-title">
        <div className="character-panel-heading"><h2 id="character-chat-title">대화</h2><span>Toon Studio</span></div>
        <div className="character-chat-log" ref={chatLog} role="log" aria-label="오케스트레이터와의 대화" aria-live="polite" aria-relevant="additions text">
          {state.messages.length === 0 ? <p className="character-chat-empty">떠오르는 특징이나 성격부터 편하게 이야기해 주세요.</p> : state.messages.map(message => <article className={`character-message ${message.role}`} key={message.id}>
            <span className="character-message-name">{message.role === 'user' ? '나' : 'Toon Studio'}</span>
            <p>{message.content}</p>
          </article>)}
        </div>

        {!confirmed ? <form className="character-composer" onSubmit={event => void submitTurn(event)}>
          <label htmlFor="character-reply" className="character-question">{chatField ? FIELD_QUESTIONS[chatField] : state.next_question || '어떤 부분을 바꾸고 싶으세요?'}</label>
          {state.fixture && state.brief ? <label className="character-chat-target" htmlFor="character-chat-field">반영할 항목
            <select id="character-chat-field" value={chatField} disabled={locked || Boolean(editDraft)} onChange={event => { initialDraftRecovery.current.active = false; setChatField(event.target.value as ChatField | ''); }}>
              <option value="">현재 질문</option>
              {(['appearance', 'personality', 'desired_feeling', 'voice'] as const).map(field => <option value={field} key={field}>{FIELD_LABELS[field]}</option>)}
            </select>
          </label> : null}
          <textarea id="character-reply" ref={composer} value={draft} maxLength={chatField === 'voice' ? 2000 : 3000} rows={3} disabled={locked || Boolean(editDraft)}
            placeholder={state.question_field === 'review' ? '바꾸고 싶은 특징을 이야기해 주세요.' : '예: 낯을 가리지만 친해지면 장난이 많은 가상의 캐릭터예요.'}
            onChange={event => { initialDraftRecovery.current.active = false; setDraft(event.target.value); }} onKeyDown={handleComposerKey} />
          <div className="character-composer-actions"><span>Ctrl / ⌘ + Enter로 보내기</span><button type="submit" className="character-button primary" disabled={locked || !draft.trim() || Boolean(editDraft)}>
            {busy ? <LoaderCircle size={15} className="character-spin" aria-hidden="true" /> : <Send size={15} aria-hidden="true" />}보내기
          </button></div>
        </form> : <div className="character-direction-confirmed"><Check size={16} aria-hidden="true" />캐릭터 방향 확인됨</div>}
      </section>

      <section className="character-result" aria-labelledby="character-result-title">
        <div className="character-panel-heading"><h2 id="character-result-title">현재 캐릭터 방향</h2>{state.brief ? <span>{versionLabel(state.brief.version)}</span> : null}</div>
        {state.brief ? <>
          <BriefSummary brief={state.brief} />
          {state.brief.reference_observations.length > 0 ? <div className="character-reference-list">{state.brief.reference_observations.map((reference, index) => <div key={`${reference.label}-${index}`}>
            <h3>{reference.label}</h3>
            {reference.desired_traits.length ? <p>참고할 느낌: {reference.desired_traits.join(' · ')}</p> : null}
            {reference.not_to_copy.length ? <p>가져오지 않을 요소: {reference.not_to_copy.join(' · ')}</p> : null}
          </div>)}</div> : null}

          {state.issues.length > 0 ? <ul className="character-issues">{state.issues.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.message}</li>)}</ul> : null}

          {editDraft && !confirmed ? <form className="character-edit-form" onSubmit={event => void saveEdits(event)}>
            <h3>캐릭터 방향 수정</h3>
            {(Object.keys(FIELD_LABELS) as (keyof BriefFields)[]).map(field => <label className="character-edit-field" key={field} htmlFor={`character-edit-${field}`}>
              {FIELD_LABELS[field]}{field === 'identity_invariants' || field === 'avoid_elements' ? <span>한 줄에 하나씩</span> : null}
              <textarea id={`character-edit-${field}`} rows={2} maxLength={field === 'identity_invariants' || field === 'avoid_elements' ? 20000 : field === 'voice' ? 2000 : 3000}
                value={editDraft[field]} disabled={locked} onChange={event => { setEditDraft(current => current ? { ...current, [field]: event.target.value } : current); setEditError(''); }} />
            </label>)}
            {editError ? <p className="character-edit-error" role="alert">{editError}</p> : null}
            <div className="character-result-actions"><button type="button" className="character-button" disabled={locked} onClick={() => { setEditDraft(null); setEditBase(null); setEditError(''); }}><X size={15} aria-hidden="true" />취소</button><button className="character-button primary" type="submit" disabled={locked}>수정 반영<Check size={15} aria-hidden="true" /></button></div>
          </form> : !confirmed ? <div className="character-result-actions">
            <button type="button" className="character-button" disabled={locked} onClick={startEditing}><Pencil size={14} aria-hidden="true" />직접 수정</button>
            <button type="button" className="character-button primary" disabled={locked || !state.can_confirm || Boolean(draft.trim())} onClick={() => void decide('confirm')}>방향 확인하고 다음으로<ArrowRight size={15} aria-hidden="true" /></button>
          </div> : null}
        </> : <div className="character-brief-empty"><span aria-hidden="true">✦</span><p>이야기한 내용이<br />캐릭터 방향으로 정리됩니다.</p></div>}

        {confirmed ? <div className="character-pending">
          <Image size={24} strokeWidth={1.4} aria-hidden="true" /><h3>시각 후보 연결 대기</h3><p>이미지 생성 연결 후 후보를 확인할 수 있습니다.</p>
          <button type="button" className="character-button" disabled={locked} onClick={() => void decide('reopen')}><Pencil size={14} aria-hidden="true" />캐릭터 방향 수정</button>
        </div> : null}

        {state.versions.length > 1 ? <details className="character-history"><summary>방향 수정 기록 ({state.versions.length})</summary><ol>{[...state.versions].reverse().map(brief => <li key={brief.version}><strong>{versionLabel(brief.version)}{brief.version === state.brief?.version ? ' · 현재' : ''}</strong><BriefSummary brief={brief} compact /></li>)}</ol></details> : null}
      </section>
    </div> : null}
  </section>;
}

function BriefSummary({ brief, compact = false }: { brief: CharacterBrief; compact?: boolean }) {
  return <dl className={`character-brief${compact ? ' compact' : ''}`}>
    {(['appearance', 'personality', 'desired_feeling', 'voice'] as const).filter(field => !compact || brief[field]).map(field => <div key={field}><dt>{FIELD_LABELS[field]}</dt><dd className={brief[field] ? '' : 'undecided'}>{brief[field] || '아직 정하지 않음'}</dd></div>)}
    {brief.identity_invariants.length ? <div><dt>{FIELD_LABELS.identity_invariants}</dt><dd><ul>{brief.identity_invariants.map((value, index) => <li key={index}>{value}</li>)}</ul></dd></div> : null}
    {brief.avoid_elements.length ? <div><dt>{FIELD_LABELS.avoid_elements}</dt><dd><ul>{brief.avoid_elements.map((value, index) => <li key={index}>{value}</li>)}</ul></dd></div> : null}
  </dl>;
}
