import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowRight, Check, CircleAlert, FileText, Info, LoaderCircle, MessageSquare, Plus, RotateCcw, Square, Workflow } from 'lucide-react';
import { actOnStudioRun, createStudioProject, getStudioProject, getStudioRun, initializeStudio, startStudioRun, StudioApiError } from './studioApi';
import type { StudioAction, StudioInputKind, StudioPanel, StudioProject, StudioProjectSnapshot, StudioRun, StudioStory } from './studioTypes';

const ROLE_LABELS: Record<string, string> = {
  story_generator: '이야기 초안 정리', evaluator: '이야기와 장면 검토', validator: '입력과 결과 연결 확인',
  story_evaluator: '이야기 독립 검토', board_evaluator: '장면 구성 독립 검토',
  storyboard_planner: '컷별 장면 구성', orchestrator: '다음 작업 준비', human: '사용자 확인 대기',
};
const STAGE_LABELS: Record<string, string> = { story: '이야기', format: '컷 구성', storyboard: '콘티' };
const STAGES = ['story', 'format', 'storyboard'];
const INPUT_LABELS: Record<StudioInputKind, string> = { idea: '아이디어', anecdote: '경험·썰', script: '정리된 이야기', reference: '이야기 참고 자료' };

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '작업을 처리하지 못했습니다. 다시 시도해 주세요.';
}
function friendlyMessage(message: string): string {
  return message.replace(/synthetic character fixture/gi, '합성 캐릭터 예시').replace(/G2/g, '콘티 품질 확인').replace(/G1/g, '이야기 확인').replace(/fixture/gi, '합성 예시').replace(/blocker/gi, '진행 차단 항목').replace(/synthetic character/gi, '합성 캐릭터').replace(/overlay/gi, '텍스트');
}
function activeRun(run: StudioRun | null): boolean { return run?.status === 'queued' || run?.status === 'running'; }
function dateLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function timeLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

