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
- **Real logos, cleaned up.** Company and tool logos live in the assets folder; the **client
  logos load privately from Streamlit Secrets** (never stored in the repo). Logos that ship on
  a white or checkerboard background get that background
  removed automatically, and everything is down‑scaled before it goes into the PDF so
  the file stays small and opens quickly.
- **Incidents the easy way.** You pick a date and the Incident‑Nr is generated for you
  in the `YYMMDD` house format (e.g. `05.06.2026` → `260605`). No incidents that month?
  The report prints the standard "no maintenance cases" note instead of an empty table.
- **Flexible hours block.** Total label ("Aufgewendete Stunden" or "Gesamtaufwand"),
  an optional free quota (Gratiskontingent) that you can switch on only when it applies,
  and a billable figure that's calculated for you (with a manual override when you need it).
- **Sensible file names.** The PDF is named exactly the way we file them, including
  client and project where applicable.

---

## Clients & projects

Client names, project names, client logos, and default tool lists are loaded from
**Streamlit Secrets** — they are not stored in this repository. Configure them in
`.streamlit/secrets.toml` (local) or **App Settings → Secrets** (Streamlit Cloud).
See `SECRETS_TO_PASTE.txt` (generated locally, gitignored) for the full template.

---

## How it's put together

The app is intentionally small — four files plus an assets folder:

| File / folder                | What it's responsible for                                                        |
| ---------------------------- | -------------------------------------------------------------------------------- |
| `app.py`                     | The Streamlit form: client/project selection, sources, incidents, hours, state.  |
| `assets.py`                  | Loads the logos, removes their backgrounds, down‑scales and base64‑encodes them. |
| `pdf_generator.py`           | Fills the HTML template with your data and renders it to a PDF.                   |
| `templates/report.html`      | The actual report design (HTML + CSS, Jinja2). All styling lives here.           |
| `Maintenance Report Assets/` | Company and tool logo image files (client logos live in Streamlit Secrets).       |

**The flow, end to end:** you fill in the form in `app.py` → the values are collected
into a single data dictionary → `pdf_generator.py` renders `templates/report.html` with
that data → the finished PDF is offered as a download.

**Rendering engine.** The PDF is rendered with **WeasyPrint**, which needs no browser — this is
what runs both locally and on Streamlit Cloud. On Linux/Streamlit Cloud, WeasyPrint's system
libraries are installed from `packages.txt` (already in the repo). The code can optionally use
headless Chromium (Playwright) if it happens to be installed, but that is not required.

---

## Getting started

You'll need **Python 3.10+**.

```bash
# 1. Install the dependencies
python -m pip install -r requirements.txt

# 2. Run the app
python -m streamlit run app.py
```

Your browser opens with the form. Fill it in, click **Generate PDF**, then **Download PDF**.

> **Windows note:** if `streamlit` isn't recognised as a command, prefix it with `python -m`
> (e.g. `python -m streamlit run app.py`). That avoids needing it on your PATH. If `python`
> itself isn't found, try `py` instead (`py -m streamlit run app.py`).

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
- **Add or change a client / project / default tool set / quota:** edit the `[clients]`
  section in your secrets (`.streamlit/secrets.toml` locally, or the Streamlit Cloud
  Secrets UI). No code changes needed.
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
- **`streamlit` "not recognized".** Use `python -m streamlit …` (see the Windows note above).
- **PDF generation error mentioning WeasyPrint / Pango / Cairo.** WeasyPrint needs system
  libraries; on Streamlit Cloud they're installed from `packages.txt`. Locally, install
  WeasyPrint's system dependencies per its documentation for your OS.
- **A logo isn't appearing.** Check that the file name in `Maintenance Report Assets/` exactly
  matches the entry in the `LOGOS` map in `assets.py` (including spaces and extension).

---

## Requirements

See `requirements.txt`. In short: `streamlit`, `jinja2`, `weasyprint` (PDF renderer), and
`Pillow` (logo image handling). On Linux/Streamlit Cloud, WeasyPrint's system libraries are
installed from `packages.txt`.
