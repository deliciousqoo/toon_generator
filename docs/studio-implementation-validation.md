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

## 2026-10-18 캐릭터 방향 대화 구현

D-0036에 따라 기본 화면을 캐릭터부터 시작하는 흐름으로 바꿨다. 현재 구현은 외형·성격·원하는 느낌을 순서대로 보완하고 방향 카드를 수정·확인하는 단계다. 이미지 후보와 시트는 연결 대기이며, 실제 모델은 호출하지 않았다. 이전 이야기 합성 화면은 `?storyFixture=1`에서 유지한다.

- 최종 전체 Python 검사: **104개 및 25개 subtest 통과**(47.23초). 캐릭터 전용 26개와 API 통합 2개를 포함하며, 나머지 기존 회귀 검사도 통과했다.
- TypeScript 검사와 Vite production build 통과. 여러 TSX 변경에 React 품질 체크리스트를 적용했다.
- 별도 프로세스 `127.0.0.1:8878`, 전용 저장소 `.test-data/character-preview-20261018`에서 브라우저로 입력 → 추가 질문 → 방향 카드 → 성격만 직접 수정 → 확인 → 수정 단계 복귀를 진행했다.
- 수정 후 외형·느낌이 보존되고 `v1.0.4`가 생성됨을 화면과 SQLite에서 대조했다. 프로세스를 종료·재시작하고 페이지를 새로고침한 뒤 대화·수정 내용·4개 방향 버전이 복원됐다.
- 방향 확인은 `direction_confirmed=true`만 만든다. `visual_ready=false`, `sheet_approved=false`를 유지하고 새 캐릭터 프로젝트의 이야기 실행은 409로 차단한다.
- 중복 요청 재생, 오래된 확인·다른 프로젝트 차단, 제공자 범위/계약 불일치와 오래된 미완료 작업을 모델 호출 전에 격리하는 동작을 검사했다. 격리해도 원래 작업 자료와 새 방향·확인 이력은 보존한다.
- 격리된 확정 상태에서 수정 단계 복귀 → 차단 사항 해소 전 확인 거부 → 새 입력·재평가 → 새 버전 확인까지 검사했다. 첫 메시지의 응답 유실 후 재조회에서는 저장된 최초 복구 초안만 정리하도록 프런트엔드를 보완하고 코드 검토·빌드를 마쳤다. 최종 브라우저 console error/warning은 없었다.

```powershell
.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=30 --basetemp .test-data/character-reviewed-20261018 tests
pnpm --dir frontend run build
```

테스트는 가상의 재료와 결정론적 worker로 수행했다. 이 결과는 자연어 이해·레퍼런스 이미지 분석·캐릭터 독창성·생성 화질을 검증하지 않는다. 실제 제공자 권고와 제안 한도는 [모델 연결 권고안](character-model-evaluation.md)에 있으며 OpenAI 어댑터·비용 예약 장부는 후속 작업이다. 캐릭터 상태·체크포인트를 포함하는 v2 전체 백업도 이번 검증에 포함하지 않았다.

## 2026-10-18 ChatGPT Pro 구독 연결

D-0037과 사용자의 실제 연결·대화 검증 요청에 따라 기본 캐릭터 제공자를 `chatgpt_subscription`으로 연결했다. 위의 결정론적 검증과는 별도 기록이다. 유료 API 키, 다른 앱의 로그인 정보, 제공자 자동 전환은 사용하지 않았다. `--character-fixture`를 명시한 경우에만 오프라인 제공자를 사용한다.

