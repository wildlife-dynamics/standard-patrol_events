#!/bin/bash
set -e

# Builds the data package from a wd-partner-tasks checkout into the local channel.
PARTNER_TASKS=${PARTNER_TASKS:?set PARTNER_TASKS to a wd-partner-tasks checkout}
RECIPES=(
    "release/ecoscope-workflows-ext-standard-patrol-events"
)
OUT=/tmp/ecoscope-workflows-custom/release/artifacts
project_root=$PARTNER_TASKS/src/ecoscope-workflows-ext-standard-patrol-events
export HATCH_VCS_VERSION=$(cd $project_root && hatch version)
echo "HATCH_VCS_VERSION=$HATCH_VCS_VERSION"

echo "Building recipes: ${RECIPES[@]}"

# The channel directory is shared with other packages (e.g. ext-custom): remove only our own artifacts.
mkdir -p $OUT
rm -f $OUT/*/ecoscope-workflows-ext-standard-patrol-events-*.conda

for rec in "${RECIPES[@]}"; do
    echo "Building $rec"
    rattler-build build \
    --recipe $PARTNER_TASKS/publish/recipes/${rec}.yaml \
    --output-dir $OUT \
    --channel https://prefix.dev/ecoscope-workflows \
    --channel conda-forge
done
