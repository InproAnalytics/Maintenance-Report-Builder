"""
Maintenance Report Generator
----------------------------
Fill in the form, pick a client/project, and generate a German PDF report that
matches the standard maintenance-report design. UI is in English.

Run:  python -m streamlit run app.py
"""
import datetime as dt

import streamlit as st

from assets import logo_data_uri
from pdf_generator import generate_pdf

st.set_page_config(page_title="Maintenance Report Generator", page_icon="📄", layout="wide")

# --------------------------------------------------------------------- constants
GERMAN_MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

DEFAULT_OVERVIEW = (
    "Der monatliche Wartungsbericht stellt sicher, dass unsere Systeme und Services "
    "reibungslos funktionieren. Wir überwachen Datenanbindungen, prüfen API-Schnittstellen "
    "und gewährleisten die ordnungsgemäße Ausführung aller Reports. So erkennen wir "
    "frühzeitig mögliche Probleme und minimieren deren Auswirkungen."
)

STATUS_LABELS = {
    "green": "🟢 No error",
    "yellow": "🟡 Support provided / resolved",
    "red": "🔴 Acute error (unresolved)",
}
STATUS_KEYS = list(STATUS_LABELS.keys())


# --------------------------------------------------------------------- config from secrets

def _build_config():
    """Build the client/project CONFIG dict from Streamlit Secrets."""
    cfg = {}
    logos = st.secrets.get("client_logos", {})
    for client_name, client_data in st.secrets["clients"].items():
        projects = {}
        for proj_key, proj_data in client_data["projects"].items():
            # "default" in TOML maps to "" (no project name) in the app
            actual_key = "" if proj_key == "default" else proj_key
            projects[actual_key] = {
                "title": proj_data["title"],
                "quota": int(proj_data["quota"]),
                "filename_token": proj_data["filename_token"],
                "tools": [tuple(t) for t in proj_data["tools"]],
            }
        cfg[client_name] = {
            "client_logo_uri": logos.get(client_name, ""),
            "header_logo_h": client_data.get("header_logo_h", "36px"),
            "projects": projects,
        }
    return cfg


try:
    CONFIG = _build_config()
except Exception as _cfg_err:
    st.error(
        f"Client configuration could not be loaded from Streamlit Secrets: {_cfg_err}\n\n"
        "Make sure the **[clients]** section is present in `.streamlit/secrets.toml` "
        "(local) or **App Settings → Secrets** (Streamlit Cloud)."
    )
    st.stop()

_CLIENT_NAMES = list(CONFIG.keys())


def project_cfg(client, project):
    return CONFIG[client]["projects"][project]


def apply_defaults(client, project):
    cfg = project_cfg(client, project)
    st.session_state.title = cfg["title"]
    st.session_state.quotas = [{"label": "", "value": cfg["quota"]}]
    st.session_state.total_value = 0
    st.session_state.total_label = "Aufgewendete Stunden"
    st.session_state.use_h = False
    st.session_state.include_quota = False


# --------------------------------------------------------------------- shared helpers

def _on_quick_select_all():
    val = st.session_state.quick_select_all
    client = st.session_state.quick_client_sel
    for p in CONFIG[client]["projects"]:
        st.session_state[f"quick_proj_{p}"] = val


def build_filename(client: str, project_key: str, month_name: str, year: int) -> str:
    token = project_cfg(client, project_key)["filename_token"]
    parts = ["Monatsreport", f"{month_name} {year}", "-", client]
    if token:
        parts += ["-", token]
    return " ".join(parts) + ".pdf"


def build_empty_report_data(client: str, project_key: str, month_name: str, year: int) -> dict:
    cfg = project_cfg(client, project_key)
    return {
        "month_year_upper": f"{month_name.upper()} {year}",
        "title": cfg["title"],
        "overview": DEFAULT_OVERVIEW,
        "client_logo": CONFIG[client]["client_logo_uri"],
        "client_logo_height": CONFIG[client]["header_logo_h"],
        "company_logo": logo_data_uri("_company"),
        "sources": [
            {"name": t, "logo": logo_data_uri(t), "status": "green", "problem": ""}
            for t, _ in cfg["tools"]
        ],
        "incidents": [],
        "measures": [],
        "hours": {
            "total_label": "Aufgewendete Stunden",
            "total_value": 0,
            "suffix": "",
            "quotas": [{"label": "", "value": cfg["quota"]}],
            "billable_value": 0,
        },
    }


# --------------------------------------------------------------------- state init
_first_client = _CLIENT_NAMES[0]
_first_project = list(CONFIG[_first_client]["projects"].keys())[0]

