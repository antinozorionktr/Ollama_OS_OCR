import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    FileText,
    Image as ImageIcon,
    Download,
    Trash2,
    Eye,
    CheckCircle2,
    AlertCircle,
    Clock,
    Loader2,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';

const DocumentTable = () => {
    const navigate = useNavigate();
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deletingId, setDeletingId] = useState(null);
    const [downloadingId, setDownloadingId] = useState(null);

    useEffect(() => {
        fetch('/api/results')
            .then(res => res.json())
            .then(data => {
                const results = data.results || [];
                const mappedDocs = results.map(r => {
                    let status = 'processing';
                    if (r.error) status = 'flagged';
                    else if (r.formatted_text === 'approved') status = 'approved';
                    else if (r.raw_text) status = 'review';

                    let elements = [];
                    if (r.structured_data && Object.keys(r.structured_data).length > 0) {
                        elements = Object.keys(r.structured_data).slice(0, 2).map(k =>
                            k.toUpperCase().replace(/_/g, ' ')
                        );
                    }
                    if (elements.length === 0 && status === 'processing') elements = ['Analyzing...'];
                    if (elements.length === 0 && status === 'review') elements = ['PROCESSED'];
                    if (elements.length === 0 && status === 'approved') elements = ['APPROVED'];
                    if (elements.length === 0 && status === 'flagged') elements = ['ERROR'];

                    const ext = r.file_name?.match(/\.(png|jpe?g)$/i) ? 'img' : 'pdf';

                    return {
                        id: r.id,
                        name: r.file_name || 'Unknown Document',
                        type: ext,
                        pages: r.page_count || 1,
                        date: r.processed_at ? r.processed_at.split('T')[0] : 'Pending',
                        status,
                        elements,
                        isAlert: status === 'flagged',
                    };
                });
                setDocuments(mappedDocs);
            })
            .catch(err => console.error('Error fetching results', err))
            .finally(() => setLoading(false));
    }, []);

    const handleDelete = async (e, docId) => {
        e.stopPropagation();
        if (!window.confirm('Delete this document and its OCR data?')) return;
        setDeletingId(docId);
        try {
            await fetch(`/api/results/${docId}`, { method: 'DELETE' });
            setDocuments(prev => prev.filter(d => d.id !== docId));
        } catch (err) {
            console.error('Delete failed', err);
            alert('Failed to delete document.');
        } finally {
            setDeletingId(null);
        }
    };

    const handleDownload = async (e, docId, docName) => {
        e.stopPropagation();
        setDownloadingId(docId);
        try {
            const genRes = await fetch(`/api/results/${docId}/docx`, { method: 'POST' });
            const genData = await genRes.json();
            if (!genData.success) throw new Error(genData.error || 'Generation failed');

            const dlRes = await fetch(`/api/results/${docId}/docx/download`);
            if (!dlRes.ok) throw new Error('Download failed');
            const blob = await dlRes.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${docName.replace(/\.[^.]+$/, '')}.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Download failed', err);
            alert('Failed to download document.');
        } finally {
            setDownloadingId(null);
        }
    };

    const getStatusBadge = (status) => {
        switch (status) {
            case 'processing':
                return (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-[#2F353B] text-[10px] font-black uppercase tracking-widest border border-slate-200">
                        <Clock size={12} className="text-[#4B5320] animate-pulse" />
                        Processing
                    </span>
                );
            case 'review':
                return (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-[10px] font-black uppercase tracking-widest border border-blue-100">
                        <Eye size={12} />
                        Ready for Review
                    </span>
                );
            case 'approved':
                return (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-black uppercase tracking-widest border border-emerald-100">
                        <CheckCircle2 size={12} />
                        Approved
                    </span>
                );
            case 'flagged':
                return (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-50 text-rose-700 text-[10px] font-black uppercase tracking-widest border border-rose-100">
                        <AlertCircle size={12} />
                        Flagged
                    </span>
                );
            default:
                return null;
        }
    };

    const getFileIcon = (type) => (
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${type === 'pdf' ? 'bg-rose-50 text-rose-500' : 'bg-blue-50 text-blue-500'}`}>
            {type === 'pdf' ? <FileText size={20} /> : <ImageIcon size={20} />}
        </div>
    );

    return (
        <div className="bg-white rounded-3xl border border-[#C2B280]/20 shadow-sm overflow-hidden flex flex-col">
            <div className="overflow-x-auto overflow-y-hidden">
                <table className="w-full border-collapse">
                    <thead>
                        <tr className="bg-slate-50/50 border-b border-[#C2B280]/10">
                            <th className="py-5 px-6 text-left text-[10px] font-black text-[#4B5320] uppercase tracking-[0.2em] whitespace-nowrap">DOCUMENT NAME</th>
                            <th className="py-5 px-6 text-left text-[10px] font-black text-[#4B5320] uppercase tracking-[0.2em] whitespace-nowrap">UNITS</th>
                            <th className="py-5 px-6 text-left text-[10px] font-black text-[#4B5320] uppercase tracking-[0.2em] whitespace-nowrap">TIMESTAMP</th>
                            <th className="py-5 px-6 text-left text-[10px] font-black text-[#4B5320] uppercase tracking-[0.2em] whitespace-nowrap">OCR CLASSIFICATION</th>
                            <th className="py-5 px-6 text-left text-[10px] font-black text-[#4B5320] uppercase tracking-[0.2em] whitespace-nowrap">ENTITIES</th>
                            <th className="py-5 px-6 text-right text-[10px] font-black text-[#4B5320] uppercase tracking-[0.2em] whitespace-nowrap">ACTION PANEL</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#C2B280]/10">
                        {loading && (
                            <tr>
                                <td colSpan={6} className="py-20 text-center">
                                    <div className="flex flex-col items-center gap-4 text-[#4B5320]/40">
                                        <Loader2 size={32} className="animate-spin" />
                                        <span className="font-black uppercase tracking-widest text-[10px]">Retrieving secure records...</span>
                                    </div>
                                </td>
                            </tr>
                        )}
                        {!loading && documents.length === 0 && (
                            <tr>
                                <td colSpan={6} className="py-20 text-center text-slate-400 font-bold uppercase tracking-widest text-xs italic">
                                    No records found in current sector.
                                </td>
                            </tr>
                        )}
                        {documents.map((doc) => (
                            <tr
                                key={doc.id}
                                onClick={() => navigate(`/documents/${doc.id}`)}
                                className="group hover:bg-[#C2B280]/5 transition-all cursor-pointer"
                            >
                                <td className="py-4 px-6">
                                    <div className="flex items-center gap-4">
                                        {getFileIcon(doc.type)}
                                        <span className="text-sm font-extrabold text-[#2F353B] group-hover:text-[#4B5320] transition-colors truncate max-w-[200px] uppercase tracking-tight">
                                            {doc.name}
                                        </span>
                                    </div>
                                </td>
                                <td className="py-4 px-6">
                                    <span className="text-xs font-black text-slate-400 tracking-widest uppercase">{doc.pages} Pages</span>
                                </td>
                                <td className="py-4 px-6 text-[11px] font-bold text-slate-500 tabular-nums">
                                    {doc.date}
                                </td>
                                <td className="py-4 px-6">
                                    {getStatusBadge(doc.status)}
                                </td>
                                <td className="py-4 px-6">
                                    <div className="flex flex-wrap gap-1.5">
                                        {doc.elements.map((tag, idx) => (
                                            <span
                                                key={idx}
                                                className={`
                                                    px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-tighter border
                                                    ${doc.isAlert ? 'bg-rose-50 text-rose-600 border-rose-100' : 'bg-[#4B5320]/5 text-[#4B5320] border-[#4B5320]/10'}
                                                    ${tag === 'Analyzing...' ? 'animate-pulse' : ''}
                                                `}
                                            >
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                </td>
                                <td className="py-4 px-6 text-right" onClick={e => e.stopPropagation()}>
                                    <div className="flex items-center justify-end gap-1">
                                        <button
                                            className="p-2 text-slate-300 hover:text-[#4B5320] hover:bg-[#4B5320]/5 rounded-lg transition-all"
                                            onClick={() => navigate(`/documents/${doc.id}`)}
                                        >
                                            <Eye size={16} />
                                        </button>
                                        <button
                                            className="p-2 text-slate-300 hover:text-[#4B5320] hover:bg-[#4B5320]/5 rounded-lg transition-all disabled:opacity-30"
                                            disabled={downloadingId === doc.id}
                                            onClick={(e) => handleDownload(e, doc.id, doc.name)}
                                        >
                                            {downloadingId === doc.id ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                                        </button>
                                        <button
                                            className="p-2 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all disabled:opacity-30"
                                            disabled={deletingId === doc.id}
                                            onClick={(e) => handleDelete(e, doc.id)}
                                        >
                                            {deletingId === doc.id ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="px-8 py-5 flex items-center justify-between border-t border-[#C2B280]/10 bg-slate-50/30">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                    {loading ? 'CALCULATING...' : `TOTAL ARCHIVE RECORDS: ${documents.length}`}
                </span>
                <div className="flex items-center gap-1.5">
                    <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-[#C2B280]/10 text-slate-400 hover:border-[#4B5320]/30 hover:text-[#4B5320] disabled:opacity-20 transition-all">
                        <ChevronLeft size={16} />
                    </button>
                    {[1, 2, 3].map(p => (
                        <button
                            key={p}
                            className={`w-8 h-8 flex items-center justify-center rounded-lg text-[10px] font-black transition-all ${p === 1 ? 'bg-[#4B5320] text-white shadow-md' : 'text-slate-400 hover:text-[#4B5320]'}`}
                        >
                            {p}
                        </button>
                    ))}
                    <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-[#C2B280]/10 text-slate-400 hover:border-[#4B5320]/30 hover:text-[#4B5320] transition-all">
                        <ChevronRight size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DocumentTable;