export default function StudioWorkspace() {
  const [projects, setProjects] = useState<StudioProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [snapshot, setSnapshot] = useState<StudioProjectSnapshot | null>(null);
  const [run, setRun] = useState<StudioRun | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [loadingProject, setLoadingProject] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [reload, setReload] = useState(0);
  const [idea, setIdea] = useState('');
  const [inputKind, setInputKind] = useState<StudioInputKind>('idea');
  const [newStory, setNewStory] = useState(false);
  const mutationLock = useRef(false);

  useEffect(() => {
    let live = true;
    setInitializing(true);
    void initializeStudio().then(items => {
      if (!live) return;
      setProjects(items);
      setProjectId(current => current && items.some(item => item.id === current) ? current : items[0]?.id ?? '');
      setCreateOpen(items.length === 0);
      setError('');
    }).catch(reason => { if (live) setError(errorMessage(reason)); }).finally(() => { if (live) setInitializing(false); });
    return () => { live = false; };
  }, [reload]);

  useEffect(() => {
    if (!projectId) { setSnapshot(null); setRun(null); return; }
    const controller = new AbortController();
    setLoadingProject(true);
    setSnapshot(null);
    setRun(null);
    setNewStory(false);
    setIdea('');
    setNotice('');
    void getStudioProject(projectId, controller.signal).then(result => {
      setSnapshot(result);
      setRun(result.current_run);
    }).catch(reason => { if (!controller.signal.aborted) setError(errorMessage(reason)); }).finally(() => {
      if (!controller.signal.aborted) setLoadingProject(false);
    });
    return () => controller.abort();
  }, [projectId, reload]);

  function putRun(value: StudioRun) {
    setRun(value);
    setSnapshot(current => current ? {
      ...current,
      current_run: value,
      runs: current.runs.some(item => item.id === value.id) ? current.runs.map(item => item.id === value.id ? value : item) : [...current.runs, value],
    } : current);
  }

  const pollingId = activeRun(run) ? run?.id : null;
  useEffect(() => {
    if (!pollingId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await getStudioRun(projectId, pollingId!, controller.signal);
        if (controller.signal.aborted) return;
        setRun(result);
        setSnapshot(current => current ? {
          ...current, current_run: result, runs: current.runs.map(item => item.id === result.id ? result : item),
        } : current);
        if (activeRun(result)) timer = setTimeout(() => void poll(), 900);
      } catch (reason) {
        if (controller.signal.aborted) return;
        setError('진행 상태를 불러오지 못했습니다. 연결을 확인하고 다시 불러와 주세요. ' + errorMessage(reason));
      }
    }
    timer = setTimeout(() => void poll(), 350);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [pollingId, projectId]);

  async function mutate(work: () => Promise<void>): Promise<boolean> {
    if (mutationLock.current) return false;
    mutationLock.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    try { await work(); return true; }
    catch (reason) {
      if (reason instanceof StudioApiError && reason.status === 409 && run) {
        try { putRun(await getStudioRun(run.project_id, run.id)); } catch { /* Preserve the original conflict message. */ }
        setError('현재 결과를 다시 불러왔습니다. 내용을 확인한 뒤 다시 요청해 주세요. ' + reason.message);
      } else setError(errorMessage(reason));
      return false;
    } finally { mutationLock.current = false; setBusy(false); }
  }

  async function createProject(value: { name: string; audience: string; series_direction: string }) {
    return mutate(async () => {
      const created = await createStudioProject({ ...value, synthetic_confirmed: true });
      setProjects(current => [...current, created]);
      setProjectId(created.id);
      setCreateOpen(false);
      setNotice('테스트 프로젝트를 만들었습니다. 이야기의 재료부터 입력해 주세요.');
    });
  }

  async function startStory(event: FormEvent) {
    event.preventDefault();
    if (!projectId || !idea.trim()) return;
    await mutate(async () => {
      putRun(await startStudioRun(projectId, idea.trim(), inputKind));
      setNewStory(false);
      setIdea('');
    });
  }

  async function runAction(action: StudioAction, feedback?: string, targets?: string[]) {
    if (!run) return false;
    return mutate(async () => {
      putRun(await actOnStudioRun(run, action, feedback, targets));
      setNotice(action.startsWith('revise_') ? '수정 요청을 받았습니다. 처리 과정과 새 버전을 이 화면에서 확인할 수 있습니다.' : action === 'reject' ? '작업을 멈췄습니다. 지금까지의 결과와 기록은 보관됩니다.' : '요청을 받았습니다. 다음 결과를 준비합니다.');
    });
  }

  const working = activeRun(run);
  const controlsLocked = busy || working || loadingProject || initializing;
  const project = snapshot?.project;

  return <div className="studio-shell">
    <header className="studio-header">
      <div className="studio-brand"><Workflow size={23} aria-hidden="true" />Toon Studio</div>
      <div className="studio-header-tools">
        {projects.length > 0 ? <select className="studio-select" aria-label="프로젝트 선택" value={projectId} disabled={controlsLocked} onChange={event => { setProjectId(event.target.value); setCreateOpen(false); setError(''); }}>
          {projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select> : null}
        <button type="button" className="studio-button small" disabled={controlsLocked} onClick={() => setCreateOpen(value => !value)}><Plus size={15} aria-hidden="true" />새 프로젝트</button>
      </div>
    </header>
    <main className="studio-main">
      <div className="studio-fixture-note"><Info size={16} aria-hidden="true" /><p><strong>합성 예시로 작업 흐름을 확인하는 개발 화면입니다.</strong> {run && run.provider !== 'deterministic_fixture' ? '이야기 결과에 연결된 제공자를 사용합니다. 시각 콘티 품질은 아직 확인되지 않았습니다.' : '기본 모드는 정해진 예시 규칙을 사용하며 실제 AI 생성에 연결되지 않았습니다.'} 실제 캐릭터·계정·개인 경험 자료를 넣지 말고 가상의 테스트 재료를 사용해 주세요.</p></div>
      {error ? <div className="studio-alert" role="alert"><p>{error}</p><div className="studio-error-actions"><button type="button" className="studio-button small" disabled={busy} onClick={() => { setError(''); setReload(value => value + 1); }}><RotateCcw size={14} aria-hidden="true" />다시 불러오기</button></div></div> : null}
      {notice ? <p className="studio-notice" role="status">{notice}</p> : null}
      {initializing ? <div className="studio-empty" role="status"><LoaderCircle size={18} className="studio-spin" aria-hidden="true" /> 작업 공간을 불러오는 중입니다.</div> : null}
      {createOpen && !initializing ? <ProjectForm busy={busy} hasProject={projects.length > 0} onCancel={() => setCreateOpen(false)} onCreate={createProject} /> : null}
      {!project && !loadingProject && !initializing && !createOpen ? <div className="studio-welcome"><p className="studio-kicker">이야기부터, 한 단계씩</p><h1>재료를 꺼내고 이야기로 다듬어 가세요.</h1><p>프로젝트 방향을 간단히 정한 뒤 이야기, 컷 구성, 콘티를 같은 화면에서 확인하고 수정합니다.</p><button className="studio-button primary" type="button" onClick={() => setCreateOpen(true)}>첫 테스트 프로젝트 만들기<ArrowRight size={16} aria-hidden="true" /></button><ol className="studio-simple-steps"><li>프로젝트 방향</li><li>이야기 정리</li><li>컷 구성</li><li>콘티 검토</li></ol></div> : null}
      {loadingProject ? <p className="studio-empty" role="status">프로젝트와 마지막 작업을 불러오고 있습니다.</p> : null}
      {project ? <>
        <div className="studio-project-intro"><div><p className="studio-kicker">내 작업 공간</p><h1>{project.name}</h1><p>{project.series_direction}</p></div>{run ? <button className="studio-button small" type="button" disabled={controlsLocked} onClick={() => setNewStory(value => !value)}><Plus size={14} aria-hidden="true" />{newStory ? '현재 이야기로 돌아가기' : '다른 테스트 이야기'}</button> : null}</div>
        <details className="studio-context"><summary>이번 테스트에서 사용하는 기반 확인</summary><p>대상: {project.audience}</p><p>이 단계에서는 준비된 합성 캐릭터·시리즈 설정을 사용합니다. 실제 에피소드 작업을 시작하기 전에 레퍼런스를 받고 캐릭터 후보를 수정해 바이블과 시트를 확정하는 별도 단계가 먼저 제공되어야 합니다.</p><dl>{project.fixture_versions.map(source => <div key={source.artifact_id}><dt>{fixtureLabel(source.role)}</dt><dd>{source.version}</dd></div>)}</dl></details>
        {!run || newStory ? <form className="studio-composer" onSubmit={startStory}>
          <div className="studio-composer-header"><p>어떤 이야기를 풀어볼까요?</p><select className="studio-select" aria-label="이야기 재료의 용도" value={inputKind} disabled={controlsLocked} onChange={event => setInputKind(event.target.value as StudioInputKind)}>{Object.entries(INPUT_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></div>
          <label className="studio-field"><span className="studio-kicker">대략적인 재료만 적어도 됩니다</span><textarea className="studio-textarea" required maxLength={20000} value={idea} disabled={controlsLocked} placeholder="가상의 테스트 상황을 적어 주세요. 예: 기대했던 계획이 어긋나지만 작은 발견으로 기분이 바뀌는 이야기." onChange={event => setIdea(event.target.value)} /></label>
          <div className="studio-composer-bottom"><p>제목이나 컷 수는 지금 정하지 않아도 됩니다. 현재 테스트는 정해진 예시 규칙으로 작동합니다.</p><button type="submit" className="studio-button primary" disabled={controlsLocked || !idea.trim()}>{busy ? <LoaderCircle size={16} className="studio-spin" aria-hidden="true" /> : <MessageSquare size={16} aria-hidden="true" />}이야기 정리 시작</button></div>
        </form> : null}
        {run && !newStory ? <>
          <ol className="studio-stagebar" aria-label="현재 작업 단계">{STAGES.map((stage, index) => {
            const activeIndex = STAGES.indexOf(run.current_stage);
            return <li key={stage} className={stage === run.current_stage ? 'active' : index < activeIndex ? 'done' : ''} aria-current={stage === run.current_stage ? 'step' : undefined}><span className="studio-stage-number">{index < activeIndex ? <Check size={14} aria-hidden="true" /> : String(index + 1).padStart(2, '0')}</span>{STAGE_LABELS[stage]}</li>;
          })}</ol>
          <RunStatus run={run} />
          <div className="studio-content-stack">
            <details className="studio-details" style={{ marginTop: 0, paddingTop: 0, borderTop: 0 }}><summary>처음 입력한 이야기 재료</summary><p className="studio-story-premise" style={{ marginTop: 12 }}>{run.idea}</p></details>
            {run.story ? run.current_stage === "story" ? <StoryCard story={run.story} /> : <details className="studio-stage-result"><summary>확인한 이야기 다시 보기 · {run.story.version}</summary><StoryCard story={run.story} /></details> : null}
            {run.format_proposal ? run.current_stage === 'format' ? <FormatCard run={run} /> : <details className="studio-stage-result"><summary>확인한 컷 구성 다시 보기 · {run.format_proposal.version}</summary><FormatCard run={run} /></details> : null}
            {run.storyboard ? <section className="studio-card" aria-labelledby="board-heading"><div className="studio-section-head"><div><h2 id="board-heading">컷별 장면 구성</h2><p>앞선 이야기의 행동과 감정이 각 장면에 어떻게 이어지는지 확인하세요.</p></div><span className="studio-version-label">{run.storyboard.version}</span></div><div className="studio-storyboard-grid">{run.storyboard.panels.map(panel => <PanelCard key={panel.id} panel={panel} />)}</div><p className="studio-preview-boundary">현재 결과는 장면 설명을 이용한 개발용 구조 예시입니다. 인물의 동작·표정·배치를 읽을 수 있는 시각 콘티가 없어 콘티 품질 확인과 최종 확정은 완료할 수 없습니다.</p></section> : null}
            {!working ? <ReviewControls key={`${run.id}:${run.revision}:${run.pending_action}`} run={run} disabled={busy} onAction={runAction} /> : null}
          </div>
          <HistoryDetails run={run} runs={snapshot.runs} disabled={controlsLocked} onSelect={value => { putRun(value); setError(''); setNotice(''); }} />
        </> : null}
      </> : null}
      <footer className="studio-footer">자료와 작업 기록은 이 PC의 로컬 저장소에 보관됩니다. 현재 화면은 이야기·콘티 작업 흐름 검증용입니다.</footer>
    </main>
  </div>;
}

function fixtureLabel(key: string): string {
  if (key.includes('character')) return '합성 캐릭터';
  if (key.includes('series') || key.includes('strategy')) return '합성 시리즈';
  if (key.includes('reference')) return '합성 참고 자료';
  return '기반 자료';
}

function ProjectForm({ busy, hasProject, onCreate, onCancel }: { busy: boolean; hasProject: boolean; onCreate: (value: { name: string; audience: string; series_direction: string }) => Promise<boolean>; onCancel: () => void }) {
  const [name, setName] = useState('');
  const [audience, setAudience] = useState('');
  const [direction, setDirection] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!confirmed || !name.trim() || !audience.trim() || !direction.trim()) return;
    await onCreate({ name: name.trim(), audience: audience.trim(), series_direction: direction.trim() });
  }
  return <section className="studio-create" aria-labelledby="create-heading"><div className="studio-section-head"><div><h2 id="create-heading">프로젝트 방향부터 간단히 정해요</h2><p>캐릭터와 에피소드의 세부 설정은 작업하며 다듬습니다.</p></div>{hasProject ? <button type="button" className="studio-button ghost small" disabled={busy} onClick={onCancel}>닫기</button> : null}</div><form onSubmit={submit}><div className="studio-create-grid"><label className="studio-field">프로젝트 이름<input className="studio-input" required maxLength={120} value={name} disabled={busy} onChange={event => setName(event.target.value)} placeholder="테스트 프로젝트의 이름" autoFocus /></label><label className="studio-field">독자·대상<input className="studio-input" required maxLength={1000} value={audience} disabled={busy} onChange={event => setAudience(event.target.value)} placeholder="누가 읽는 이야기인가요?" /></label><label className="studio-field studio-wide">시리즈 방향<textarea className="studio-textarea" required maxLength={3000} value={direction} disabled={busy} onChange={event => setDirection(event.target.value)} placeholder="어떤 이야기를 계속 다루고 싶은지 한두 문장으로 적어 주세요." /></label></div><div className="studio-form-bottom"><label className="studio-checkbox"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} /><span>가상의 테스트 프로젝트이며 실제 캐릭터·계정·개인 자료를 사용하지 않습니다.</span></label><button type="submit" className="studio-button primary" disabled={busy || !confirmed || !name.trim() || !audience.trim() || !direction.trim()}>{busy ? <LoaderCircle size={16} className="studio-spin" aria-hidden="true" /> : null}프로젝트 만들기<ArrowRight size={15} aria-hidden="true" /></button></div></form></section>;
}