if "initialized" not in st.session_state:
    today = dt.date.today()
    st.session_state.month_idx = today.month - 1
    st.session_state.year = today.year
    st.session_state.overview = DEFAULT_OVERVIEW
    st.session_state.client = _first_client
    st.session_state.project = _first_project
    st.session_state.sel_key = f"{_first_client}|{_first_project}"
    st.session_state.incidents = []
    st.session_state.measures = []
    apply_defaults(_first_client, _first_project)
    # quick-batch section
    st.session_state.quick_client_sel = _first_client
    st.session_state.quick_month_idx = today.month - 1
    st.session_state.quick_year = today.year
    st.session_state.quick_single_proj = False
    st.session_state.quick_select_all = False
    st.session_state.quick_prev_client = _first_client
    st.session_state.quick_pdfs = []
    for _cd in CONFIG.values():
        for _p in _cd["projects"]:
            if _p:
                st.session_state[f"quick_proj_{_p}"] = False
    st.session_state.initialized = True


# --------------------------------------------------------------------- callbacks
def add_incident():
    st.session_state.incidents.append(
        {"date": dt.date.today(), "description": "", "reason": "", "status": "behoben und abgeschlossen"}
    )

def remove_incident(i):
    st.session_state.incidents.pop(i)

def add_measure():
    st.session_state.measures.append({"nr": "", "text": ""})

def remove_measure(i):
    st.session_state.measures.pop(i)

def add_quota():
    st.session_state.quotas.append({"label": "", "value": 0})

def remove_quota(i):
    st.session_state.quotas.pop(i)


# --------------------------------------------------------------------- header
st.title("📄 Maintenance Report Generator")
st.caption("English form · German PDF output. Pick the client/project to load its defaults, then adjust anything.")

# ================================================================= QUICK BATCH SECTION
st.header("⚡ Quick empty reports (no incidents)")
st.caption(
    "Batch-generate clean no-incident reports — all tools green, default quota, hours 0. "
    "No editing needed."
)

qc1, qc2, qc3 = st.columns(3)
quick_client = qc1.selectbox("Client", _CLIENT_NAMES, key="quick_client_sel")
qc2.selectbox("Month", range(12), key="quick_month_idx", format_func=lambda i: GERMAN_MONTHS[i])
qc3.number_input("Year", min_value=2020, max_value=2100, step=1, key="quick_year")

# Clear stale PDFs and checkbox state whenever the client changes
if st.session_state.get("quick_prev_client") != quick_client:
    st.session_state.quick_pdfs = []
    st.session_state.quick_single_proj = False
    st.session_state.quick_select_all = False
    st.session_state.quick_prev_client = quick_client

# Determine whether this client has a single unnamed project or multiple named ones
_qprojects = list(CONFIG[quick_client]["projects"].keys())
_is_single = len(_qprojects) == 1 and _qprojects[0] == ""

if _is_single:
    _single_label = CONFIG[quick_client]["projects"][""]["title"]
    st.checkbox(f"{quick_client} ({_single_label})", key="quick_single_proj")
    selected_projects = [""] if st.session_state.quick_single_proj else []
else:
    st.checkbox("Select all", key="quick_select_all", on_change=_on_quick_select_all)
    _pcols = st.columns(len(_qprojects))
    for _col, _p in zip(_pcols, _qprojects):
        _col.checkbox(_p, key=f"quick_proj_{_p}")
    selected_projects = [p for p in _qprojects if st.session_state.get(f"quick_proj_{p}")]

# Generate
if st.button("⚡ Generate selected reports", type="primary", disabled=not selected_projects):
    _qmonth = GERMAN_MONTHS[st.session_state.quick_month_idx]
    _qyear = int(st.session_state.quick_year)
    _generated = []
    _errors = []
    with st.spinner(f"Rendering {len(selected_projects)} report(s)..."):
        for _proj_key in selected_projects:
            try:
                _data = build_empty_report_data(quick_client, _proj_key, _qmonth, _qyear)
                _pdf = generate_pdf(_data)
                _fname = build_filename(quick_client, _proj_key, _qmonth, _qyear)
                _label = _proj_key if _proj_key else quick_client
                _generated.append({"label": _label, "filename": _fname, "bytes": _pdf})
            except Exception as _e:  # noqa: BLE001
                _errors.append(f"{_proj_key or quick_client}: {_e}")
    st.session_state.quick_pdfs = _generated
    for _err in _errors:
        st.error(_err)

