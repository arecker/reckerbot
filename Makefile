.PHONY: build run seed test

build:
	scripts/build.sh

seed:
	scripts/seed.sh

test:
	python -m unittest discover
