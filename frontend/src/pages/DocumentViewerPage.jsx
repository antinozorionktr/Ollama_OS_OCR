import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText, AlignLeft, LayoutTemplate, Download, LayoutGrid, RotateCw } from 'lucide-react';
import FieldPanel from '../components/viewer/FieldPanel';

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
            <div className="h-full w-full flex flex-col items-center justify-center bg-slate-50 gap-4">
                <div className="w-12 h-12 border-4 border-[#4B5320]/20 border-t-[#4B5320] rounded-full animate-spin"></div>
                <p className="text-[#4B5320] font-black uppercase tracking-widest text-sm">Decoding Archive...</p>
            </div>
        );
    }

    if (!document) {
        return (
            <div className="h-full w-full flex flex-col items-center justify-center bg-slate-50">
                <div className="text-center space-y-4">
                    <p className="text-slate-400 font-bold uppercase tracking-widest">Document missing from archive.</p>
                    <button 
                        className="flex items-center gap-2 px-6 py-2 bg-[#4B5320] text-white rounded-lg font-bold uppercase text-xs"
                        onClick={() => navigate('/documents')}
                    >
                        <ArrowLeft size={16} /> Return to Archive
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col bg-white overflow-hidden">
            {/* ── Top Bar ── */}
            <div className="h-14 bg-[#2F353B] flex items-center justify-between px-6 shrink-0 relative z-30 shadow-md">
                <button 
                    className="flex items-center gap-2 px-3 py-1.5 text-white/70 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-all text-xs font-bold uppercase tracking-wider"
                    onClick={() => navigate('/documents')}
                >
                    <ArrowLeft size={16} />
                    Archive
                </button>

                <div className="flex-1 flex justify-center px-4">
                    <span className="text-white font-black uppercase tracking-[0.15em] text-sm truncate max-w-md">
                        {document.filename}
                    </span>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-3 bg-black/20 px-4 py-1.5 rounded-full border border-white/5">
                        <button
                            className="text-white/50 hover:text-white disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                            onClick={() => goToPage(currentPage - 1)}
                            disabled={currentPage <= 1}
                        >
                            <ChevronLeft size={20} />
                        </button>
                        <span className="text-white/90 text-xs font-black uppercase tracking-widest min-w-[100px] text-center">
                            Unit {currentPage} <span className="text-white/30">/</span> {totalPages}
                        </span>
                        <button
                            className="text-white/50 hover:text-white disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                            onClick={() => goToPage(currentPage + 1)}
                            disabled={currentPage >= totalPages}
                        >
                            <ChevronRight size={20} />
                        </button>
                    </div>

                    <button 
                        onClick={handleRerun}
                        className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-all"
                        title="Re-analyze Document"
                    >
                        <RotateCw size={18} />
                    </button>
                </div>
            </div>

            {/* ── Three-Panel Body ── */}
            <div className="flex-1 flex min-h-0 overflow-hidden relative">
                {/* Left Sidebar: View Selector */}
                <div className="w-72 bg-slate-50 border-r border-[#C2B280]/20 flex flex-col shrink-0">
                    <div className="p-4 px-6 border-b border-[#C2B280]/10 flex items-center justify-between bg-white">
                        <h3 className="text-[#2F353B] font-black uppercase tracking-widest text-[10px]">Analysis Modes</h3>
                    </div>
                    
                    <div className="flex-1 overflow-y-auto p-3 space-y-1">
                        {VIEWS.map(view => {
                            const Icon = view.icon;
                            const isActive = activeView === view.key;
                            return (
                                <button
                                    key={view.key}
                                    className={`
                                        w-full flex items-center gap-4 p-4 rounded-2xl transition-all text-left
                                        ${isActive ? 'bg-[#4B5320] text-white shadow-lg translate-x-1' : 'text-slate-600 hover:bg-[#C2B280]/10'}
                                    `}
                                    onClick={() => setActiveView(view.key)}
                                >
                                    <div className={`shrink-0 ${isActive ? 'text-white' : 'text-[#4B5320]'}`}>
                                        <Icon size={20} />
                                    </div>
                                    <div className="min-w-0">
                                        <p className={`text-xs font-black uppercase tracking-tight block truncate ${isActive ? 'text-white' : 'text-[#2F353B]'}`}>
                                            {view.label}
                                        </p>
                                        <p className={`text-[9px] uppercase font-bold tracking-wider leading-tight ${isActive ? 'text-white/60' : 'text-slate-400'}`}>
                                            {view.description}
                                        </p>
                                    </div>
                                </button>
                            );
                        })}
                    </div>

                    {/* Page List Section */}
                    {totalPages > 1 && (
                        <div className="mt-auto border-t border-[#C2B280]/20 bg-slate-100/50">
                             <div className="p-3 px-6 border-b border-[#C2B280]/10">
                                <h3 className="text-[#2F353B] font-black uppercase tracking-widest text-[10px] opacity-50">Document Units</h3>
                            </div>
                            <div className="grid grid-cols-4 gap-1 p-3">
                                {Array.from({ length: totalPages }, (_, i) => i + 1).map(pageNum => (
                                    <button
                                        key={pageNum}
                                        className={`
                                            aspect-square flex items-center justify-center rounded-lg text-[10px] font-black transition-all
                                            ${currentPage === pageNum ? 'bg-[#4B5320] text-white shadow-md' : 'bg-white text-slate-500 hover:bg-[#C2B280]/20'}
                                        `}
                                        onClick={() => goToPage(pageNum)}
                                    >
                                        {pageNum}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Center: Original Document Preview */}
                <div className="flex-1 flex flex-col min-w-0 relative shadow-inner bg-slate-200/40">
                    <div className="h-12 border-b border-[#C2B280]/10 bg-white/50 backdrop-blur-sm flex items-center justify-between px-6 shrink-0 relative z-10">
                        <span className="text-[#2F353B] font-black uppercase tracking-widest text-[10px]">Source Preview</span>
                        <div className="flex items-center gap-4 bg-white/80 px-4 py-1 rounded-full shadow-sm border border-[#C2B280]/20">
                            <button className="text-slate-400 hover:text-[#4B5320]" onClick={() => setZoom(z => Math.max(z - 0.2, 0.4))}>
                                <ZoomOut size={16} />
                            </button>
                            <span className="text-[10px] font-black text-[#2F353B] min-w-[40px] text-center">
                                {Math.round(zoom * 100)}%
                            </span>
                            <button className="text-slate-400 hover:text-[#4B5320]" onClick={() => setZoom(z => Math.min(z + 0.2, 3))}>
                                <ZoomIn size={16} />
                            </button>
                        </div>
                    </div>
                    
                    <div className="flex-1 overflow-auto p-8 flex justify-center items-start scrollbar-thin scrollbar-thumb-slate-300">
                        <div 
                            className="bg-white shadow-2xl transition-transform duration-200 ease-out" 
                            style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
                        >
                            {document.filename?.toLowerCase().endsWith('.pdf') ? (
                                <iframe
                                    src={`/api/documents/${id}/preview#page=${currentPage}`}
                                    className="w-[850px] aspect-[1/1.41] border shadow-inner"
                                    title="Document Preview"
                                />
                            ) : (
                                <img
                                    src={`/api/documents/${id}/preview`}
                                    alt="Document Preview"
                                    className="max-w-4xl h-auto block"
                                />
                            )}
                        </div>
                    </div>
                </div>

                {/* Right: View Content */}
                <div className="w-[45%] max-w-[800px] bg-white border-l border-[#C2B280]/20 flex flex-col shrink-0 shadow-2xl relative z-10">
                    <div className="h-14 border-b border-[#C2B280]/10 flex items-center justify-between px-8 bg-slate-50/50 backdrop-blur-md shrink-0">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-[#4B5320] rounded-lg text-white">
                                {React.createElement(VIEWS.find(v => v.key === activeView)?.icon || FileText, { size: 16 })}
                            </div>
                            <span className="text-[#2F353B] font-black uppercase tracking-[0.1em] text-sm">
                                {VIEWS.find(v => v.key === activeView)?.label || 'Analysis Output'}
                            </span>
                        </div>
                        <span className="bg-[#138808]/10 text-[#138808] text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-tighter">
                            Verified Analysis
                        </span>
                    </div>
                    
                    <div className="flex-1 overflow-y-auto p-1 leading-relaxed">
                        {activeView === 'structured' ? (
                            <FieldPanel
                                documentType={document.document_type || 'Document'}
                                fields={editedFields}
                                onFieldClick={handleFieldChange}
                                onSave={handleSave}
                                onRerun={handleRerun}
                            />
                        ) : (
                            <div className="p-8 font-mono text-sm text-[#2F353B] whitespace-pre-wrap bg-white selection:bg-[#C2B280]/30">
                                {getViewContent()}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DocumentViewerPage;
