.PHONY: install build test dev clean

# Cross-platform generic Makefile for WaseemBrain

install:
	npm install
	npm run setup:python

build:
	npm run build:all

test:
	npm run test:all

dev-interface:
	npm run dev

dev-brain:
	npm run start:python

dev-router:
	cd router-daemon && cargo run

clean:
	npm run clean
