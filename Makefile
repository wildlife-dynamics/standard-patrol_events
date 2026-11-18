WORKFLOW ?= standard_patrol_events
PARTNER ?= costaecuador
PKG_DIR := workflows/$(WORKFLOW)/ecoscope-workflows-$(subst _,-,$(WORKFLOW))-workflow
OUTPUT_DIR ?= /tmp/$(WORKFLOW)/$(PARTNER)

.PHONY: build compile recompile run dev run-dev clear-cache link

# Dev loop: one pixi env (`dev` in pixi.toml) compiles the workflow with wt-compiler
# --from-env (tasks read from the installed env: no throwaway env, no downloads) and runs
# it with the step cache (--with-caching). ext-custom and the data package are linked
# editable, so their edits apply on the next run. The compiled package is bound to the
# dev env's exact versions: run it with `make run-dev`, and `make recompile` before
# committing the package. Paths resolve per checkout (main or worktree).
W_DYNAMICS ?= $(abspath $(shell git rev-parse --path-format=absolute --git-common-dir)/../..)
EXT_CUSTOM ?= $(W_DYNAMICS)/ecoscope-workflow-task-library-spe/src/ecoscope-workflows-ext-custom
DEV_ENV := .pixi/envs/dev
CACHE_DIR ?= /tmp/$(WORKFLOW)/wt-cache
PARAMS ?=

build:
	# pixi exec, not pixi run: the workspace's compile env needs this package, which doesn't exist before the first build.
	pixi exec -s rattler-build -s hatch -s hatch-vcs -s pip ./publish/build.sh

compile: build
	./dev/recompile.sh $(WORKFLOW) --install

recompile: build
	./dev/recompile.sh $(WORKFLOW) --update

# Real data (no mock IO): the PARTNER case's params from test-cases.yaml.
run:
	mkdir -p $(OUTPUT_DIR)
	pixi run yq -y '."$(PARTNER)".params' workflows/$(WORKFLOW)/test-cases.yaml > $(OUTPUT_DIR)/params.yaml
	cd $(PKG_DIR) && ECOSCOPE_WORKFLOWS_RESULTS="file://$(OUTPUT_DIR)" \
		pixi run ecoscope-workflows-$(subst _,-,$(WORKFLOW))-workflow run \
		--config-file $(OUTPUT_DIR)/params.yaml --execution-mode sequential --no-mock-io

dev:
	$(MAKE) link
	$(DEV_ENV)/bin/wt-compiler compile --spec workflows/$(WORKFLOW)/spec.yaml \
		--pkg-name-prefix=ecoscope-workflows --results-env-var=ECOSCOPE_WORKFLOWS_RESULTS \
		--from-env --with-caching --clobber --update

# Reruns only recompute steps whose code or inputs changed (cache-report.json per run).
# EarthRanger fetches are reused for 12 h; `make clear-cache` to refetch.
# PARAMS=<file> runs a one-off params file instead of the PARTNER test case.
run-dev:
	mkdir -p $(OUTPUT_DIR)
	if [ -n "$(PARAMS)" ]; then cp $(PARAMS) $(OUTPUT_DIR)/params.yaml; \
	else pixi run yq -y '."$(PARTNER)".params' workflows/$(WORKFLOW)/test-cases.yaml > $(OUTPUT_DIR)/params.yaml; fi
	cd $(PKG_DIR) && ECOSCOPE_WORKFLOWS_RESULTS="file://$(OUTPUT_DIR)" \
		WT_CACHE__STORE=$(CACHE_DIR) WT_CACHE__SCOPE=local-dev WT_CACHE__IO_TTL=12h WT_CACHE__LAZY=true \
		WT_CACHE__EPOCH=$$($(CURDIR)/dev/epoch.sh $(EXT_CUSTOM) $(CURDIR)/src/ecoscope-workflows-ext-standard-patrol-events) \
		$(CURDIR)/$(DEV_ENV)/bin/python -m ecoscope_workflows_$(WORKFLOW)_workflow.cli run \
		--config-file $(OUTPUT_DIR)/params.yaml --execution-mode sequential --no-mock-io

clear-cache:
	rm -rf /tmp/$(WORKFLOW)/wt-cache

# top_level.txt maps each editable package to its distribution, so the cache can version it.
link:
	$(DEV_ENV)/bin/python -m pip install -q --no-deps \
		-e $(EXT_CUSTOM) -e $(CURDIR)/src/ecoscope-workflows-ext-standard-patrol-events
	for pkg in ecoscope_workflows_ext_custom ecoscope_workflows_ext_standard_patrol_events; do \
		echo $$pkg > $$(ls -d $(DEV_ENV)/lib/python3*/site-packages/$${pkg}-*.dist-info | head -1)/top_level.txt; \
	done
