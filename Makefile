WORKFLOW ?= standard_patrol_events

.PHONY: build compile recompile run

build:
	# pixi exec, not pixi run: the workspace's compile env needs this package, which doesn't exist before the first build.
	pixi exec -s rattler-build -s hatch -s hatch-vcs -s pip ./publish/build.sh

compile: build
	./dev/recompile.sh $(WORKFLOW) --install

recompile: build
	./dev/recompile.sh $(WORKFLOW) --update

run:
	@echo "spec added in B3 (usage: make run PARTNER=<name>)"