# Download buttons — rendered from session_state every run so clicking one keeps the others
for _item in st.session_state.get("quick_pdfs", []):
    st.download_button(
        f"⬇️ Download {_item['label']} report",
        data=_item["bytes"],
        file_name=_item["filename"],
        mime="application/pdf",
        key=f"qdl_{_item['label']}",
    )

st.divider()

# --------------------------------------------------------------------- 1. client/project
st.header("1 · Client & Project")
c1, c2, c3, c4 = st.columns(4)
client = c1.selectbox("Client", _CLIENT_NAMES,
                      index=_CLIENT_NAMES.index(st.session_state.client) if st.session_state.client in _CLIENT_NAMES else 0)
projects = list(CONFIG[client]["projects"].keys())
proj_labels = {p: (p if p else "(no project)") for p in projects}
project = c2.selectbox("Project", projects,
                       index=projects.index(st.session_state.project) if st.session_state.project in projects else 0,
                       format_func=lambda p: proj_labels[p])

sel_key = f"{client}|{project}"
if sel_key != st.session_state.sel_key:
    st.session_state.client = client
    st.session_state.project = project
    st.session_state.sel_key = sel_key
    apply_defaults(client, project)
    # Clear stale keyed-widget state for the dynamic rows so they re-init
    # with the newly loaded project defaults (otherwise old values stick).
    for k in list(st.session_state.keys()):
        if k.startswith(("src_", "inc_", "m_", "q_")):
            del st.session_state[k]
    st.rerun()

st.session_state.month_idx = c3.selectbox("Month", range(12),
                                           index=st.session_state.month_idx,
                                           format_func=lambda i: GERMAN_MONTHS[i])
st.session_state.year = c4.number_input("Year", min_value=2020, max_value=2100,
                                        value=st.session_state.year, step=1)

st.session_state.title = st.text_input("Report title (big heading on page 1)", value=st.session_state.title)
st.session_state.overview = st.text_area("Overview text (Übersicht)", value=st.session_state.overview, height=110)

# --------------------------------------------------------------------- 2. sources
st.header("2 · Data sources")
st.caption("Tool list is fixed for the selected Client/Project. Set a status and an optional problem note for each tool.")

for i, (tool_name, _) in enumerate(project_cfg(client, project)["tools"]):
    c1, c2, c3 = st.columns([2.3, 2, 4.2])
    c1.write("")
    c1.markdown(f"**{tool_name}**")
    c2.selectbox(
        "Status", STATUS_KEYS,
        index=0,
        format_func=lambda k: STATUS_LABELS[k],
        key=f"src_status_{i}",
    )
    c3.text_input(
        "Problem description",
        placeholder="Blank shows '-' in the PDF",
        key=f"src_problem_{i}",
    )

# --------------------------------------------------------------------- 3. incidents
st.header("3 · Incidents")
st.caption("The Incident Nr is generated from the date (05.06.2026 → 260605). Leave empty for a 'no incidents' report.")

for i, inc in enumerate(st.session_state.incidents):
    nr = inc["date"].strftime("%y%m%d")
    with st.expander(f"Incident {i + 1} · Nr {nr}", expanded=True):
        a, b = st.columns(2)
        inc["date"] = a.date_input("Date", value=inc["date"], key=f"inc_date_{i}", format="DD.MM.YYYY")
        b.text_input("Generated Incident Nr", value=inc["date"].strftime("%y%m%d"), key=f"inc_nr_{i}", disabled=True)
        inc["description"] = st.text_input("Description (Beschreibung)", value=inc["description"], key=f"inc_desc_{i}")
        inc["reason"] = st.text_input("Reason (Grund)", value=inc["reason"], key=f"inc_reason_{i}")
        inc["status"] = st.text_input("Status", value=inc["status"], key=f"inc_status_{i}")
        st.button("🗑️ Remove incident", key=f"inc_del_{i}", on_click=remove_incident, args=(i,))

st.button("➕ Add incident", on_click=add_incident)

# --------------------------------------------------------------------- 4. support measures
st.header("4 · Support measures (Support Maßnahmen)")
st.caption("Grouped by an ID (often the incident Nr, but can differ). One measure per line. "
           "If none, the report shows the standard 'no maintenance cases' note.")

for i, m in enumerate(st.session_state.measures):
    with st.expander(f"Measure group {i + 1} · {m['nr'] or '(id)'}", expanded=True):
        m["nr"] = st.text_input("ID / Nr", value=m["nr"], key=f"m_nr_{i}")
        m["text"] = st.text_area("Measures — one per line", value=m["text"], height=110, key=f"m_text_{i}")
        st.button("🗑️ Remove group", key=f"m_del_{i}", on_click=remove_measure, args=(i,))

st.button("➕ Add measure group", on_click=add_measure)

