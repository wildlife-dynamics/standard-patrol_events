# Standard Patrol & Events

An Ecoscope workflow that turns an EarthRanger site's patrols and events for a chosen period into a dashboard and a Word report (English, Spanish or Portuguese).

- `spec.yaml`, `layout.json`, `metadata.yaml`, `test-cases.yaml`: the workflow, its dashboard layout and its test cases
- `ecoscope-workflows-standard-patrol-events-workflow/`: the compiled workflow (don't edit by hand)
- Tasks come from [`ecoscope-workflows-ext-standard-patrol-events`](https://github.com/wildlife-dynamics/wd-partner_tasks/tree/main/src/ecoscope-workflows-ext-standard-patrol-events) in wd-partner-tasks, published to `repo.prefix.dev/ecoscope-workflows-custom`

## Recompile

```bash
./dev/recompile.sh --update
```

## Run a test case

```bash
pixi run bash dev/pytest-cli.sh standard_patrol_events --case apncentral
```

## Dev loop (editable tasks)

With a wd-partner-tasks checkout next to this repo (or `PARTNER_TASKS=<path>`): `make dev` compiles against the editable task package, `make run-dev PARTNER=<case>` runs a test case with the step cache, `make test` runs the spec checks. Run `make recompile` before committing.
