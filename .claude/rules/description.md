# Description 작성 기준 (Public Open API)

proto 주석의 description 영역은 그대로 공개 API 문서가 된다.
외부 개발자가 API를 이해하고 올바르게 사용할 수 있도록 작성한다.
model.md의 "주석 작성" 규칙을 기반으로 아래 기준을 추가 적용한다.

## 1. Marker 중복 금지

marker로 이미 표현된 정보를 description에 반복하지 않는다.
Required/Nullable 여부, 글자수 제한(MinLength, MaxLength), 패턴, 최소/최대값 등.

## 2. 자기 설명성

필드 이름을 단순 반복하는 것이 아니라, 필드의 용도와 의미를 전달해야 한다.

**판단 기준**: "필드 이름을 모르는 상태에서 description만 읽어도 이 필드가 뭔지 알 수 있는가?"

| 부족 | 충분 |
|------|------|
| "The bot ID." | "Unique bot identifier." |
| "Medium topic build key." | "Key for selecting the message topic template within the medium." |

## 3. 관찰 가능한 동작만 서술

**핵심 판단 기준**: "API 소비자가 이 정보를 직접 관찰하거나 경험하는가?"

**포함 (O) — 소비자가 관찰할 수 있는 것**:
- 필드 간 조건부 관계 ("Applicable when send_mode is RESERVED_WITH_SENDER_TIME.")
- 기본 동작/자동 설정 ("Randomly assigned if not specified on creation.")
- 유니크 제약 ("Unique within the channel.")
- 값의 포맷 ("ISO 8601 date-time without timezone offset.")
- API 동작 제약 ("Users updated more than a year ago are not retrieved.")

**제외 (X) — 내부 구현 메커니즘**:
- 저장소/인프라 (DB 종류, 테이블명, 인덱스, TTL 설정)
- 내부 서비스명, 코드 상수/변수명
- Desk API 전용 동작

**예시**:
- (X) "Records are automatically expired one year after the last update." → 내부 TTL 메커니즘
- (O) "Users updated more than a year ago are not retrieved." → API 소비자가 관찰하는 동작

## 4. model vs service 배치

| 위치 | 서술 대상 |
|------|----------|
| Model message/field | 데이터가 무엇인지, 필드 간 관계 |
| Service request message | API 동작, 조회 제약, 페이지네이션 동작 |
| Service response message | 한 줄 요약 ("Response for {operation}.") |

데이터의 수명, 조회 제한 등 API 동작에 관한 정보는 model이 아닌 service에 배치한다.

## 5. 간결성

- 필드 description: 1~2문장
- 동일 의미 반복 금지
- 자명한 정보 생략

## 6. 일관성

같은 유형의 필드는 같은 패턴을 따른다 (bot.proto 레퍼런스 기준).

| 필드 유형 | 패턴 | 예시 |
|---|---|---|
| 엔티티 ID | "Unique {entity} identifier." | "Unique bot identifier." |
| 소속 ID | "Channel ID this {entity} belongs to." | "Channel ID this bot belongs to." |
| 타임스탬프 (생성/수정) | "{Entity} {creation/last update} timestamp." | "Bot creation timestamp." |
| 타임스탬프 (이벤트) | "Timestamp when {event description}." | "Timestamp when the user viewed the message." |
