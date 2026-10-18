import { useEffect, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { ArrowRight, Check, CircleAlert, Copy, Download, ImagePlus, LoaderCircle, Pencil, Plus, RotateCcw, Send, Upload, X } from 'lucide-react';
import type { CharacterState } from './characterTypes';
import type { VisualProvenance } from './characterVisualTypes';
import type { ChatGPTConnectionStatus } from './chatgptApi';
import { canUseChatGPT, isChatGPTUsageLimit, safeConnectionUrl } from './chatgptApi';
import { visualAssetUrl } from './characterVisualApi';
import { cancelEpisodeRough, createEpisode, decideEpisode, downloadEpisode, EpisodeApiError, getEpisode, listEpisodes, requestEpisodeRough, roughAssetUrl, saveEpisodeFormat, sendEpisodeTurn, uploadEpisodeRough } from './episodeApi';
import type { EpisodeBoard, EpisodeCharacterSnapshot, EpisodeDecision, EpisodeFormat, EpisodePanel, EpisodeRoughJob, EpisodeState, EpisodeStory, EpisodeTurnStage } from './episodeTypes';
import './episodeStyles.css';

interface Props {
  projectId: string; character: CharacterState | null; active: boolean;
  connectionStatus?: ChatGPTConnectionStatus | null; onConnectionNeeded?: () => void; onBusyChange?: (busy: boolean) => void;
}

const STAGES = ['intent', 'story', 'format', 'storyboard'] as const;
const STAGE_LABELS = ['소재 정리', '이야기', '컷 구성', '콘티'];
const STORY_FIELDS = [{ id: '', label: '전체 내용' }, { id: 'action', label: '행동' }, { id: 'emotion', label: '감정' }, { id: 'dialogue', label: '대사만' }];
const BOARD_FIELDS = [{ id: '', label: '전체 내용' }, { id: 'scene', label: '장면' }, { id: 'action', label: '행동' }, { id: 'expression', label: '표정' }, { id: 'dialogue', label: '대사만' }, { id: 'camera', label: '카메라' }, { id: 'composition', label: '구도' }, { id: 'background', label: '배경' }, { id: 'continuity', label: '연속성' }, { id: 'text_placement', label: '대사 위치' }];
const INTENT_LABELS = { topic: '이야기 소재', intended_emotion: '전하고 싶은 감정', ending: '마무리', constraints: '유지할 내용' };
const PANEL_INSTRUCTION_LABELS = { scene: '장면', action: '행동', expression: '표정', camera: '카메라', composition: '구도', background: '배경', continuity: '연속성', text_placement: '대사 위치' };

function errorText(reason: unknown): string {
  if (reason instanceof TypeError) return '서버에 연결하지 못했습니다. 작성한 내용은 보관했습니다. 연결을 확인한 뒤 다시 불러와 주세요.';
  return reason instanceof Error ? reason.message : '작업을 반영하지 못했습니다. 작성한 내용은 보관했습니다.';
}
function turnApplied(before: EpisodeState, after: EpisodeState, stage: EpisodeTurnStage, requestId?: string): boolean {
  if (before.project_id !== after.project_id || before.id !== after.id) return false;
  if (requestId && !after.messages.some(message => message.id === `${requestId}-assistant` && message.version)) return false;
  if (stage === 'story') return Boolean(after.story && after.story.version !== before.story?.version);
  if (stage === 'storyboard') return Boolean(after.storyboard && after.storyboard.version !== before.storyboard?.version);
  return after.messages.length > before.messages.length && after.messages.some(message => message.role === 'assistant' && Boolean(message.version) && !before.messages.some(old => old.id === message.id));
}

export default function EpisodeWorkspace({ projectId, character, active, connectionStatus, onConnectionNeeded, onBusyChange }: Props) {
  const [episodes, setEpisodes] = useState<EpisodeState[]>([]);
  const [state, setState] = useState<EpisodeState | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [newStory, setNewStory] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [targetIds, setTargetIds] = useState<string[]>([]);
  const [editField, setEditField] = useState('');
  const [roughTarget, setRoughTarget] = useState('');
  const [roughDrafts, setRoughDrafts] = useState<Record<string, string>>({});
  const [formatDirty, setFormatDirty] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const requestIdentity = useRef<{ signature: string; id: string } | null>(null);
  const latest = useRef(state);
  const loaded = useRef(false);
  const handlers = useRef({ onBusyChange, active });
  const log = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const result = useRef<HTMLDivElement>(null);
  latest.current = state;
  handlers.current = { onBusyChange, active };

  const stage = state?.current_stage ?? 'intent';
  const turnStage: EpisodeTurnStage = stage === 'storyboard' || stage === 'complete' ? 'storyboard' : stage === 'intent' ? 'intent' : 'story';
  const draftKey = newStory || !state ? 'new' : `${state.id}:${turnStage}:${targetIds.join(',')}:${editField}`;
  const draft = drafts[draftKey] ?? '';
  const connectionReady = canUseChatGPT(connectionStatus);
  const usageStopped = isChatGPTUsageLimit(connectionStatus);
  const usageUrl = safeConnectionUrl(connectionStatus?.manage_usage_url);
  const currentCharacter = Boolean(character?.sheet_approved && character.visuals.approved_sheet_version && character.brief);
  const snapshotMatches = !state || Boolean(currentCharacter && character?.brief?.version === state.character_snapshot.direction.version && character?.visuals.approved_sheet_version === state.character_snapshot.sheet.version);
  const mutationBlocked = state?.mutation_blocked || (!snapshotMatches ? '캐릭터 시트가 변경됐습니다. 확인한 시트로 새 이야기를 시작해 주세요. 이전 결과는 보관됩니다.' : '');
  const locked = busy || loading;
  const canMutate = !locked && !mutationBlocked;
  const pendingJobs = state?.rough_jobs.filter(job => job.status === 'awaiting_image') ?? [];
  const boardApproved = Boolean(state?.storyboard && state.approved_board_version === state.storyboard.version && state.usable_storyboard);

  useEffect(() => {
    const connection = new AbortController();
    controller.current = connection;
    return () => { connection.abort(); handlers.current.onBusyChange?.(false); };
  }, [projectId]);

  useEffect(() => {
    if (!active || lock.current) return;
    const connection = controller.current;
    if (!connection || connection.signal.aborted) return;
    setLoading(true);
    const request = loaded.current && latest.current
      ? getEpisode(projectId, latest.current.id, connection.signal).then(value => [value])
      : listEpisodes(projectId, connection.signal);
    void request.then(values => {
      if (connection.signal.aborted) return;
      if (!loaded.current) { setEpisodes(values); setState(values[0] ?? null); }
      else if (values[0]) putState(values[0]);
      loaded.current = true;
      setError('');
    }).catch(reason => { if (!connection.signal.aborted) setError(errorText(reason)); })
      .finally(() => { if (!connection.signal.aborted) setLoading(false); });
  }, [active, projectId]);

  useEffect(() => { if (log.current) log.current.scrollTop = log.current.scrollHeight; }, [state?.messages.length]);
  useEffect(() => { handlers.current.onBusyChange?.(busy || loading); }, [busy, loading]);

  function putState(value: EpisodeState) {
    latest.current = value;
    setState(value);
    setEpisodes(items => items.some(item => item.id === value.id) ? items.map(item => item.id === value.id ? value : item) : [value, ...items]);
  }
  function requestId(action: string, body: unknown): string {
    const signature = JSON.stringify({ projectId, episodeId: latest.current?.id, action, body });
    if (requestIdentity.current?.signature !== signature) requestIdentity.current = { signature, id: crypto.randomUUID() };
    return requestIdentity.current.id;
  }
  function setDraft(text: string) { setDrafts(values => ({ ...values, [draftKey]: text })); }

  function revealNewResult(before: EpisodeState | null, after: EpisodeState) {
    if (after.current_stage === 'intent' || !window.matchMedia('(max-width: 900px)').matches) return;
    const changed = before?.id !== after.id || before.current_stage !== after.current_stage ||
      before.story?.version !== after.story?.version || before.format?.version !== after.format?.version ||
      before.storyboard?.version !== after.storyboard?.version;
    if (!changed) return;
    window.requestAnimationFrame(() => {
      if (handlers.current.active && latest.current?.id === after.id) result.current?.scrollIntoView({ block: 'start', behavior: 'auto' });
    });
  }

  async function reload() {
    if (lock.current) return;
    const connection = controller.current;
    if (!connection || connection.signal.aborted) return;
    setLoading(true);
    setError('');
    try {
      if (state) putState(await getEpisode(projectId, state.id, connection.signal));
      else { const values = await listEpisodes(projectId, connection.signal); if (!connection.signal.aborted) { setEpisodes(values); setState(values[0] ?? null); loaded.current = true; } }
      if (!connection.signal.aborted) setNotice('현재 결과를 다시 불러왔습니다. 작성 중인 내용은 보관했습니다.');
    } catch (reason) { if (!connection.signal.aborted) setError(errorText(reason)); }
    finally { if (!connection.signal.aborted) setLoading(false); }
  }

  async function mutate(work: (signal: AbortSignal) => Promise<EpisodeState>, turn?: { before: EpisodeState; stage: EpisodeTurnStage; requestId: string }): Promise<boolean> {
    const connection = controller.current;
    if (lock.current || !connection || connection.signal.aborted) return false;
    lock.current = true;
    setBusy(true);
    handlers.current.onBusyChange?.(true);
    setError(''); setNotice('');
    const before = latest.current;
    try {
      const value = await work(connection.signal);
      if (connection.signal.aborted) return false;
      putState(value);
      requestIdentity.current = null;
      if (turn && !turnApplied(turn.before, value, turn.stage, turn.requestId)) {
        setError(value.issues.find(issue => issue.severity === 'blocker')?.message || '이번 입력을 반영하지 못했습니다. 작성한 내용은 보관했습니다.');
        return false;
      }
      revealNewResult(before, value);
      return true;
    } catch (reason) {
      if (connection.signal.aborted) return false;
      if (turn) {
        const saved = await getEpisode(projectId, turn.before.id, connection.signal).catch(() => null);
        if (saved && !connection.signal.aborted && turnApplied(turn.before, saved, turn.stage, turn.requestId)) {
          putState(saved); requestIdentity.current = null;
          revealNewResult(turn.before, saved);
          setNotice('입력이 이미 반영된 것을 확인했습니다. 저장된 결과를 불러왔습니다.');
          return true;
        }
      }
      if (reason instanceof EpisodeApiError && reason.status === 409 && latest.current) {
        const refreshed = await getEpisode(projectId, latest.current.id, connection.signal).catch(() => null);
        if (refreshed && !connection.signal.aborted) putState(refreshed);
        if (!connection.signal.aborted) setError('최신 결과를 다시 불러왔습니다. 작성한 내용과 선택한 파일은 보관했습니다. 결과를 확인한 뒤 다시 요청해 주세요. ' + reason.message);
      } else setError(errorText(reason));
      return false;
    } finally {
      if (!connection.signal.aborted) { lock.current = false; setBusy(false); handlers.current.onBusyChange?.(false); }
    }
  }

  async function start(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim() || !currentCharacter || !character?.brief || !character.visuals.approved_sheet_version || locked) return;
    if (!connectionReady) { onConnectionNeeded?.(); return; }
    const message = draft.trim(); const sentKey = draftKey;
    const input = { expected_direction_version: character.brief.version, expected_sheet_version: character.visuals.approved_sheet_version };
    await mutate(async signal => {
      const created = await createEpisode(projectId, { ...input, request_id: requestId('create', input) }, signal);
      if (signal.aborted) return created;
      putState(created); setNewStory(false); setTargetIds([]); setEditField(''); setRoughTarget('');
      // A created episode survives a failed first role; its unsent message becomes the current draft.
      const key = `${created.id}:intent::`;
      setDrafts(values => ({ ...values, [key]: message }));
      requestIdentity.current = null;
      const body = { expected_revision: created.revision, stage: 'intent' as const, message, target_ids: [], edit_fields: [] };
      const id = requestId('turn', body);
      let result: EpisodeState;
      try { result = await sendEpisodeTurn(projectId, created.id, { ...body, request_id: id }, signal); }
      catch (reason) {
        const saved = await getEpisode(projectId, created.id, signal).catch(() => null);
        if (!saved || !turnApplied(created, saved, 'intent', id)) throw reason;
        result = saved;
      }
      if (turnApplied(created, result, 'intent', id)) {
        setDrafts(values => ({ ...values, [sentKey]: '', [key]: '' }));
      } else setError(result.issues.find(issue => issue.severity === 'blocker')?.message || '첫 입력을 반영하지 못했습니다. 작성한 내용은 보관했습니다.');
      return result;
    });
  }

  async function sendTurn(event?: FormEvent, requestedStage?: EpisodeTurnStage) {
    event?.preventDefault();
    if (!state || !canMutate || !connectionReady || stage === 'format' || stage === 'complete') return;
    const chosenStage = requestedStage ?? turnStage;
    const text = draft.trim() || (chosenStage === 'story' ? '지금까지 정리한 소재와 의도로 이야기 초안을 만들어 주세요.' : chosenStage === 'storyboard' ? '확인한 이야기와 컷 구성에 맞춰 컷별 장면 구성을 만들어 주세요.' : '');
    if (!text) return;
    const availableFields = (chosenStage === 'story' ? STORY_FIELDS : BOARD_FIELDS).map(field => field.id).filter(Boolean);
    const availableIds = chosenStage === 'story' ? state.story?.beats.map(beat => beat.id) ?? [] : state.storyboard?.panels.map(panel => panel.id) ?? [];
    const selectedIds = requestedStage ? [] : targetIds.length ? targetIds : editField ? availableIds : [];
    const selectedFields = requestedStage ? [] : editField ? [editField] : targetIds.length ? availableFields : [];
    const body = {
      expected_revision: state.revision, stage: chosenStage, message: text,
      ...(chosenStage === 'story' && state.story ? { expected_version: state.story.version } : {}),
      ...(chosenStage === 'storyboard' && state.storyboard ? { expected_version: state.storyboard.version } : {}),
      target_ids: selectedIds, edit_fields: selectedFields,
    };
    const sentKey = draftKey;
    const id = requestId('turn', body);
    if (await mutate(signal => sendEpisodeTurn(projectId, state.id, { ...body, request_id: id }, signal), { before: state, stage: chosenStage, requestId: id })) {
      setDrafts(values => ({ ...values, [sentKey]: '' })); setTargetIds([]); setEditField('');
    }
  }

  async function decision(action: EpisodeDecision) {
    if (!state || !canMutate) return;
    const version = action.endsWith('story') ? state.story?.version : action.endsWith('format') ? state.format?.version : state.storyboard?.version;
    if (!version) return;
    const body = { expected_revision: state.revision, action, expected_version: version };
    if (await mutate(signal => decideEpisode(projectId, state.id, { ...body, request_id: requestId('decision', body) }, signal))) {
      setTargetIds([]); setEditField(''); setRoughTarget(''); setFormatDirty(false);
      setNotice(action.startsWith('confirm') ? '이 버전을 확인했습니다.' : '수정할 수 있도록 열었습니다. 이전 버전은 보관됩니다.');
    }
  }

  async function updateFormat(cutCount: number, layout: EpisodeFormat['layout']): Promise<boolean> {
    if (!state?.format || !canMutate) return false;
    const body = { expected_revision: state.revision, expected_version: state.format.version, cut_count: cutCount, layout };
    return mutate(signal => saveEpisodeFormat(projectId, state.id, { ...body, request_id: requestId('format', body) }, signal));
  }

  async function prepareRough(event: FormEvent) {
    event.preventDefault();
    if (!state?.storyboard || !roughTarget || !canMutate) return;
    const roughKey = `${state.id}:${roughTarget}`;
    const body = { expected_revision: state.revision, expected_board_version: state.storyboard.version, panel_id: roughTarget, instruction: roughDrafts[roughKey]?.trim() || '' };
    if (await mutate(signal => requestEpisodeRough(projectId, state.id, { ...body, request_id: requestId('rough', body) }, signal))) {
      setRoughDrafts(values => ({ ...values, [roughKey]: '' })); setRoughTarget('');
    }
  }

  async function uploadRough(job: EpisodeRoughJob, file: File, provenance: VisualProvenance, identity: string): Promise<boolean> {
    if (!state?.storyboard || !canMutate) return false;
    const body = { expected_revision: state.revision, expected_board_version: state.storyboard.version };
    return mutate(signal => uploadEpisodeRough(projectId, state.id, job.id, { ...body, request_id: requestId('upload', { ...body, job: job.id, identity, provenance }) }, file, provenance, signal));
  }
  async function cancelRough(job: EpisodeRoughJob) {
    if (!state || !canMutate) return;
    const body = { expected_revision: state.revision };
    await mutate(signal => cancelEpisodeRough(projectId, state.id, job.id, { ...body, request_id: requestId('cancel', { ...body, job: job.id }) }, signal));
  }
  async function exportBoard() {
    const connection = controller.current;
    if (!state || lock.current || !connection || connection.signal.aborted) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const blob = await downloadEpisode(projectId, state.id, connection.signal);
      if (connection.signal.aborted) return;
      const url = URL.createObjectURL(blob); const link = document.createElement('a');
      link.href = url; link.download = `storyboard-${state.storyboard?.version ?? state.id}.zip`; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) { if (!connection.signal.aborted) setError(errorText(reason)); }
    finally { if (!connection.signal.aborted) { lock.current = false; setBusy(false); } }
  }

  function target(id: string, field = '') { setTargetIds([id]); setEditField(field); window.setTimeout(() => composer.current?.focus(), 0); }
  function composerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && !event.nativeEvent.isComposing) { event.preventDefault(); void sendTurn(); }
  }

  const currentSheet = character?.visuals.sheets.find(sheet => sheet.version === character.visuals.approved_sheet_version);
  const currentSnapshot = currentSheet && character?.brief ? { project_id: projectId, direction: character.brief, sheet: currentSheet, assets: character.visuals.assets } : null;
  const snapshot = newStory || !state ? currentSnapshot : state.character_snapshot;
  const selectedLabels = targetIds.map(id => turnStage === 'story' ? `전개 ${state?.story?.beats.find(beat => beat.id === id)?.order ?? id}` : `${state?.storyboard?.panels.find(panel => panel.id === id)?.order ?? id}컷`);
  const stageIndex = stage === 'complete' ? STAGES.length : STAGES.indexOf(stage);
  const blockerIssues = state?.issues.filter(issue => issue.severity === 'blocker') ?? [];
  const allRoughs = Boolean(state?.storyboard?.panels.length && state.storyboard.panels.every(panel => state.rough_assets.some(asset => asset.id === state.roughs[panel.id])));
  const showNew = !state || newStory;

  return <section className="episode-workspace character-workspace" aria-label="이야기와 콘티 작업" aria-busy={busy || loading}>
    <div className="episode-heading"><h1>이야기·콘티</h1><div className="episode-heading-actions">
      {episodes.length ? <select className="episode-select" aria-label="이야기 선택" value={state?.id ?? ''} disabled={locked} onChange={event => { const selected = episodes.find(item => item.id === event.target.value); if (selected) { putState(selected); setNewStory(false); setTargetIds([]); setEditField(''); setRoughTarget(''); setError(''); } }}>
        {episodes.map(item => <option key={item.id} value={item.id}>{item.story?.title || item.title}</option>)}
      </select> : null}
      {state ? <button className="character-button subtle" type="button" disabled={locked || !currentCharacter} onClick={() => { setNewStory(value => !value); setTargetIds([]); setEditField(''); setError(''); }}><Plus size={14} aria-hidden="true" />{newStory ? '현재 이야기' : '새 이야기'}</button> : null}
      <button className="character-button subtle" type="button" disabled={locked} onClick={() => void reload()} aria-label="이야기와 콘티 다시 불러오기"><RotateCcw size={14} aria-hidden="true" /></button>
    </div></div>

    {snapshot ? <PinnedCharacter snapshot={snapshot} /> : null}
    {mutationBlocked && !showNew ? <p className="episode-warning" role="alert">{mutationBlocked}</p> : null}
    {error ? <div className="character-error" role="alert"><CircleAlert size={17} aria-hidden="true" /><p>{error}</p>{(usageStopped || connectionStatus?.blocked) && usageUrl ? <a className="character-button subtle" href={usageUrl} target="_blank" rel="noopener noreferrer">사용량 관리</a> : null}<button className="character-button subtle" type="button" disabled={locked} onClick={() => void reload()}>다시 불러오기</button></div> : null}
    <p className="character-announcement" role="status">{busy ? 'Toon Studio가 현재 내용을 반영하고 있습니다.' : loading ? '저장된 결과를 불러오고 있습니다.' : notice}</p>

    {showNew ? currentCharacter ? <form className="episode-intro" onSubmit={event => void start(event)}>
      <h2>이 캐릭터로 어떤 이야기를 만들까요?</h2><label htmlFor="episode-new-message">떠오르는 상황이나 전하고 싶은 감정<textarea id="episode-new-message" value={draft} required maxLength={6000} rows={5} disabled={locked} onChange={event => setDraft(event.target.value)} placeholder="정해진 줄거리 없이 상황만 이야기해도 됩니다." /></label>
      {!connectionReady ? <ConnectionRequired stopped={usageStopped} onConnect={onConnectionNeeded} /> : null}
      <div className="episode-intro-actions">{newStory ? <button className="character-button" type="button" disabled={locked} onClick={() => setNewStory(false)}>취소</button> : null}<button className="character-button primary" type="submit" disabled={locked || !draft.trim() || !connectionReady}>대화 시작<ArrowRight size={15} aria-hidden="true" /></button></div>
    </form> : <div className="character-visual-empty"><p>캐릭터 시트를 먼저 확인해 주세요.</p></div> : null}
    {state ? <div hidden={showNew}>
      <nav aria-label="이야기 작업 단계"><ol className="character-steps">{STAGE_LABELS.map((label, index) => <li key={label} className={index === stageIndex ? 'current' : index < stageIndex ? 'done' : ''} aria-current={index === stageIndex ? 'step' : undefined}><span className="character-step-number" aria-hidden="true">{index < stageIndex ? <Check size={14} /> : index + 1}</span><span>{label}</span></li>)}</ol></nav>

      <div className="episode-layout">
        <section className="character-conversation" aria-labelledby="episode-conversation-title"><div className="character-panel-heading"><h2 id="episode-conversation-title">대화</h2><span>Toon Studio</span></div>
          <div className="character-chat-log" ref={log} role="log" aria-label="이야기 오케스트레이터와의 대화" aria-live="polite" aria-relevant="additions text">{state.messages.length ? state.messages.map(message => <article className={`character-message ${message.role}`} key={message.id}><span className="character-message-name">{message.role === 'user' ? '나' : 'Toon Studio'}</span><p>{message.content}</p></article>) : <p className="character-chat-empty">어떤 이야기를 만들고 싶은지 알려 주세요.</p>}</div>
          {stage !== 'format' && stage !== 'complete' ? <form className="character-composer" onSubmit={event => void sendTurn(event)}>
            <label className="character-question" htmlFor="episode-message">{targetIds.length ? '선택한 부분을 어떻게 바꿀까요?' : state.next_question || '바꾸거나 더 정하고 싶은 내용을 이야기해 주세요.'}</label>
            {targetIds.length ? <div className="episode-target"><span>{selectedLabels.join(' · ')}</span><button className="character-button subtle" type="button" disabled={locked} onClick={() => { setTargetIds([]); setEditField(''); }}><X size={12} aria-hidden="true" />전체로</button></div> : null}
            {stage === 'story' && state.story || stage === 'storyboard' && state.storyboard ? <div className="episode-scope"><label htmlFor="episode-edit-field">{targetIds.length ? '선택한 부분의' : turnStage === 'story' ? '모든 전개의' : '모든 컷의'} 수정할 항목<select id="episode-edit-field" value={editField} disabled={!canMutate} onChange={event => setEditField(event.target.value)}>{(turnStage === 'story' ? STORY_FIELDS : BOARD_FIELDS).map(field => <option value={field.id} key={field.id}>{field.label}</option>)}</select></label></div> : null}
            <textarea id="episode-message" ref={composer} rows={3} maxLength={6000} value={draft} disabled={!canMutate} onChange={event => setDraft(event.target.value)} onKeyDown={composerKey} placeholder={stage === 'intent' ? '질문에 답하거나 이야기의 의도를 더 알려 주세요.' : '예: 이 부분의 대사를 더 짧게 바꿔 주세요.'} />
            {!connectionReady ? <ConnectionRequired stopped={usageStopped} onConnect={onConnectionNeeded} /> : null}
            <div className="character-composer-actions"><span>Ctrl / ⌘ + Enter</span><button className="character-button primary" type="submit" disabled={!canMutate || !connectionReady || !draft.trim()}>{busy ? <LoaderCircle size={15} className="character-spin" aria-hidden="true" /> : <Send size={15} aria-hidden="true" />}보내기</button></div>
          </form> : <div className="character-direction-confirmed"><Check size={16} aria-hidden="true" />{stage === 'format' ? '현재 컷 구성을 확인해 주세요.' : '콘티 확인 완료'}</div>}
        </section>

        <div ref={result}>
          {stage === 'intent' ? <section className="episode-result"><ResultHeading title="정리한 이야기 의도" /><div className="episode-result-body"><dl className="episode-result-facts">{(Object.keys(INTENT_LABELS) as (keyof typeof INTENT_LABELS)[]).filter(key => state.intent[key]).map(key => <div key={key}><dt>{INTENT_LABELS[key]}</dt><dd>{state.intent[key]}</dd></div>)}</dl></div><div className="character-result-actions"><span /><button className="character-button primary" type="button" disabled={!canMutate || !connectionReady || !state.intent.topic || !state.intent.intended_emotion || !state.intent.ending || Boolean(draft.trim())} onClick={() => void sendTurn(undefined, 'story')}>이 내용으로 이야기 초안<ArrowRight size={15} aria-hidden="true" /></button></div></section> : null}
          {stage === 'story' && state.story ? <StoryResult story={state.story} disabled={!canMutate} onTarget={target} /> : null}
          {stage === 'story' && state.story ? <div className="character-result-actions"><span /><button className="character-button primary" type="button" disabled={!canMutate || Boolean(draft.trim()) || blockerIssues.length > 0} onClick={() => void decision('confirm_story')}>이 이야기 확인하고 컷 구성<ArrowRight size={15} aria-hidden="true" /></button></div> : null}
          {stage === 'format' && state.format ? <section className="episode-result"><ResultHeading title="컷 구성" version={state.format.version} /><FormatEditor key={state.id} value={state.format} disabled={!canMutate} onSave={updateFormat} onDirty={setFormatDirty} /><div className="character-result-actions"><button className="character-button" type="button" disabled={!canMutate} onClick={() => void decision('reopen_story')}><Pencil size={14} aria-hidden="true" />이야기 수정</button><button className="character-button primary" type="button" disabled={!canMutate || formatDirty || blockerIssues.length > 0} onClick={() => void decision('confirm_format')}>이 구성 확인하고 콘티로<ArrowRight size={15} aria-hidden="true" /></button></div></section> : null}
          {stage === 'storyboard' && !state.storyboard ? <section className="episode-result"><ResultHeading title="장면 구성 준비" /><div className="episode-result-body"><p>{state.format?.cut_count}컷으로 확인한 이야기를 장면별로 펼칩니다.</p></div><div className="character-result-actions"><button className="character-button" type="button" disabled={!canMutate} onClick={() => void decision('reopen_format')}>컷 구성 수정</button><button className="character-button primary" type="button" disabled={!canMutate || !connectionReady || Boolean(draft.trim())} onClick={() => void sendTurn(undefined, 'storyboard')}>장면 구성 만들기<ArrowRight size={15} aria-hidden="true" /></button></div></section> : null}
          {(stage === 'storyboard' || stage === 'complete') && state.storyboard ? <section className="episode-result"><ResultHeading title={allRoughs ? '콘티 미리보기' : '컷별 장면 구성'} version={state.storyboard.version} /><div className="episode-result-body"><div className={`episode-panels${state.format?.layout === 'vertical_grid' || state.storyboard.panels.length === 1 ? ' vertical-flow' : ''}`}>{state.storyboard.panels.map(panel => <PanelResult key={panel.id} panel={panel} state={state} disabled={!canMutate || boardApproved} pending={pendingJobs.some(job => job.panel_id === panel.id)} onTarget={target} onRough={id => setRoughTarget(id)} />)}</div></div>
            {boardApproved ? <div className="episode-approved"><Check size={16} aria-hidden="true" /><span>콘티 v{state.storyboard.version} 확인됨</span><button className="character-button subtle" type="button" disabled={locked || Boolean(mutationBlocked)} onClick={() => void exportBoard()}><Download size={13} aria-hidden="true" />콘티 내려받기</button><button className="character-button subtle" type="button" disabled={!canMutate} onClick={() => void decision('reopen_board')}><Pencil size={13} aria-hidden="true" />콘티 수정</button></div> : <div className="character-result-actions"><button className="character-button" type="button" disabled={!canMutate} onClick={() => void decision('reopen_format')}>컷 구성 수정</button><button className="character-button primary" type="button" disabled={!canMutate || !allRoughs || pendingJobs.length > 0 || Boolean(draft.trim()) || blockerIssues.length > 0} onClick={() => void decision('confirm_board')}>이 콘티 최종 확인<Check size={15} aria-hidden="true" /></button></div>}
            {!allRoughs && !boardApproved ? <p className="episode-warning">각 컷의 러프 이미지를 가져온 뒤 콘티를 최종 확인할 수 있습니다.</p> : null}
            {roughTarget && !boardApproved ? <form className="episode-rough-composer" onSubmit={event => void prepareRough(event)}><label htmlFor="episode-rough-instruction">{state.storyboard.panels.find(panel => panel.id === roughTarget)?.order}컷 · 러프 이미지 요청</label><textarea id="episode-rough-instruction" value={roughDrafts[`${state.id}:${roughTarget}`] ?? ''} maxLength={3000} rows={3} disabled={!canMutate} onChange={event => setRoughDrafts(values => ({ ...values, [`${state.id}:${roughTarget}`]: event.target.value }))} placeholder="캐릭터 시트와 이 컷의 장면 설명을 기준으로 요청합니다." /><div className="episode-intro-actions"><button className="character-button" type="button" disabled={locked} onClick={() => setRoughTarget('')}>취소</button><button className="character-button primary" type="submit" disabled={!canMutate || pendingJobs.some(job => job.panel_id === roughTarget)}>생성 요청 준비<ArrowRight size={14} aria-hidden="true" /></button></div></form> : null}
          </section> : null}
          {blockerIssues.length ? <ul className="character-issues">{blockerIssues.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.message}</li>)}</ul> : null}
        </div>
      </div>

      {episodes.some(episode => episode.rough_jobs.some(job => job.status === 'awaiting_image')) ? <section className="episode-rough-jobs" aria-label="콘티 러프 이미지 가져오기" hidden={!pendingJobs.length}>{episodes.flatMap(episode => episode.rough_jobs.filter(job => job.status === 'awaiting_image').map(job => <RoughUpload key={`${episode.id}:${job.id}`} job={job} state={episode} hidden={episode.id !== state.id} disabled={!canMutate || episode.id !== state.id} onUpload={uploadRough} onCancel={cancelRough} />))}</section> : null}
      {stage !== 'intent' && state.story && stage !== 'story' ? <details className="episode-result-archive"><summary>확인한 이야기 · v{state.story.version}</summary><StoryResult story={state.story} disabled onTarget={() => undefined} /></details> : null}
      {state.format && stage !== 'format' ? <details className="episode-result-archive"><summary>확인한 컷 구성 · v{state.format.version}</summary><div className="episode-result-body"><p>{state.format.cut_count}컷 · {state.format.layout === 'single_panel' ? '한 컷' : '세로 흐름'}</p></div></details> : null}
      {state.versions.length ? <details className="episode-result-archive"><summary>수정 기록 ({state.versions.length})</summary>{[...state.versions].reverse().map((entry, index) => <details className="episode-result-archive" key={`${entry.kind}-${entry.artifact.version}-${index}`}><summary>{entry.kind === 'story' ? '이야기' : entry.kind === 'format' ? '컷 구성' : '장면 구성'} v{entry.artifact.version}</summary>{entry.kind === 'story' ? <StoryResult story={entry.artifact as EpisodeStory} disabled onTarget={() => undefined} /> : entry.kind === 'storyboard' ? <HistoricalBoard board={entry.artifact as EpisodeBoard} /> : <p>{(entry.artifact as EpisodeFormat).cut_count}컷 · {(entry.artifact as EpisodeFormat).layout === 'single_panel' ? '한 컷' : '세로 흐름'}</p>}</details>)}</details> : null}
    </div> : null}
  </section>;
}