function RunStatus({ run }: { run: StudioRun }) {
  const working = activeRun(run);
  const waiting = run.status === 'awaiting_review';
  const title = working ? (run.current_role ? ROLE_LABELS[run.current_role] ?? '결과를 준비하고 있습니다' : '작업을 준비하고 있습니다') : waiting ? '지금 결과를 확인해 주세요' : run.status === 'blocked' ? '다음 단계에 필요한 결과가 남아 있습니다' : run.status === 'stopped' ? '작업이 멈춰 있습니다' : '작업 흐름 확인 완료 · 실제 시각 콘티는 아직 필요';
  return <div className={`studio-status ${run.status === 'blocked' ? 'blocked' : ''}`} role="status" aria-live="polite">{working ? <LoaderCircle className="studio-spin" size={20} aria-hidden="true" /> : run.status === 'blocked' ? <CircleAlert size={20} aria-hidden="true" /> : <MessageSquare size={20} aria-hidden="true" />}<div><strong>{title}</strong><p>{friendlyMessage(run.summary)}</p><small>{working ? '진행 상황과 결과가 자동으로 갱신됩니다.' : run.status === 'completed' ? '아래에서 컷 구성이나 이야기 방향을 수정하고 새 버전을 다시 확인할 수 있습니다.' : '확인과 수정 요청은 아래에서 이어갈 수 있습니다.'}</small></div></div>;
}

