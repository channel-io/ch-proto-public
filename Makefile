.PHONY: install clean all generate lint

all: install generate

install:
	@echo "Installing dependencies ..."
	go mod download
	go install ./tools/protoc-gen-java-canonical-enum-namings
	go install ./tools/protoc-gen-java-set-or-clear
	ln -sf $${GRPC_JAVA_PATH}/protoc-gen-grpc-java $${GOPATH}/bin/protoc-gen-grpc-java
	@echo ""

generate:
	rm -rf coreapi/java
	buf generate
	@echo "Code generation complete."

lint:
	buf lint
	./scripts/lint-model-validate.sh

clean:
	go mod tidy
