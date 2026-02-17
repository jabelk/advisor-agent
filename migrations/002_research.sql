-- Migration 002: Research Data Ingestion & Analysis
-- Tables: company, source_document, research_signal, notable_investor, ingestion_run

CREATE TABLE IF NOT EXISTS company (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    cik TEXT,
    sector TEXT,
    added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    active INTEGER NOT NULL DEFAULT 1
) STRICT;

CREATE INDEX IF NOT EXISTS idx_company_ticker ON company(ticker);
CREATE INDEX IF NOT EXISTS idx_company_active ON company(active);

CREATE TABLE IF NOT EXISTS source_document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES company(id),
    source_type TEXT NOT NULL,
    content_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    content_hash TEXT NOT NULL,
    local_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    analysis_status TEXT NOT NULL DEFAULT 'pending',
    analysis_error TEXT,
    metadata_json TEXT,
    UNIQUE(source_type, source_id)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_source_document_source_type ON source_document(source_type);
CREATE INDEX IF NOT EXISTS idx_source_document_company_id ON source_document(company_id);
CREATE INDEX IF NOT EXISTS idx_source_document_published_at ON source_document(published_at);
CREATE INDEX IF NOT EXISTS idx_source_document_analysis_status ON source_document(analysis_status);
CREATE INDEX IF NOT EXISTS idx_source_document_content_hash ON source_document(content_hash);

CREATE TABLE IF NOT EXISTS research_signal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES company(id),
    document_id INTEGER NOT NULL REFERENCES source_document(id),
    signal_type TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    confidence TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT,
    source_section TEXT,
    metrics_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE INDEX IF NOT EXISTS idx_research_signal_company_id ON research_signal(company_id);
CREATE INDEX IF NOT EXISTS idx_research_signal_signal_type ON research_signal(signal_type);
CREATE INDEX IF NOT EXISTS idx_research_signal_evidence_type ON research_signal(evidence_type);
CREATE INDEX IF NOT EXISTS idx_research_signal_created_at ON research_signal(created_at);
CREATE INDEX IF NOT EXISTS idx_research_signal_document_id ON research_signal(document_id);

CREATE TABLE IF NOT EXISTS notable_investor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    cik TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE INDEX IF NOT EXISTS idx_notable_investor_name ON notable_investor(name);
CREATE INDEX IF NOT EXISTS idx_notable_investor_cik ON notable_investor(cik);
CREATE INDEX IF NOT EXISTS idx_notable_investor_active ON notable_investor(active);

CREATE TABLE IF NOT EXISTS ingestion_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    documents_ingested INTEGER NOT NULL DEFAULT 0,
    signals_generated INTEGER NOT NULL DEFAULT 0,
    errors_json TEXT,
    sources_json TEXT
) STRICT;

CREATE INDEX IF NOT EXISTS idx_ingestion_run_status ON ingestion_run(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_run_started_at ON ingestion_run(started_at DESC);

PRAGMA user_version = 2;
