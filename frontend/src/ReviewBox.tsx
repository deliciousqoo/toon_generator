import { Check, MessageSquare, RotateCcw, ShieldCheck, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Artifact, Decision, Gate } from './types';
import { Approval, Version } from './ui';
export default function ReviewBox({ artifact, gate, busy, onReview, compact = false, canApprove = true }: { artifact: Artifact; gate: Gate; busy: boolean; onReview: (artifact: Artifact, gate: Gate, decision: Decision, notes: string) => Promise<boolean>; compact?: boolean; canApprove?: boolean }) {
  const [notes, setNotes] = useState('');
  const [decision, setDecision] = useState<Decision | null>(null);
  const reviewed = ['approved', 'rework', 'rejected'].includes(artifact.approval?.status ?? '');
  useEffect(() => { setDecision(null); setNotes(''); }, [artifact.artifact_id, artifact.version]);
  async function submit() { if (decision && await onReview(artifact, gate, decision, notes)) { setDecision(null); setNotes(''); } }
  return <section className={`review-box ${compact ? 'compact' : ''}`}><div className="review-heading"><span className="review-symbol"><ShieldCheck size={19} /></span><div><h3>{gate} · {{ RG: '레퍼런스 검토', CG: '캐릭터 검토', SG: '시리즈 검토', G2: '콘티 검토', G3: '초안 검토' }[gate]}</h3><p>{gate === 'G2' ? '컷의 흐름과 대사를 확인한 뒤 초안으로 진행하세요.' : gate === 'G3' ? '선택한 초안과 전체 배치를 직접 검토하세요.' : '현재 버전의 설정과 사용 근거를 직접 확인하세요.'}</p></div><div className="review-status"><Version artifact={artifact} /><Approval artifact={artifact} /></div></div>
    {reviewed ? <p className="micro review-completed">현재 버전의 검토가 기록되었습니다. 다시 검토하려면 수정 또는 재생성한 새 버전을 저장하세요.</p> : <><div className="review-choices"><button disabled={busy || !canApprove} className={decision === 'approved' ? 'selected green' : ''} onClick={() => setDecision('approved')}><Check size={15} />승인</button><button disabled={busy} className={decision === 'rework' ? 'selected orange' : ''} onClick={() => setDecision('rework')}><RotateCcw size={15} />수정 요청</button><button disabled={busy} className={decision === 'rejected' ? 'selected red' : ''} onClick={() => setDecision('rejected')}><X size={15} />반려</button></div>{!canApprove && <p className="micro review-completed">모든 컷의 후보를 선택하면 승인할 수 있습니다. 수정 요청과 반려는 지금도 기록할 수 있습니다.</p>}
    {decision && <div className="review-compose"><label className="sr-only" htmlFor={`notes-${gate}`}>검토 메모</label><textarea id={`notes-${gate}`} placeholder="검토 근거, 수정할 부분 또는 승인 메모를 남겨주세요." value={notes} onChange={e => setNotes(e.target.value)} rows={2} /><button className="button dark" disabled={busy || decision === 'approved' && !canApprove} onClick={submit}><MessageSquare size={15} />{decision === 'approved' ? '현재 버전 승인 기록' : '검토 결정 기록'}</button><p className="micro">이 결정은 현재 버전에만 적용됩니다. 수정 후에는 다시 검토합니다.</p></div>}</>}
  </section>;
}
