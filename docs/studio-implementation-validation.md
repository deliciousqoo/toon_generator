# Stage 04 첫 기술 구현 검증 기록

기준일: 2026-10-14. 권한: D-0035와 사용자의 중단 후 계속 진행 지시. 범위: [P0 기준](p0-implementation-baseline.md)의 합성 기술 슬라이스. 실제 모델 호출, 실제 캐릭터/에피소드, 그림 품질과 게시 수락을 검사한 기록이 아니다.

## 구현된 경로와 기술

| 위치 | 실제 사용/구현 | 증명 범위 |
|---|---|---|
| 작업 화면 | React 19.1.1, TypeScript 5.9.3, Vite 7.1.12 | 흰색 단일 작업면, 최소 프로젝트, 이야기 우선, 현재 단계·진행·의견·과거 버전, 완료 후 재작업 |
| API/계약 | FastAPI 0.143.0, Pydantic 2.14.1, JSON Schema 2020-12 | additive `/api/studio`, `toon-studio-contract-v2` 2.0.0, 기존 v1 보존, 정확 source versions와 revision 충돌 |
| 오케스트레이터 | LangGraph 1.2.15, checkpoint-sqlite 3.1.2 | SqliteSaver + `interrupt`/`Command` 사람 정지·재개, 로컬 이벤트/버전, 제한된 역할 실행, 프로세스 재시작 복구 |
| 생성/평가/검증 | story_generator, storyboard_planner, 독립 evaluator 지시, 결정론적 validator | 정확 역할 입력, 분리된 기준·근거·위치와 평가 artifact, 제한된 재작성, 부분 수정, 창작 자기 승인 없음 |
| 모델 어댑터 | HTTPX 0.28.1 + Ollama JSON 프로토콜 코드 | 기본 fixture 및 fake-provider로 흐름 검증. 실제 Ollama 모델 호출·추론 위치·품질은 미검증 |
| 시각 산출물 | 개발용 텍스트 fixture | 실제 시각 콘티, Stage 05 이미지, ComfyUI·ControlNet·IP-Adapter·Krita 사용 증거 아님 |
| 개발 보조 스킬 | build-agents, react-best-practices, verification | Codex 개발/검토 보조에 사용. 제품 내부 플러그인으로 설치한 것이 아님 |

