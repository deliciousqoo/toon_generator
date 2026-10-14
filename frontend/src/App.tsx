import { lazy, Suspense } from 'react';
import StudioWorkspace from './StudioWorkspace';

const LegacyApp = lazy(() => import('./LegacyApp'));

export default function App() {
  if (new URLSearchParams(window.location.search).get('legacy') === '1') {
    return <Suspense fallback={<p className="studio-loading">이전 작업 화면을 불러오는 중입니다.</p>}><LegacyApp /></Suspense>;
  }
  return <StudioWorkspace />;
}
