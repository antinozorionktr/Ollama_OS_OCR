import React, { useState, useRef } from 'react';
import {
    LayoutGrid, Table, CheckSquare, Edit3, PenTool, LayoutTemplate,
    CloudUpload, Paperclip, List, FileText, X, ShieldCheck, Lock, Info, CheckCircle
} from 'lucide-react';
import './UploadPage.css';

const UploadPage = () => {
    const [uploads, setUploads] = useState([]);
    const fileInputRef = useRef(null);

    const capabilities = [
        { icon: LayoutGrid, title: 'Complex Forms', desc: 'Multi-column military application processing.' },
        { icon: Table, title: 'Tables & Grids', desc: 'Extraction of supply lists and personnel tables.' },
        { icon: CheckSquare, title: 'Checklists', desc: 'Verification of equipment inspection logs.' },
        { icon: Edit3, title: 'Handwritten Notes', desc: 'Advanced OCR for field manual annotations.' },
        { icon: PenTool, title: 'Digital Signatures', desc: 'Authentication of commanding officer approval.' },
        { icon: LayoutTemplate, title: 'Mixed Layouts', desc: 'Processing of unstructured operational orders.' }
    ];

    const handleFileSelect = (e) => {
        uploadFiles(Array.from(e.target.files));
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            uploadFiles(Array.from(e.dataTransfer.files));
            e.dataTransfer.clearData();
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
    };

    const uploadFiles = (files) => {
        files.forEach(file => {
            const fileId = Math.random().toString(36).substring(7);

            const newUpload = {
                id: fileId,
                name: file.name,
                size: (file.size / (1024 * 1024)).toFixed(1) + ' MB',
                progress: 0,
                status: 'processing'
            };

            setUploads(prev => [...prev, newUpload]);

            const formData = new FormData();
            formData.append('file', file);

            // Simulate OCR processing time while fetch runs
            const progressInterval = setInterval(() => {
                setUploads(prev => prev.map(u => {
                    if (u.id === fileId && u.progress < 90) {
                        return { ...u, progress: u.progress + 5 };
                    }
                    return u;
                }));
            }, 1000);

            fetch('/api/process/upload?extract_raw=true&extract_structured=true', {
                method: 'POST',
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    clearInterval(progressInterval);
                    setUploads(prev => prev.map(u =>
                        u.id === fileId ? { ...u, progress: 100, status: 'complete' } : u
                    ));

                    setTimeout(() => {
                        setUploads(prev => prev.filter(u => u.id !== fileId));
                    }, 8000);
                })
                .catch(err => {
                    clearInterval(progressInterval);
                    setUploads(prev => prev.map(u =>
                        u.id === fileId ? { ...u, status: 'error' } : u
                    ));
                });
        });
    };

    return (
        <div className="upload-page">
            <div className="upload-grid">
                {/* Left Span 2: Upload Area & Queue */}
                <div className="upload-main-col">

                    <div className="upload-text-header">
                        <h1 className="page-title">Upload Document</h1>
                        <p className="page-desc">Securely process field reports, medical records, and official orders through the military-grade OCR pipeline.</p>
                    </div>

                    <div
                        className="upload-dropzone group"
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                    >
                        <div className="camouflage-pattern dropzone-camo"></div>
                        <div className="dropzone-content">
                            <div className="dropzone-icon-box stencil-border stencil-top-left stencil-top-right">
                                <CloudUpload className="text-primary upload-cloud-icon" size={48} />
                            </div>
                            <h3 className="dropzone-title">Drop mission files here</h3>
                            <p className="dropzone-desc">Supports high-resolution PDF, JPEG, and PNG. Maximum single file size: 50MB.</p>

                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileSelect}
                                style={{ display: 'none' }}
                                multiple
                            />
                            <button className="browse-btn" onClick={() => fileInputRef.current.click()}>
                                <Paperclip size={18} />
                                Browse Internal Storage
                            </button>
                        </div>
                    </div>

                    {uploads.length > 0 && (
                        <div className="processing-queue">
                            <div className="queue-header">
                                <h2 className="queue-title">
                                    <List className="text-primary" size={20} />
                                    Active Processing Queue
                                </h2>
                                <span className="queue-badge">{uploads.filter(u => u.status === 'processing').length} Files Remaining</span>
                            </div>

                            <div className="queue-list">
                                {uploads.map(file => (
                                    <div className="queue-item" key={file.id}>
                                        <div className="file-icon-box">
                                            {file.status === 'complete' ? (
                                                <CheckCircle className="text-green-600" size={24} color="#059669" />
                                            ) : (
                                                <FileText className="text-red-600" size={24} />
                                            )}
                                        </div>

                                        <div className="file-details">
                                            <div className="file-info-header">
                                                <p className="file-name">{file.name}</p>
                                                <p className="file-progress-text" style={{ color: file.status === 'error' ? 'red' : 'inherit' }}>
                                                    {file.status === 'error' ? 'Failed' : `${file.progress}% • ${file.size}`}
                                                </p>
                                            </div>
                                            <div className="progress-bar-container">
                                                <div
                                                    className="progress-bar"
                                                    style={{
                                                        width: `${file.progress}%`,
                                                        backgroundColor: file.status === 'complete' ? '#10b981' : file.status === 'error' ? '#ef4444' : 'var(--color-primary)'
                                                    }}
                                                ></div>
                                            </div>
                                        </div>

                                        <button className="cancel-btn" onClick={() => setUploads(prev => prev.filter(u => u.id !== file.id))}>
                                            <X size={20} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Right Span 1: Capabilities & Info */}
                <div className="upload-side-col">
                    <div className="capabilities-card">
                        <div className="camouflage-pattern caps-camo"></div>
                        <div className="caps-content">
                            <div className="caps-header">
                                <ShieldCheck className="text-secondary" size={24} />
                                <h3>System Capabilities</h3>
                            </div>

                            <div className="caps-list">
                                {capabilities.map((cap, idx) => {
                                    const Icon = cap.icon;
                                    return (
                                        <div key={idx} className="cap-item">
                                            <Icon className="text-secondary" size={20} />
                                            <div className="cap-text">
                                                <p className="cap-title">{cap.title}</p>
                                                <p className="cap-desc">{cap.desc}</p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                        <div className="caps-footer text-primary">
                            <span className="security-level">Security Level: Confidential</span>
                            <Lock size={16} />
                        </div>
                    </div>

                    <div className="protocol-notice">
                        <div className="notice-header">
                            <Info className="text-primary" size={18} />
                            <h4>Protocol Notice</h4>
                        </div>
                        <p className="notice-content">
                            All documents uploaded are processed via the secure intranet gateway. Data is encrypted using AES-256 standards before entering the main repository.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UploadPage;
