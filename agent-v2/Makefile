# Agent v2 - OCaml Agent Framework Makefile

.PHONY: all build clean test install exec doc

all: build

build:
	dune build

clean:
	dune clean
	rm -rf _build

test:
	dune runtest

install:
	opam install . --deps-only

exec:
	dune exec agent-v2

doc:
	dune build @doc

watch:
	dune build --watch
