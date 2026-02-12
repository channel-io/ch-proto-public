# Service Proto 작성 규칙

`coreapi/service/` 하위에 API 요청/응답 메시지를 정의할 때 따르는 규칙.

## 파일 헤더

```protobuf
syntax = "proto3";

package coreapi.service;

import "buf/validate/validate.proto";

option go_package = "github.com/channel-io/ch-proto-public/coreapi/go/service";
option java_multiple_files = true;
option java_package = "io.channel.api.proto.coreapi.service";
```

## 메시지 네이밍 규칙

| 패턴 | 용도 | 예시 |
|------|------|------|
| `{Verb}{Resource}Request` | 요청 메시지 | `SearchBotsRequest`, `GetBotRequest`, `UpsertBotRequest`, `DeleteBotRequest` |
| `{Verb}{Resource}Result` | 응답 메시지 | `SearchBotsResult`, `GetBotResult`, `UpsertBotResult`, `DeleteBotResult` |

### 동사 선택

| 동사 | 의미 |
|------|------|
| `Get` | 단건 조회 |
| `Search` / `List` | 목록 조회 |
| `Create` | 생성 |
| `Update` | 수정 |
| `Upsert` | 생성 또는 수정 |
| `Delete` | 삭제 |

## buf.validate 사용

요청 메시지의 필드 검증에는 `buf.validate`를 사용한다.
model의 kubebuilder marker와 달리, service에서는 런타임 검증을 위해 `buf.validate`를 쓴다.

### required 필드

```protobuf
string channel_id = 1 [(buf.validate.field).required = true];
```

### CEL 표현식

복합 검증 로직은 CEL(Common Expression Language)로 작성한다.

```protobuf
string name = 2 [
  (buf.validate.field).cel = {
    id: "string.maxLen"
    message: "value must be no more than 30 characters"
    expression: "size(this) <= 30"
  },
  (buf.validate.field).cel = {
    id: "string.minLen"
    message: "value must be at least 1 characters"
    expression: "size(this) >= 1"
  },
  (buf.validate.field).required = true
];
```

### 정규식 패턴

```protobuf
string name = 2 [
  (buf.validate.field).string.pattern = "^[^@#$%:/]+$"
];
```

### optional + 검증

nullable 필드에도 검증을 붙일 수 있다. 값이 존재할 때만 검증된다.

```protobuf
optional string description = 3 [(buf.validate.field).cel = {
  id: "string.maxLen"
  message: "value must be no more than 180 characters"
  expression: "size(this) <= 180"
}];
```

### 중첩 메시지 참조

공통 메시지를 필드로 포함할 때는 FQN으로 참조한다.

```protobuf
coreapi.common.Pagination pagination = 1;
```

## 메시지 주석

### 요청 메시지

API 엔드포인트의 동작을 설명한다. 이 주석이 OpenAPI description으로 변환된다.

```protobuf
// Retrieves a bot list.
//
// The number of bots retrieved is restricted by the limit query parameter,
// and is capped to values in the closed interval [1, 500].
// ...
message SearchBotsRequest {
```

포함할 내용:
- 엔드포인트가 하는 일 (한 줄 요약)
- 페이지네이션, 정렬 등 동작 세부사항
- 제외되는 항목 (예: "AI bots (ALF) are excluded")
- 에러 케이스 (예: "Returns 404 if the bot does not exist")

### 응답 메시지

간결하게 한 줄로 작성한다.

```protobuf
// Response for bot list retrieval.
message SearchBotsResult {
```

### 삭제 응답

삭제 API의 빈 응답은 HTTP 의미를 주석에 명시한다.

```protobuf
// Response for bot deletion. Empty on success (204 No Content).
message DeleteBotResult {}
```

## 응답 메시지 필드 패턴

| 조회 유형 | 필드 패턴 |
|----------|----------|
| 단건 조회 | `coreapi.model.Bot bot = 1;` |
| 목록 조회 | `repeated coreapi.model.Bot bots = 1;` + `string next = 2;` (커서) |
| 생성/수정 | `coreapi.model.Bot bot = 1;` (생성/수정된 결과) |
| 삭제 | 빈 메시지 `{}` |

## 참고 예시

현재 `coreapi/service/bot.proto`가 이 규칙을 따르는 레퍼런스 구현이다.
