"""CSS condiviso per tutto il gestionale."""

COMMON_CSS = """
<style>
/* Sidebar */
[data-testid="stSidebar"] { background-color: #1e293b; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* Nasconde il menu Streamlit */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Metriche */
[data-testid="stMetric"] {
    background-color: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 12px 16px;
}

/* Tabella prestazioni custom */
.prest-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.prest-table th {
    background: #1e293b; color: white; padding: 8px 6px; text-align: left;
    position: sticky; top: 0; z-index: 10; font-weight: 600; font-size: 0.8rem;
}
.prest-table td { padding: 6px 6px; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }
.prest-table tr:nth-child(even) { background: #f0f9ff; }
.prest-table tr:nth-child(odd) { background: #ffffff; }
.prest-table tr.active-row { background: #fef9c3 !important; }
.prest-table tr:hover { background: #e0f2fe !important; cursor: pointer; }
.prest-table .col-check { width: 30px; text-align: center; }
.prest-table .col-actions { width: 70px; text-align: center; white-space: nowrap; }
.prest-table .col-money { text-align: right; font-family: monospace; }
.prest-table .badge-fatt { background: #dcfce7; color: #166534; padding: 2px 6px;
    border-radius: 4px; font-size: 0.75rem; }
.prest-table .badge-nofatt { background: #fef3c7; color: #92400e; padding: 2px 6px;
    border-radius: 4px; font-size: 0.75rem; }

/* Azione buttons */
.action-btn {
    display: inline-block; padding: 3px 6px; border-radius: 4px;
    text-decoration: none; font-size: 0.85rem; margin: 0 1px;
}
.action-btn:hover { opacity: 0.8; }
.btn-edit { background: #dbeafe; color: #1d4ed8 !important; }
.btn-incasso { background: #dcfce7; color: #166534 !important; }

/* Responsive */
@media (max-width: 768px) {
    .prest-table { font-size: 0.75rem; }
    .prest-table th, .prest-table td { padding: 4px 3px; }
    .hide-mobile { display: none !important; }
}

/* Scrollable table container */
.table-container {
    max-height: 65vh; overflow-y: auto; border: 1px solid #e2e8f0;
    border-radius: 8px; margin-bottom: 1rem;
}

/* Filtri sezione */
.filter-section {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 1rem; margin-bottom: 1rem;
}

/* Banner mese-anno */
.month-banner {
    text-align: center; background: #1e293b; color: #38bdf8;
    padding: 8px; border-radius: 8px; font-size: 1.3em; font-weight: bold;
    margin: 0.5rem 0;
}

/* Header gradiente */
.page-header {
    background: linear-gradient(135deg, #1e293b, #334155);
    color: white; padding: 1rem 1.5rem; border-radius: 12px; margin-bottom: 1rem;
}
.page-header h2 { margin: 0; color: white; }
.page-header p { margin: 0.3rem 0 0; opacity: 0.8; font-size: 0.9rem; }
</style>
"""