function StoryCard({ story }: { story: StudioStory }) {
  return <section className="studio-card" aria-labelledby="story-heading"><div className="studio-section-head"><div><h2 id="story-heading">이야기 초안</h2><p>제공된 재료를 바탕으로 순서와 감정의 흐름을 정리했습니다. {story.fixture ? '현재는 정해진 합성 예시 규칙을 사용합니다.' : '모델이 제안한 결과를 확인하고 필요한 부분을 수정해 주세요.'}</p></div><span className="studio-version-label">{story.version}</span></div><p className="studio-story-premise">{story.premise}</p>{story.understanding ? <p className="studio-format-reason" style={{ marginTop: 12 }}>{story.understanding}</p> : null}<ol className="studio-beats">{story.beats.map(beat => <li key={beat.id}><span className="studio-beat-number">{beat.order}</span><div><strong>{beat.emotion}</strong><p>{beat.action}</p>{beat.dialogue ? <p className="studio-format-reason">“{beat.dialogue}”</p> : null}</div></li>)}</ol><div className="studio-payoff"><strong>마지막에 남길 변화</strong><p>{friendlyMessage(story.payoff)}</p></div><div className="studio-feedback-applied"><strong>현재 이야기 의도</strong><p>{friendlyMessage(story.narrative_intent)}</p>{Array.isArray(story.feedback_applied) && story.feedback_applied.length > 0 ? <p>접수된 의견: {story.feedback_applied.join(" · ")}</p> : null}</div></section>;
}

