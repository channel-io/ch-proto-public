.PHONY: install clean all

# --- Variables ---

MAKE ?= make

PROTOC          ?= protoc
PROTOC_ROOT_DIR ?= .
PROTOVALIDATE_ROOT_DIR ?= ./shared/v1/validation/proto/protovalidate

PROTOC_OPTS     ?= -I $(PROTOC_ROOT_DIR) -I $(PROTOVALIDATE_ROOT_DIR)

# Java
PROTOC_JAVA_PLUGIN_PATH ?= $(GRPC_JAVA_PATH)
PROTOC_JAVA_PLUGIN_BIN  ?= $(PROTOC_JAVA_PLUGIN_PATH)/protoc-gen-grpc-java
PROTOC_JAVA_OPTS        ?= \
	--plugin=$(PROTOC_JAVA_PLUGIN_BIN) \
	--java_out=$(shell echo $(PKG_ROOT)/java) \
	--grpc-java_out=$(shell echo $(PKG_ROOT)/java)

# Go
PROTOC_GO_OPTS ?= --go_out=. --go-grpc_out=.

# Rust
PROTOC_RUST_OPTS ?= --prost_out=$(shell echo $(PKG_ROOT)/rust) --tonic_out=$(shell echo $(PKG_ROOT)/rust)

# TypeScript
PROTOC_TS_PLUGIN ?= ./node_modules/.bin/protoc-gen-ts_proto
PROTOC_TS_OPTS   ?= --plugin=$(PROTOC_TS_PLUGIN) --ts_proto_out=.

# --- Targets ---

all: install
	@echo "No service targets defined yet. Add .proto files and register targets here."

install:
	@echo "Installing dependencies ..."
	go mod download > /dev/null
	yarn install > /dev/null
	cargo install protoc-gen-tonic@0.4.1 protoc-gen-prost@0.4.0 > /dev/null
	@echo ""

	@echo "Installing executables ..."
	GOPRIVATE=github.com/channel-io go install github.com/channel-io/go-lib/pkg/protoc-gen-java-canonical-enum-namings@v0.8.4 > /dev/null
	GOPRIVATE=github.com/channel-io go install github.com/channel-io/go-lib/pkg/protoc-gen-java-set-or-clear@v0.8.4 > /dev/null
	@echo ""

clean:
	go mod tidy
	cargo uninstall protoc-gen-tonic protoc-gen-prost

# --- Individual targets ---
# Add service-specific targets here as .proto files are added.
# Example (following ch-proto pattern):
#
#   auth-v1: PKG_ROOT = auth/v1
#   auth-v1: PKG_ENTRY = auth/v1/**/*.proto
#   auth-v1: PROTOC_GO_OPTS = --go_out=. --go-grpc_out=. --go_opt=module=github.com/channel-io/ch-proto-public
#   auth-v1: auth-v1-prepare-gen auth-v1-java auth-v1-go auth-v1-post-gen

# --- Recipes ---

%-prepare-gen:
	@echo "Generating stubs for $(PKG_ENTRY) ..."

%-java: %-java-clean
	$(PROTOC) $(PROTOC_OPTS) $(PROTOC_JAVA_OPTS) $(PKG_ENTRY)

%-java-with-plugins:
	$(PROTOC) $(PROTOC_OPTS) \
		$(PROTOC_JAVA_OPTS) \
		--plugin=protoc-gen-set_or_clear=$${GOPATH}/bin/protoc-gen-java-set-or-clear \
		--set_or_clear_out=$(shell echo $(PKG_ROOT)/java) \
		--plugin=protoc-gen-enum_canonical_names=$${GOPATH}/bin/protoc-gen-java-canonical-enum-namings \
		--enum_canonical_names_out=$(shell echo $(PKG_ROOT)/java) \
		$(PKG_ENTRY)

%-java-clean:
	rm -rf $(PKG_ROOT)/java
	mkdir -p $(PKG_ROOT)/java

%-go:
	$(PROTOC) $(PROTOC_OPTS) $(PROTOC_GO_OPTS) $(PKG_ENTRY)

%-rust:
	$(PROTOC) $(PROTOC_OPTS) $(PROTOC_RUST_OPTS) $(PKG_ENTRY)

%-typescript:
	$(PROTOC) $(PROTOC_OPTS) $(PROTOC_TS_OPTS) $(PKG_ENTRY)

%-post-gen:
	@echo "Generating stubs for $(PKG_ENTRY) ... done"
	@echo ""
