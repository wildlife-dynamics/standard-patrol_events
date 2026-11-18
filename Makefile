WORKFLOW ?= standard_patrol_events
PARTNER ?= costaecuador
PKG_DIR := workflows/$(WORKFLOW)/ecoscope-workflows-$(subst _,-,$(WORKFLOW))-workflow
OUTPUT_DIR ?= /tmp/$(WORKFLOW)/$(PARTNER)

.PHONY: build compile recompile run dev link

# `make dev`: compile, keep the existing env, and link ext-custom + this repo's data
# package into it as editable installs, so their edits apply on the next run with no
# package build. Paths resolve per checkout (main or worktree).
W_DYNAMICS ?= $(abspath $(shell git rev-parse --path-format=absolute --git-common-dir)/../..)
EXT_CUSTOM ?= $(W_DYNAMICS)/ecoscope-workflow-task-library-spe/src/ecoscope-workflows-ext-custom

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

# --clobber deletes the env, so it is moved aside and back (no reinstall, no network).
# (wt-compiler --env-overrides can't resolve task names, hence the pip link.)
dev:
	mkdir -p /tmp/$(WORKFLOW)
	if [ -d $(PKG_DIR)/.pixi ]; then mv $(PKG_DIR)/.pixi /tmp/$(WORKFLOW)/.pixi-keep; fi; \
	./dev/recompile.sh $(WORKFLOW) --update; rc=$$?; \
	if [ -d /tmp/$(WORKFLOW)/.pixi-keep ]; then rm -rf $(PKG_DIR)/.pixi; mv /tmp/$(WORKFLOW)/.pixi-keep $(PKG_DIR)/.pixi; fi; \
	[ $$rc -eq 0 ] && $(MAKE) link

link:
	cd $(PKG_DIR) && .pixi/envs/default/bin/python -m pip install -q --no-deps \
		-e $(EXT_CUSTOM) -e $(CURDIR)/src/ecoscope-workflows-ext-standard-patrol-events
