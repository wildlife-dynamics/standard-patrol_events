WORKFLOW ?= standard_patrol_events
PARTNER ?= costaecuador
PKG_DIR := workflows/$(WORKFLOW)/ecoscope-workflows-$(subst _,-,$(WORKFLOW))-workflow
OUTPUT_DIR ?= /tmp/$(WORKFLOW)/$(PARTNER)

.PHONY: build compile recompile run

build:
	# pixi exec, not pixi run: the workspace's compile env needs this package, which doesn't exist before the first build.
	pixi exec -s rattler-build -s hatch -s hatch-vcs -s pip ./publish/build.sh

compile: build
	./dev/recompile.sh $(WORKFLOW) --install

recompile: build
	./dev/recompile.sh $(WORKFLOW) --update

# Real data (no mock IO): param.yaml with partner and data source set to PARTNER.
run:
	mkdir -p $(OUTPUT_DIR)
	pixi run yq -y '.partner.var = "$(PARTNER)" | .er_client.data_source.name = "$(PARTNER)"' \
		workflows/$(WORKFLOW)/param.yaml > $(OUTPUT_DIR)/params.yaml
	cd $(PKG_DIR) && ECOSCOPE_WORKFLOWS_RESULTS="file://$(OUTPUT_DIR)" \
		pixi run ecoscope-workflows-$(subst _,-,$(WORKFLOW))-workflow run \
		--config-file $(OUTPUT_DIR)/params.yaml --execution-mode sequential --no-mock-io