function ConnectionRequired({ stopped, onConnect }: { stopped: boolean; onConnect?: () => void }) {
  return <div className="character-connection-required"><span>{stopped ? '사용 한도로 작업이 중단됐습니다.' : 'ChatGPT 연결 후 대화를 이어갈 수 있습니다.'}</span><button className="character-button subtle" type="button" onClick={onConnect}>{stopped ? '사용량·재개 설정' : 'ChatGPT 연결'}</button></div>;
}
function ResultHeading({ title, version }: { title: string; version?: string }) {
  return <div className="character-panel-heading"><h2>{title}</h2>{version ? <span>v{version}</span> : null}</div>;
}
function PinnedCharacter({ snapshot }: { snapshot: Pick<EpisodeCharacterSnapshot, 'project_id' | 'direction' | 'sheet' | 'assets'> }) {
  const assets = new Map(snapshot.assets.map(asset => [asset.id, asset]));
  return <details className="episode-character"><summary>기준 캐릭터 · 방향 v{snapshot.direction.version} / 시트 v{snapshot.sheet.version}</summary><div className="episode-character-images">{snapshot.sheet.coverage.map(component => { const asset = assets.get(snapshot.sheet.components[component.id]); const url = asset ? visualAssetUrl(snapshot.project_id, asset.id, asset.url) : undefined; return <figure key={component.id}>{url ? <img src={url} alt={`기준 캐릭터 · ${component.label}`} loading="lazy" /> : <div className="episode-panel-image missing">이미지 확인 필요</div>}<figcaption>{component.label}</figcaption></figure>; })}</div></details>;
}
function StoryResult({ story, disabled, onTarget }: { story: EpisodeStory; disabled: boolean; onTarget: (id: string, field?: string) => void }) {
  return <section className="episode-result"><ResultHeading title="현재 이야기" version={story.version} /><div className="episode-result-body"><h3>{story.title}</h3><p>{story.premise}</p><ol className="episode-beats">{story.beats.map(beat => <li key={beat.id}><div className="episode-beat-top"><strong>전개 {beat.order}</strong>{!disabled ? <button className="character-button subtle" type="button" onClick={() => onTarget(beat.id)}><Pencil size={12} aria-hidden="true" />이 부분 수정</button> : null}</div><p>{beat.action}</p>{beat.emotion ? <p><span className="episode-result-label">감정</span>{beat.emotion}</p> : null}<p className="episode-beat-dialogue"><span className="episode-result-label">대사</span>{beat.dialogue || '대사 없음'}</p>{!disabled ? <button className="character-button subtle" type="button" onClick={() => onTarget(beat.id, 'dialogue')}>대사만 수정</button> : null}</li>)}</ol><p style={{ marginTop: 20 }}><span className="episode-result-label">마무리</span>{story.payoff}</p></div></section>;
}
function FormatEditor({ value, disabled, onSave, onDirty }: { value: EpisodeFormat; disabled: boolean; onSave: (cutCount: number, layout: EpisodeFormat['layout']) => Promise<boolean>; onDirty: (value: boolean) => void }) {
  const [count, setCount] = useState(value.cut_count);
  const [layout, setLayout] = useState(value.layout);
  const dirty = useRef(false);
  const changed = count !== value.cut_count || layout !== value.layout;
  const changeHandler = useRef(onDirty); changeHandler.current = onDirty;
  useEffect(() => { if (!dirty.current) { setCount(value.cut_count); setLayout(value.layout); } }, [value.version, value.cut_count, value.layout]);
  useEffect(() => { changeHandler.current(changed); }, [changed]);
  function editCount(next: number) { dirty.current = true; setCount(next); if (next === 1) setLayout('single_panel'); else if (next > 1) setLayout('vertical_grid'); }
  return <form className="episode-format-form" onSubmit={event => { event.preventDefault(); void onSave(count, layout).then(saved => { if (saved) dirty.current = false; }); }}><label htmlFor="episode-cut-count">컷 수<input id="episode-cut-count" type="number" min={1} max={8} step={1} value={count} required disabled={disabled} onChange={event => editCount(Number(event.target.value))} /></label><label htmlFor="episode-layout">배치<select id="episode-layout" value={layout} disabled={disabled} onChange={event => { dirty.current = true; const next = event.target.value as EpisodeFormat['layout']; setLayout(next); if (next === 'single_panel') setCount(1); }}><option value="single_panel">한 컷</option><option value="vertical_grid">세로 흐름</option></select></label><p>{value.rationale}</p><div className="episode-intro-actions"><button className="character-button" type="submit" disabled={disabled || !changed || !Number.isInteger(count) || count < 1 || count > 8}>구성 수정 반영<Check size={14} aria-hidden="true" /></button></div></form>;
}
function PanelResult({ panel, state, disabled, pending, onTarget, onRough }: { panel: EpisodePanel; state: EpisodeState; disabled: boolean; pending: boolean; onTarget: (id: string, field?: string) => void; onRough: (id: string) => void }) {
  const asset = state.rough_assets.find(item => item.id === state.roughs[panel.id]);
  const url = asset ? roughAssetUrl(state.project_id, state.id, asset.id, asset.url) : undefined;
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const hasImage = Boolean(url && failedUrl !== url);
  return <article className="episode-panel">
    <div className="episode-panel-top"><strong>{panel.order}컷</strong>{hasImage ? <Check size={14} aria-label="러프 이미지 등록됨" /> : <span className="episode-result-label">장면 구성</span>}</div>
    {hasImage ? <img className="episode-panel-image" src={url} alt={`${panel.order}컷 러프 · ${panel.action}`} loading="lazy" onError={() => setFailedUrl(url ?? null)} /> : <div className="episode-panel-image missing"><ImagePlus size={26} strokeWidth={1.3} aria-hidden="true" /><span>{url ? '러프 이미지를 불러오지 못했습니다.' : '러프 이미지 필요'}</span></div>}
    <div className="episode-panel-body">
      {!hasImage ? <><p><span className="episode-result-label">장면</span>{panel.scene}</p><p>{panel.action}</p><p><span className="episode-result-label">표정</span>{panel.expression}</p></> : null}
      <p className="episode-panel-dialogue"><span className="episode-result-label">대사</span>{panel.dialogue || '대사 없음'}</p>
      <PanelInstructions panel={panel} includeScene={hasImage} />
    </div>
    {!disabled ? <div className="episode-panel-actions"><button className="character-button subtle" type="button" onClick={() => onTarget(panel.id)}><Pencil size={12} aria-hidden="true" />이 컷 수정</button><button className="character-button subtle" type="button" onClick={() => onTarget(panel.id, 'dialogue')}>대사만 수정</button><button className="character-button subtle" type="button" disabled={pending} onClick={() => onRough(panel.id)}><ImagePlus size={12} aria-hidden="true" />{pending ? '이미지 가져오기 대기' : asset ? '러프 이미지 수정' : '러프 이미지 요청'}</button></div> : null}
  </article>;
}
function PanelInstructions({ panel, includeScene }: { panel: EpisodePanel; includeScene: boolean }) {
  const fields = (Object.keys(PANEL_INSTRUCTION_LABELS) as (keyof typeof PANEL_INSTRUCTION_LABELS)[]).filter(key => includeScene || !['scene', 'action', 'expression'].includes(key));
  return <details><summary>{includeScene ? '장면 지시 보기' : '구도·연속성 보기'}</summary><dl>{fields.map(key => <div key={key}><dt>{PANEL_INSTRUCTION_LABELS[key]}</dt><dd>{panel[key]}</dd></div>)}</dl></details>;
}
function HistoricalBoard({ board }: { board: EpisodeBoard }) {
  return <ol className="episode-beats">{board.panels.map(panel => <li key={panel.id}><strong>{panel.order}컷</strong><p>{panel.scene}</p><p>{panel.action}</p><p>{panel.dialogue || '대사 없음'}</p></li>)}</ol>;
}

