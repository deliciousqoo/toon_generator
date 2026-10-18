import { useEffect, useRef, useState } from 'react';
import type { FormEvent, MouseEvent } from 'react';
import { ArrowRight, Check, CircleAlert, Copy, Download, ImagePlus, LoaderCircle, Pencil, Plus, RotateCcw, Upload, X } from 'lucide-react';
import { CharacterApiError, getCharacter } from './characterApi';
import { attachVisualComponent, buildVisualSheet, cancelVisualJob, confirmVisualSheet, downloadVisualSheet, reopenVisualSheet, requestVisualJob, saveVisualCoverage, selectVisualCandidate, uploadVisualImage, visualAssetUrl, visualSheetExportUrl } from './characterVisualApi';
import type { CharacterState } from './characterTypes';
import type { CandidateRef, CharacterCandidate, CharacterVisualState, SheetComponent, VisualAsset, VisualJob, VisualMutation, VisualProvenance } from './characterVisualTypes';
import './characterVisualStyles.css';

interface Props {
  state: CharacterState;
  onStateChange: (state: CharacterState) => void;
  onBusyChange?: (busy: boolean) => void;
  disabled?: boolean;
}

const EMPTY_VISUALS: CharacterVisualState = { assets: [], candidates: [], jobs: [], selected_candidate: null, coverage: [], coverage_version: 0, components: {}, sheets: [], current_sheet_version: null, approved_sheet_version: null, decisions: [] };
const COVERAGE_OPTIONS: SheetComponent[] = [
  { id: 'front', label: '정면' }, { id: 'side', label: '측면' }, { id: 'back', label: '뒷모습' },
  { id: 'happy', label: '기쁜 표정' }, { id: 'surprised', label: '놀란 표정' }, { id: 'acting', label: '대표 행동' },
];

function sameCandidate(a: CandidateRef | null, b: CandidateRef | null) { return Boolean(a && b && a.candidate_id === b.candidate_id && a.version === b.version); }
function candidateKey(candidate: CandidateRef) { return `${candidate.candidate_id}:${candidate.version}`; }
function imageUrl(projectId: string, asset?: VisualAsset) { return asset ? visualAssetUrl(projectId, asset.id, asset.url) : undefined; }
function errorText(reason: unknown) { return reason instanceof TypeError ? '서버에 연결하지 못했습니다. 작성한 내용은 보관했습니다.' : reason instanceof Error ? reason.message : '작업을 반영하지 못했습니다. 다시 시도해 주세요.'; }

