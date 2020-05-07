.PHONY: build bump install install-test-deps lint seed test

build:
	scripts/build.sh

bump:
	bump2version minor

install:
	kubectl apply -f kubernetes.yml

install-test-deps:
	pip install -r requirements/test.txt

lint:
	flake8

seed:
	scripts/seed.sh

test:
	python -m unittest discover