function RoughUpload({ job, state, disabled, hidden = false, onUpload, onCancel }: { job: EpisodeRoughJob; state: EpisodeState; disabled: boolean; hidden?: boolean; onUpload: (job: EpisodeRoughJob, file: File, provenance: VisualProvenance, identity: string) => Promise<boolean>; onCancel: (job: EpisodeRoughJob) => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [identity, setIdentity] = useState('');
  const [source, setSource] = useState<VisualProvenance['source']>('user_upload');
  const [model, setModel] = useState('');
  const [prompt, setPrompt] = useState('');
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const inputId = `episode-rough-image-${job.id}`;
  const panel = state.storyboard?.panels.find(item => item.id === job.panel_id);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || disabled) return;
    if (file.size > 16 * 1024 * 1024) { setError('이미지는 16MB 이하로 가져와 주세요.'); return; }
    const provenance: VisualProvenance = { source, model: model.trim() || null, prompt: prompt.trim() || null, workflow: null, seed: null, fixture: false, unknowns: [...(!model.trim() ? ['model'] : []), ...(!prompt.trim() ? ['prompt'] : []), 'workflow', 'seed'] };
    if (await onUpload(job, file, provenance, identity)) { setFile(null); setError(''); }
  }
  async function copy() { try { await navigator.clipboard.writeText(job.prompt); setCopied(true); } catch { setError('복사하지 못했습니다. 아래 요청문을 직접 선택해 복사해 주세요.'); } }
  return <article className="character-visual-job" hidden={hidden}><div className="character-visual-job-heading"><h3>{panel?.order ?? job.panel_id}컷 · 러프 이미지 가져오기</h3><button className="character-button subtle" type="button" disabled={disabled} onClick={() => void onCancel(job)} aria-label={`${panel?.order ?? job.panel_id}컷 러프 요청 취소`}><X size={13} aria-hidden="true" />취소</button></div>{job.instruction ? <p className="character-job-instruction">{job.instruction}</p> : null}<details className="character-generation-request"><summary>생성 요청 보기·복사</summary><p>요청문과 기준 이미지를 Codex에 전달한 뒤 결과를 가져오세요.</p><button className="character-button subtle" type="button" onClick={() => void copy()}><Copy size={13} aria-hidden="true" />{copied ? '복사됨' : '요청문 복사'}</button><textarea readOnly value={job.prompt} rows={7} aria-label={`${panel?.order ?? job.panel_id}컷 이미지 생성 요청문`} /><div className="character-job-source-images">{job.source_asset_ids.map((id, index) => { const characterAsset = state.character_snapshot.assets.find(asset => asset.id === id); const roughAsset = state.rough_assets.find(asset => asset.id === id); const url = characterAsset ? visualAssetUrl(state.project_id, id, characterAsset.url) : roughAsset ? roughAssetUrl(state.project_id, state.id, id, roughAsset.url) : undefined; return url ? <a key={id} href={url} download={`storyboard-source-${index + 1}.png`}><img src={url} alt={`러프 생성 기준 ${index + 1}`} /><span><Download size={12} aria-hidden="true" />기준 이미지 {index + 1}</span></a> : <span key={id}>기준 이미지를 확인해 주세요.</span>; })}</div></details><form onSubmit={event => void submit(event)}><label className="character-visual-file" htmlFor={inputId}><Upload size={18} aria-hidden="true" /><span>{file?.name || '결과 이미지 선택'}</span><input id={inputId} type="file" accept="image/png,image/jpeg,image/webp" disabled={disabled} onChange={event => { setFile(event.target.files?.[0] ?? null); setIdentity(crypto.randomUUID()); setError(''); }} /></label><div className="character-visual-import-row"><label>이미지 출처<select value={source} disabled={disabled} onChange={event => setSource(event.target.value as VisualProvenance['source'])}><option value="user_upload">직접 가져온 이미지</option><option value="codex_imagegen">Codex에서 생성한 이미지</option></select></label><button className="character-button primary" type="submit" disabled={disabled || !file}><Upload size={14} aria-hidden="true" />러프 이미지 반영</button></div><details className="character-visual-provenance"><summary>생성 정보 추가 · 선택</summary><label>사용 모델<input value={model} maxLength={200} disabled={disabled} onChange={event => setModel(event.target.value)} placeholder="알고 있는 경우만 입력" /></label><label>실제로 사용한 요청문<textarea value={prompt} rows={3} maxLength={20000} disabled={disabled} onChange={event => setPrompt(event.target.value)} placeholder="알고 있는 경우만 입력" /></label></details>{error ? <p className="character-edit-error" role="alert">{error}</p> : null}</form></article>;
}
