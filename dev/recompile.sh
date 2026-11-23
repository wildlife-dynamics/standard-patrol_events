#!/bin/bash
# Recompile spec.yaml into ecoscope-workflows-standard-patrol-events-workflow/.
#   ./dev/recompile.sh --install   the first time: a new lock file, and the packages installed
#   ./dev/recompile.sh --update    after that: keeps the lock file and bumps VERSION.yaml
set -e

flags=$*

pixi update --manifest-path pixi.toml -e compile

# (re)initialize dot executable to ensure graphviz is available
pixi run --manifest-path pixi.toml -e compile dot -c

echo "recompiling spec.yaml with flags '--clobber ${flags}'"
pixi run --manifest-path pixi.toml -e compile \
    wt-compiler compile --spec spec.yaml \
    --pkg-name-prefix=ecoscope-workflows \
    --results-env-var=ECOSCOPE_WORKFLOWS_RESULTS \
    --no-progress \
    --clobber ${flags}

# shortcut: until wt-compiler emits root rules (see the script)
python3 dev/add_root_rules.py ecoscope-workflows-standard-patrol-events-workflow/ecoscope_workflows_standard_patrol_events_workflow/rjsf.json
