import { cloneElement, isValidElement, useEffect, useId, useRef } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { Check, Clock3, GitBranch, LoaderCircle, X } from 'lucide-react';
import type { Artifact } from './types';
export function Pill({ children, color = 'neutral' }: { children: ReactNode; color?: 'neutral' | 'green' | 'orange' | 'red' }) { return <span className={`pill ${color}`}>{children}</span>; }
export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  const id = useId(); const labelId = `${id}-label`; const hintId = `${id}-hint`; const controlId = `${id}-control`;
  const directControl = isValidElement(children) && typeof children.type === 'string' && ['input', 'textarea', 'select'].includes(children.type);
  const control = isValidElement(children) ? cloneElement(children as ReactElement<{ id?: string; 'aria-labelledby'?: string; 'aria-describedby'?: string; role?: string }>, { id: controlId, 'aria-labelledby': labelId, ...(hint ? { 'aria-describedby': hintId } : {}), ...(!directControl ? { role: 'group' } : {}) }) : children;
  return <div className="field"><label id={labelId} htmlFor={directControl ? controlId : undefined}>{label}</label>{control}{hint && <small id={hintId}>{hint}</small>}</div>;
}
export function Busy({ text = '작업 중' }: { text?: string }) { return <span className="busy"><LoaderCircle size={16} className="spin" />{text}</span>; }
export function Empty({ icon, title, children, action }: { icon?: ReactNode; title: string; children: ReactNode; action?: ReactNode }) { return <div className="empty-state"><div className="empty-icon">{icon ?? <GitBranch size={28} />}</div><h3>{title}</h3><p>{children}</p>{action}</div>; }
export function Version({ artifact }: { artifact: Artifact | null | undefined }) { return artifact ? <Pill><GitBranch size={12} />v{artifact.version}</Pill> : null; }
export function Approval({ artifact }: { artifact: Artifact | null | undefined }) { const status = artifact?.approval?.status; const approved = status === 'approved'; const rejected = status === 'rejected'; return <Pill color={approved ? 'green' : rejected ? 'red' : 'orange'}>{approved ? <Check size={12} /> : <Clock3 size={12} />}{approved ? '승인됨' : rejected ? '반려됨' : status === 'rework' ? '수정 요청됨' : '검토 대기'}</Pill>; }
export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const titleId = useId(); const panel = useRef<HTMLElement>(null); const close = useRef(onClose); close.current = onClose;
  useEffect(() => { const previous = document.activeElement as HTMLElement | null; const el = panel.current; if (!el) return; const focusable = () => Array.from(el.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]')); focusable()[0]?.focus(); function keydown(event: KeyboardEvent) { if (event.key === 'Escape') { event.preventDefault(); close.current(); } else if (event.key === 'Tab') { const items = focusable(); const first = items[0]; const last = items[items.length - 1]; if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); } } } el.addEventListener('keydown', keydown); const scroll = document.body.style.overflow; document.body.style.overflow = 'hidden'; return () => { el.removeEventListener('keydown', keydown); document.body.style.overflow = scroll; previous?.focus(); }; }, []);
  return <div className="modal-backdrop" onClick={onClose}><section ref={panel} className="modal" role="dialog" aria-modal="true" aria-labelledby={titleId} onClick={e => e.stopPropagation()}><div className="modal-head"><h2 id={titleId}>{title}</h2><button className="icon-button" type="button" aria-label="닫기" onClick={onClose}><X size={20} /></button></div>{children}</section></div>;
}
export function localDate(value: string): string { return new Date(value).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
export function textValue(value: string | string[] | undefined): string { return Array.isArray(value) ? value.join(', ') : value ?? ''; }
export const artifactNames: Record<string, string> = { project_brief: '프로젝트 설정', reference_research: '레퍼런스', character_package: '캐릭터', account_strategy: '시리즈 방향', episode_brief: '에피소드 입력', storyboard_package: '콘티', image_generation_run_manifest: '이미지 초안', asset_record: '파일 자료' };
export const decisionNames: Record<string, string> = { approved: '승인', rework: '수정 요청', rejected: '반려', pending: '검토 대기', awaiting_human: '검토 대기' };