- 사용자가 OpenAI 동의 화면을 완료했다. 앱 자체의 OAuth state·PKCE·nonce·발급 client ID·JWT 서명/신원을 검증하고 계정별 모델 7개를 조회했다. 실제 선택 모델은 `gpt-6.1-sol`이며 reasoning effort나 service tier는 별도 지정하지 않았다.
- 브라우저에서 Toon Studio의 플랜 사용 허용 ON, 한도 후 추가 크레딧 사용 OFF, 자동 충전 OFF를 직접 확인했다. 이는 해당 시점 계정 설정의 관찰이다. 앱이 그 설정을 조회·잠금하는 공식 API를 구현한 것으로 표현하지 않는다.
- 인증 정보는 검증 전용 데이터 루트의 `private/chatgpt/session.bin`에 Windows DPAPI로 암호화되어 저장된다. 자격 증명·계정의 원본 식별자·OAuth 코드를 UI, 로그, Git에 남기지 않는다.
- 초기 실제 요청에서 HTTP 200 응답의 Content-Type이 누락되고 SSE 본문이 도착하는 동작을 관찰했다. 또 `response.output_text.delta`와 `response.output_text.done`이 일치해도 `response.completed`의 output이 비어 있는 경우를 관찰했다. 원문 대신 구조·길이·일치 여부만 내부 실패 메타데이터에 남겨 진단했다. 완료 이벤트와 구조 검증을 통과하지 못한 요청은 방향 버전을 생성하지 않았다.
- terminal output이 정확히 빈 배열인 경우에는 완료된 assistant `response.output_item.done`, `response.output_text.done`, delta의 내용·항목 ID·output/content index가 모두 일치하고 전체 응답 status가 명시적 completed일 때만 복원한다. terminal 본문이 있는 경로는 그 본문을 대조한다. 중단되거나 미완료인 조각만으로 결과를 만들지 않는다.
- 실제 브라우저에서 외형만 입력 → 성격 질문 → 성격 반영 → 느낌 질문 → 느낌 반영 → 성격만 직접 수정 → 정확 `v1.0.4` 확인 → 수정 단계 복귀를 완료했다. SQLite에서 외형·느낌·말투·특징 목록·레퍼런스의 값이 부분 수정 전후 동일하고 성격만 지정한 값으로 바뀌었음을 대조했다. 4개 버전, 18개 메시지, 2개 결정이 보존됐고 시각/시트 완료 플래그는 모두 false였다.
- 서버를 최종 비동기 요청 코드로 재시작하고 페이지를 불러온 뒤 상태 payload의 SHA-256, 버전·메시지·결정·호출 수가 모두 이전과 같음을 확인했다. 복구 과정에서 추가 모델 호출은 없었다. 이어 실제 대화로 말투만 추가해 `v1.0.5`를 만들고 다른 항목이 동일한지 DB로 대조한 뒤 방향을 확인했다. 최종 5개 버전, 20개 메시지, 3개 결정, 15회 시도이며 `direction_confirmed=true`, `visual_ready=false`, `sheet_approved=false`다. 초기 거부된 5회도 시도 수에 포함된다.
- 한도 초과 뒤 연결 끊김, 재시작 후 정지 유지, 계정·모델 변경, 프로젝트별 40회 상한, 역할 호출 중 중단, 부분 스트림·잘못된 JSON·잘못된 버전은 모의 HTTP와 로컬 DB로 검사한다. 실제 구독 한도를 소진하는 검사는 수행하지 않는다.
- 연결·한도 실패가 HTTP 200의 blocked 상태로 반환돼도 새로운 방향 버전이 없으면 대화 입력과 직접 수정값을 유지하도록 보완했다. 미전송 초안의 새로고침 복구는 이번 범위에 포함하지 않았다.
- 독립 검토에서 찾은 세 가지 경계를 보완했다. HTTP 401·429 헤더를 받는 즉시 정지를 저장하고, terminal 본문이 있어도 명시적 응답 완료와 assistant 메시지를 확인한다. `AsyncClient` 요청은 남은 총 시간의 `asyncio.timeout` 안에서 실행하며 읽기별 타이머가 연장되는 문제를 막았다. 실제 시간 초과 시 스트림 취소·정리와 요청 1회만 발생함을 모의 스트림으로 검증했다. 실제 서버에서 재시작 후 두 역할의 후속 대화도 성공했다.
- 최종 전체 Python 검사: **250개 및 25개 subtest 통과**(49.97초). 구독 제공자 Mock 109개, OAuth 33개, 앱 통합 2개와 캐릭터/기존 회귀 검사를 포함한다. TypeScript `tsc -b`와 Vite production build도 통과했다. 최종 확인 상태로 한 번 더 재시작한 뒤 payload hash와 15회 시도 수가 그대로임을 확인했다.

```powershell
.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=30 --basetemp .test-data/subscription-release-20261018 tests
```