구현 API는 설치된 패키지와 공식 문서를 대조했다. LangGraph의 사람 정지·재개는 [interrupt 안내](https://docs.langchain.com/oss/python/langgraph/interrupts), 지속성 구조는 [persistence 안내](https://docs.langchain.com/oss/python/langgraph/persistence)를 참조했다. Ollama의 JSON 응답/입력 방식은 [generate API](https://docs.ollama.com/api/generate)와 [structured outputs](https://docs.ollama.com/capabilities/structured-outputs)를 확인했다. 이 문서 참조는 모델 실행 결과가 아니다.

## 검증 결과

- 기존 플랫폼 API·백업·저장·렌더·런처 검사: 43개 및 25개 subtest 통과.
- 최초 전체 통합: 65개 및 25개 subtest 통과. 이후 브라우저 검토에서 완료 후 수정 경로가 닫혀 있음을 발견하고 보완했다.
- 보완한 하네스 코어: 29개 통과. 완료 후 재시작·부분 콘티 재작업, 완료 후 이야기 재작성과 선행 확인, 저장된 미래 schema/등록 ID 불일치/다른 프로젝트의 설정 자료 차단을 포함한다.
- 최종 전체 통합: **76개 및 25개 subtest 통과**(48.81초). 검사 내용: 사람 지점 복구, 중복/오래된 확인 차단, 프로젝트 격리, 정확한 source 참조, 평가 근거, 자동 수정/기술 retry, 실패/반려/실행 중 중단, 완료 후 재작업, schema 문서와 실제 계약의 일치. 미래 계약의 대기 작업은 제공자 호출 전에 멈추며 HTTP 오류에 원본 값을 노출하지 않는다.
- 최종 diff 검토에서 발견한 legacy 백업/신규 artifact의 고정 app_version은 공유 `APP_VERSION` 0.2.0으로 정합화했다. 기존 기록의 버전과 v1 계약/패키지 버전은 바꾸지 않았다. 보완 후 관련 legacy 검사 **31개 및 25개 subtest 통과**(58.65초).
- Python runtime 56개 핀과 설치 metadata가 모두 일치한다. studio v2 JSON Schema 검사를 통과했고 코드에서 내보낸 schema와 검사로 대조했다.
- 최종 TypeScript 검사와 Vite production build 통과. v1 legacy 화면은 `?legacy=1`에 보존하고 지연 로딩한다.

```powershell
.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=30 --basetemp .test-data/studio-storage-gates-20261014 tests
pnpm --dir frontend run build
.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=30 --basetemp .test-data/studio-legacy-metadata-20261014 tests/test_backup.py tests/test_storage_schema.py tests/test_platform.py
```

Windows 샌드박스 안의 TestClient 검사는 앱 로직 진입 전에 asyncio loopback socketpair 생성에서 대기했다. stack trace로 구분하고 제한된 합성 임시 데이터의 검사를 샌드박스 밖에서 실행했다. Vite도 샌드박스 realpath 제한을 피해 빌드했다. 앱의 실제 loopback 경계와 CSRF 동작은 검증에서 유지했다.

## 브라우저 → API → SQLite → 화면

소유한 검증 프로세스를 `127.0.0.1:8877`와 전용 `.test-data` 저장소로 실행했다. 기존 사용자 저장소는 이 검증에 사용하지 않았다.

| 사용자 행동 | 관찰한 결과 |
|---|---|
| 세 항목 프로젝트 생성, 가상의 이야기 입력 | 현재 역할 요약·진행 상태 → 이야기 결과와 사람 대기 |
| 이야기 대사 수정 | 새 이야기 버전, 나머지 action/payoff 보존, 의견 기록 |
| 이야기 확인 후 프로세스 종료·재시작 | 확인된 이야기와 컷 구성 대기가 복구됨 |
| 형식 확인 | 이야기/형식 정확 버전에 연결된 컷 데이터 생성 |
| 둘째 컷 대사만 수정 | 새 보드 버전, 첫째/셋째 컷과 이야기/형식 보존; SQLite 값도 직접 확인 |
| 합성 흐름 확인 | `technical_review_complete=true`, `generation_ready=false`, `creative_quality_verified=false`, `G2` 기록 없음 |
| 완료 후 컷 수정·다시 확인 | 이전 완료 결과/결정 보존, 새 보드 버전과 재확인 |
| 완료 후 이야기부터 수정 | 새 이야기 검토로 복귀, 형식/보드 현재 결과 제거, 기존 버전/결정 보존 |

최종 화면의 콘솔 error/warning은 없었다. 서버에서는 성공한 작업을 local checkpoint/version DB로 보존했다. 이 관찰은 기본 deterministic fixture 경로에 대한 것이다.

## 남은 작업

1. P1 모델 실행 조건을 구체화하고 합성 이야기/평가/시각 러프 품질을 비교한다. loopback 연결만으로 실제 추론 위치를 추정하지 않는다. 이미지 모델과 목표 PC는 현재 PC 기준으로 결정하지 않는다.
2. 전용 캐릭터 대화·후보·수정·바이블/시트 UI, 실제 시트 coverage 및 사람 선택을 구현한다. 현재 선행 합성 package는 이 단계를 대체하지 않는다.
3. format 대안/컷 합치기·나누기, richer text/beat mapping과 시각 renderer를 확장한다. 실제 시각 요건을 충족한 콘티만 G2로 확인한다.
4. 정확 G2를 소비하는 Stage 05 이미지 생성·선택/부분 재생성과 Stage 06 검수로 확대한다.
5. studio v2 버전/체크포인트/결정을 포함하는 전체 백업·복원·PC 이동을 통합한다. 현재 기존 v1 백업 통과가 이를 증명하지 않는다.

첫 기술 슬라이스 통과를 제품 전체 또는 창작 품질 완성으로 기록하지 않는다.
