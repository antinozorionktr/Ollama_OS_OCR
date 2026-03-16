import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Clock, Layers, Trash2, Eye } from 'lucide-react';

const DocumentsPage = () => {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        fetchDocuments();
    }, []);

    const fetchDocuments = () => {
        setLoading(true);
        fetch('/api/documents')
            .then(r => r.json())
            .then(data => setDocuments(data.documents || []))
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    const deleteDocument = (id, e) => {
        e.stopPropagation();
        if (!confirm('Delete this document and all its data?')) return;
        fetch(`/api/documents/${id}`, { method: 'DELETE' })
            .then(() => fetchDocuments())
            .catch(console.error);
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div className="p-8 max-w-7xl mx-auto min-h-full">
            <div className="mb-10">
                <h1 className="text-3xl font-extrabold text-[#2F353B] uppercase tracking-tight mb-2">Processed Documents</h1>
                <p className="text-[#475569] text-base font-semibold uppercase tracking-widest opacity-70">
                    {documents.length} document{documents.length !== 1 ? 's' : ''} in the system
                </p>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-20 text-[#4B5320] font-bold animate-pulse uppercase tracking-[0.2em] text-sm">
                    Scanning archive database...
                </div>
            ) : documents.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-32 bg-white rounded-3xl border border-dashed border-[#C2B280]/40 text-slate-400">
                    <div className="w-20 h-20 rounded-full bg-slate-50 flex items-center justify-center mb-6">
                        <FileText size={48} className="opacity-20" />
                    </div>
                    <p className="text-lg font-bold text-[#2F353B]/50 uppercase tracking-wide mb-8">No documents processed yet.</p>
                    <button 
                        onClick={() => navigate('/')}
                        className="px-8 py-3 bg-[#4B5320] text-white rounded-xl font-bold uppercase tracking-wider text-sm shadow-lg hover:bg-[#3A4310] transition-all"
                    >
                        Process New Document
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4">
                    {documents.map(doc => (
                        <div
                            key={doc.id}
                            className="group bg-white rounded-2xl border border-[#C2B280]/20 p-5 flex items-center gap-6 shadow-sm hover:shadow-md hover:border-[#4B5320]/30 transition-all cursor-pointer relative"
                            onClick={() => navigate(`/documents/${doc.id}`)}
                        >
                            <div className="w-14 h-14 rounded-xl bg-[#C2B280]/10 flex items-center justify-center text-[#4B5320] group-hover:bg-[#4B5320] group-hover:text-white transition-all shrink-0">
                                <FileText size={28} />
                            </div>
                            
                            <div className="flex-1 min-w-0">
                                <h3 className="text-base font-extrabold text-[#2F353B] truncate uppercase tracking-tight mb-2 group-hover:text-[#4B5320] transition-colors">
                                    {doc.filename}
                                </h3>
                                <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[#475569] text-[11px] font-bold uppercase tracking-widest opacity-70">
                                    <span className="flex items-center gap-1.5">
                                        <Layers size={14} className="text-[#4B5320]" />
                                        {doc.total_pages} Units
                                    </span>
                                    <span className="flex items-center gap-1.5">
                                        <Clock size={14} className="text-[#4B5320]" />
                                        {formatDate(doc.uploaded_at)}
                                    </span>
                                    {doc.processing_time_seconds && (
                                        <span className="bg-[#4B5320]/5 px-2 py-0.5 rounded text-[#4B5320]">
                                            Analysis: {doc.processing_time_seconds.toFixed(1)}s
                                        </span>
                                    )}
                                </div>
                            </div>
                            
                            <div className="flex items-center gap-2 pr-2">
                                <button 
                                    className="p-3 text-slate-300 hover:text-[#4B5320] hover:bg-[#4B5320]/5 rounded-xl transition-all"
                                    title="Open Analysis"
                                >
                                    <Eye size={20} />
                                </button>
                                <button
                                    className="p-3 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
                                    title="Evict Document"
                                    onClick={(e) => deleteDocument(doc.id, e)}
                                >
                                    <Trash2 size={20} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default DocumentsPage;