프로토콜은 [Sign in with ChatGPT](chatgpt-subscription-guide.md)의 공식 문서와 [Responses 스트리밍 이벤트](https://developers.openai.com/api/reference/resources/responses/streaming-events)를 대조했다. 이미지 후보·캐릭터 시트·레퍼런스 이미지 분석·전체 v2 백업은 이 연결 검증의 완료 범위가 아니다.

## 2026-10-18 시각 후보 수정과 캐릭터 시트

D-0038과 사용자의 **Codex 이미지 생성 + 앱 반영** 선택에 따라 실제 가상 캐릭터 이미지로 검증했다. 앱 안에서 자동 이미지 모델을 호출하는 기능은 아니다. 기존 방향 `v1.0.5`를 사용했고 이미지 작업 동안 구독 텍스트 호출 수는 15회로 유지됐다. 유료 API 키·자동 제공자 전환은 사용하지 않았다.

| 단계 | 브라우저와 저장 자료에서 확인한 결과 |
|---|---|
| 후보 준비·가져오기 | 실제 Codex 생성 A/B를 각각 요청에 등록하고 비교했다. 이미지 출처와 실제 실행 프롬프트를 기록했다. |
| 후보 수정 | 사용자가 B를 선택했다. 잔질감·명암을 줄인 B 수정본을 별도 `v1.0.2`로 등록했고 원본 후보를 보존했다. |
| 시트 구성 | 사용자가 수정본 B와 정면·측면·뒷모습·기쁜 표정의 기본 4항목을 선택했다. 정면은 선택 이미지 재사용, 나머지는 별도 생성·등록했다. |
| 시트 검토 | 네 이미지로 시트 `v1.0.1`을 구성했다. 방향·후보 선택과 최종 시트 확인은 별도 결정이다. |
| 부분 수정 | 기쁜 표정의 입만 줄인 이미지를 요청·등록해 시트 `v1.0.2`를 만들었다. DB에서 해당 자산 ID만 변경되고 다른 3개 ID·체크섬과 이전 시트 객체는 동일함을 확인했다. 수정 대기 중 최종 확인이 잠겼다. |
| 재시작 복구 | 세 항목 생성 대기 상태에서 한 번, 시트 부분 수정 대기에서 한 번 프로세스를 재시작했다. 상태 payload SHA-256·선택·요청·시트·텍스트 호출 수가 정확히 일치했고 추가 생성은 없었다. |
| 연결 갱신 | 재시작으로 CSRF 세션이 바뀐 상태의 업로드는 안내와 함께 멈췄다. 선택 파일·출처·프롬프트를 보존했고 명시적 재클릭으로 한 번 등록됐다. |

사용자가 시트 `v1.0.2`를 최종 확인했다. 브라우저에서 해당 정확 버전을 확인으로 저장한 뒤 `stage=complete`, `sheet_approved=true`, `approved_sheet_version=1.0.2`와 사람의 확인 기록을 DB로 대조했다. 방향은 `v1.0.5`, 선택한 B 후보는 `v1.0.2`, 구성은 정면·측면·뒷모습·기쁜 표정이다.

완료 화면의 **시트 내려받기**로 실제 ZIP을 내려받았다. 문서 3개와 PNG 6개(현재 시트 4개와 수정 원본 2개), 총 9개 항목의 CRC·이미지 디코딩·바이트 크기·SHA-256·원본 참조를 독립적으로 대조했다. 선택하지 않은 A 후보는 제외됐고 모든 원본 참조가 ZIP 안에서 해결된다. 다운로드 사본의 SHA-256은 `be6d81e52baa4767a6dd3ec7c8bcb72e438b1159e69b99cb16856970275ef9d6`다. 이 기록은 해당 시트 내보내기 검증이며 전체 프로젝트 복원 검증은 아니다.

최종 확인 후 한 번 더 서버를 재시작하고 화면을 다시 불러왔다. 승인 상태·revision 33·전체 상태 payload SHA-256이 정확히 일치했고 텍스트 호출 수는 15회로 유지됐다. 최종 브라우저 console error/warning은 없었다. 사용자가 명시 승인한 구현 커밋 `6256a92`는 `origin/main`에 푸시하고 원격 커밋 ID 일치를 확인했다.

실제 built-in 이미지 생성은 **7회/상한 8회**다. 원본 결과는 로컬 `.test-data/visual-assets-20261018`, 앱의 정규화된 PNG와 체크섬은 미리보기 저장소에 보관한다. 모델·시드·정확한 도구 버전은 도구에서 제공하지 않아 미상으로 남겼다. 추천 요청과 실제 실행 요청은 구분했다. 생성 이미지의 시각 일관성은 직접 확인했지만 입 외 픽셀의 완전한 동일성이나 창작 권리 검수를 증명하지 않는다.

검증 과정에서 Windows의 260자 초과 이미지 경로가 실패하는 문제를 찾아 파일 경로를 줄이고 Windows 파일 I/O의 확장 경로를 적용했다. 기존 이미지 위치를 이동하지 않고 이전 경로 읽기도 유지했다. 긴 경로의 실제 저장·읽기와 이전 배치 호환 회귀 검사를 추가했다.

- 최종 전체 Python 검사: **275개 및 25개 subtest 통과**(62.52초). 시각 전용 25개는 잘못된 파일/소유권·fixture 우회·오래된 방향/후보/구성/시트·중복/동시 업로드·부분 수정·누락/변조·정확 승인/내보내기·수정 원본 추적·긴 경로를 포함한다. 제공자/구독 한도 검사는 기존 Mock 범위를 유지한다.
- 최종 TypeScript `tsc -b`와 Vite production build 통과. 독립 검토에서 찾은 구성 버전 재사용, 수정 대상과 정체성 참조의 구분, 내보내기의 원본 추적을 보완했고 이후 P1/P2 추가 지적은 없었다.
- 실제 브라우저 검증은 기존 전용 `127.0.0.1:8878` 및 `.test-data/character-preview-20261018`에서 수행했다. 기본 바로가기의 8765 저장소와 구독 로그인은 별개다. 기존 8877 프로세스는 변경하지 않았다.

```powershell
.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=30 --basetemp .test-data/visual-full-regression-20261018 tests
pnpm --dir frontend run build
```

범위와 제한: 실제 이야기 worker에 정확 시트 묶음을 고정 전달하는 연결은 후속 단계이며 새 캐릭터의 이야기 실행은 계속 409로 멈춘다. 시트 ZIP은 전체 v2 백업이 아니다. 현재 방향에 속한 이전 미선택 후보 파일도 무결성을 검사하므로 누락·변조 시 프로젝트 조회가 멈출 수 있고 원본 복원이 필요하다. 자동 복구 UI, 레퍼런스 이미지 자동 분석, 앱 내부 자동 이미지 생성, 실제 에피소드·게시 검증은 포함하지 않는다. 상세 사용법은 [후보·시트 안내](character-visual-guide.md), 계약은 [시각 API](contracts/character-visual-api.md)를 따른다.