function PanelCard({ panel }: { panel: StudioPanel }) {
  return <article className="studio-cut"><div className="studio-cut-preview"><div className="studio-preview-placeholder"><FileText size={27} strokeWidth={1.4} aria-hidden="true" /><span>시각 콘티가 아직 준비되지 않았습니다</span></div><span className="studio-preview-tag">개발용 장면 설명</span></div><div className="studio-cut-body"><div className="studio-cut-head"><h3>{panel.order}컷 · {panel.scene}</h3></div><p className="studio-cut-action">{panel.action}</p><dl><dt>표정</dt><dd>{panel.expression}</dd><dt>화면</dt><dd>{panel.camera} · {panel.composition}</dd><dt>시선</dt><dd>{panel.gaze_target}</dd><dt>호흡</dt><dd>{panel.pacing}</dd><dt>목적</dt><dd>{panel.visual_purpose}</dd><dt>연결</dt><dd>{friendlyMessage(panel.continuity)}</dd><dt>텍스트</dt><dd>{friendlyMessage(panel.text_placement)}</dd><dt>장면 메모</dt><dd>{friendlyMessage(panel.thumbnail.description)}</dd></dl>{panel.dialogue ? <p className="studio-cut-dialogue">{panel.dialogue}</p> : null}</div></article>;
}

