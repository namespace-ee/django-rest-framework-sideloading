.PHONY: help clean lint format test build
.DEFAULT_GOAL := help

help:
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

clean: ## remove build artifacts
	rm -fr build/ dist/ *.egg-info
	find . -name '*.py[co]' -delete

lint: ## check the code with ruff
	uv run ruff check .
	uv run ruff format --check .

format: ## reformat the code with ruff
	uv run ruff check --fix .
	uv run ruff format .

test: ## run the tests
	uv run pytest tests/

build: clean ## build the sdist and wheel
	uv build
