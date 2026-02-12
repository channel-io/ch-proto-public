# ch-proto-public

Channel.io의 공개 Protocol Buffers 정의 레포지토리.

## Prerequisites

- [Protocol Buffers Compiler (protoc)](https://github.com/protocolbuffers/protobuf/releases)
- [Go 1.25+](https://go.dev/dl/)
- [Node.js + Yarn](https://yarnpkg.com/)
- [Rust + Cargo](https://www.rust-lang.org/tools/install)
- [gRPC Java plugin](https://github.com/grpc/grpc-java)

## Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/channel-io/ch-proto-public.git
cd ch-proto-public

# Install dependencies
make install
```

## Code Generation

```bash
# Generate all
make all

# Generate for a specific service (example)
# make <service-name>
```

## Supported Languages

| Language   | Tool                               |
|------------|------------------------------------|
| Java       | protoc + grpc-java                 |
| Go         | protoc-gen-go, protoc-gen-go-grpc  |
| Rust       | prost, tonic                       |
| TypeScript | ts-proto                           |

## License

MIT