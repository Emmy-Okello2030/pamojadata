from src.page_handlers import PAGE_RENDERERS


def test_page_renderers_exist():
    expected_pages = [
        "🏠 Home",
        "📁 Data Input",
        "🔍 Data Quality",
        "📈 Analysis",
        "🔮 Risk Prediction",
        "📊 Dashboard",
        "✍️ AI Report",
        "📐 Logframe Builder",
        "🛡️ Data Responsibility",
        "👥 User Management",
        "🌐 HDX Data",
        "📍 3W Tracking",
        "💰 Budget Tracking",
        "⚙️ Settings",
    ]

    for page in expected_pages:
        assert page in PAGE_RENDERERS
        assert callable(PAGE_RENDERERS[page])


def test_app_sidebar_uses_page_renderers():
    with open('app.py', 'r', encoding='utf-8') as fh:
        app_source = fh.read()

    assert 'page_options = list(PAGE_RENDERERS.keys())' in app_source
    assert '"📁 Data Input",' not in app_source
    assert '"📈 Analysis",' not in app_source
