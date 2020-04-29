.PHONY: build bump install run seed test

build:
	scripts/build.sh

bump:
	bump2version minor

install:
	kubectl apply -f kubernetes.yml

seed:
	scripts/seed.sh

test:
	python -m unittest discover
