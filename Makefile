.PHONY: install clean all generate lint

all: install generate

install:
	@echo "Installing dependencies ..."
	go mod download
	go install ./tools/protoc-gen-java-canonical-enum-namings
	go install ./tools/protoc-gen-java-set-or-clear
	go install ./tools/protoc-gen-go-canonical-enum-namings
	go install ./tools/protoc-gen-go-coreapi-json-names
	ln -sf $${GRPC_JAVA_PATH}/protoc-gen-grpc-java $${GOPATH}/bin/protoc-gen-grpc-java
	@echo ""

generate:
	rm -rf coreapi/java
	rm -rf coreapi/go
	buf generate
	gofmt -w coreapi/go
	@echo "Code generation complete."

lint:
	buf lint
	./scripts/lint-model-validate.sh
	python3 scripts/validate-nullable-scalar-validation.py
	@test -z "$$(gofmt -l coreapi/go)" || { echo "gofmt needed in coreapi/go:"; gofmt -l coreapi/go; exit 1; }

clean:
	go mod tidy