export default function CharacterVisualWorkspace({ state, onStateChange, onBusyChange, disabled = false }: Props) {
  const visuals = state.visuals || EMPTY_VISUALS;
  const [view, setView] = useState<'candidates' | 'sheet'>(state.stage === 'candidates' ? 'candidates' : 'sheet');
  const [focused, setFocused] = useState<CandidateRef | null>(visuals.selected_candidate);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [targetComponent, setTargetComponent] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [coverageOpen, setCoverageOpen] = useState(false);
  const [coverageDraft, setCoverageDraft] = useState<SheetComponent[]>(visuals.coverage.length ? visuals.coverage : [COVERAGE_OPTIONS[0]]);
  const [customLabel, setCustomLabel] = useState('');
  const active = useRef<AbortController | null>(null);
  const mutationLock = useRef(false);
  const coverageDirty = useRef(false);
  const identity = useRef<{ signature: string; id: string } | null>(null);
  const handlers = useRef({ onStateChange, onBusyChange });
  handlers.current = { onStateChange, onBusyChange };
  const projectId = state.project_id;
  const directionVersion = state.brief?.version || '';

  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    return () => { controller.abort(); handlers.current.onBusyChange?.(false); };
  }, [projectId]);

  useEffect(() => { setView(state.stage === 'candidates' ? 'candidates' : 'sheet'); }, [state.stage]);
  useEffect(() => {
    if (coverageDirty.current) return;
    setCoverageDraft(visuals.coverage.length ? visuals.coverage : [COVERAGE_OPTIONS[0]]);
    setCoverageOpen(false);
  }, [visuals.coverage_version, directionVersion]);

  const assets = new Map(visuals.assets.map(asset => [asset.id, asset]));
  const currentCandidates = visuals.candidates.filter(candidate => candidate.direction_version === directionVersion);
  const latestById = new Map<string, CharacterCandidate>();
  for (const candidate of currentCandidates) latestById.set(candidate.candidate_id, candidate);
  const latestCandidates = [...latestById.values()];
  const focusedCandidate = currentCandidates.find(candidate => sameCandidate(candidate, focused)) || null;
  const draftKey = view === 'sheet' ? `sheet:${targetComponent}` : focusedCandidate ? `candidate:${candidateKey(focusedCandidate)}` : 'new-candidate';
  const draft = drafts[draftKey] || '';
  const selectedCandidate = currentCandidates.find(candidate => sameCandidate(candidate, visuals.selected_candidate)) || null;
  const pendingJobs = visuals.jobs.filter(job => job.status === 'awaiting_image' && job.direction_version === directionVersion);
  const candidateJobs = pendingJobs.filter(job => job.kind !== 'sheet_component');
  const sheetJobs = pendingJobs.filter(job => job.kind === 'sheet_component' && job.coverage_version === visuals.coverage_version && job.candidate_id === selectedCandidate?.candidate_id && job.candidate_version === selectedCandidate?.version);
  const pendingRevision = candidateJobs.some(job => job.kind === 'candidate_revision' && job.candidate_id === focusedCandidate?.candidate_id);
  const selectedRevisionPending = candidateJobs.some(job => job.kind === 'candidate_revision' && job.candidate_id === selectedCandidate?.candidate_id);
  const currentSheet = visuals.sheets.find(sheet => sheet.version === visuals.current_sheet_version);
  const approved = Boolean(state.sheet_approved && currentSheet && visuals.approved_sheet_version === currentSheet.version);
  const locked = disabled || busy;
  const allComponentsReady = visuals.coverage.length > 0 && visuals.coverage.every(component => assets.has(visuals.components[component.id]));

  function setDraft(value: string) { setDrafts(current => ({ ...current, [draftKey]: value })); }

  function common(action: string, payload: unknown): VisualMutation {
    const signature = JSON.stringify({ projectId, revision: state.revision, directionVersion, action, payload });
    if (identity.current?.signature !== signature) identity.current = { signature, id: crypto.randomUUID() };
    return { request_id: identity.current.id, expected_revision: state.revision, expected_direction_version: directionVersion };
  }

  async function mutate(work: (signal: AbortSignal) => Promise<CharacterState>, success: string): Promise<CharacterState | null> {
    const controller = active.current;
    if (!controller || controller.signal.aborted || mutationLock.current || disabled) return null;
    mutationLock.current = true;
    setBusy(true);
    handlers.current.onBusyChange?.(true);
    setError(''); setNotice('');
    try {
      const value = await work(controller.signal);
      if (controller.signal.aborted) return null;
      handlers.current.onStateChange(value);
      identity.current = null;
      setNotice(success);
      return value;
    } catch (reason) {
      if (controller.signal.aborted) return null;
      if (reason instanceof CharacterApiError && reason.status === 409) {
        try {
          const latest = await getCharacter(projectId, controller.signal);
          if (!controller.signal.aborted) handlers.current.onStateChange(latest);
          setError('최신 결과를 불러왔습니다. 입력한 내용은 보관했습니다. 결과를 확인한 뒤 다시 시도해 주세요.');
        } catch { if (!controller.signal.aborted) setError('결과가 변경됐습니다. 입력한 내용은 보관했습니다. 다시 불러온 뒤 확인해 주세요.'); }
      } else setError(errorText(reason));
      return null;
    } finally {
      if (!controller.signal.aborted) {
        mutationLock.current = false; setBusy(false); handlers.current.onBusyChange?.(false);
      }
    }
  }

  async function refresh() {
    await mutate(signal => getCharacter(projectId, signal), '현재 결과를 다시 불러왔습니다.');
  }

  async function createJob(kind: VisualJob['kind'], componentId?: string) {
    if (locked || !directionVersion) return;
    const candidate = kind === 'candidate_revision' ? focusedCandidate : selectedCandidate;
    if (kind !== 'candidate' && !candidate) return;
    const part = visuals.coverage.find(component => component.id === (componentId || targetComponent));
    const instruction = draft.trim() || (kind === 'sheet_component' && part ? `${part.label} 이미지를 준비해 주세요. 선택한 캐릭터의 외형과 고유 특징을 유지해 주세요.` : '');
    const payload = {
      kind, instruction,
      ...(kind !== 'candidate' && candidate ? { candidate_id: candidate.candidate_id, candidate_version: candidate.version } : {}),
      ...(kind === 'sheet_component' ? { component_id: componentId || targetComponent, expected_coverage_version: visuals.coverage_version } : {}),
    };
    const result = await mutate(signal => requestVisualJob(projectId, { ...common('job', payload), ...payload }, signal), '생성 요청을 준비했습니다. 결과 이미지를 가져와 주세요.');
    if (result) { setDraft(''); setTargetComponent(''); }
  }

  async function selectCandidate() {
    if (!focusedCandidate || locked || pendingRevision) return;
    if (sameCandidate(focusedCandidate, visuals.selected_candidate)) { setView('sheet'); return; }
    const payload = { candidate_id: focusedCandidate.candidate_id, candidate_version: focusedCandidate.version };
    await mutate(signal => selectVisualCandidate(projectId, { ...common('select', payload), ...payload }, signal), '선택한 후보를 확인했습니다. 시트 구성을 정해 주세요.');
  }

  async function saveCoverage(event: FormEvent) {
    event.preventDefault();
    if (!selectedCandidate || !coverageDraft.length || locked) return;
    const payload = { candidate_id: selectedCandidate.candidate_id, candidate_version: selectedCandidate.version, components: coverageDraft };
    if (await mutate(async signal => {
      const result = await saveVisualCoverage(projectId, { ...common('coverage', payload), ...payload }, signal);
      coverageDirty.current = false;
      return result;
    }, '시트 구성을 저장했습니다.')) setCoverageOpen(false);
  }

  async function attachCandidate(componentId: string) {
    if (!selectedCandidate || locked) return;
    const payload = { candidate_id: selectedCandidate.candidate_id, candidate_version: selectedCandidate.version, expected_coverage_version: visuals.coverage_version, asset_id: selectedCandidate.asset_id };
    await mutate(signal => attachVisualComponent(projectId, componentId, { ...common('attach', { componentId, ...payload }), ...payload }, signal), '선택한 후보 이미지를 시트에 넣었습니다.');
  }

  async function buildSheet() {
    if (!selectedCandidate || locked || !allComponentsReady || sheetJobs.length || selectedRevisionPending) return;
    const payload = { candidate_id: selectedCandidate.candidate_id, candidate_version: selectedCandidate.version, expected_coverage_version: visuals.coverage_version };
    await mutate(signal => buildVisualSheet(projectId, { ...common('build', payload), ...payload }, signal), '시트 미리보기가 준비됐습니다. 각 이미지를 확인해 주세요.');
  }

  async function decideSheet(reopen: boolean) {
    if (!currentSheet || locked || (!reopen && (sheetJobs.length || selectedRevisionPending))) return;
    const payload = { expected_sheet_version: currentSheet.version };
    const handler = reopen ? reopenVisualSheet : confirmVisualSheet;
    await mutate(signal => handler(projectId, { ...common(reopen ? 'sheet-reopen' : 'sheet-confirm', payload), ...payload }, signal), reopen ? '새 버전으로 시트를 수정할 수 있습니다.' : '캐릭터 시트의 정확한 버전을 확인했습니다.');
  }

  async function upload(job: VisualJob, file: File, provenance: VisualProvenance, fileIdentity: string) {
    const result = await mutate(signal => uploadVisualImage(projectId, job.id, common('upload', { jobId: job.id, fileIdentity, provenance }), file, provenance, signal), '이미지를 가져왔습니다. 결과를 확인해 주세요.');
    if (result && job.kind !== 'sheet_component') {
      const candidate = [...result.visuals.candidates].reverse().find(item => item.candidate_id === job.candidate_id);
      if (candidate) setFocused({ candidate_id: candidate.candidate_id, version: candidate.version });
    }
    return Boolean(result);
  }

  async function cancelJob(job: VisualJob) {
    await mutate(signal => cancelVisualJob(projectId, job.id, common('cancel-job', job.id), signal), '이 생성 요청을 취소했습니다.');
  }

  async function downloadSheet(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    const controller = active.current;
    if (!approved || locked || mutationLock.current || !controller || controller.signal.aborted) return;
    mutationLock.current = true;
    setBusy(true); handlers.current.onBusyChange?.(true); setError(''); setNotice('');
    try {
      const blob = await downloadVisualSheet(projectId, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = 'character-sheet.zip'; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice('확인한 시트의 다운로드를 시작했습니다.');
    } catch (reason) {
      if (controller.signal.aborted) return;
      if (reason instanceof CharacterApiError && reason.status === 409) {
        const latest = await getCharacter(projectId, controller.signal).catch(() => null);
        if (latest && !controller.signal.aborted) handlers.current.onStateChange(latest);
      }
      if (!controller.signal.aborted) setError(errorText(reason));
    } finally {
      if (!controller.signal.aborted) { mutationLock.current = false; setBusy(false); handlers.current.onBusyChange?.(false); }
    }
  }

  const jobs = view === 'candidates' ? candidateJobs : sheetJobs;
  const visibleJobs = new Set(jobs.map(job => job.id));
  const coverageOptions = [...COVERAGE_OPTIONS, ...coverageDraft.filter(component => !COVERAGE_OPTIONS.some(option => option.id === component.id))];

  return <section className="character-visual-workspace" aria-label="캐릭터 이미지 작업" aria-busy={busy}>
    <div className="character-visual-toolbar">
      <div><h2>{view === 'candidates' ? '어떤 모습이 가장 마음에 드나요?' : approved ? '확인한 캐릭터 시트' : '캐릭터 시트를 완성해 볼까요?'}</h2>
        {view === 'sheet' && selectedCandidate ? <span>선택 후보 · v{selectedCandidate.version}{currentSheet ? ` / 시트 v${currentSheet.version}` : ''}</span> : null}</div>
      <div className="character-visual-toolbar-actions">
        {view === 'sheet' ? <button className="character-button subtle" disabled={locked} onClick={() => setView('candidates')}>후보 다시 보기</button>
          : selectedCandidate ? <button className="character-button subtle" disabled={locked} onClick={() => setView('sheet')}>시트로 돌아가기<ArrowRight size={14} aria-hidden="true" /></button> : null}
        <button type="button" className="character-button subtle" disabled={locked} onClick={() => void refresh()} aria-label="이미지 작업 다시 불러오기"><RotateCcw size={14} aria-hidden="true" /></button>
      </div>
    </div>

    {error ? <div className="character-error" role="alert"><CircleAlert size={17} aria-hidden="true" /><p>{error}</p></div> : null}
    <p className="character-visual-notice" role="status">{busy ? '현재 결과에 반영하고 있습니다.' : notice}</p>

    {view === 'candidates' ? <>
      {latestCandidates.length ? <div className="character-candidate-grid" role="group" aria-label="시각 후보">
        {latestCandidates.map((candidate, index) => <button type="button" key={candidateKey(candidate)} className={`character-candidate${sameCandidate(candidate, focused) ? ' selected' : ''}`}
          aria-pressed={sameCandidate(candidate, focused)} disabled={locked} onClick={() => { setFocused({ candidate_id: candidate.candidate_id, version: candidate.version }); setTargetComponent(''); }}>
          <AssetImage projectId={projectId} asset={assets.get(candidate.asset_id)} alt={`캐릭터 후보 ${index + 1}`} />
          <span className="character-candidate-caption"><strong>후보 {index + 1}</strong><span>v{candidate.version}{sameCandidate(candidate, visuals.selected_candidate) ? ' · 확인됨' : ''}</span>{sameCandidate(candidate, focused) ? <Check size={17} aria-hidden="true" /> : null}</span>
        </button>)}
      </div> : <div className="character-visual-empty"><ImagePlus size={32} strokeWidth={1.3} aria-hidden="true" /><p>캐릭터 후보 이미지를 가져와 주세요.</p></div>}

      {focusedCandidate ? <section className="character-selected-preview" aria-label="선택한 후보 자세히 보기">
        <AssetImage projectId={projectId} asset={assets.get(focusedCandidate.asset_id)} alt="현재 살펴보는 캐릭터 후보" />
        <div><span className="character-visual-eyebrow">현재 후보 · v{focusedCandidate.version}</span>
          {focusedCandidate.feedback ? <p>{focusedCandidate.feedback}</p> : null}
          <button type="button" className="character-button primary" disabled={locked || pendingRevision} onClick={() => void selectCandidate()}>
            {sameCandidate(focusedCandidate, visuals.selected_candidate) ? '이 후보의 시트 보기' : '이 후보 확인하고 시트로'}<ArrowRight size={15} aria-hidden="true" />
          </button>
        </div>
      </section> : null}

      <form className="character-visual-composer" onSubmit={event => { event.preventDefault(); void createJob(focusedCandidate ? 'candidate_revision' : 'candidate'); }}>
        <label htmlFor="character-visual-feedback">{focusedCandidate ? '이 후보에서 바꿀 부분' : '새 후보에 반영할 내용'}</label>
        <textarea id="character-visual-feedback" rows={3} maxLength={3000} value={draft} disabled={locked} onChange={event => setDraft(event.target.value)}
          placeholder={focusedCandidate ? '예: 머리 위 잎사귀를 조금 더 작게 해 주세요.' : '확인한 캐릭터 방향을 바탕으로 요청합니다.'} />
        <div className="character-visual-form-actions">
          {focusedCandidate ? <button type="button" className="character-button" disabled={locked} onClick={() => setFocused(null)}><Plus size={14} aria-hidden="true" />새 후보</button> : <span />}
          <button type="submit" className="character-button" disabled={locked || (Boolean(focusedCandidate) && (!draft.trim() || pendingRevision))}>
            {focusedCandidate ? <Pencil size={14} aria-hidden="true" /> : <Plus size={14} aria-hidden="true" />}{focusedCandidate ? '수정 요청 준비' : '후보 요청 준비'}
          </button>
        </div>
      </form>
      {focusedCandidate && currentCandidates.filter(candidate => candidate.candidate_id === focusedCandidate.candidate_id).length > 1 ? <details className="character-visual-history"><summary>이 후보의 수정 전후 보기</summary>
        <div className="character-candidate-history">{currentCandidates.filter(candidate => candidate.candidate_id === focusedCandidate.candidate_id).map(candidate => <button type="button" key={candidateKey(candidate)} className={sameCandidate(candidate, focused) ? 'selected' : ''} disabled={locked} onClick={() => setFocused(candidate)}>
          <AssetImage projectId={projectId} asset={assets.get(candidate.asset_id)} alt={`수정 기록 v${candidate.version}`} /><span>v{candidate.version}</span>
        </button>)}</div>
      </details> : null}
    </> : selectedCandidate ? <>
      {selectedRevisionPending ? <div className="character-sheet-revision-pending" role="status"><span>후보 수정 결과를 확인한 뒤 시트를 완성할 수 있습니다.</span><button type="button" className="character-button subtle" disabled={locked} onClick={() => setView('candidates')}>후보 수정 확인</button></div> : null}
      {approved && currentSheet ? <div className="character-sheet-approved" role="status"><Check size={18} aria-hidden="true" /><span>캐릭터 방향 v{currentSheet.direction_version} · 시트 v{currentSheet.version} 확인됨</span>
        <a className="character-button subtle" href={visualSheetExportUrl(projectId)} download="character-sheet.zip" aria-disabled={locked} onClick={event => void downloadSheet(event)}><Download size={14} aria-hidden="true" />시트 내려받기</a>
        <button className="character-button subtle" type="button" disabled={locked} onClick={() => void decideSheet(true)}><Pencil size={14} aria-hidden="true" />시트 수정</button></div> : null}

      {!approved && (!visuals.coverage.length || coverageOpen) ? <form className="character-coverage-form" onSubmit={saveCoverage}>
        <h3>시트에 넣을 항목</h3>
        <fieldset disabled={locked}><legend className="character-visually-hidden">시트 구성 선택</legend><div className="character-coverage-options">{coverageOptions.map(component => <label key={component.id}>
          <input type="checkbox" checked={coverageDraft.some(item => item.id === component.id)} onChange={event => { coverageDirty.current = true; setCoverageOpen(true); setCoverageDraft(items => event.target.checked ? [...items, component] : items.filter(item => item.id !== component.id)); }} />{component.label}
        </label>)}</div></fieldset>
        <div className="character-coverage-custom"><input aria-label="시트 항목 직접 입력" placeholder="다른 항목 추가" maxLength={120} value={customLabel} disabled={locked || coverageDraft.length >= 16} onChange={event => { coverageDirty.current = true; setCoverageOpen(true); setCustomLabel(event.target.value); }} />
          <button className="character-button subtle" type="button" disabled={locked || !customLabel.trim() || coverageDraft.length >= 16} onClick={() => { coverageDirty.current = true; setCoverageDraft(items => [...items, { id: `custom-${crypto.randomUUID()}`, label: customLabel.trim() }]); setCustomLabel(''); }}><Plus size={14} aria-hidden="true" />추가</button></div>
        <div className="character-visual-form-actions">{visuals.coverage.length ? <button className="character-button" type="button" disabled={locked} onClick={() => { coverageDirty.current = false; setCoverageDraft(visuals.coverage); setCoverageOpen(false); }}>취소</button> : <span />}
          <button className="character-button primary" type="submit" disabled={locked || !coverageDraft.length || coverageDraft.length > 16}>이 구성으로 확인<ArrowRight size={15} aria-hidden="true" /></button></div>
      </form> : null}

      {visuals.coverage.length ? <>
        <div className="character-sheet-grid" aria-label="캐릭터 시트 미리보기">{visuals.coverage.map(component => <article className="character-sheet-cell" key={component.id}>
          <div className="character-sheet-cell-heading"><h3>{component.label}</h3>{assets.has(visuals.components[component.id]) ? <Check size={14} aria-label="이미지 등록됨" /> : <span>이미지 필요</span>}</div>
          <AssetImage projectId={projectId} asset={assets.get(visuals.components[component.id])} alt={`캐릭터 시트 · ${component.label}`} />
          {!approved ? <div className="character-sheet-cell-actions">
            <button type="button" className="character-button subtle" disabled={locked || sheetJobs.some(job => job.component_id === component.id)} onClick={() => setTargetComponent(component.id)}>
              <Pencil size={13} aria-hidden="true" />{assets.has(visuals.components[component.id]) ? '이 부분 수정' : '이미지 요청'}
            </button>
            {!assets.has(visuals.components[component.id]) ? <button type="button" className="character-button subtle" disabled={locked || sheetJobs.some(job => job.component_id === component.id)} onClick={() => void attachCandidate(component.id)}>선택 후보 이미지 사용</button> : null}
          </div> : null}
        </article>)}</div>

        {!approved && targetComponent ? <form className="character-visual-composer" onSubmit={event => { event.preventDefault(); void createJob('sheet_component'); }}>
          <label htmlFor="character-sheet-feedback">{visuals.coverage.find(component => component.id === targetComponent)?.label} · 요청할 내용</label>
          <textarea id="character-sheet-feedback" rows={3} maxLength={3000} value={draft} disabled={locked} onChange={event => setDraft(event.target.value)} placeholder="선택한 캐릭터의 특징을 유지하며 이 항목을 준비해 주세요." />
          <div className="character-visual-form-actions"><button className="character-button" type="button" disabled={locked} onClick={() => setTargetComponent('')}>취소</button><button className="character-button" type="submit" disabled={locked}>생성 요청 준비<ArrowRight size={14} aria-hidden="true" /></button></div>
        </form> : null}

        {!approved ? <div className="character-sheet-final-actions"><button className="character-button" type="button" disabled={locked} onClick={() => setCoverageOpen(true)}>구성 변경</button>
          {currentSheet ? <button className="character-button primary" type="button" disabled={locked || sheetJobs.length > 0 || selectedRevisionPending || !allComponentsReady} onClick={() => void decideSheet(false)}>이 시트 최종 확인<Check size={15} aria-hidden="true" /></button>
            : <button className="character-button primary" type="button" disabled={locked || !allComponentsReady || sheetJobs.length > 0 || selectedRevisionPending} onClick={() => void buildSheet()}>시트 미리보기 완성<ArrowRight size={15} aria-hidden="true" /></button>}
        </div> : null}
      </> : null}

      {visuals.sheets.length > 0 ? <details className="character-visual-history"><summary>시트 버전 기록 ({visuals.sheets.length})</summary><ul>{[...visuals.sheets].reverse().map(sheet => <li key={sheet.version}>v{sheet.version} · {sheet.coverage.map(component => component.label).join(' · ')}{sheet.version === visuals.approved_sheet_version ? ' · 확인됨' : sheet.version === visuals.current_sheet_version ? ' · 현재' : ''}</li>)}</ul></details> : null}
    </> : <div className="character-visual-empty"><p>먼저 캐릭터 후보를 확인해 주세요.</p><button className="character-button" onClick={() => setView('candidates')}>후보 보기</button></div>}

    {pendingJobs.length ? <section className="character-visual-jobs" aria-label="이미지 가져오기" hidden={!jobs.length}>{pendingJobs.map((job, index) => <JobUpload key={job.id} job={job} index={index} componentLabel={visuals.coverage.find(component => component.id === job.component_id)?.label} assets={assets} projectId={projectId} disabled={locked} hidden={!visibleJobs.has(job.id)} onUpload={upload} onCancel={cancelJob} />)}</section> : null}
  </section>;
}