# --------------------------------------------------------------------- 5. hours
st.header("5 · Hours (Aufgewendete Stunden)")
h1, h2, h3 = st.columns(3)
st.session_state.total_label = h1.selectbox(
    "Total label", ["Aufgewendete Stunden", "Gesamtaufwand"],
    index=["Aufgewendete Stunden", "Gesamtaufwand"].index(st.session_state.get("total_label", "Aufgewendete Stunden")),
)
st.session_state.total_value = h2.number_input("Total value", min_value=0,
                                               value=int(st.session_state.get("total_value", 0)), step=1)
st.session_state.use_h = h3.checkbox("Append 'h' to numbers", value=st.session_state.get("use_h", False))

include_quota = st.checkbox(
    "Include free quota line (Verfügbares Gratiskontingent)",
    value=st.session_state.get("include_quota", False),
    help="Uncheck to leave the Gratiskontingent line out of the PDF entirely.",
)
st.session_state.include_quota = include_quota
if include_quota:
    st.markdown("**Free quota lines (Gratiskontingent)**")
    for i, q in enumerate(st.session_state.quotas):
        a, b, c = st.columns([3, 1.5, 0.6])
        q["label"] = a.text_input("Label suffix (e.g. project name; blank = none)", value=q["label"], key=f"q_label_{i}")
        q["value"] = b.number_input("Hours", min_value=0, value=int(q["value"]), step=1, key=f"q_val_{i}")
        c.write(""); c.write("")
        c.button("🗑️", key=f"q_del_{i}", on_click=remove_quota, args=(i,))
    st.button("➕ Add quota line", on_click=add_quota)
else:
    st.caption("No free quota line will appear in the PDF.")

total_quota = sum(int(q["value"]) for q in st.session_state.quotas) if include_quota else 0
auto_billable = max(0, int(st.session_state.total_value) - total_quota)
ov = st.checkbox("Override billable hours")
if ov:
    billable = st.number_input("Billable (Zu verrechnende Leistungsstunden)", min_value=0, value=auto_billable, step=1)
else:
    billable = auto_billable
    st.info(f"Billable (auto): **{billable}**  =  {st.session_state.total_value} − {total_quota}")

# --------------------------------------------------------------------- 6. generate
st.header("6 · Generate")

month_name = GERMAN_MONTHS[st.session_state.month_idx]
month_year_upper = f"{month_name.upper()} {st.session_state.year}"

filename = build_filename(st.session_state.client, st.session_state.project, month_name, st.session_state.year)

st.caption(f"Output file name: **{filename}**")

if st.button("📄 Generate PDF", type="primary"):
    suffix = "h" if st.session_state.use_h else ""
    tools = project_cfg(client, project)["tools"]
    sources = [
        {
            "name": tool_name,
            "logo": logo_data_uri(tool_name),
            "status": st.session_state.get(f"src_status_{i}", "green"),
            "problem": st.session_state.get(f"src_problem_{i}", ""),
        }
        for i, (tool_name, _) in enumerate(tools)
    ]
    incidents = [
        {
            "nr": inc["date"].strftime("%y%m%d"),
            "description": inc["description"],
            "reason": inc["reason"],
            "date": inc["date"].strftime("%d.%m.%Y"),
            "status": inc["status"],
        }
        for inc in st.session_state.incidents
    ]
    measures = [
        {"nr": m["nr"], "items": [ln.strip() for ln in m["text"].splitlines() if ln.strip()]}
        for m in st.session_state.measures
        if m["nr"] or m["text"].strip()
    ]
    data = {
        "month_year_upper": month_year_upper,
        "title": st.session_state.title,
        "overview": st.session_state.overview,
        "client_logo": CONFIG[st.session_state.client]["client_logo_uri"],
        "client_logo_height": CONFIG[st.session_state.client]["header_logo_h"],
        "company_logo": logo_data_uri("_company"),
        "sources": sources,
        "incidents": incidents,
        "measures": measures,
        "hours": {
            "total_label": st.session_state.total_label,
            "total_value": st.session_state.total_value,
            "suffix": suffix,
            "quotas": ([{"label": q["label"], "value": q["value"]} for q in st.session_state.quotas] if include_quota else []),
            "billable_value": billable,
        },
    }
    try:
        with st.spinner("Rendering PDF..."):
            pdf_bytes = generate_pdf(data)
        st.success("PDF generated.")
        st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=filename, mime="application/pdf")
    except Exception as e:  # noqa: BLE001
        st.error(f"PDF generation failed: {e}")
        st.caption("If this is a Playwright error, run `python -m playwright install chromium` once.")
