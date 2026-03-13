import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Clock, Layers, Trash2, Eye } from 'lucide-react';
import './DocumentsPage.css';

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
        <div className="documents-page light-theme">
            <div className="documents-header">
                <h1 className="page-title">Processed Documents</h1>
                <p className="page-desc">{documents.length} document{documents.length !== 1 ? 's' : ''} in the system</p>
            </div>

            {loading ? (
                <div className="documents-loading">Loading documents...</div>
            ) : documents.length === 0 ? (
                <div className="documents-empty">
                    <FileText size={48} />
                    <p>No documents processed yet.</p>
                    <button onClick={() => navigate('/')}>Upload a document</button>
                </div>
            ) : (
                <div className="documents-list">
                    {documents.map(doc => (
                        <div
                            key={doc.id}
                            className="document-card"
                            onClick={() => navigate(`/documents/${doc.id}`)}
                        >
                            <div className="document-icon">
                                <FileText size={24} />
                            </div>
                            <div className="document-info">
                                <h3 className="document-name">{doc.filename}</h3>
                                <div className="document-meta">
                                    <span><Layers size={14} /> {doc.total_pages} page{doc.total_pages !== 1 ? 's' : ''}</span>
                                    <span><Clock size={14} /> {formatDate(doc.uploaded_at)}</span>
                                    {doc.processing_time_seconds && (
                                        <span>{doc.processing_time_seconds.toFixed(1)}s</span>
                                    )}
                                </div>
                            </div>
                            <div className="document-actions">
                                <button className="view-btn" title="View">
                                    <Eye size={18} />
                                </button>
                                <button
                                    className="delete-btn"
                                    title="Delete"
                                    onClick={(e) => deleteDocument(doc.id, e)}
                                >
                                    <Trash2 size={18} />
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
