#!/bin/bash
# Usage: dev/recompile.sh <workflow> [--install|--update]. Never hand-edit the generated workflow package.
set -e

workflow=$1
shift
flags=$*

pixi update --manifest-path pixi.toml -e compile
pixi run --manifest-path pixi.toml -e compile dot -c

echo "recompiling workflows/${workflow}/spec.yaml with flags '--clobber ${flags}'"
pixi run --manifest-path pixi.toml -e compile \
    wt-compiler compile --spec workflows/${workflow}/spec.yaml --clobber ${flags}
