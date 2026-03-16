import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    LayoutGrid, Table, CheckSquare, Edit3, PenTool, LayoutTemplate,
    CloudUpload, Paperclip, List, FileText, X, ShieldCheck, Lock, Info, CheckCircle
} from 'lucide-react';

const UploadPage = () => {
    const [uploads, setUploads] = useState([]);
    const fileInputRef = useRef(null);
    const navigate = useNavigate();

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

            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    clearInterval(progressInterval);
                    setUploads(prev => prev.map(u =>
                        u.id === fileId ? { ...u, progress: 100, status: 'complete', documentId: data.document_id } : u
                    ));

                    // Navigate to document viewer after brief delay
                    if (data.document_id) {
                        setTimeout(() => {
                            navigate(`/documents/${data.document_id}`);
                        }, 2000);
                    }
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
        <div className="p-8 max-w-7xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Span 2: Upload Area & Queue */}
                <div className="lg:col-span-2 space-y-8">

                    <div className="space-y-2">
                        <h1 className="text-3xl font-extrabold text-[#2F353B] uppercase tracking-tight">Upload Document</h1>
                        <p className="text-[#475569] max-w-2xl text-base">Securely process field reports, medical records, and official orders through the military-grade OCR pipeline.</p>
                    </div>

                    <div
                        className="relative min-h-[400px] border-2 border-dashed border-[#C2B280]/30 rounded-3xl flex flex-col items-center justify-center p-12 transition-all duration-300 hover:border-[#4B5320] hover:bg-[#C2B280]/5 overflow-hidden group shadow-sm bg-white"
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                    >
                        <div className="absolute inset-0 camouflage-pattern opacity-[0.03] pointer-events-none group-hover:opacity-[0.05] transition-opacity"></div>
                        
                        <div className="relative flex flex-col items-center z-10">
                            <div className="w-20 h-20 mb-6 flex items-center justify-center relative">
                                <div className="absolute inset-0 border-2 border-[#4B5320] rounded-[4px] clip-corner-tl clip-corner-tr pointer-events-none opacity-40"></div>
                                <CloudUpload className="text-[#4B5320] drop-shadow-sm" size={48} />
                            </div>
                            
                            <h3 className="text-2xl font-bold text-[#2F353B] mb-2 uppercase tracking-wide">Drop mission files here</h3>
                            <p className="text-slate-500 mb-8 text-center max-w-sm">Supports high-resolution PDF, JPEG, and PNG. Maximum single file size: 50MB.</p>

                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileSelect}
                                className="hidden"
                                multiple
                            />
                            <button 
                                className="flex items-center gap-2 px-8 py-3.5 bg-[#4B5320] text-white rounded-xl font-bold uppercase tracking-wider text-sm shadow-lg hover:bg-[#3A4310] hover:-translate-y-0.5 transition-all active:translate-y-0"
                                onClick={() => fileInputRef.current.click()}
                            >
                                <Paperclip size={18} />
                                Browse Internal Storage
                            </button>
                        </div>
                    </div>

                    {uploads.length > 0 && (
                        <div className="bg-white rounded-2xl border border-[#C2B280]/20 shadow-sm overflow-hidden">
                            <div className="px-6 py-4 border-b border-[#C2B280]/10 bg-slate-50/50 flex items-center justify-between">
                                <h2 className="flex items-center gap-2 text-sm font-bold text-[#2F353B] uppercase tracking-widest">
                                    <List className="text-[#4B5320]" size={20} />
                                    Active Processing Queue
                                </h2>
                                <span className="bg-[#4B5320]/10 text-[#4B5320] text-[10px] font-black px-2.5 py-1 rounded-full uppercase">
                                    {uploads.filter(u => u.status === 'processing').length} Files Remaining
                                </span>
                            </div>

                            <div className="divide-y divide-[#C2B280]/10">
                                {uploads.map(file => (
                                    <div className="group flex items-center gap-5 p-6 hover:bg-slate-50/50 transition-colors" key={file.id}>
                                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${file.status === 'complete' ? 'bg-emerald-50' : 'bg-red-50'}`}>
                                            {file.status === 'complete' ? (
                                                <CheckCircle className="text-emerald-600" size={24} />
                                            ) : (
                                                <FileText className="text-red-600" size={24} />
                                            )}
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-2">
                                                <p className="text-sm font-bold text-[#2F353B] truncate pr-4 uppercase tracking-tight">{file.name}</p>
                                                <p className={`text-[11px] font-black uppercase ${file.status === 'error' ? 'text-red-500' : 'text-slate-500'}`}>
                                                    {file.status === 'error' ? 'Analysis Failed' : `${file.progress}% • ${file.size}`}
                                                </p>
                                            </div>
                                            <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full transition-all duration-500 ${
                                                        file.status === 'complete' ? 'bg-emerald-500' : file.status === 'error' ? 'bg-red-500' : 'bg-[#4B5320]'
                                                    }`}
                                                    style={{ width: `${file.progress}%` }}
                                                ></div>
                                            </div>
                                        </div>

                                        <button 
                                            className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                            onClick={() => setUploads(prev => prev.filter(u => u.id !== file.id))}
                                        >
                                            <X size={20} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Right Span 1: Capabilities & Info */}
                <div className="space-y-6">
                    <div className="bg-[#2F353B] rounded-3xl p-8 relative overflow-hidden shadow-xl border border-white/5">
                        <div className="absolute inset-0 camouflage-pattern opacity-10 pointer-events-none"></div>
                        <div className="relative z-10">
                            <div className="flex items-center gap-3 mb-8 border-b border-white/10 pb-4">
                                <ShieldCheck className="text-[#C2B280]" size={24} />
                                <h3 className="text-[#C2B280] font-black uppercase tracking-widest text-sm">System Capabilities</h3>
                            </div>

                            <div className="space-y-6">
                                {capabilities.map((cap, idx) => {
                                    const Icon = cap.icon;
                                    return (
                                        <div key={idx} className="flex gap-4 group">
                                            <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center shrink-0 group-hover:bg-white/10 transition-colors">
                                                <Icon className="text-[#C2B280]/80" size={20} />
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-white text-xs font-bold uppercase tracking-tight">{cap.title}</p>
                                                <p className="text-white/40 text-[10px] leading-relaxed uppercase font-semibold">{cap.desc}</p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            <div className="mt-10 pt-6 border-t border-white/10 flex items-center justify-between text-[#C2B280]/60">
                                <span className="text-[10px] font-black uppercase tracking-[0.2em]">Security Level: Confidential</span>
                                <Lock size={14} />
                            </div>
                        </div>
                    </div>

                    <div className="bg-[#C2B280]/10 border border-[#C2B280]/20 rounded-2xl p-6">
                        <div className="flex items-center gap-2 mb-3 text-[#4B5320]">
                            <Info size={18} />
                            <h4 className="text-xs font-black uppercase tracking-widest">Protocol Notice</h4>
                        </div>
                        <p className="text-[#2F353B]/70 text-[11px] leading-relaxed font-bold uppercase italic">
                            All documents uploaded are processed via the secure intranet gateway. Data is encrypted using AES-256 standards before entering the main repository.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UploadPage;
