import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText, AlignLeft, LayoutTemplate, Download, LayoutGrid } from 'lucide-react';
import FieldPanel from '../components/viewer/FieldPanel';
import './DocumentViewerPage.css';

/**
 * Parses structured_data string in various formats:
 * 1. JSON (preferable)
 * 2. Key: Value list
 */
const parseStructuredData = (dataStr) => {
    if (!dataStr) return {};
    
    // Attempt JSON
    try {
        const parsed = JSON.parse(dataStr);
        if (typeof parsed === 'object' && parsed !== null) {
            const transformed = {};
            Object.entries(parsed).forEach(([k, v]) => {
                transformed[k] = typeof v === 'object' && v !== null ? v : { value: v };
            });
            return transformed;
        }
    } catch (e) {
        // Not JSON
        // If it looks like a single large extraction result (no colons on many lines)
        // just return it as a 'general_data' field
        const lines = dataStr.split('\n');
        const fields = {};
        let currentKey = null;

        lines.forEach(line => {
            const match = line.match(/^([^:]+):\s*(.*)$/);
            if (match) {
                currentKey = match[1].trim().toLowerCase().replace(/\s+/g, '_');
                fields[currentKey] = { value: match[2].trim() };
            } else if (currentKey && line.trim()) {
                // Append multi-line value
                fields[currentKey].value += '\n' + line.trim();
            }
        });

        if (Object.keys(fields).length === 0 && dataStr.trim()) {
            return { extraction_result: { value: dataStr.trim() } };
        }
        return fields;
    }
    return {};
};

const VIEWS = [
    { key: 'cleaned', label: 'Cleaned Text', icon: FileText, description: 'LLM-cleaned readable text' },
    { key: 'raw', label: 'Raw Text', icon: AlignLeft, description: 'Direct vision model output' },
    { key: 'layout', label: 'Recreated Layout', icon: LayoutTemplate, description: 'Reconstructed document layout' },
    { key: 'structured', label: 'Structured Data', icon: LayoutGrid, description: 'Key-value pairs & entities' },
];