function FormatCard({ run }: { run: StudioRun }) {
  const format = run.format_proposal;
  if (!format) return null;
  return <section className="studio-card" aria-labelledby="format-heading">
    <div className="studio-section-head"><h2 id="format-heading">이야기에 맞는 컷 구성</h2><span className="studio-version-label">{format.version}</span></div>
    <p className="studio-format-stat">{format.selected_format === 'single_panel' ? '한 장면' : `${format.cut_count}개의 장면`}</p>
    <p className="studio-format-reason">{friendlyMessage(format.rationale)}</p>
    <p className="studio-format-layout">이 구성은 제안입니다. 방향을 바꾸려면 아래에서 수정 의견을 남겨 주세요.</p>
  </section>;
}

function PreviousArtifact({ artifact }: { artifact: unknown }) {
  if (!artifact || typeof artifact !== 'object') return null;
  const value = artifact as Record<string, unknown>;
  const entries = Array.isArray(value.beats) ? value.beats : Array.isArray(value.panels) ? value.panels : [];
  return <details className="studio-version-content"><summary>이 버전의 결과 내용</summary>
    {typeof value.premise === 'string' ? <p>{value.premise}</p> : null}
    {typeof value.rationale === 'string' ? <p>{friendlyMessage(value.rationale)}</p> : null}
    {entries.length > 0 ? <ol>{entries.map((entry: unknown, index: number) => {
      if (!entry || typeof entry !== 'object') return null;
      const item = entry as Record<string, unknown>;
      return <li key={typeof item.id === 'string' ? item.id : index}>{typeof item.action === 'string' ? item.action : ''}{typeof item.expression === 'string' ? <small>표정: {item.expression}</small> : null}</li>;
    })}</ol> : null}
    {typeof value.payoff === 'string' ? <p>마무리: {friendlyMessage(value.payoff)}</p> : null}
  </details>;
}

