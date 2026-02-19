"""
DocVision OCR — Streamlit Dashboard (v3 — Persistent)
All results and batch progress are saved to SQLite.
VPN drops, page refreshes, and browser reconnects won't lose your work.
"""

import streamlit as st
import os
import json
import time
import tempfile
import uuid
from pathlib import Path
from datetime import datetime

from utils.ollama_client import OllamaOCRClient
from utils.extractors import StructuredExtractor
from utils.time_estimator import TimeEstimator
from utils.logger import setup_logger, get_log_buffer, clear_log_buffer
from utils.store import get_store
from utils.docx_generator import generate_docx_for_result

logger = setup_logger("docvision.app")

# ─── Page Config ───
st.set_page_config(
    page_title="DocVision OCR",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;600&display=swap');

    :root {
        --bg-primary: #0a0a0f;
        --bg-card: #12121a;
        --accent-invoice: #f97316;
        --accent-contract: #6366f1;
        --accent-crac: #06b6d4;
        --accent-success: #22c55e;
        --accent-warning: #eab308;
        --text-muted: #94a3b8;
        --border-subtle: #1e293b;
    }

    .stApp { font-family: 'DM Sans', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0f0f1a 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 2rem;
        position: relative; overflow: hidden;
    }
    .main-header::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, var(--accent-invoice), var(--accent-contract), var(--accent-crac));
    }
    .main-header h1 {
        font-family: 'DM Sans', sans-serif; font-weight: 700; font-size: 2rem; margin: 0;
        background: linear-gradient(135deg, #f97316, #6366f1, #06b6d4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .main-header p { color: var(--text-muted); margin: 0.5rem 0 0 0; font-size: 0.95rem; }

    .doc-type-badge {
        display: inline-block; padding: 0.3rem 0.8rem; border-radius: 20px;
        font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
    }
    .badge-invoice { background: rgba(249,115,22,0.15); color: #f97316; border: 1px solid rgba(249,115,22,0.3); }
    .badge-contract { background: rgba(99,102,241,0.15); color: #6366f1; border: 1px solid rgba(99,102,241,0.3); }
    .badge-crac { background: rgba(6,182,212,0.15); color: #06b6d4; border: 1px solid rgba(6,182,212,0.3); }

    .stat-card {
        background: var(--bg-card); border: 1px solid var(--border-subtle);
        border-radius: 12px; padding: 1.25rem; text-align: center;
    }
    .stat-card h3 { font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 600; margin: 0; }
    .stat-card p { color: var(--text-muted); font-size: 0.8rem; margin: 0.3rem 0 0 0; text-transform: uppercase; letter-spacing: 0.05em; }

    .eta-banner {
        background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(6,182,212,0.08));
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 12px; padding: 1rem 1.5rem; margin: 0.5rem 0;
    }
    .eta-banner .eta-time { font-family: 'JetBrains Mono', monospace; font-size: 1.6rem; font-weight: 600; color: #818cf8; }
    .eta-banner .eta-label { color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; }

    .resume-banner {
        background: linear-gradient(135deg, rgba(234,179,8,0.08), rgba(249,115,22,0.08));
        border: 1px solid rgba(234,179,8,0.35);
        border-radius: 12px; padding: 1.25rem 1.5rem; margin: 0.5rem 0;
    }
    .resume-banner h4 { color: #eab308; margin: 0 0 0.5rem 0; }

    .log-entry {
        font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
        padding: 0.2rem 0; border-bottom: 1px solid rgba(255,255,255,0.03); line-height: 1.5;
    }
    .log-ts { color: #64748b; }
    .log-level-INFO { color: #22c55e; }
    .log-level-DEBUG { color: #64748b; }
    .log-level-WARNING { color: #eab308; }
    .log-level-ERROR { color: #ef4444; font-weight: 600; }

    .health-ok { color: #22c55e; font-weight: 600; }
    .health-err { color: #ef4444; font-weight: 600; }

    div[data-testid="stSidebar"] { background: #0d0d14; }
</style>
""", unsafe_allow_html=True)


# ─── Env defaults ───
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "mistral-small3.1:24b-2503-fp16")
DEFAULT_INVOICE_DIR = os.environ.get("INVOICE_DIR", "/data/Invoice")
DEFAULT_CONTRACT_DIR = os.environ.get("CONTRACT_DIR", "/data/Contract")
DEFAULT_CRAC_DIR = os.environ.get("CRAC_DIR", "/data/Crac")

# ─── Persistent store (SQLite) ───
store = get_store()

# Mark any previously running batches as interrupted on app start
store.interrupt_active_batches()

# ─── Session State ───
if "estimator" not in st.session_state:
    st.session_state.estimator = TimeEstimator()

# ─── Helpers ───
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def list_files(directory: str) -> list[str]:
    if not directory or not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
    )


def get_doc_type_badge(doc_type: str) -> str:
    cls = {"invoice": "badge-invoice", "contract": "badge-contract", "crac": "badge-crac"}.get(doc_type.lower(), "badge-invoice")
    return f'<span class="doc-type-badge {cls}">{doc_type.upper()}</span>'


def format_eta(seconds: float) -> str:
    if seconds <= 0:
        return "Done"
    if seconds < 60:
        return f"{int(seconds)}s"
    m, s = int(seconds // 60), int(seconds % 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m2 = int(m // 60), int(m % 60)
    return f"{h}h {m2}m"


def render_log_viewer(max_lines: int = 50):
    logs = get_log_buffer()
    if not logs:
        st.caption("No log entries yet.")
        return
    recent = logs[-max_lines:]
    html_lines = []
    for entry in reversed(recent):
        ts = entry.get("ts", "")[:19].replace("T", " ")
        level = entry.get("level", "INFO")
        msg = entry.get("msg", "")
        extras = ""
        if entry.get("duration_s"):
            extras += f" ⏱ {entry['duration_s']}s"
        if entry.get("file_name"):
            extras += f" 📄 {entry['file_name']}"
        html_lines.append(
            f'<div class="log-entry"><span class="log-ts">{ts}</span> '
            f'<span class="log-level-{level}">{level:7s}</span> {msg}{extras}</div>'
        )
    st.markdown(
        f'<div style="max-height:400px; overflow-y:auto; background:#0a0a10; '
        f'border:1px solid #1e293b; border-radius:8px; padding:0.75rem;">{"".join(html_lines)}</div>',
        unsafe_allow_html=True,
    )


def run_batch_processing(files_list, batch_id, label_prefix="Processing"):
    """Shared batch processing logic for both new and resumed batches."""
    client = OllamaOCRClient(base_url=ollama_url, model=model_name)
    extractor = StructuredExtractor(client)
    estimator = st.session_state.estimator
    estimator.start_batch(len(files_list))

    progress_bar = st.progress(0)
    eta_container = st.empty()
    status_container = st.empty()
    timing_container = st.empty()
    file_timings = []

    for idx, item in enumerate(files_list):
        if isinstance(item, dict):
            file_path, doc_type = item["file_path"], item["doc_type"]
        else:
            file_path, doc_type = item

        file_name = os.path.basename(file_path)
        bs = estimator.get_batch_stats()
        eta_str = format_eta(bs["eta_seconds"])
        elapsed_str = format_eta(bs["elapsed_seconds"])

        eta_container.markdown(f"""
        <div class="eta-banner">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div><div class="eta-label">ETA</div><div class="eta-time">⏳ {eta_str}</div></div>
                <div style="text-align:right;"><div class="eta-label">Elapsed</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;color:#94a3b8;">{elapsed_str}</div></div>
                <div style="text-align:right;"><div class="eta-label">Avg/File</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;color:#94a3b8;">{bs['avg_per_file_seconds']}s</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        status_container.markdown(
            f"⏳ **{label_prefix} ({idx+1}/{len(files_list)}):** `{file_name}` [{doc_type.upper()}]"
        )

        timing_record = estimator.start_file(file_name, doc_type)

        try:
            result = extractor.process_document(
                file_path=file_path, doc_type=doc_type,
                extract_raw=extract_raw, extract_structured=extract_structured,
            )
            result["file_name"] = file_name
            result["file_path"] = file_path
            result["doc_type"] = doc_type
            result["processed_at"] = datetime.now().isoformat()

            result_id = store.save_result(result, batch_id=batch_id)
            estimator.finish_file(timing_record, status="done")
            store.mark_file_done(batch_id, file_path, result_id, timing_record.duration_s)

            file_timings.append({"file": file_name, "type": doc_type,
                                 "pages": result.get("page_count", 1),
                                 "time": f"{timing_record.duration_s}s", "status": "✅"})

        except Exception as e:
            estimator.finish_file(timing_record, status="error")
            store.mark_file_error(batch_id, file_path, str(e), timing_record.duration_s or 0)
            err_result = {
                "file_name": file_name, "file_path": file_path, "doc_type": doc_type,
                "error": str(e), "processed_at": datetime.now().isoformat(),
            }
            store.save_result(err_result, batch_id=batch_id)
            logger.error(f"Error processing {file_name}: {e}",
                         extra={"file_name": file_name, "step": "process_error", "error": str(e)})
            file_timings.append({"file": file_name, "type": doc_type,
                                 "pages": "-", "time": f"{timing_record.duration_s}s", "status": "❌"})

        progress_bar.progress((idx + 1) / len(files_list))
        timing_container.dataframe(file_timings, use_container_width=True, hide_index=True)

    store.finish_batch(batch_id, status="completed")
    final_bs = estimator.get_batch_stats()
    eta_container.empty()
    status_container.success(
        f"✅ Batch complete — **{len(files_list)}** documents in **{format_eta(final_bs['elapsed_seconds'])}**"
    )
    logger.info(f"Batch {batch_id} complete", extra={"step": "batch_complete", "status": "done"})


# ─── Header ───
st.markdown("""
<div class="main-header">
    <h1>🔍 DocVision OCR</h1>
    <p>Intelligent document processing — results persist across refreshes & VPN reconnects.</p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    model_name = st.text_input("Ollama Model", value=DEFAULT_MODEL)
    ollama_url = st.text_input("Ollama Base URL", value=DEFAULT_OLLAMA_URL)

    if st.button("🩺 Check Connection"):
        client = OllamaOCRClient(base_url=ollama_url, model=model_name)
        health = client.health_check()
        if health["ollama_reachable"] and health["model_available"]:
            st.markdown('<span class="health-ok">✅ Ollama connected, model ready</span>', unsafe_allow_html=True)
        elif health["ollama_reachable"]:
            st.markdown('<span class="health-err">⚠️ Ollama connected but model not found</span>', unsafe_allow_html=True)
            st.caption(f"Available: {', '.join(health.get('available_models', []))}")
        else:
            st.markdown('<span class="health-err">❌ Cannot reach Ollama</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📁 Data Folders")
    invoice_dir = st.text_input("📄 Invoice Folder", value=DEFAULT_INVOICE_DIR)
    contract_dir = st.text_input("📑 Contract Folder", value=DEFAULT_CONTRACT_DIR)
    crac_dir = st.text_input("📋 CRAC Folder", value=DEFAULT_CRAC_DIR)

    st.markdown("---")
    st.markdown("### 🎯 Extraction")
    extract_raw = st.checkbox("Extract raw text", value=True)
    extract_structured = st.checkbox("Extract structured fields", value=True)

    st.markdown("---")
    st.markdown("### 📤 Export")
    export_format = st.selectbox("Export format", ["JSON", "CSV", "Markdown"])

    st.markdown("---")
    all_results = store.get_all_results()
    st.markdown(f"<small style='color:#64748b'>💾 {len(all_results)} results in database</small>", unsafe_allow_html=True)
    st.markdown("<small style='color:#64748b'>DocVision OCR v3.0 • Persistent</small>", unsafe_allow_html=True)


# ─── Stats Row ───
folder_stats = {
    "invoice": list_files(invoice_dir),
    "contract": list_files(contract_dir),
    "crac": list_files(crac_dir),
}
result_counts = store.get_results_count()

c1, c2, c3, c4 = st.columns(4)
for col, (dtype, color) in zip(
    [c1, c2, c3, c4],
    [("invoice", "var(--accent-invoice)"), ("contract", "var(--accent-contract)"),
     ("crac", "var(--accent-crac)"), ("total", "var(--accent-success)")],
):
    if dtype == "total":
        count = sum(result_counts.values())
        label = "PROCESSED"
    else:
        count = len(folder_stats.get(dtype, []))
        label = dtype.upper()
    col.markdown(
        f'<div class="stat-card"><h3 style="color:{color}">{count}</h3><p>{label}</p></div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─── Tabs ───
tab_process, tab_upload, tab_results, tab_logs, tab_export = st.tabs([
    "📂 Batch Process", "📤 Upload Files", "📊 Results", "📋 Logs", "💾 Export"
])


# ═══════════════════════════════════════════════
# TAB 1: BATCH PROCESS (resumable)
# ═══════════════════════════════════════════════
with tab_process:
    st.markdown("#### Batch Process Folders")

    # ── Check for interrupted batch ──
    interrupted_batch = store.get_active_batch()

    if interrupted_batch:
        batch_stats = store.get_batch_stats(interrupted_batch["id"])
        st.markdown(f"""
        <div class="resume-banner">
            <h4>⚡ Interrupted Batch Detected</h4>
            <div style="color:#94a3b8; font-size:0.9rem;">
                Batch <code>{interrupted_batch['id'][:8]}...</code> was interrupted
                (likely due to VPN disconnect or page refresh).<br>
                <strong>{batch_stats['done']}</strong>/{batch_stats['total_files']} completed,
                <strong>{batch_stats['pending']}</strong> remaining,
                <strong>{batch_stats['errors']}</strong> errors.
            </div>
        </div>
        """, unsafe_allow_html=True)

        rc1, rc2, rc3 = st.columns(3)
        resume_clicked = rc1.button("▶️ Resume Batch", type="primary", use_container_width=True)
        discard_clicked = rc2.button("🗑️ Discard & Start New", use_container_width=True)
        skip_clicked = rc3.button("⏭️ Mark Complete", use_container_width=True)

        if discard_clicked:
            store.finish_batch(interrupted_batch["id"], status="discarded")
            st.rerun()

        if skip_clicked:
            store.finish_batch(interrupted_batch["id"], status="completed")
            st.rerun()

        if resume_clicked:
            pending = store.get_pending_files(interrupted_batch["id"])
            if not pending:
                store.finish_batch(interrupted_batch["id"], status="completed")
                st.success("All files already processed!")
                st.rerun()
            else:
                run_batch_processing(pending, interrupted_batch["id"], label_prefix="Resuming")

    # ── New batch section ──
    st.markdown("---")
    st.markdown("##### Start New Batch")

    folders_to_process = st.multiselect(
        "Select document types",
        ["invoice", "contract", "crac"],
        default=["invoice", "contract", "crac"],
    )

    if st.button("🚀 Start Batch Processing", type="primary", use_container_width=True):
        if not any([invoice_dir, contract_dir, crac_dir]):
            st.error("Configure at least one folder path in the sidebar.")
        else:
            folder_map = {"invoice": invoice_dir, "contract": contract_dir, "crac": crac_dir}
            files_to_process = []
            for doc_type in folders_to_process:
                for fp in list_files(folder_map[doc_type]):
                    files_to_process.append((fp, doc_type))

            if not files_to_process:
                st.warning("No supported files found in selected folders.")
            else:
                batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
                store.create_batch(batch_id, files_to_process, config={
                    "model": model_name, "ollama_url": ollama_url,
                    "extract_raw": extract_raw, "extract_structured": extract_structured,
                })
                logger.info(f"Batch {batch_id} started: {len(files_to_process)} files",
                            extra={"step": "batch_start"})

                run_batch_processing(files_to_process, batch_id, label_prefix="Processing")


# ═══════════════════════════════════════════════
# TAB 2: UPLOAD
# ═══════════════════════════════════════════════
with tab_upload:
    st.markdown("#### Upload & Process Individual Files")

    uc1, uc2 = st.columns([3, 1])
    with uc2:
        upload_doc_type = st.selectbox("Document type", ["invoice", "contract", "crac"])
    with uc1:
        uploaded_files = st.file_uploader(
            "Drop files here",
            type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"],
            accept_multiple_files=True,
        )

    if uploaded_files and st.button("🔍 Process Uploaded Files", type="primary"):
        client = OllamaOCRClient(base_url=ollama_url, model=model_name)
        extractor = StructuredExtractor(client)

        for uploaded_file in uploaded_files:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                suffix = Path(uploaded_file.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                try:
                    t0 = time.time()
                    result = extractor.process_document(
                        file_path=tmp_path, doc_type=upload_doc_type,
                        extract_raw=extract_raw, extract_structured=extract_structured,
                    )
                    dur = round(time.time() - t0, 2)
                    result["file_name"] = uploaded_file.name
                    result["file_path"] = "uploaded"
                    result["doc_type"] = upload_doc_type
                    result["processed_at"] = datetime.now().isoformat()
                    store.save_result(result)
                    st.success(f"✅ {uploaded_file.name} — processed in {dur}s")
                except Exception as e:
                    st.error(f"❌ Error processing {uploaded_file.name}: {e}")
                finally:
                    os.unlink(tmp_path)


# ═══════════════════════════════════════════════
# TAB 3: RESULTS (from DB) with Word download
# ═══════════════════════════════════════════════
with tab_results:
    st.markdown("#### Processing Results")
    st.caption("💾 Stored in database — click 📄 to download a clean Word report for any result.")

    db_results = store.get_all_results()

    if not db_results:
        st.info("No results yet. Process some documents first.")
    else:
        filter_type = st.multiselect(
            "Filter by type", ["invoice", "contract", "crac"],
            default=["invoice", "contract", "crac"], key="results_filter",
        )
        filtered = [r for r in db_results if r.get("doc_type") in filter_type]
        st.write(f"Showing **{len(filtered)}** of {len(db_results)} results")

        for idx, result in enumerate(filtered):
            proc_time = result.get("processing_time_seconds", "?")
            label = (
                f"{result.get('file_name', '?')}  |  "
                f"{result.get('doc_type', '?').upper()}  |  "
                f"⏱ {proc_time}s  |  "
                f"{result.get('processed_at', '')[:19]}"
            )

            with st.expander(label, expanded=(idx == 0)):
                if result.get("error"):
                    st.error(f"Error: {result['error']}")
                    continue

                # ── Top row: badge + Word download button ──
                top_c1, top_c2 = st.columns([3, 1])
                with top_c1:
                    st.markdown(get_doc_type_badge(result.get("doc_type", "")), unsafe_allow_html=True)
                with top_c2:
                    docx_key = f"docx_gen_{result['id']}_{idx}"
                    if st.button("📄 Download Word", key=docx_key, use_container_width=True):
                        with st.spinner("Generating Word document..."):
                            docx_path = generate_docx_for_result(result)
                            if docx_path:
                                st.session_state[f"docx_path_{result['id']}"] = docx_path

                    # Show download if generated
                    cached_path = st.session_state.get(f"docx_path_{result['id']}")
                    if cached_path and os.path.exists(cached_path):
                        with open(cached_path, "rb") as f:
                            st.download_button(
                                "⬇️ Save .docx",
                                data=f.read(),
                                file_name=os.path.basename(cached_path),
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_{result['id']}_{idx}",
                                use_container_width=True,
                            )

                r1, r2, r3 = st.tabs(["📝 Clean Text", "📋 Structured Data", "🔗 Raw JSON"])

                with r1:
                    raw = result.get("raw_text", "")
                    if raw:
                        from utils.text_cleaner import clean_ocr_text
                        cleaned = clean_ocr_text(raw)
                        st.text_area("Cleaned Extracted Text", value=cleaned, height=300,
                                     key=f"raw_{result['id']}_{idx}")
                    else:
                        st.info("Raw text extraction was not enabled.")

                with r2:
                    structured = result.get("structured_data", {})
                    if structured:
                        for key, value in structured.items():
                            if isinstance(value, list):
                                st.markdown(f"**{key.replace('_', ' ').title()}**")
                                if value and isinstance(value[0], dict):
                                    st.dataframe(value, use_container_width=True)
                                else:
                                    for item in value:
                                        st.write(f"  • {item}")
                            elif isinstance(value, dict):
                                st.markdown(f"**{key.replace('_', ' ').title()}**")
                                for k, v in value.items():
                                    st.write(f"  **{k}**: {v}")
                            else:
                                st.write(f"**{key.replace('_', ' ').title()}**: {value}")
                    else:
                        st.info("Structured extraction was not enabled.")

                with r3:
                    st.json(result)

        # ── Bulk Word generation ──
        st.markdown("---")
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("📄 Generate All Word Docs", use_container_width=True):
                success_count = 0
                with st.spinner(f"Generating Word documents for {len(filtered)} results..."):
                    progress = st.progress(0)
                    for i, res in enumerate(filtered):
                        if not res.get("error"):
                            path = generate_docx_for_result(res)
                            if path:
                                success_count += 1
                        progress.progress((i + 1) / len(filtered))
                st.success(f"✅ Generated {success_count} Word documents in `/app/data/docx_outputs/`")

        with bc2:
            if st.button("🗑️ Clear All Results from Database", type="secondary", use_container_width=True):
                store.delete_all_results()
                st.rerun()


# ═══════════════════════════════════════════════
# TAB 4: LOGS
# ═══════════════════════════════════════════════
with tab_logs:
    st.markdown("#### Live Backend Logs")
    st.caption("In-memory buffer + persistent file logs at `/app/logs/`")

    lc1, lc2 = st.columns([1, 5])
    with lc1:
        if st.button("🔄 Refresh"):
            pass
        if st.button("🗑️ Clear"):
            clear_log_buffer()
            st.rerun()

    max_lines = st.slider("Max visible lines", 20, 200, 80, step=10)
    render_log_viewer(max_lines=max_lines)


# ═══════════════════════════════════════════════
# TAB 5: EXPORT (from DB)
# ═══════════════════════════════════════════════
with tab_export:
    st.markdown("#### Export Results")

    db_results_export = store.get_all_results()

    if not db_results_export:
        st.info("No results to export yet.")
    else:
        st.write(f"**{len(db_results_export)}** results ready for export.")

        if export_format == "JSON":
            export_data = json.dumps(db_results_export, indent=2, default=str)
            st.download_button(
                "⬇️ Download JSON", data=export_data,
                file_name=f"ocr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json", use_container_width=True,
            )

        elif export_format == "CSV":
            import csv, io
            output = io.StringIO()
            rows = []
            for r in db_results_export:
                row = {
                    "file_name": r.get("file_name", ""),
                    "doc_type": r.get("doc_type", ""),
                    "processing_time_s": r.get("processing_time_seconds", ""),
                    "processed_at": r.get("processed_at", ""),
                    "raw_text": (r.get("raw_text") or "")[:500],
                    "error": r.get("error", ""),
                }
                for k, v in r.get("structured_data", {}).items():
                    row[f"field_{k}"] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                rows.append(row)
            if rows:
                all_keys = set()
                for row in rows:
                    all_keys.update(row.keys())
                writer = csv.DictWriter(output, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(rows)
            st.download_button(
                "⬇️ Download CSV", data=output.getvalue(),
                file_name=f"ocr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv", use_container_width=True,
            )

        elif export_format == "Markdown":
            md = ["# OCR Processing Results\n",
                  f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"]
            for r in db_results_export:
                md.append(f"## {r.get('file_name', 'Unknown')}")
                md.append(f"- **Type**: {r.get('doc_type', 'N/A')}")
                md.append(f"- **Time**: {r.get('processing_time_seconds', '?')}s")
                md.append(f"- **Processed**: {r.get('processed_at', 'N/A')[:19]}")
                if r.get("error"):
                    md.append(f"- **Error**: {r['error']}\n")
                    continue
                if r.get("raw_text"):
                    md.append("\n### Raw Text\n```")
                    md.append(r["raw_text"][:1000])
                    md.append("```\n")
                if r.get("structured_data"):
                    md.append("### Structured Fields\n")
                    for k, v in r["structured_data"].items():
                        md.append(f"- **{k}**: {v}")
                    md.append("")
            st.download_button(
                "⬇️ Download Markdown", data="\n".join(md),
                file_name=f"ocr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown", use_container_width=True,
            )