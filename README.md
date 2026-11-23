# Standard Patrol & Events Report

This Ecoscope workflow creates a report on patrols and events recorded in EarthRanger over a period you choose. It builds an interactive dashboard and a Word report, in English, Spanish or Portuguese, that a site can send to its authority each month or quarter.

The report brings together where the patrols went and how much effort they put in, who went, what they found along the way, and maps of where effort and events cluster. It works for any EarthRanger site: every difference between sites is a setting on the config page.

---

## How to run it

Open the workflow in Ecoscope and fill in the config page from top to bottom. Only the first three need filling in; everything else has a default that works on a first run.

1. **Workflow Details:** a name for this run, for example `Los Alerces · October 2026`.
2. **Data Source:** the site's EarthRanger connection.
3. **Time Range:** the reporting period, usually a month or a quarter, with the site's timezone.
4. **Patrol Filter** (optional): tick **Team**, **Team Leader** or **Single Patrol** to narrow the patrols. A single patrol hides the settings that don't apply to it.
5. **Patrol Type:** which patrol types to include; empty means all.
6. **Patrol Effort:** how the effort table is grouped (patrol type, team, leader, individual patrol or an area of a map layer) and which columns it shows.
7. **Patrol Grouping:** how patrol tracks are coloured on the map.
8. **Events:** all events in the period, or only the events linked to the patrols.
9. **Event Type** and **Event State:** which events to include; empty means all.
10. **Event Grouping:** group events by event type or by event category, in the tables, charts and map.
11. **Event Details:** show every field, or choose the fields per event type.
12. **Report Settings:** the title, subtitle and language, and which sections the report includes (all are on by default).
13. **Download Event Attachments:** event photos are included in the report, up to 50 by default. Tick **Leave Out Event Photos** to skip them.
14. Press **Run**.

**Base Maps** sits under Advanced and is already set up, so you can leave it as it is.

### What it reads from EarthRanger

- **Patrols** in the period, with their type, team and GPS route. Where the site records patrols as **legs** (a new leg when the transport, leader or team changes), each leg keeps its own leader, team and form.
- **Events** recorded in the period, with their type, category, state, priority, details and photos.
- **Map layers** (optional), when you group patrol effort by area.

The report can only show what was recorded: a patrol without a GPS route has no distance, and a site that doesn't use legs or event states simply shows less.

---

## The dashboard

The four numbers at the top give the period at a glance. Below them, the map shows where patrols went and where events were recorded, the tables show effort and legs, and the density maps and charts show where and when things happened. The Word report is in the dashboard's files, ready to download.

| On the dashboard | What it shows |
|---|---|
| Patrols | How many patrols there were in the period |
| Distance | How far they travelled, measured on the GPS routes |
| Patrol hours | How long they lasted in total |
| Events | How many events were recorded |
| Patrol tracks and events | The routes coloured by the patrol grouping, with the events marked |
| Patrol effort | Patrols, distance, hours and more for each group, with a total; groups run from least to most distance |
| Patrol legs | Each leg's patrol, type, leader, team, start, end, distance and time |
| Patrol time density | Where patrols spent their time, as a share of all patrol time |
| Event density | How many events were recorded in each grid cell |
| Events | Events by type or category |
| Events by month | Event counts over time |
| Event summary | Counts by type or category |
| Event records | One row per event, with the chosen details |

---

## The Word report

The report follows the order a technician would write it in, with numbered sections. A section you switch off in **Report Settings** disappears and the numbering closes up.

- **Cover.** The title, subtitle, period, who generated it and when.
- **Headline figures.** Patrols, distance, hours, patrol days and events.
- **Personnel.** Who went on patrol, leg by leg.
- **Patrol effort.** The effort table, grouped as you chose.
- **Maps.** The patrol tracks with events, the patrol time density map and the event density map.
- **Event summary.** Events by type or category, events by month, and events by category and priority.
- **Event details.** One table of every event with its details, or one table per event type.
- **Photos.** The event photos with their captions.
- **Conclusions.** An empty box for the technician to write in.

Headings, captions and labels are in the language you chose, and times are in the timezone you chose.

---

## Common questions

**The run stops with "Patrol 70 not found in the report period".**
The patrol falls outside the dates you chose, or the number isn't right. Widen the time range and check the number in EarthRanger.

**The run stops with "No patrol in the period was led by …".**
The leader's name doesn't match any patrol leader in the period. The message lists the leaders it found; type the name as it appears there.

**The run stops with "Map Layer '…' not found or has no areas".**
The map layer chosen for grouping effort by area doesn't exist on the site, or it's empty. Pick another layer, or group effort another way.

**The dashboard and report are empty.**
No patrols or events matched the period and filters. Widen the time range or clear the filters.

**Distance shows 0 km for some patrols.**
Those patrols have little or no GPS route, for example when the tracking device was off.

**Can the report look different?**
Yes. The layout is a Word file in the task package, [`standard_patrol_events.docx`](https://github.com/wildlife-dynamics/wd-partner_tasks/blob/main/src/ecoscope-workflows-ext-standard-patrol-events/ecoscope_workflows_ext_standard_patrol_events/data/standard_patrol_events.docx). Ask the Ecoscope team for changes.

---

<sub>For developers: compiling, testing and releasing the workflow are covered in [DEVELOPMENT.md](DEVELOPMENT.md).</sub>
