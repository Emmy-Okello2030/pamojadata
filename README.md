<<<<<<< HEAD
# PamojaData 🌍

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://pamojadata-snqdbr5wqwdy9okm64bnc7.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **End-to-end humanitarian programme intelligence platform** — from field data collection to donor report submission, automated and AI-powered.

Built by [Emily Okello](https://github.com/Emmy-Okello2030) | Humanitarian Data Analyst & M&E Specialist

---

## 🔴 Live Demo

**[https://pamojadata-snqdbr5wqwdy9okm64bnc7.streamlit.app/](https://pamojadata-snqdbr5wqwdy9okm64bnc7.streamlit.app/)**

Default credentials: `admin` / `admin123` *(change after first login)*

---

## 🌍 What is PamojaData?

M&E officers in humanitarian organisations spend 3–7 days every reporting cycle manually compiling donor reports. PamojaData automates the entire pipeline:

```
Field Data → Quality Checks → Indicator Analysis → Risk Prediction → AI Narrative → Donor Report
```

Built specifically for small-to-mid INGOs and UN agencies who need powerful M&E tools without expensive enterprise software.

*Pamoja means "together" in Swahili.*

---

## ✨ Features

### 📁 Data Management
- Upload CSV/Excel programme data with intelligent column mapping
- Direct KoboToolbox API integration — no manual exports needed
- Live HDX (Humanitarian Data Exchange) dataset browsing and import

### 🔍 Data Quality
- ML-powered anomaly detection using Isolation Forest
- Automated checks: missing values, duplicates, negative values, outliers
- IASC data responsibility compliance — PII scanner and consent checklist

### 📈 Analysis Engine
- Automatic target vs achievement calculations
- Variance, % achievement and status flagging (Met / On Track / Off Track)
- Sector, location and multi-period trend analysis

### 🔮 Risk Prediction
- Random Forest ML model predicts at-risk indicators before they go off track
- Feature importance analysis — understand what drives risk
- Rule-based fallback when insufficient training data

### 📊 Interactive Dashboard
- Plotly charts: donut, bar, line, gauge and geographic breakdown
- Real-time KPI cards
- Top and bottom performer tracking

### ✍️ AI Report Generation
- Google Gemini AI writes professional donor narratives
- 6 donor styles: General, USAID, EU, UN, Global Fund, Gates Foundation
- Qualitative field notes integration
- Editable narrative before export
- Word document (.docx) export with colour-coded tables and charts

### 📐 Logframe Builder
- Build logical frameworks from scratch (Goal → Outcome → Output → Activity)
- Set indicators, baselines, targets, means of verification
- Export formatted logframe as Word document

### 📍 3W Tracking
- Who does What Where — standard humanitarian coordination tool
- Sector and location presence analysis
- Coverage gap detection
- Bulk import and Word export

### 💰 Budget Tracking
- Budget line management with quarterly breakdown
- Expenditure recording and burn rate analysis
- Utilisation charts by category and period

### 👥 User Management
- Role-based access control: Admin, Programme Manager, M&E Officer, Donor
- PBKDF2-SHA256 password hashing
- 8-hour session expiry
- Account activation/deactivation

### 🛡️ Data Responsibility
- IASC Operational Guidance aligned
- PII field scanner with risk levels
- Consent checklist
- Data minimisation best practices

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Data Processing | Python, Pandas, NumPy |
| Database | SQLite |
| Machine Learning | Scikit-learn (Random Forest, Isolation Forest) |
| AI Narrative | Google Gemini API |
| Visualization | Plotly, Matplotlib |
| Report Export | Python-docx |
| Field Data | KoboToolbox API |
| Open Data | HDX API (OCHA) |
| Deployment | Streamlit Cloud |
| Containerization | Docker |

---

## 🚀 Getting Started

### Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/Emmy-Okello2030/pamojadata.git
cd pamojadata

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Gemini API key
mkdir .streamlit
echo 'GEMINI_API_KEY = "your-key-here"' > .streamlit/secrets.toml

# 5. Run the app
streamlit run app.py
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com)

### Run with Docker

```bash
docker build -t pamojadata .
docker run -p 8501:8501 -e GEMINI_API_KEY=your-key pamojadata
```

### Run Tests

```bash
pip install -r dev-requirements.txt
pytest
```

---

## 📁 Project Structure

```
pamojadata/
├── app.py                          # Main Streamlit application
├── src/
│   ├── analysis/
│   │   └── indicator_analysis.py   # Indicator performance calculations
│   ├── auth/
│   │   └── auth.py                 # Authentication & role management
│   ├── budget/
│   │   └── budget.py               # Budget tracking & expenditure
│   ├── collection/
│   │   └── kobo_connector.py       # KoboToolbox API integration
│   ├── database/
│   │   └── db.py                   # SQLite database engine
│   ├── hdx/
│   │   └── hdx_connector.py        # HDX open data integration
│   ├── logframe/
│   │   └── logframe.py             # Logical framework builder
│   ├── prediction/
│   │   └── risk_predictor.py       # ML risk prediction models
│   ├── quality/
│   │   └── quality_checks.py       # Data quality & anomaly detection
│   ├── reporting/
│   │   ├── ai_reporter.py          # Gemini AI narrative generation
│   │   └── report_export.py        # Word document assembly
│   ├── responsibility/
│   │   └── data_responsibility.py  # IASC data responsibility module
│   ├── three_w/
│   │   └── three_w.py              # 3W operational presence tracking
│   └── visualization/
│       └── charts.py               # Plotly & Matplotlib charts
├── data/
│   └── sample_program_data.csv     # Sample data for testing
├── tests/                          # Unit tests
├── .streamlit/
│   └── secrets.toml                # API keys (never commit this)
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 🔐 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key for AI narratives | Yes |
| `PAMOJADATA_ADMIN_USER` | Override default admin username | Optional |
| `PAMOJADATA_ADMIN_PASSWORD` | Override default admin password | Optional |
| `PAMOJADATA_ADMIN_EMAIL` | Override default admin email | Optional |

---

## 🗺️ Roadmap

- [x] Core indicator analysis engine
- [x] ML risk prediction
- [x] AI narrative generation
- [x] KoboToolbox integration
- [x] HDX data integration
- [x] Logframe builder
- [x] 3W tracking
- [x] Budget tracking
- [x] User authentication & RBAC
- [x] Data responsibility (IASC)
- [ ] PDF export
- [ ] KoboToolbox real-time sync
- [ ] Multi-language support (French, Swahili)
- [ ] PostgreSQL migration for production scale
- [ ] Mobile-responsive improvements

---

## 📊 Skills Demonstrated

This project was built to demonstrate the intersection of data science and humanitarian sector expertise:

- Python & Pandas — data processing pipelines
- SQL & SQLite — relational database design
- Machine Learning — Random Forest, Isolation Forest (Scikit-learn)
- AI/LLM Integration — Google Gemini API, prompt engineering
- Data Visualization — Plotly, Matplotlib
- REST API Integration — KoboToolbox, HDX/OCHA
- Report Generation — Python-docx
- Cloud Deployment — Streamlit Cloud, Docker
- M&E Frameworks — logframes, indicator design, donor reporting
- Data Responsibility — IASC humanitarian data principles

---

## 👤 About the Author

**Emily Okello** — Data Science student at KCA University, Nairobi, with hands-on M&E experience in the humanitarian sector. PamojaData is a portfolio project built to bridge the gap between data skills and real-world humanitarian programme needs.

- 🔗 [GitHub](https://github.com/Emmy-Okello2030)
- 🌍 [Live App](https://pamojadata-snqdbr5wqwdy9okm64bnc7.streamlit.app/)

---

## 📄 License

MIT License — free to use, modify and distribute with attribution.
=======
# PamojaData ??

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://pamojadata-snqdbr5wqwdy9okm64bnc7.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

> **End-to-end humanitarian programme intelligence platform** � from field data collection to donor report submission, automated and AI-powered.

Built by [Emily Okello](https://github.com/Emmy-Okello2030)

---

## ?? Live Demo

**[https://pamojadata-snqdbr5wqwdy9okm64bnc7.streamlit.app/](https://pamojadata-snqdbr5wqwdy9okm64bnc7.streamlit.app/)**
>>>>>>> d133e42c2881987c36fa49c7db3d1f42bd08f97a
