# 캐릭터 대화 첫 구현

기준일: 2026-10-18. 범위: D-0036의 캐릭터 방향 대화·수정·저장과 D-0037의 [ChatGPT 구독 연결](chatgpt-subscription-guide.md). 기본 실행은 ChatGPT 연결이 필요하며, 명시적인 `--character-fixture` 실행만 AI 미연결 합성 테스트다. 방향 카드를 캐릭터 시트로 표시하거나 시트 승인으로 사용하지 않는다.

## 진행

1. 기본 주소를 열고 **ChatGPT 연결 → Continue with ChatGPT**에서 앱의 구독 사용에 동의한다. 연결한 계정의 모델을 선택한다. 프로젝트 이름은 선택 사항이며 첫 가상 캐릭터의 특징을 자유롭게 입력하고 **대화 시작**을 누른다.
2. 대화의 현재 질문에 성격·원하는 느낌을 하나씩 답한다. 오른쪽 방향 카드에 전달한 정보가 반영된다. 구독 제공자는 실제 모델로 입력을 정리하고 별도 역할로 검토한다. 명시적인 fixture 실행에서는 테스트 worker가 현재 질문에 해당하는 칸에 입력을 보존한다.
3. 이미 정한 항목을 바꾸려면 대화에서 바꿀 부분을 구체적으로 말하거나 **직접 수정**을 사용한다. 직접 수정은 지정한 항목 외의 값을 그대로 보존하며 새 버전을 만든다. 오프라인 fixture에서는 자연어 해석을 대신해 **반영할 항목**을 선택한다.
4. 필수 방향이 정리되면 **방향 확인하고 다음으로**를 누른다. 확인한 정확 버전을 저장하고 **시각 후보**로 이동한다. D-0038의 [후보·시트 흐름](character-visual-guide.md)에서 이미지 요청 준비 → Codex 생성 → 가져오기 → 비교·수정 → 시트 구성으로 이어진다.
5. **캐릭터 방향 수정**으로 돌아와 수정하고 다시 확인할 수 있다. 새로고침/앱 재시작 후 같은 프로젝트를 열면 대화·현재 방향·이전 버전·확인 기록이 복구된다.

화면에는 현재 단계·결과·대화·필요 행동을 우선 표시하고, 긴 제품 설명과 전체 기술 로그를 두지 않는다. 작업 모드는 작은 배지로 표시한다. 외형·성격·원하는 느낌은 한 번에 모두 채우는 시작 폼 대신 대화로 순차 보완한다. 말투·고정 특징·제외 요소는 선택 사항이다.

## 내부 구조

- API: `POST /api/studio/character-projects`, `GET /api/studio/projects/{pid}/character`, `POST .../turns`, `.../confirm`, `.../reopen`.
- 새 프로젝트는 `sheet_status=missing`, `approval_status=pending`이며 합성 주인공 fixture를 주입하지 않는다. 시트가 없으면 이야기 실행 API도 409로 막는다.
- LangGraph: designer → deterministic validator → independent evaluator → human review interrupt. 확인 응답은 정확 버전으로 재개한다. worker 역할은 분리하되 사용자 대화 창은 하나다.
- SQLite: 데이터 루트의 `studio/character/directions.sqlite3`에 상태·요청·불변 버전·제공자 호출 한도를, `checkpoints.sqlite3`에 그래프 중간 상태를 저장한다.
- 요청 ID로 중복 응답을 재생하고 revision/version 충돌을 차단한다. 모델/계약/프로젝트가 맞지 않는 미완료 복구 작업은 제공자를 호출하기 전에 격리한다.
- 방향 확인만으로는 `visual_ready`, `sheet_approved`가 true가 되지 않는다. D-0038에서 실제 후보·시트 이미지를 등록하고 선택한 구성 전체의 시트를 별도로 최종 확인해야 한다. 레퍼런스 이미지 자동 분석과 전체 v2 백업은 아직 구현하지 않았다.
- 기존 Stage04 합성 자료는 `?storyFixture=1`, v1 자료는 `?legacy=1`에서 보존한다. 별도 기술 테스트에서만 기존 fixture를 사용한다.

## 선택적 Ollama 코드 경로

기존 엔지니어링 서비스의 선택적 Ollama 어댑터는 보존했다. 별도 실행 범위가 구체화된 경우에만 `TOON_CHARACTER_ENABLE_OLLAMA=1`, `TOON_CHARACTER_OLLAMA_MODEL`, `TOON_CHARACTER_PROVIDER_APPROVAL_FILE`을 사용한다. 기본 앱의 캐릭터 연결은 이 환경 변수를 읽지 않는다. 명시적인 `--character-fixture`도 항상 오프라인 결정론적 제공자다. `docs/contracts/character-provider-approval.example.json`은 비활성 예시다. Stage04용 환경 변수/승인 파일은 캐릭터 실행에 적용되지 않는다.

이 경로는 `synthetic_character_direction`, 정확한 모델·역할·loopback endpoint·기한·호출/시간 한도가 필요하다. loopback은 실제 모델의 추론 위치나 외부 위임 여부를 증명하지 않는다. 실행 승인 파일·키·모델 가중치는 Git에 넣지 않는다. 구독 어댑터의 연결·한도·검증 범위는 별도 안내를 따른다.
