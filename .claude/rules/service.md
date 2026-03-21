# Service Proto 작성 규칙

`coreapi/service/` 하위에 API 요청/응답 메시지를 정의할 때 따르는 규칙.

## 파일 구성 원칙: 리소스 바운더리

service proto 파일은 **독립 리소스 단위**로 구성한다.
종속 엔티티의 오퍼레이션은 상위 리소스 파일에 포함한다.

### 판별 기준: "이 엔티티가 상위 엔티티 없이 독립 존재할 수 있는가?"
- **Yes (독립)** → 별도 service 파일: `bot.proto`, `user.proto`, `manager.proto`, `group.proto`, `user_chat.proto` 등
- **No (종속)** → 상위 리소스 파일에 포함: ChatSession, ChatBookmark, Message, Thread, FileUrl 등은 Group/UserChat에 포함

### 현재 파일 구성
| 파일 | 포함하는 오퍼레이션 |
|------|-------------------|
| `group.proto` | Group CRUD + 세션 + 메시지 + 스레드 + 파일URL |
| `user_chat.proto` | UserChat CRUD + 상태변경 + 세션 + 메시지 + 파일URL |
| `manager.proto` | Manager CRUD + Online(expand) + OperatorStatus(expand) |
| `user.proto` | User CRUD + Online(expand) |
| `meet.proto` | Meet 전용 오퍼레이션 (call logs, STT messages, recording) |
| `announcement.proto` | 시스템 레벨 브로드캐스트 (독립 액션) |

### 금지
- 종속 엔티티를 별도 service 파일로 분리하지 않는다 (예: `chat_message.proto`, `chat_session.proto` 금지)
- `chat_type` 파라미터로 Group/UserChat을 구분하는 범용 메시지를 만들지 않는다. 상위 리소스별로 전용 메시지를 정의한다.

## bool expand 패턴

추가 조회(별도 저장소/네트워크)가 필요한 종속 엔티티는 Request에 `include_` bool 플래그를 두고, Result에 해당 필드를 선택적으로 채운다.

```protobuf
message GetManagerRequest {
  string manager_id = 1;
  string channel_id = 2;
  bool include_online = 3;            // expand: 별도 네트워크 조회
  bool include_operator_status = 4;   // expand: 별도 DB 조회
}

message GetManagerResult {
  coreapi.model.Manager manager = 1;
  coreapi.model.Online online = 2;                 // include_online=true 시 채워짐
  coreapi.model.OperatorStatus operator_status = 3; // include_operator_status=true 시 채워짐
}
```

### expand 대상 판별
- **같은 트랜잭션으로 가져올 수 있는 종속 엔티티** → Result에 항상 포함 (expand 불필요)
- **별도 저장소/네트워크 조회가 필요한 종속 엔티티** → `include_` 플래그로 선택적 포함

### expand는 종속 엔티티만
core API의 expand는 해당 리소스 바운더리 안의 종속 엔티티만 대상으로 한다.
독립 엔티티 간 조합(예: Group 조회 시 Manager 목록 포함)은 core API가 아닌 open API 핸들러에서 여러 core API를 호출하여 구성한다.

## 파일 헤더

```protobuf
syntax = "proto3";

package coreapi.service;

import "buf/validate/validate.proto";

option go_package = "github.com/channel-io/ch-proto-public/coreapi/go/service";
option java_multiple_files = true;
option java_package = "io.channel.api.proto.pub.coreapi.service";
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

`protovalidate.md` 참조. 요청 메시지의 필드 검증에 `buf.validate`를 사용한다.

### 중첩 메시지 참조

공통 메시지를 필드로 포함할 때는 FQN으로 참조한다.

```protobuf
coreapi.common.Pagination pagination = 1;
```

## 메시지 주석

### 요청 메시지

API 엔드포인트의 동작을 설명한다.

```protobuf
// Retrieves a bot list.
//
// The number of bots retrieved is restricted by the limit query parameter,
// and is capped to values in the closed interval [1, 500].
// ...
message SearchBotsRequest {
  // ...
}
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
  // ...
}
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
| 목록 조회 | `repeated coreapi.model.T items = 1;` + `string next_cursor = 2;` + `bool has_next = 3;` |
| 생성/수정 | `coreapi.model.Bot bot = 1;` (생성/수정된 결과) |
| 삭제 | 빈 메시지 `{}` |

## 응답 필드의 kubebuilder marker

응답 메시지 필드에도 OpenAPI 문서 정확성을 위해 kubebuilder marker를 사용할 수 있다.
대표적으로 `next_cursor`에 `+kubebuilder:validation:Nullable`을 사용한다.

```protobuf
// Opaque cursor for the next page.
// Use has_next to determine whether another page exists.
//
// +kubebuilder:validation:Nullable
string next_cursor = 2;
```

## 참고 예시

- `coreapi/service/manager.proto` — bool expand 패턴 (include_online, include_operator_status) 레퍼런스
- `coreapi/service/group.proto` — 종속 오퍼레이션(세션, 메시지, 스레드, 파일) 통합 레퍼런스
- `coreapi/service/one_time_msg.proto` — v6 페이지네이션 표준 레퍼런스
