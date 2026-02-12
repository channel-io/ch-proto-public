# ch-proto-public

Channel.io의 공개 Protocol Buffers 정의 레포지토리.

## Prerequisites

### 필수 도구

| 도구 | 버전 | 설치 | 용도 |
|------|------|------|------|
| [Go](https://go.dev/dl/) | 1.25+ | `brew install go` | 모듈 관리, 내부 플러그인 설치 |
| [Buf CLI](https://buf.build/docs/installation/) | latest | `brew install bufbuild/buf/buf` | proto 코드 생성, lint |
| [Protocol Buffers Compiler (protoc)](https://github.com/protocolbuffers/protobuf/releases) | v3.19+ | `brew install protobuf` | Java 코드 생성 (buf 내부에서 호출) |
| [gRPC Java plugin](https://github.com/grpc/grpc-java/tree/master/compiler) | - | 직접 빌드 필요 | Java gRPC 코드 생성 |

### 환경변수

```bash
# gRPC Java 플러그인 바이너리 디렉토리 경로
export GRPC_JAVA_PATH=/path/to/grpc-java/compiler/build/exe/java_plugin

# channel-io 내부 Go 모듈 접근 (내부 Java 플러그인 설치에 필요)
export GOPRIVATE=github.com/channel-io
```

## Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/channel-io/ch-proto-public.git
cd ch-proto-public

# Install dependencies + link plugins
make install
```

`make install`이 수행하는 작업:
- `go mod download` — Go 의존성 다운로드
- channel-io 내부 Java 플러그인 2개 설치 (`protoc-gen-java-set-or-clear`, `protoc-gen-java-canonical-enum-namings`)
- `protoc-gen-grpc-java` 심볼릭 링크 생성 (`$GRPC_JAVA_PATH` → `$GOPATH/bin`)

## Code Generation

```bash
# 의존성 설치 + 코드 생성
make all

# 코드 생성만
make generate

# lint
make lint
```

## Supported Languages

| Language | Plugin | 방식 |
|----------|--------|------|
| Go | protoc-gen-go, protoc-gen-go-grpc | buf remote (설치 불필요) |
| Java | protoc built-in, protoc-gen-grpc-java | buf local (protoc + 로컬 바이너리) |

## License

MIT
