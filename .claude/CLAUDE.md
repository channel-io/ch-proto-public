# ch-proto-public

Channel.io 공개 Protocol Buffers 정의 레포지토리.
Go + Java 코드 생성을 지원한다.

## 구조

```
ch-proto-public/
├── coreapi/
│   ├── common/          # 공통 타입 (pagination, sort_order 등)
│   ├── model/           # 도메인 모델 (bot 등)
│   ├── service/         # 서비스 요청/응답 메시지
│   ├── go/              # [generated] Go 코드
│   └── java/            # [generated] Java 코드
├── shared/v1/validation/ # buf.validate 벤더 (수정 금지)
├── buf.yaml             # buf 모듈 설정 (lint, deps)
├── buf.gen.yaml         # buf 코드 생성 플러그인 설정
├── buf.lock             # buf 의존성 잠금 (자동 생성)
├── Makefile             # 빌드 명령어
└── go.mod               # Go 모듈
```

## 코드 생성

```bash
make install   # 의존성 설치 (최초 1회)
make generate  # buf generate 실행
make lint      # buf lint 실행
```

- `coreapi/go/`, `coreapi/java/` 하위 파일은 자동 생성된다. 직접 수정하지 않는다.
- proto 파일을 수정한 후 반드시 `make generate`로 재생성하고, 생성된 파일도 함께 커밋한다.

## Proto 작성 규칙

- package 네이밍: `coreapi.{domain}` (예: `coreapi.common`, `coreapi.model`, `coreapi.service`)
- 필드명: `snake_case` (protobuf 표준)
- 다른 메시지 참조 시 FQN 사용: `coreapi.model.Bot` (import 경로와 별개)
- 모든 proto 파일에 `go_package`, `java_package`, `java_multiple_files` 옵션 필수

### 언어별 옵션 패턴

```protobuf
option go_package = "github.com/channel-io/ch-proto-public/coreapi/go/{domain}";
option java_multiple_files = true;
option java_package = "io.channel.api.proto.coreapi.{domain}";
```

### 파일 분류

| 디렉토리 | 용도 | 예시 |
|----------|------|------|
| `coreapi/common/` | 여러 도메인에서 공유하는 타입 | `Pagination`, `SortOrder` |
| `coreapi/model/` | 도메인 엔티티 모델 | `Bot`, `NameDesc` |
| `coreapi/service/` | API 요청/응답 메시지 | `SearchBotsRequest`, `UpsertBotRequest` |

## 의존성

- `buf.build/bufbuild/protovalidate` — `buf.validate` 필드 검증
- `google/protobuf/timestamp.proto` — 타임스탬프 타입

## 주의 사항

- `shared/v1/validation/` — 벤더 디렉토리. 수정 금지.
- `reference/` — 내부 ch-proto 참조용 심링크. gitignore 대상.
- `buf.lock` — `buf dep update`로 자동 생성. 직접 수정 금지.
- 생성된 코드(`coreapi/go/`, `coreapi/java/`)는 커밋 대상이지만 직접 수정 금지.
