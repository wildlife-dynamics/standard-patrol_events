# Patrol legs in the report and dashboard — design

Date: 2026-11-18 · Status: draft for approval

## Why

EarthRanger's new patrol model splits a patrol into legs (tramos): each leg has its own
transport (patrol type), leader, members, times and forms (shared mission fields and
per-transport fields such as plate or engine hours). APN is moving to it and other sites
will follow. Readers of a multi-leg patrol want to know who was on each part, how the
patrol travelled, and how much effort went into each way of travelling. Today the report
shows one track and one colour per patrol, and the legs table repeats the patrol number
with no grouping, which reads like duplicate patrols.

## Goals

- One table that shows each patrol once, with its legs in order beneath it.
- A map whose colours and legend show how patrols travelled (per leg, not per patrol).
- Effort (km, hours) available per way of travelling, exact rather than approximated.

## Non-goals

- Patrol totals inside the patrol cell (can come later; the cell has room).
- Merged cells on the dashboard (its table widget can't merge; see below).
- Resolving the old test setup's leg fields (APN-central #66–69 `medio_desplazamiento`).

## Anti-goals

- Anything that makes a single-leg patrol (most patrols on most sites) look more complex
  than a plain patrol list.

## Approaches considered

- **A. Legs as the unit everywhere (chosen).** One track per leg; map coloured by leg
  transport; effort can group by transport; table grouped by patrol with one line per
  leg. Exact per-leg numbers, consistent across map, table and effort.
- **B. Patrol as the unit, legs as detail.** One track per patrol coloured by leg; nested
  table; effort stays per patrol type. Simpler, but per-transport effort is approximate.
- **C. Minimal.** Leg column in the table and leg info in the map tooltip only. Doesn't
  answer "effort per way of travelling".

## Design

**Data.** Core already fetches GPS points per leg and stamps each point with the leg id
(`patrol_segment_id`) and that leg's own type. Keep the leg id through the track
pipeline (today the spec drops it) and build one track per leg. Headline counts stay per
patrol (patrols, total km, total hours, patrol days).

**Report table** (replaces today's legs table):

| Patrullaje | Tramo | Medio | Inicio – Fin | km | Horas | Líder | Integrantes | Detalles |
|---|---|---|---|---|---|---|---|---|
| **#70** · 11 nov · 2 tramos *(merged over its legs)* | 1 | Pedestre | 09:08 – 09:10 | 0.1 | 0.0 | Andres | … | Mandato: … |
| | 2 | Camioneta | 09:10 – 09:11 | — | — | Andres | … | Patente: HAU-292 · … |

- The patrol cell is merged down over its legs (docxtpl vertical merge), showing the
  patrol number, date and leg count. Legs in start-time order.
- km and hours per leg come from that leg's track; "—" when the leg recorded no points.
- Labels follow the report language: Tramo / Leg / Trecho.

**Dashboard table:** same columns, one row per leg, patrol number repeated, sorted so a
patrol's legs sit together (the widget can't merge cells).

**Map:** tracks coloured by leg transport; the legend lists the transports actually
used. Tooltip: patrol number, leg number, leader.

**Effort table:** a new grouping option, "transport" (leg type), next to the existing
ones.

## Calls made (not discussed; correct me)

- Legs with no transport show "Sin tipo" / "No type" / "Sem tipo" (report language)
  instead of "-", in the table and the map legend.
- Today's "#66 · 1/2" patrol labels are replaced by the merged cell and Tramo column.
- The per-leg km/hours columns are included in the table (they answer the effort question
  at a glance); the Integrantes column stays.

## Left to the builder

Task names, where the leg-to-track join lives, test fixtures, and the exact docxtpl
template markup for the merged cell.
