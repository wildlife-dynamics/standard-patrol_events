# Development

- `spec.yaml`, `layout.json`, `metadata.yaml`, `test-cases.yaml`: the workflow, its dashboard layout and its test cases
- `ecoscope-workflows-standard-patrol-events-workflow/`: the compiled workflow (don't edit by hand)
- Tasks come from [`ecoscope-workflows-ext-standard-patrol-events`](https://github.com/wildlife-dynamics/wd-partner_tasks/tree/main/src/ecoscope-workflows-ext-standard-patrol-events) in wd-partner-tasks, published to `repo.prefix.dev/ecoscope-workflows-custom` with a `standard-patrol-events-v<version>` tag

## Recompile

```bash
./dev/recompile.sh --update
```

## Run a test case

```bash
pixi run bash dev/pytest-cli.sh standard_patrol_events --case apncentral
```

CI runs every test case; it needs the repo secrets `APN_*`, `APNCENTRAL_*`, `BELIZE_*`, `COSTAECUADOR_*` and `MEP_*` (`_SERVER`, `_USERNAME`, `_PASSWORD`).

## Dev loop (editable tasks)

With a wd-partner-tasks checkout next to this repo (or `PARTNER_TASKS=<path>`): `make dev` compiles against the editable task package, `make run-dev PARTNER=<case>` runs a test case with the step cache, `make test` runs the spec checks. `make dev` rewrites the compiled package, so run `make recompile` before committing.

## README diagrams

`docs/images/*.svg` are exported from the matching `*.excalidraw` files. To change one, open the `.excalidraw` file at [excalidraw.com](https://excalidraw.com), edit it, and export it as SVG with "Embed scene" off.

## Releasing a task change

1. Merge the change in wd-partner-tasks and tag `standard-patrol-events-v<next>`.
2. Pin that version in `spec.yaml` and recompile.