function AssetImage({ projectId, asset, alt }: { projectId: string; asset?: VisualAsset; alt: string }) {
  const url = imageUrl(projectId, asset);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return url && failedUrl !== url ? <img className="character-visual-image" src={url} alt={alt} loading="lazy" onError={() => setFailedUrl(url)} />
    : <div className="character-visual-image missing"><ImagePlus size={26} strokeWidth={1.3} aria-hidden="true" /><span>{url ? '이미지를 불러오지 못했습니다.' : '이미지 없음'}</span></div>;
}

interface JobUploadProps {
  job: VisualJob; index: number; componentLabel?: string; assets: Map<string, VisualAsset>; projectId: string; disabled: boolean; hidden?: boolean;
  onUpload: (job: VisualJob, file: File, provenance: VisualProvenance, fileIdentity: string) => Promise<boolean>;
  onCancel: (job: VisualJob) => Promise<void>;
}

function JobUpload({ job, index, componentLabel, assets, projectId, disabled, hidden = false, onUpload, onCancel }: JobUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fileIdentity, setFileIdentity] = useState('');
  const [source, setSource] = useState<VisualProvenance['source']>('user_upload');
  const [model, setModel] = useState('');
  const [prompt, setPrompt] = useState('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const inputId = `visual-image-${job.id}`;
  const label = job.kind === 'candidate_revision' ? '후보 수정' : job.kind === 'sheet_component' ? componentLabel || '시트 항목' : '새 후보';

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || disabled) return;
    if (file.size > 16 * 1024 * 1024) { setError('이미지는 16MB 이하로 가져와 주세요.'); return; }
    const provenance: VisualProvenance = {
      source, model: model.trim() || null, workflow: null, prompt: prompt.trim() || null, seed: null,
      unknowns: [...(!model.trim() ? ['model'] : []), ...(!prompt.trim() ? ['prompt'] : []), 'workflow', 'seed'], fixture: false,
    };
    if (await onUpload(job, file, provenance, fileIdentity)) { setFile(null); setError(''); }
  }

  async function copyPrompt() {
    try { await navigator.clipboard.writeText(job.prompt); setCopied(true); }
    catch { setError('요청문을 복사하지 못했습니다. 아래 요청문을 직접 선택해 복사해 주세요.'); }
  }

  return <article className="character-visual-job" hidden={hidden}>
    <div className="character-visual-job-heading"><h3>{label} · 이미지 가져오기{job.kind !== 'sheet_component' && index ? ` ${index + 1}` : ''}</h3><button type="button" className="character-button subtle" disabled={disabled} onClick={() => void onCancel(job)} aria-label={`${label} 요청 취소`}><X size={14} aria-hidden="true" />취소</button></div>
    {job.instruction ? <p className="character-job-instruction">{job.instruction}</p> : null}
    <details className="character-generation-request"><summary>생성 요청 보기·복사</summary><p>요청문과 기준 이미지를 Codex에 전달한 뒤 결과를 가져오세요.</p>
      <button type="button" className="character-button subtle" onClick={() => void copyPrompt()}><Copy size={13} aria-hidden="true" />{copied ? '복사됨' : '요청문 복사'}</button>
      <textarea readOnly value={job.prompt} rows={7} aria-label="이미지 생성 요청문" />
      {job.source_asset_ids.length ? <div className="character-job-source-images">{job.source_asset_ids.map((id, imageIndex) => { const asset = assets.get(id); const url = imageUrl(projectId, asset); return url ? <a key={id} href={url} download={`character-source-${imageIndex + 1}.png`}><img src={url} alt={`이미지 생성 기준 ${imageIndex + 1}`} /><span><Download size={12} aria-hidden="true" />기준 이미지 {imageIndex + 1}</span></a> : <span key={id}>기준 이미지 파일을 확인해 주세요.</span>; })}</div> : null}
    </details>
    <form onSubmit={submit}>
      <label className="character-visual-file" htmlFor={inputId}><Upload size={18} aria-hidden="true" /><span>{file?.name || '결과 이미지 선택'}</span><input type="file" id={inputId} accept="image/png,image/jpeg,image/webp" disabled={disabled} onChange={event => { setFile(event.target.files?.[0] || null); setFileIdentity(crypto.randomUUID()); setError(''); }} /></label>
      <div className="character-visual-import-row"><label>이미지 출처<select value={source} disabled={disabled} onChange={event => setSource(event.target.value as VisualProvenance['source'])}><option value="user_upload">직접 가져온 이미지</option><option value="codex_imagegen">Codex에서 생성한 이미지</option></select></label>
        <button type="submit" className="character-button primary" disabled={disabled || !file}>{disabled ? <LoaderCircle size={14} className="character-spin" aria-hidden="true" /> : <Upload size={14} aria-hidden="true" />}이미지 반영</button></div>
      <details className="character-visual-provenance"><summary>생성 정보 추가 · 선택</summary><label>사용 모델<input value={model} disabled={disabled} maxLength={200} onChange={event => setModel(event.target.value)} placeholder="알고 있는 경우만 입력" /></label><label>실제로 사용한 요청문<textarea value={prompt} disabled={disabled} maxLength={20000} rows={3} onChange={event => setPrompt(event.target.value)} placeholder="알고 있는 경우만 입력" /></label></details>
      {error ? <p className="character-edit-error" role="alert">{error}</p> : null}
    </form>
  </article>;
}
