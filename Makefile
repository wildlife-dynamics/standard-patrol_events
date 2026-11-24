WORKFLOW ?= standard_patrol_events
PARTNER ?= costaecuador
PKG_DIR := ecoscope-workflows-$(subst _,-,$(WORKFLOW))-workflow
OUTPUT_DIR ?= /tmp/$(WORKFLOW)/$(PARTNER)

.PHONY: compile recompile run dev run-dev clear-cache link test

# Dev loop: one pixi env (`dev` in pixi.toml) compiles the workflow with wt-compiler
# --from-env (tasks read from the installed env: no throwaway env, no downloads) and runs
# it with the step cache (--with-caching). the task package (wd-partner-tasks) is linked
# editable, so its edits apply on the next run. The compiled package is bound to the
# dev env's exact versions: run it with `make run-dev`, and `make recompile` before
# committing the package. Paths resolve per checkout (main or worktree).
W_DYNAMICS ?= $(abspath $(shell git rev-parse --path-format=absolute --git-common-dir)/../..)
# The task package lives in wd-partner-tasks.
PARTNER_TASKS ?= $(W_DYNAMICS)/wd-partner-tasks-standard-patrol-events
EXT_SPE := $(PARTNER_TASKS)/src/ecoscope-workflows-ext-standard-patrol-events
SPE_VERSION := $(shell grep -A1 "name: ecoscope-workflows-ext-standard-patrol-events" spec.yaml | sed -n 's/.*version: "==\(.*\)"/\1/p')
DEV_ENV := .pixi/envs/dev
CACHE_DIR ?= /tmp/$(WORKFLOW)/wt-cache
PARAMS ?=

compile:
	./dev/recompile.sh --install

recompile:
	./dev/recompile.sh --update

# Real data (no mock IO): the PARTNER case's params from test-cases.yaml.
run:
	mkdir -p $(OUTPUT_DIR)
	pixi run yq -y '."$(PARTNER)".params' test-cases.yaml > $(OUTPUT_DIR)/params.yaml
	cd $(PKG_DIR) && ECOSCOPE_WORKFLOWS_RESULTS="file://$(OUTPUT_DIR)" \
		pixi run ecoscope-workflows-$(subst _,-,$(WORKFLOW))-workflow run \
		--config-file $(OUTPUT_DIR)/params.yaml --execution-mode sequential --no-mock-io

dev:
	$(MAKE) link
	$(DEV_ENV)/bin/wt-compiler compile --spec spec.yaml \
		--pkg-name-prefix=ecoscope-workflows --results-env-var=ECOSCOPE_WORKFLOWS_RESULTS \
		--from-env --with-caching --clobber --update
	python3 dev/add_root_rules.py $(PKG_DIR)/ecoscope_workflows_$(WORKFLOW)_workflow/rjsf.json

# Reruns only recompute steps whose code or inputs changed (cache-report.json per run).
# EarthRanger fetches are reused for 12 h; `make clear-cache` to refetch.
# PARAMS=<file> runs a one-off params file instead of the PARTNER test case.
run-dev:
	mkdir -p $(OUTPUT_DIR)
	if [ -n "$(PARAMS)" ]; then cp $(PARAMS) $(OUTPUT_DIR)/params.yaml; \
	else pixi run yq -y '."$(PARTNER)".params' test-cases.yaml > $(OUTPUT_DIR)/params.yaml; fi
	cd $(PKG_DIR) && ECOSCOPE_WORKFLOWS_RESULTS="file://$(OUTPUT_DIR)" \
		WT_CACHE__STORE=$(CACHE_DIR) WT_CACHE__SCOPE=local-dev WT_CACHE__IO_TTL=12h WT_CACHE__LAZY=true \
		WT_CACHE__EPOCH=$$($(CURDIR)/dev/epoch.sh $(EXT_SPE)) \
		$(CURDIR)/$(DEV_ENV)/bin/python -m ecoscope_workflows_$(WORKFLOW)_workflow.cli run \
		--config-file $(OUTPUT_DIR)/params.yaml --execution-mode sequential --no-mock-io

test:
	$(DEV_ENV)/bin/python -m pytest tests -q

clear-cache:
	rm -rf /tmp/$(WORKFLOW)/wt-cache

# top_level.txt maps each editable package to its distribution, so the cache can version it.
LINKED := ecoscope_workflows_ext_standard_patrol_events
link:
	# pip's reinstall at a new version leaves the old dist-info holding only our
	# top_level.txt; that stub shadows the real metadata and blocks pip, so clear it first.
	for pkg in $(LINKED); do for d in $(DEV_ENV)/lib/python3*/site-packages/$${pkg}-*.dist-info; do \
		if [ -d $$d ] && [ ! -f $$d/METADATA ]; then rm -f $$d/top_level.txt && rmdir $$d; fi; \
	done; done
	# Report the version spec.yaml pins, so wt-compiler --from-env accepts the editable install.
	SETUPTOOLS_SCM_PRETEND_VERSION=$(SPE_VERSION) \
		$(DEV_ENV)/bin/python -m pip install -q --no-deps \
		-e $(EXT_SPE)
	# Listed in RECORD, so pip removes it with the package on the next reinstall (no stub).
	for pkg in $(LINKED); do for d in $(DEV_ENV)/lib/python3*/site-packages/$${pkg}-*.dist-info; do \
		if [ -f $$d/METADATA ]; then echo $$pkg > $$d/top_level.txt; \
			grep -q "/top_level.txt," $$d/RECORD || echo "$$(basename $$d)/top_level.txt,," >> $$d/RECORD; fi; \
	done; done