function ReviewControls({ run, disabled, onAction }: { run: StudioRun; disabled: boolean; onAction: (action: StudioAction, feedback?: string, targetIds?: string[]) => Promise<boolean> }) {
  const [feedback, setFeedback] = useState('');
  const [targets, setTargets] = useState<string[]>([]);
  const [validation, setValidation] = useState('');
  const boardStage = run.current_stage === 'storyboard' && Boolean(run.storyboard);
  const fixtureBoard = run.pending_action === 'approve_storyboard' && !run.storyboard?.usable_storyboard;
  const stopped = run.status === 'stopped';
  const completed = run.status === 'completed';
  const executionFailed = run.status === 'blocked' && !run.pending_action;
  const recoveryOnly = stopped || executionFailed;
  const retryExhausted = recoveryOnly && !run.retry_available;
  const approvalBlocked = run.issues.some(issue => issue.severity === 'blocker');
  const fixture = run.provider === 'deterministic_fixture';
  const approveLabel = run.pending_action === 'approve_story' ? '이 방향으로 컷 구성 제안받기' : run.pending_action === 'approve_format' ? '이 구성으로 장면 만들기' : fixtureBoard ? '합성 흐름 검토 완료' : '콘티 확정';
  async function revise(fromStory = false) {
    if (!feedback.trim()) { setValidation('바꾸고 싶은 부분을 한 문장 이상 적어 주세요.'); return; }
    setValidation('');
    await onAction(fromStory || !boardStage ? 'revise_story' : 'revise_storyboard', feedback.trim(), fromStory ? undefined : targets);
  }
  return <section className="studio-card">
    <p className="studio-review-title">{retryExhausted ? '이 작업의 재시도 한도에 도달했습니다' : executionFailed ? '연결과 설정을 확인한 뒤 이 단계만 다시 시도할 수 있습니다' : stopped ? '다시 이어갈 준비가 되면 알려 주세요' : completed ? '확인한 결과도 계속 다듬을 수 있습니다' : boardStage ? '장면 구성에서 바꾸고 싶은 부분이 있나요?' : run.pending_action === 'approve_format' ? '이 컷 구성이 이야기와 맞나요?' : '이야기 방향을 확인해 주세요'}</p>
    <p className="studio-review-hint">{executionFailed ? '이전 결과와 체크포인트는 보존되어 있습니다.' : boardStage ? '특정 컷을 선택하거나 이야기 방향부터 수정할 수 있습니다. 이전 확인 기록을 보존하고 수정한 결과를 새 버전으로 다시 확인합니다.' : '원하는 행동, 감정, 결말을 알려 주세요. 수정 의견과 반영 결과가 함께 기록됩니다.'}</p>
    {run.issues.length > 0 ? <ul className="studio-issue-list">{run.issues.map(issue => <li key={issue.id}>{friendlyMessage(issue.message)}</li>)}</ul> : null}
    {!recoveryOnly ? <>
      <label className="studio-field">수정 의견
        <textarea className="studio-textarea" value={feedback} maxLength={5000} disabled={disabled}
          placeholder={fixture ? '테스트 예: 행동: 주인공이 한 걸음 다가간다. 또는 대사: 한번 해 보자.' : boardStage ? '예: 마지막 컷의 표정을 더 분명하게 보여 주세요.' : '예: 주인공이 직접 선택하는 장면을 넣고, 마지막 감정 변화를 더 분명하게 해 주세요.'}
          onChange={event => { setFeedback(event.target.value); setValidation(''); }} />
      </label>
      {fixture ? <p className="studio-review-hint" style={{ marginTop: 8 }}>현재 예시 모드는 의견을 보존하며, ‘행동:’ 또는 ‘대사:’로 시작하는 요청만 정해진 규칙으로 바꿉니다. 자연어 수정 능력은 모델 연결 후 별도로 확인해야 합니다.</p> : null}
      {boardStage ? <div className="studio-review-actions" aria-label="수정할 컷 선택">{run.storyboard?.panels.map(panel => <label key={panel.id} className="studio-cut-select"><input type="checkbox" checked={targets.includes(panel.id)} disabled={disabled} onChange={event => setTargets(current => event.target.checked ? [...current, panel.id] : current.filter(id => id !== panel.id))} />{panel.order}컷</label>)}</div> : null}
      {validation ? <p className="studio-review-error" role="alert">{validation}</p> : null}
    </> : null}
    <div className="studio-review-actions">
      {!completed && run.pending_action ? <button className="studio-button primary" type="button" disabled={disabled || approvalBlocked} onClick={() => void onAction(run.pending_action!)}>{approveLabel}<ArrowRight size={15} aria-hidden="true" /></button> : null}
      {!recoveryOnly ? <button type="button" className="studio-button" disabled={disabled || !feedback.trim()} onClick={() => void revise()}><RotateCcw size={15} aria-hidden="true" />{targets.length > 0 ? `선택한 ${targets.length}개 컷 수정 요청` : '수정 요청 보내기'}</button> : <button type="button" className="studio-button primary" disabled={disabled || retryExhausted} onClick={() => void onAction('retry')}><RotateCcw size={15} aria-hidden="true" />{executionFailed ? '이 단계 다시 시도' : '작업 다시 이어가기'}</button>}
      {boardStage && !recoveryOnly ? <button type="button" className="studio-button" disabled={disabled || !feedback.trim()} onClick={() => void revise(true)}>이야기부터 수정</button> : null}
      {!recoveryOnly && !completed ? <button className="studio-button ghost small" type="button" disabled={disabled} onClick={() => void onAction('reject')}><Square size={12} aria-hidden="true" />작업 멈추기</button> : null}
    </div>
    {retryExhausted ? <p className="studio-review-hint">이전 결과는 보존되어 있습니다. 새 이야기 작업을 시작하거나 연결 설정을 확인해 주세요.</p> : null}
    {fixtureBoard ? <p className="studio-review-hint" style={{ marginTop: 12 }}>이번 확인은 합성 예시의 작업 흐름 검증입니다. 실제 시각 콘티의 품질 승인이나 이미지 생성 허가로 이어지지 않습니다.</p> : null}
  </section>;
}
function HistoryDetails({ run, runs, disabled, onSelect }: { run: StudioRun; runs: StudioRun[]; disabled: boolean; onSelect: (value: StudioRun) => void }) {
  return <>
    <details className="studio-details"><summary>수정·버전 기록 ({run.versions.length})</summary><ol className="studio-version-list">{[...run.versions].reverse().map(version => <li key={`${version.artifact_id}:${version.version}`}><strong>{version.kind === 'story' ? '이야기' : version.kind === 'storyboard' ? '장면 구성' : version.kind === 'format' || version.kind === 'format_proposal' ? '컷 구성' : '작업 결과'} · {version.version}</strong><p>{version.summary}</p><small>{dateLabel(version.created_at)}</small><PreviousArtifact artifact={version.artifact} /></li>)}</ol>{run.versions.length === 0 ? <p className="studio-empty">첫 결과가 준비되면 버전이 여기에 기록됩니다.</p> : null}</details>
    <details className="studio-details"><summary>어떤 작업이 진행됐는지 보기</summary><ol className="studio-event-list">{run.events.map(event => <li key={event.id}><time dateTime={event.at}>{timeLabel(event.at)}</time><div><strong>{ROLE_LABELS[event.role] ?? '작업 진행'}</strong><p>{event.message}</p></div></li>)}</ol></details>
    {runs.length > 1 ? <details className="studio-details"><summary>다른 테스트 이야기 열기 ({runs.length})</summary><div className="studio-run-picker"><label className="studio-field">테스트 기록<select className="studio-select" value={run.id} disabled={disabled} onChange={event => { const selected = runs.find(value => value.id === event.target.value); if (selected) onSelect(selected); }}>{[...runs].reverse().map(value => <option value={value.id} key={value.id}>{dateLabel(value.created_at)} · {value.idea.slice(0, 35)}</option>)}</select></label></div></details> : null}
    <details className="studio-details"><summary>개발용 실행 정보</summary><pre className="studio-technical">{JSON.stringify({ run_id: run.id, revision: run.revision, engine: run.engine, provider: run.provider, status: run.status, stage: run.current_stage, role: run.current_role, story_version: run.story?.version, format_version: run.format_proposal?.version, storyboard_version: run.storyboard?.version, sources: run.story?.source_versions }, null, 2)}</pre></details>
  </>;
}
