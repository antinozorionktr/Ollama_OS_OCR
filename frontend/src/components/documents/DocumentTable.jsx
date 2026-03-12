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
} from 'lucide-react';
import './DocumentTable.css';

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

    /* ── Delete handler ── */
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

    /* ── Download (DOCX) handler ── */
    const handleDownload = async (e, docId, docName) => {
        e.stopPropagation();
        setDownloadingId(docId);
        try {
            // Trigger DOCX generation first
            const genRes = await fetch(`/api/results/${docId}/docx`, { method: 'POST' });
            const genData = await genRes.json();
            if (!genData.success) throw new Error(genData.error || 'Generation failed');

            // Then download
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

    /* ── Status badge ── */
    const getStatusBadge = (status) => {
        switch (status) {
            case 'processing':
                return (
                    <span className="status-badge processing">
                        <Clock size={12} strokeWidth={2.5} />
                        Processing
                    </span>
                );
            case 'review':
                return (
                    <span className="status-badge review">
                        <Eye size={12} strokeWidth={2.5} />
                        Ready for Review
                    </span>
                );
            case 'approved':
                return (
                    <span className="status-badge approved">
                        <CheckCircle2 size={12} strokeWidth={2.5} />
                        Approved
                    </span>
                );
            case 'flagged':
                return (
                    <span className="status-badge flagged">
                        <AlertCircle size={12} strokeWidth={2.5} />
                        Flagged
                    </span>
                );
            default:
                return null;
        }
    };

    /* ── File icon ── */
    const getFileIcon = (type) =>
        type === 'pdf'
            ? <div className="file-icon-wrapper pdf"><FileText size={20} /></div>
            : <div className="file-icon-wrapper img"><ImageIcon size={20} /></div>;

    return (
        <div className="document-table-container">
            <table className="document-table">
                <thead>
                    <tr>
                        <th>DOCUMENT NAME</th>
                        <th>PAGES</th>
                        <th>UPLOAD DATE</th>
                        <th>OCR STATUS</th>
                        <th>DETECTED ELEMENTS</th>
                        <th className="text-right">ACTIONS</th>
                    </tr>
                </thead>
                <tbody>
                    {loading && (
                        <tr>
                            <td colSpan={6} className="table-loading">
                                <Loader2 size={20} className="spin-icon" />
                                Loading documents…
                            </td>
                        </tr>
                    )}
                    {!loading && documents.length === 0 && (
                        <tr>
                            <td colSpan={6} className="table-empty">No documents found.</td>
                        </tr>
                    )}
                    {documents.map((doc) => (
                        <tr
                            key={doc.id}
                            onClick={() => navigate(`/documents/${doc.id}`)}
                            className="doc-row"
                        >
                            <td className="doc-name-cell">
                                {getFileIcon(doc.type)}
                                <span className="doc-name">{doc.name}</span>
                            </td>
                            <td className="doc-pages">{doc.pages}</td>
                            <td className="doc-date">{doc.date}</td>
                            <td className="doc-status">{getStatusBadge(doc.status)}</td>
                            <td className="doc-elements">
                                <div className="tags-wrapper">
                                    {doc.elements.map((tag, idx) => (
                                        <span
                                            key={idx}
                                            className={`element-tag${doc.isAlert ? ' alert-tag' : ''}${tag === 'Analyzing...' ? ' analyzing-text' : ''}`}
                                        >
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </td>
                            <td className="doc-actions" onClick={e => e.stopPropagation()}>
                                <div className="action-buttons">
                                    {/* View */}
                                    <button
                                        className="action-btn view-btn"
                                        title="View document"
                                        onClick={() => navigate(`/documents/${doc.id}`)}
                                    >
                                        <Eye size={16} strokeWidth={2} />
                                    </button>

                                    {/* Download */}
                                    <button
                                        className="action-btn download-btn"
                                        title="Download DOCX"
                                        disabled={downloadingId === doc.id}
                                        onClick={(e) => handleDownload(e, doc.id, doc.name)}
                                    >
                                        {downloadingId === doc.id
                                            ? <Loader2 size={16} className="spin-icon" />
                                            : <Download size={16} strokeWidth={2} />
                                        }
                                    </button>

                                    {/* Delete */}
                                    <button
                                        className="action-btn delete-btn"
                                        title="Delete document"
                                        disabled={deletingId === doc.id}
                                        onClick={(e) => handleDelete(e, doc.id)}
                                    >
                                        {deletingId === doc.id
                                            ? <Loader2 size={16} className="spin-icon" />
                                            : <Trash2 size={16} strokeWidth={2} />
                                        }
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <div className="table-footer">
                <span className="record-count">
                    {loading ? 'LOADING RECORDS…' : `SHOWING ${documents.length} RECORDS`}
                </span>
                <div className="pagination">
                    <button className="page-btn page-nav">&lt;</button>
                    <button className="page-btn active">1</button>
                    <button className="page-btn">2</button>
                    <button className="page-btn">3</button>
                    <button className="page-btn page-nav">&gt;</button>
                </div>
            </div>
        </div>
    );
};

export default DocumentTable;
