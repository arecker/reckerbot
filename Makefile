.PHONY: seed test

seed:
	scripts/seed.sh

test:
	python -m unittest discover