const DocumentViewerPage = () => {
    const { id } = useParams();
    const navigate = useNavigate();

    // Document data
    const [document, setDocument] = useState(null);
    const [pages, setPages] = useState([]);
    const [loading, setLoading] = useState(true);

    // Viewer state
    const [currentPage, setCurrentPage] = useState(1);
    const [zoom, setZoom] = useState(1.0);
    const [activeView, setActiveView] = useState('cleaned');

    // Load document + pages
    useEffect(() => {
        fetch(`/api/documents/${id}`)
            .then(r => r.json())
            .then(data => {
                setDocument(data.document);
                setPages(data.pages || []);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [id]);

    const totalPages = document?.total_pages || pages.length || 1;
    const currentPageData = pages.find(p => p.page_number === currentPage);

    // Track edited fields for structured view
    const [editedFields, setEditedFields] = useState({});

    useEffect(() => {
        if (currentPageData?.structured_data) {
            setEditedFields(parseStructuredData(currentPageData.structured_data));
        } else {
            setEditedFields({});
        }
    }, [currentPageData]);

    const handleFieldChange = (key, value) => {
        setEditedFields(prev => ({
            ...prev,
            [key]: { ...prev[key], value }
        }));
    };

    const handleSave = async () => {
        if (!currentPageData) return;
        try {
            const dataToSave = JSON.stringify(editedFields);
            const response = await fetch(`/api/documents/${id}/pages/${currentPage}/structured`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ structured_data: dataToSave })
            });
            if (response.ok) {
                alert('Changes saved successfully!');
            } else {
                throw new Error('Failed to save');
            }
        } catch (err) {
            console.error(err);
            alert('Error saving changes');
        }
    };

    const handleRerun = async () => {
        if (!window.confirm('Re-running OCR will overwrite existing results for this document. Continue?')) return;
        try {
            const response = await fetch(`/api/documents/${id}/rerun`, { method: 'POST' });
            if (response.ok) {
                alert('OCR Re-run started! Refreshing in 3 seconds...');
                setTimeout(() => window.location.reload(), 3000);
            } else {
                throw new Error('Failed to start re-run');
            }
        } catch (err) {
            console.error(err);
            alert('Error starting re-run');
        }
    };

    const getViewContent = () => {
        if (!currentPageData) return 'Loading page content...';
        switch (activeView) {
            case 'raw': return currentPageData.raw_text || 'No raw text available';
            case 'cleaned': return currentPageData.cleaned_text || 'No cleaned text available';
            case 'layout': return currentPageData.recreated_layout || 'No layout available';
            case 'structured': return currentPageData.structured_data || 'No structured data available';
            default: return '';
        }
    };

    const goToPage = (pageNum) => {
        if (pageNum >= 1 && pageNum <= totalPages) {
            setCurrentPage(pageNum);
        }
    };

    if (loading) {
        return (
            <div className="viewer-page">
                <div className="viewer-loading">
                    <div className="loading-spinner"></div>
                    <p>Loading document...</p>
                </div>
            </div>
        );
    }

    if (!document) {
        return (
            <div className="viewer-page">
                <div className="viewer-loading">
                    <p>Document not found.</p>
                    <button className="back-btn" onClick={() => navigate('/documents')}>
                        <ArrowLeft size={18} /> Back to Documents
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="viewer-page">
            {/* ── Top Bar ── */}
            <div className="viewer-topbar">
                <button className="back-btn" onClick={() => navigate('/documents')}>
                    <ArrowLeft size={18} />
                    Documents
                </button>

                <div className="topbar-center">
                    <span className="doc-name">{document.filename}</span>
                </div>

                <div className="topbar-right">
                    {/* Page Navigation */}
                    <div className="page-nav">
                        <button
                            className="page-nav-btn"
                            onClick={() => goToPage(currentPage - 1)}
                            disabled={currentPage <= 1}
                        >
                            <ChevronLeft size={16} />
                        </button>
                        <span className="page-indicator">
                            Page {currentPage} / {totalPages}
                        </span>
                        <button
                            className="page-nav-btn"
                            onClick={() => goToPage(currentPage + 1)}
                            disabled={currentPage >= totalPages}
                        >
                            <ChevronRight size={16} />
                        </button>
                    </div>
                </div>
            </div>

            {/* ── Three-Panel Body ── */}
            <div className="viewer-body">
                {/* Left Sidebar: View Selector */}
                <div className="viewer-sidebar">
                    <div className="sidebar-header">
                        <h3>Views</h3>
                    </div>
                    <div className="view-list">
                        {VIEWS.map(view => {
                            const Icon = view.icon;
                            return (
                                <button
                                    key={view.key}
                                    className={`view-item ${activeView === view.key ? 'active' : ''}`}
                                    onClick={() => setActiveView(view.key)}
                                >
                                    <Icon size={18} />
                                    <div className="view-item-text">
                                        <span className="view-item-label">{view.label}</span>
                                        <span className="view-item-desc">{view.description}</span>
                                    </div>
                                </button>
                            );
                        })}
                    </div>

                    {/* Page List */}
                    {totalPages > 1 && (
                        <div className="page-list-section">
                            <div className="sidebar-header">
                                <h3>Pages</h3>
                            </div>
                            <div className="page-list">
                                {Array.from({ length: totalPages }, (_, i) => i + 1).map(pageNum => (
                                    <button
                                        key={pageNum}
                                        className={`page-list-item ${currentPage === pageNum ? 'active' : ''}`}
                                        onClick={() => goToPage(pageNum)}
                                    >
                                        Page {pageNum}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Center: Original Document Preview */}
                <div className="viewer-center">
                    <div className="preview-header">
                        <span className="preview-title">Original Document</span>
                        <div className="zoom-controls">
                            <button className="zoom-btn" onClick={() => setZoom(z => Math.max(z - 0.2, 0.4))}>
                                <ZoomOut size={16} />
                            </button>
                            <span className="zoom-level">{Math.round(zoom * 100)}%</span>
                            <button className="zoom-btn" onClick={() => setZoom(z => Math.min(z + 0.2, 3))}>
                                <ZoomIn size={16} />
                            </button>
                        </div>
                    </div>
                    <div className="preview-container">
                        <div className="preview-scroll" style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}>
                            {document.filename?.toLowerCase().endsWith('.pdf') ? (
                                <iframe
                                    src={`/api/documents/${id}/preview#page=${currentPage}`}
                                    className="pdf-preview"
                                    title="Document Preview"
                                />
                            ) : (
                                <img
                                    src={`/api/documents/${id}/preview`}
                                    alt="Document Preview"
                                    className="image-preview"
                                />
                            )}
                        </div>
                    </div>
                </div>

                {/* Right: View Content */}
                <div className="viewer-right">
                    <div className="content-header">
                        <span className="content-title">
                            {VIEWS.find(v => v.key === activeView)?.label || 'Content'}
                        </span>
                        <span className="content-page-badge">Page {currentPage}</span>
                    </div>
                    <div className="content-body">
                        {activeView === 'structured' ? (
                            <FieldPanel
                                documentType={document.document_type || 'Document'}
                                fields={editedFields}
                                onFieldClick={handleFieldChange}
                                onSave={handleSave}
                                onRerun={handleRerun}
                            />
                        ) : (
                            <pre className="content-text">{getViewContent()}</pre>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DocumentViewerPage;
