.PHONY: build deps run

# Variables
PROTO_SOURCE_DIR=helios-protos
PROTO_BUILD_DIR=generated

# Find all .proto files in the proto directory and subdirectories
PROTO_SRC := $(wildcard $(PROTO_SOURCE_DIR)/**/*.proto)

# 1=true, 0=false
DOCKER_DISABLED=1
export DOCKER_DISABLED

# Commands
build:
	$(call MKDIR,$(PROTO_BUILD_DIR))

	protoc -I=$(PROTO_SOURCE_DIR) --python_out=$(PROTO_BUILD_DIR) $(PROTO_SRC)

	uv run src/build.py

deps:
	uv run sync

run:
	uv run src/launcher.py