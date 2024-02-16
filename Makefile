.DEFAULT_GOAL:=help

.EXPORT_ALL_VARIABLES:

ifndef VERBOSE
.SILENT:
endif

# set default shell
SHELL=/usr/bin/env bash -o pipefail -o errexit

# TAG ?= $(shell cat TAG)
POETRY_HOME ?= ${HOME}/.local/share/pypoetry
POETRY_BINARY ?= ${POETRY_HOME}/venv/bin/poetry
POETRY_VERSION ?= 1.3.2

dist.dir := dist
egg.dir := .eggs
build.dir := build
site.dir := site
output.dir := output


notebooks.python := $(shell find ./notebooks -type f -name "*.ipynb" || :)



help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)


.PHONY: install
install:  ## Install monitoring_models with poetry
	@scripts/install.sh
	## mkdocs-material insiders
	${POETRY_BINARY} run python -m pip install git+https://${GH_TOKEN}@github.com/squidfunk/mkdocs-material-insiders.git@9.4.2-insiders-4.42.0

.PHONY: test
test: unit-test  ## Run monitoring_models tests


.PHONY: check-docs
check-docs: ## Check site
	@$(call i, Checking Documentation)
	${POETRY_BINARY} run mkdocs build -s

.PHONY: docs
docs: ## serve the site
	${POETRY_BINARY} run mkdocs build --no-strict

.PHONY: serve
serve: docs ## Serve the site
	${POETRY_BINARY} run mkdocs serve --no-strict &

.PHONY: clean
clean:  ## Remove all build artifacts.
	rm -f docs/modules.rst
	rm -rf $(build.dir)
	rm -rf $(dist.dir)
	rm -rf $(site.dir)
	
	
deploy: install docs ## build site
