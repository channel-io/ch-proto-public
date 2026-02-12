.PHONY: install clean all generate lint

all: install generate

install:
	@echo "Installing dependencies ..."
	go mod download
	GOPRIVATE=github.com/channel-io go install github.com/channel-io/go-lib/pkg/protoc-gen-java-canonical-enum-namings@v0.8.4
	GOPRIVATE=github.com/channel-io go install github.com/channel-io/go-lib/pkg/protoc-gen-java-set-or-clear@v0.8.4
	ln -sf $${GRPC_JAVA_PATH}/protoc-gen-grpc-java $${GOPATH}/bin/protoc-gen-grpc-java
	@echo ""

generate:
	rm -rf coreapi/java
	buf generate
	@echo "Code generation complete."

lint:
	buf lint

clean:
	go mod tidy
