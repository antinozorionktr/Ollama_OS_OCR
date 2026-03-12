import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, ArrowLeft, FileText, List } from 'lucide-react';
import PageViewer from '../components/viewer/PageViewer';
import FieldPanel from '../components/viewer/FieldPanel';
import './DocumentViewerPage.css';

const DocumentViewerPage = () => {
    const { id } = useParams();
    const navigate = useNavigate();

    // Result metadata
    const [result, setResult] = useState(null);
    const [loadingResult, setLoadingResult] = useState(true);

    // Extraction state
    const [extraction, setExtraction] = useState(null);
    const [extracting, setExtracting] = useState(false);

    // Viewer state
    const [page, setPage] = useState(1);
    const [zoom, setZoom] = useState(1.0);
    const [overlayEnabled, setOverlayEnabled] = useState(true);
    const [showMarkdown, setShowMarkdown] = useState(false);
    const [highlightedKey, setHighlightedKey] = useState(null);
    const [isApproved, setIsApproved] = useState(false);

    // Load result metadata on mount
    useEffect(() => {
        fetch(`/api/results/${id}`)
            .then(r => r.json())
            .then(data => {
                setResult(data);
                setIsApproved(data.formatted_text === 'approved');
            })
            .catch(console.error)
            .finally(() => setLoadingResult(false));
    }, [id]);

    // Run the universal structured extraction pipeline
    const runExtraction = useCallback(() => {
        setExtracting(true);
        setExtraction(null);
        fetch(`/api/results/${id}/extract-structured`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.extraction) {
                    setExtraction(data.extraction);
                }
            })
            .catch(console.error)
            .finally(() => setExtracting(false));
    }, [id]);

    // Auto-run on load if result exists
    useEffect(() => {
        if (!loadingResult && result) {
            runExtraction();
        }
    }, [loadingResult]);

    const handleApprove = () => {
        fetch(`/api/results/${id}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fields: extraction?.fields || {} }),
        })
            .then(r => r.json())
            .then(data => { if (data.approved) setIsApproved(true); })
            .catch(console.error);
    };

    const handleFieldClick = (key) => {
        setHighlightedKey(prev => prev === key ? null : key);
    };

    const fields = extraction?.fields || null;
    const lineItems = extraction?.line_items || [];
    const tokens = extraction?.raw_tokens || [];
    const totalPages = result?.page_count || extraction?.pages || 1;
    const rawText = result?.raw_text || result?.clean_text || null;

    return (
        <div className="viewer-page">
            {/* Top Bar */}
            <div className="viewer-topbar">
                <button className="back-btn" onClick={() => navigate('/documents')}>
                    <ArrowLeft size={18} />
                    Documents
                </button>

                <div className="topbar-center">
                    {loadingResult ? (
                        <span className="doc-name-loading">Loading…</span>
                    ) : (
                        <span className="doc-name">{result?.file_name}</span>
                    )}
                </div>

                <div className="topbar-right">
                    <button
                        className={`overlay-toggle ${overlayEnabled ? 'active' : ''}`}
                        onClick={() => setOverlayEnabled(p => !p)}
                    >
                        {overlayEnabled ? <Eye size={16} /> : <EyeOff size={16} />}
                        OCR OVERLAY {overlayEnabled ? 'ON' : 'OFF'}
                    </button>
                    <button
                        className={`overlay-toggle ${showMarkdown ? 'markdown-active' : ''}`}
                        onClick={() => setShowMarkdown(p => !p)}
                        style={{ marginLeft: '0.5rem' }}
                    >
                        {showMarkdown ? <List size={16} /> : <FileText size={16} />}
                        MARKDOWN {showMarkdown ? 'OFF' : 'ON'}
                    </button>
                </div>
            </div>

            {/* Two-panel body */}
            <div className="viewer-body">
                {/* Left: Document */}
                <div className="viewer-left">
                    <PageViewer
                        resultId={id}
                        page={page}
                        totalPages={totalPages}
                        zoom={zoom}
                        overlayEnabled={overlayEnabled}
                        tokens={tokens}
                        highlightedField={fields}
                        onPageChange={setPage}
                        onZoomIn={() => setZoom(z => Math.min(z + 0.2, 3))}
                        onZoomOut={() => setZoom(z => Math.max(z - 0.2, 0.4))}
                    />
                </div>

                {/* Right: Field Panel */}
                <div className="viewer-right">
                    <FieldPanel
                        documentType={extraction?.document_type || 'Document'}
                        fields={fields}
                        lineItems={lineItems}
                        rawText={rawText}
                        markdown={result?.markdown}
                        showMarkdown={showMarkdown}
                        isLoading={extracting}
                        isApproved={isApproved}
                        onApprove={handleApprove}
                        onSave={() => alert('Changes saved!')}
                        onRerun={runExtraction}
                        onFieldClick={handleFieldClick}
                        highlightedKey={highlightedKey}
                    />
                </div>
            </div>
        </div>
    );
};

export default DocumentViewerPage;
