.PHONY: build bump-major bump-minor bump-patch install install-test-deps lint seed test

build:
	scripts/build.sh

bump-major:
	bump2version major

bump-minor:
	bump2version minor

bump-patch:
	bump2version patch

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
