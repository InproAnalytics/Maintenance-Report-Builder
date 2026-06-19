"""Render the maintenance report HTML template and convert it to a PDF.

PDF rendering prefers headless Chromium via Playwright (most faithful gradient
rendering), and falls back to WeasyPrint if Chromium isn't available.
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_html(data: dict) -> str:
    """Render the report template to an HTML string."""
    return _env.get_template("report.html").render(**data)


def _pdf_via_playwright(html: str) -> bytes:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        pdf = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()
    return pdf


def _pdf_via_weasyprint(html: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html).write_pdf()


def html_to_pdf_bytes(html: str) -> bytes:
    """Convert HTML to PDF bytes, trying Chromium first then WeasyPrint."""
    errors = []
    for backend in (_pdf_via_playwright, _pdf_via_weasyprint):
        try:
            return backend(html)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{backend.__name__}: {e}")
    raise RuntimeError(
        "Could not generate PDF with any backend.\n"
        + "\n".join(errors)
        + "\n\nFix: run `python -m playwright install chromium`, or install WeasyPrint."
    )


def generate_pdf(data: dict) -> bytes:
    """Render template with data and return PDF bytes."""
    return html_to_pdf_bytes(render_html(data))


if __name__ == "__main__":
    # Quick sample render for local testing (no client logo — loaded from secrets at runtime).
    from assets import logo_data_uri

    sample = {
        "month_year_upper": "JANUAR 2026",
        "title": "PowerBI",
        "overview": (
            "Der monatliche Wartungsbericht stellt sicher, dass unsere Systeme und "
            "Services reibungslos funktionieren. Wir überwachen Datenanbindungen, "
            "prüfen API-Schnittstellen und gewährleisten die ordnungsgemäße Ausführung "
            "aller Reports. So erkennen wir frühzeitig mögliche Probleme und minimieren "
            "deren Auswirkungen."
        ),
        "client_logo": "",
        "client_logo_height": "36px",
        "company_logo": logo_data_uri("_company"),
        "sources": [
            {"name": "COMMITLY", "logo": logo_data_uri("COMMITLY"), "status": "green", "problem": ""},
            {"name": "Excel", "logo": logo_data_uri("Excel"), "status": "green", "problem": ""},
            {"name": "timetac", "logo": logo_data_uri("timetac"), "status": "yellow",
             "problem": "Fehlende Dartstellung der 2026er Projekte"},
            {"name": "Power BI", "logo": logo_data_uri("Power BI"), "status": "yellow",
             "problem": "Filterung nicht-leistungsbare Stunde"},
        ],
        "incidents": [
            {"nr": "260201", "description": "Stunden der 2026er Projekte werden nicht angezeigt",
             "reason": "Fehler bei Datentransfer von TimeTac nach Azure Cloud",
             "date": "01.02.2026", "status": "behoben und abgeschlossen"},
            {"nr": "260130", "description": "Nicht-leistungsbare Stunden zeigen falsche Stundenbuchungen an",
             "reason": "Filterung in PowerBI", "date": "30.01.2026", "status": "behoben und abgeschlossen"},
        ],
        "measures": [
            {"nr": "260130", "items": [
                "Implementierung erweiterte Filterlogik um ZA/Urlaub und weitere Kategorien auf der Berechnung rauszufiltern",
                "Validierung der Funktionalität und Integrität der Berechnungen",
                "Erneutes Publishen des PowerBI Reports"]},
            {"nr": "260201", "items": [
                "Fehleranalyse innerhalb der Azure Cloud Ressourcen insbesondere die Funktionalität des Docker Containers",
                "Fehleranalyse der TimeTac API",
                "Implementierung einer Azure Function für den täglichen Datentransfers der TimeTac Daten.",
                "Validierung und Testing der Funktionalitäten",
                "Deployment auf die bestehende Azure Umgebung"]},
        ],
        "hours": {
            "total_label": "Aufgewendete Stunden", "total_value": 14, "suffix": "",
            "quotas": [{"label": "", "value": 1}], "billable_value": 13,
        },
    }
    (BASE_DIR / "sample_report.pdf").write_bytes(generate_pdf(sample))
    print("Wrote sample_report.pdf")
