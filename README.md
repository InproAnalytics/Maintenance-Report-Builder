# Maintenance Report Generator

A small internal tool that turns the monthly maintenance check‑up into a finished,
client‑ready PDF in about a minute.

Every month we send each client a two‑page **Wartungsreport** — page one is the
PowerBI/data‑source status overview, page two is the incident report with the
support work and the hours. Building those by hand in a design tool was slow and
easy to get inconsistent. This app keeps the layout fixed and on‑brand, and lets
whoever is on duty just fill in a short form and hit **Generate**.

The form is in English so it's easy to work with; the **PDF it produces is in
German**, matching the report our clients already receive.

---

## What it does

- **Pick a client and project, and the rest configures itself.** The report title,
  the client logo in the header, the list of monitored tools, and the default free‑hour
  quota all switch automatically to match the selection.
- **Real logos, cleaned up.** Client, company and tool logos are pulled from an assets
  folder. Logos that ship on a white or checkerboard background get that background
  removed automatically, and everything is down‑scaled before it goes into the PDF so
  the file stays small and opens quickly.
- **Incidents the easy way.** You pick a date and the Incident‑Nr is generated for you
  in the `YYMMDD` house format (e.g. `05.06.2026` → `260605`). No incidents that month?
  The report prints the standard "no maintenance cases" note instead of an empty table.
- **Flexible hours block.** Total label ("Aufgewendete Stunden" or "Gesamtaufwand"),
  an optional free quota (Gratiskontingent) that you can switch on only when it applies,
  and a billable figure that's calculated for you (with a manual override when you need it).
- **Sensible file names.** The PDF is named exactly the way we file them, e.g.
  `Monatsreport Mai 2026 - Haidegg - Apfelsorten.pdf`.

---

## Clients & projects

Selecting a client/project loads these defaults (you can still adjust status and notes
per report):

| Client  | Project        | Report title    | Monitored tools                                            | Free quota |
| ------- | -------------- | --------------- | ---------------------------------------------------------- | ---------- |
| Russ    | —              | PowerBI         | Commitly, Excel, timetac, Power BI                         | 1 h        |
| Haidegg | FieldClimate   | FieldClimate    | FieldClimate, Power BI, Microsoft Azure                    | 2 h        |
| Haidegg | Apfelsorten    | Apfelsorten     | SharePoint, Power BI, Microsoft Azure                      | 2 h        |
| Haidegg | PV‑Monitoring  | PV‑Monitoring   | SolarEdge, SunGrow, FusionSolar, Power BI, Microsoft Azure | 4 h        |

---

## How it's put together

The app is intentionally small — four files plus an assets folder:

| File / folder                | What it's responsible for                                                        |
| ---------------------------- | -------------------------------------------------------------------------------- |
| `app.py`                     | The Streamlit form: client/project selection, sources, incidents, hours, state.  |
| `assets.py`                  | Loads the logos, removes their backgrounds, down‑scales and base64‑encodes them. |
| `pdf_generator.py`           | Fills the HTML template with your data and renders it to a PDF.                   |
| `templates/report.html`      | The actual report design (HTML + CSS, Jinja2). All styling lives here.           |
| `Maintenance Report Assets/` | Client, company and tool logo image files.                                       |

**The flow, end to end:** you fill in the form in `app.py` → the values are collected
into a single data dictionary → `pdf_generator.py` renders `templates/report.html` with
that data → the finished PDF is offered as a download.

**Rendering engine.** The PDF is produced with headless Chromium (via Playwright), which
reproduces the gradient and layout faithfully. If Chromium isn't available on the machine,
the app automatically falls back to WeasyPrint, so it still works.

---

## Getting started

You'll need **Python 3.10+**.

```bash
# 1. Install the dependencies
python -m pip install -r requirements.txt

# 2. Install the Chromium build Playwright uses (one time)
python -m playwright install chromium

# 3. Run the app
python -m streamlit run app.py
```

Your browser opens with the form. Fill it in, click **Generate PDF**, then **Download PDF**.

> **Windows note:** if `streamlit` or `playwright` aren't recognised as commands, always
> prefix them with `python -m` (e.g. `python -m streamlit run app.py`). That avoids needing
> those tools on your PATH. If `python` itself isn't found, try `py` instead
> (`py -m streamlit run app.py`).

---

## Day‑to‑day usage

1. **Client & period** – choose the client, the project, and the report month/year.
2. **Data sources** – the monitored tools for that project appear automatically. For each one,
   set a status and, if there was an issue, a short problem note:
   - 🟢 **Kein Fehler aufgetreten** – no error (the default)
   - 🟡 **Supportleistung beansprucht** – support was needed and the issue is resolved
   - 🔴 **Akuter Fehler** – an unresolved error
3. **Incidents** – add a row per incident; the Incident‑Nr is generated from the date.
   Leave it empty for a clean month.
4. **Support measures** – the work carried out, grouped by an ID (usually the incident number,
   but it can differ), one bullet per line.
5. **Hours** – enter the total; optionally enable the free quota; the billable figure is
   worked out for you.
6. **Generate** – download the PDF with the correct file name.

---

## Customising it

Most changes don't need you to touch the rendering code.

- **Change the look** (fonts, colours, spacing, logo sizes): edit `templates/report.html`.
  All the CSS is at the top of that file. Logo display sizes live in the
  `.source .left .logo img` and `.brand img` rules.
- **Add or change a client / project / default tool set / quota:** edit the `CONFIG`
  dictionary near the top of `app.py`. It's a plain Python dictionary that mirrors the
  table above.
- **Add a tool or swap a logo:** drop the image into `Maintenance Report Assets/` and add an
  entry to the `LOGOS` map in `assets.py` (friendly name → file name).
  **Transparent PNGs work best** — JPGs can't store transparency, so they arrive with a
  background that has to be cleaned up. The cleanup is automatic, but a clean PNG always
  looks crisper.

---

## Troubleshooting

- **A change to the code isn't showing up.** Stop Streamlit fully (Ctrl+C in the terminal),
  start it again, and hard‑refresh the browser (Ctrl+Shift+R). Streamlit keeps some state
  between reruns and won't always pick up structural changes on a soft refresh.
- **`playwright` / `streamlit` "not recognized".** Use `python -m playwright …` /
  `python -m streamlit …` (see the Windows note above).
- **PDF generation error mentioning Playwright/Chromium.** Run
  `python -m playwright install chromium` once. If that machine can't install Chromium,
  the WeasyPrint fallback still renders the PDF.
- **A logo isn't appearing.** Check that the file name in `Maintenance Report Assets/` exactly
  matches the entry in the `LOGOS` map in `assets.py` (including spaces and extension).

---

## Requirements

See `requirements.txt`. In short: `streamlit`, `jinja2`, `playwright` (primary renderer) and
`weasyprint` (fallback renderer).
