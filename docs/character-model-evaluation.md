# 실제 모델 연결 권고안

## D-0037 구독 우선으로 변경

2026-10-18 사용자의 명시적 요청에 따라 기본안을 **ChatGPT Pro 사용량 연결, 한도 도달 시 중단, 유료 API 자동 전환 없음**으로 변경했다. [공식 Sign in with ChatGPT 안내](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)는 개인 로컬 프로젝트를 지원한다. 실제 계정의 모델 목록에서 선택하며, `gpt-6.1-sol`이 노출되면 첫 선택으로 사용한다. 현재 SIWC 요청은 모델별 미검증 파라미터를 피하기 위해 reasoning/service-tier override를 보내지 않는다. 아래 low·Standard와 USD 금액은 이전 API 후보 권고이며 현재 앱의 활성 비용 설정이 아니다.

구독 연결은 이미지 생성을 지원하지 않는다. 아래 이미지 모델은 추후 별도 경로의 후보로만 남긴다. 연결 방법과 한도 정지는 [구독 연결 안내](chatgpt-subscription-guide.md), 실제 검증 여부는 [검증 기록](studio-implementation-validation.md)을 참고한다.

## 이전 API 후보 검토

기준일: 2026-10-18 첫 검토. 아래는 공식 자료를 확인한 엔지니어링 후보이며 실제 모델 연결·실행 허가·예산 승인·화질 검증 기록이 아니다. 이 최초 검토 당시에는 오프라인 fixture와 선택적 Ollama만 있었고 OpenAI 어댑터는 없었다. 이후 구독 연결 구현은 위 D-0037을 따른다.

| 역할 | 첫 후보 | 선정 이유 |
|---|---|---|
| 대화 오케스트레이터·캐릭터 설계·레퍼런스 이해 | `gpt-6.1-sol`, reasoning low, Standard | 텍스트/이미지 입력과 구조화 출력, 사용자 설정 보존을 우선 |
| 독립 텍스트 평가 | `gpt-6-luna`, reasoning low | 별도 지시로 구체적인 수정 위치를 반환하는 경량 평가 |
| 캐릭터 후보·선택 후 시트/이미지 수정 | `gpt-image-2.5-sunburst` | 이미지 편집 정밀도를 우선한 후보. 다른 모델로 자동 대체하지 않음 |

공식 모델 페이지: [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [Sunburst](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst). 한국어 대화와 단순화된 캐릭터의 품질은 실제 소규모 평가에서 확인한다.

## 숫자 권고

- 최초 합성 검증 전체 USD 10, 캐릭터 세션당 USD 3, 사용자 작업 한 번에 USD 1.
- 작업마다 텍스트/이미지 이해 최대 6회 또는 이미지 최대 3회. 세션 합계 텍스트/이미지 이해 40회, 이미지 8회. 재시도도 포함한다.
- 텍스트 요청 60초, 이미지 요청 180초, 작업당 300초 상한(사람 확인 대기 제외). 병렬 텍스트 2개·이미지 1개.
- 시각 후보는 medium/1024×1024/한 번에 1장, 첫 후보군 최대 3개. 선택 후 시트 상세화는 별도 사용자 작업이다.
- 자동 창작 수정은 기존 상한 2회를 넘기지 않고, 기본은 독립 평가 후 사람에게 반환한다. 이미지의 무단 연속 재생성은 하지 않는다.
- 실행 전 최대 예상 사용량과 20% 여유를 영속 사용량 장부에 예약하고 사용량을 정산한다. 이미지 timeout 등으로 처리/과금 여부가 불명확하면 예약을 유지하고 멈추며 자동으로 다시 실행하지 않는다. 이 금액 상한·예약 장부는 후속 구현 항목이며 이번 fixture에 구현됐다고 주장하지 않는다.

## 실행 전 구체화할 조건

정확한 계정/모델 접근 가능 여부, 로컬 키 설정, 선별한 합성 입력, 외부 전달 범위, 기한, 호출/시간/금액 상한을 기존 권한과 대조한다. 원본 참고 ZIP을 통째로 보내거나 타사 캐릭터를 직접적인 정체성 입력으로 고정하지 않는다.

대화/이미지는 로컬에 저장한다. Responses API 사용 시 store=false를 후보로 하지만 이것이 제공자 측 무보관을 의미하지는 않는다. [API 데이터 제어](https://developers.openai.com/api/docs/guides/your-data)를 선택한 endpoint/계정 조건에서 다시 확인한다.

로컬 대안은 대상 PC를 정한 후 Qwen 계열 vision 모델과 ComfyUI 이미지 편집 workflow 등을 동일 입력으로 비교한다. 현재 PC의 GPU를 제품의 상한으로 삼지 않는다. 새 에이전트 framework로 이전하지 않고 기존 Python/LangGraph/provider 경계를 유지한다.
