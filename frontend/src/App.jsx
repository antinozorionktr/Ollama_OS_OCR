import React, { useState, useEffect } from 'react';
import {
  Upload,
  FileText,
  CheckCircle,
  LayoutDashboard,
  History,
  Settings,
  Activity,
  ArrowRight,
  Shield,
  Zap,
  Cpu,
  Eye,
  X,
  Download
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ocrService, createWebSocket } from './services/api';
import logo from './assets/logo.png';

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [results, setResults] = useState([]);
  const [ocrLogs, setOcrLogs] = useState([]);
  const [stats, setStats] = useState({ total_files: 0, invoice: 0, contract: 0, crac: 0, processed_count: {} });
  const [filterType, setFilterType] = useState(null);
  const [selectedResult, setSelectedResult] = useState(null);
  const [selectedDocType, setSelectedDocType] = useState('invoice');

  useEffect(() => {
    fetchStats();
    fetchResults();

    const ws = createWebSocket((log) => {
      if (log.type === 'batch_update') {
        const msg = `[${new Date().toLocaleTimeString()}] PROCESS: ${log.current_file || 'Processing...'} (${log.progress_pct}%)`;
        setOcrLogs(prev => [msg, ...prev].slice(0, 50));
      } else if (log.type === 'connected') {
        setOcrLogs(prev => [`[${new Date().toLocaleTimeString()}] SYSTEM: Neural Connection Established`, ...prev]);
      }
    });

    return () => ws.close();
  }, [filterType]);

  const fetchStats = async () => {
    try {
      const resp = await ocrService.getStats();
      setStats(resp.data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  };

  const fetchResults = async () => {
    try {
      const resp = await ocrService.getResults(filterType);
      setResults(resp.data.results);
    } catch (err) {
      console.error("Failed to fetch results:", err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadProgress(10);

    const progressInterval = setInterval(() => {
      setUploadProgress(prev => (prev < 90 ? prev + 5 : prev));
    }, 200);

    try {
      const resp = await ocrService.uploadFile(file, selectedDocType);
      setUploadProgress(100);
      clearInterval(progressInterval);

      const logMsg = `[${new Date().toLocaleTimeString()}] SUCCESS: ${file.name} processed in ${resp.data.processing_time_seconds}s`;
      setOcrLogs(prev => [logMsg, ...prev]);

      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setActiveTab('results');
        fetchResults();
        fetchStats();
      }, 1000);
    } catch (err) {
      clearInterval(progressInterval);
      setIsUploading(false);
      alert(`Processing failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9fa] flex flex-col font-sans selection:bg-india-saffron selection:text-white">
      {/* Top Premium Header */}
      <header className="h-24 bg-tricolour-gradient flex items-center justify-between px-12 sticky top-0 z-50 shadow-lg overflow-hidden border-b-4 border-india-navy/10">
        {/* Left Logo */}
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="relative"
        >
          <img src={logo} alt="DocVision Logo" className="h-16 w-16 object-contain drop-shadow-md" />
        </motion.div>

        {/* Centered Title */}
        <div className="flex-1 flex flex-col items-center justify-center">
          <motion.div
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="flex flex-col items-center"
          >
            <h1 className="text-3xl font-black tracking-[0.15em] text-india-navy uppercase drop-shadow-sm">
              DOCVISION OCR SYSTEM
            </h1>
            <div className="h-1 w-32 bg-india-navy mt-1 rounded-full opacity-20" />
          </motion.div>
        </div>

        {/* Right Logo */}
        <motion.div
          initial={{ x: 20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="relative"
        >
          <img src={logo} alt="DocVision Logo" className="h-16 w-16 object-contain drop-shadow-md" />
        </motion.div>
      </header>

      {/* Sub-header for Navigation & Status */}
      <div className="bg-white/80 backdrop-blur-md border-b border-gray-200 h-14 flex items-center justify-between px-8 sticky top-24 z-40 shadow-sm">
        <nav className="flex items-center space-x-1">
          <TabButton
            active={activeTab === 'dashboard'}
            onClick={() => setActiveTab('dashboard')}
            icon={<LayoutDashboard size={16} />}
            label="Dashboard"
          />
          <TabButton
            active={activeTab === 'upload'}
            onClick={() => setActiveTab('upload')}
            icon={<Upload size={16} />}
            label="Neural Upload"
          />
          <TabButton
            active={activeTab === 'results'}
            onClick={() => setActiveTab('results')}
            icon={<FileText size={16} />}
            label="Extraction Vault"
          />
          <TabButton
            active={activeTab === 'logs'}
            onClick={() => setActiveTab('logs')}
            icon={<Activity size={16} />}
            label="Neural Stream"
          />
        </nav>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-3 py-1 bg-india-green/10 text-india-green rounded-full text-[10px] font-bold tracking-wider">
            <div className="w-1.5 h-1.5 bg-india-green rounded-full animate-pulse" />
            <span>OLLAMA ACTIVE</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center border border-gray-100 cursor-pointer hover:bg-gray-100 transition-colors">
            <Settings size={16} className="text-gray-400" />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8 max-w-7xl mx-auto w-full">
        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' && (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-8"
            >
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-india-navy">Welcome, <span className="text-india-saffron">Technician</span></h1>
                  <p className="text-gray-500 mt-2">DocVision Neural Engine is standing by for document ingestion.</p>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500 bg-white px-4 py-2 rounded-lg border border-gray-200">
                  <CheckCircle size={16} className="text-india-green" />
                  <span>System Integrity: 100%</span>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatCard label="Total Files" value={stats.total_files} icon={<FileText className="text-india-saffron" />} trend="Across all vaults" />
                <StatCard label="Invoices" value={stats.invoice} icon={<FileText className="text-india-navy" />} trend="Financial" />
                <StatCard label="Contracts" value={stats.contract} icon={<Shield className="text-india-green" />} trend="Legal" />
                <StatCard label="CRACs" value={stats.crac} icon={<Zap className="text-orange-500" />} trend="Logistics" />
              </div>

              {/* Action Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="card-glass p-8 relative overflow-hidden group cursor-pointer" onClick={() => setActiveTab('upload')}>
                  <div className="absolute top-0 right-0 w-32 h-32 bg-india-saffron opacity-5 -mr-8 -mt-8 rounded-full transition-transform group-hover:scale-150 duration-500" />
                  <div className="relative z-10">
                    <div className="w-14 h-14 bg-india-saffron bg-opacity-10 rounded-2xl flex items-center justify-center mb-6">
                      <Upload className="text-india-saffron w-8 h-8" />
                    </div>
                    <h3 className="text-2xl font-bold text-india-navy">Neural Ingestion</h3>
                    <p className="text-gray-500 mt-2 mb-6">Begin the extraction process by uploading Invoices, Contracts, or CRAC documents.</p>
                    <button className="btn-primary flex items-center gap-2">
                      Start Mission <ArrowRight size={18} />
                    </button>
                  </div>
                </div>

                <div className="card-glass p-8 relative overflow-hidden group cursor-pointer" onClick={() => setActiveTab('results')}>
                  <div className="absolute top-0 right-0 w-32 h-32 bg-india-green opacity-5 -mr-8 -mt-8 rounded-full transition-transform group-hover:scale-150 duration-500" />
                  <div className="relative z-10">
                    <div className="w-14 h-14 bg-india-green bg-opacity-10 rounded-2xl flex items-center justify-center mb-6">
                      <Shield className="text-india-green w-8 h-8" />
                    </div>
                    <h3 className="text-2xl font-bold text-india-navy">Extraction Vault</h3>
                    <p className="text-gray-500 mt-2 mb-6">Review, download, and manage your structured data extractions and documents.</p>
                    <button className="btn-secondary flex items-center gap-2">
                      Enter Vault <ArrowRight size={18} />
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              className="max-w-2xl mx-auto"
            >
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-india-navy">Neural Ingestion</h2>
                <p className="text-gray-500">Secure document processing powered by Indian AI Precision</p>
              </div>

              <div className="card-glass p-12 border-dashed border-2 border-india-saffron border-opacity-30 flex flex-col items-center justify-center text-center space-y-6 relative overflow-hidden">
                {isUploading ? (
                  <div className="w-full space-y-6">
                    <div className="relative w-48 h-48 mx-auto">
                      <svg className="w-full h-full" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="45" fill="none" stroke="#eee" strokeWidth="8" />
                        <circle cx="50" cy="50" r="45" fill="none" stroke="var(--saffron)" strokeWidth="8" strokeDasharray="283" strokeDashoffset={283 - (283 * uploadProgress) / 100} strokeLinecap="round" transform="rotate(-90 50 50)" className="transition-all duration-300" />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-3xl font-bold text-india-navy">{uploadProgress}%</span>
                        <span className="text-[10px] uppercase tracking-widest text-gray-500">Processing</span>
                      </div>
                    </div>
                    <div className="text-india-navy font-semibold animate-pulse">ANALYZING DOCUMENT NEURAL PATHWAYS...</div>
                  </div>
                ) : (
                  <>
                    <div className="w-20 h-20 bg-india-saffron bg-opacity-10 rounded-full flex items-center justify-center mb-2">
                      <Upload className="text-india-saffron w-10 h-10" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-india-navy">Drop Missions Here</h4>
                      <p className="text-gray-400 text-sm mt-1">PDF, DOCX, PNG (Max 50MB)</p>
                    </div>
                    <div className="flex flex-wrap gap-4 justify-center">
                      <button
                        onClick={() => setSelectedDocType('invoice')}
                        className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${selectedDocType === 'invoice' ? 'bg-india-saffron text-white' : 'bg-gray-100 text-gray-500'}`}
                      >
                        INVOICE
                      </button>
                      <button
                        onClick={() => setSelectedDocType('contract')}
                        className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${selectedDocType === 'contract' ? 'bg-india-navy text-white' : 'bg-gray-100 text-gray-500'}`}
                      >
                        CONTRACT
                      </button>
                      <button
                        onClick={() => setSelectedDocType('crac')}
                        className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${selectedDocType === 'crac' ? 'bg-india-green text-white' : 'bg-gray-100 text-gray-500'}`}
                      >
                        CRAC
                      </button>
                    </div>
                    <label className="btn-primary cursor-pointer">
                      Select Documents
                      <input type="file" className="hidden" onChange={handleFileUpload} />
                    </label>
                  </>
                )}
              </div>
            </motion.div>
          )}

          {activeTab === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <h2 className="text-2xl font-bold text-india-navy">Mission Records</h2>
                <div className="flex items-center gap-2 bg-white p-1 rounded-xl shadow-sm border border-gray-100">
                  <FilterTab active={filterType === null} onClick={() => setFilterType(null)} label="All" />
                  <FilterTab active={filterType === 'invoice'} onClick={() => setFilterType('invoice')} label="Invoices" />
                  <FilterTab active={filterType === 'contract'} onClick={() => setFilterType('contract')} label="Contracts" />
                  <FilterTab active={filterType === 'crac'} onClick={() => setFilterType('crac')} label="CRACs" />
                </div>
              </div>

              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-[#f8f9fa] border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Document</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Type</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Confidence</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {results.length > 0 ? (
                      results.map(res => (
                        <ResultRow
                          key={res.id}
                          name={res.file_name}
                          type={res.doc_type}
                          date={new Date(res.processed_at).toLocaleString()}
                          confidence={(res.structured_data?.confidence * 100 || 95).toFixed(1) + '%'}
                          onView={() => setSelectedResult(res)}
                        />
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" className="px-6 py-12 text-center text-gray-400 font-medium uppercase tracking-widest text-xs">
                          No neural records found in this vault
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}

          {activeTab === 'logs' && (
            <motion.div
              key="logs"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-india-navy">Neural Stream</h2>
                <div className="flex items-center gap-2 text-xs font-mono text-india-green">
                  <div className="w-2 h-2 bg-india-green rounded-full animate-ping" />
                  REAL-TIME MONITORING
                </div>
              </div>

              <div className="bg-india-navy rounded-2xl p-6 font-mono text-sm h-[500px] overflow-y-auto shadow-2xl flex flex-col items-start text-left">
                {ocrLogs.length > 0 ? (
                  ocrLogs.map((log, i) => (
                    <div key={i} className="text-gray-500 mb-1">
                      {log.includes('SUCCESS') ? (
                        <span className="text-india-green">{log}</span>
                      ) : log.includes('PROCESS') ? (
                        <span className="text-india-saffron">{log}</span>
                      ) : log.includes('SYSTEM') ? (
                        <span className="text-blue-400 font-bold">{log}</span>
                      ) : log}
                    </div>
                  ))
                ) : (
                  <div className="text-gray-600 animate-pulse">AWAITING NEURAL SIGNALS...</div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <AnimatePresence>
        {selectedResult && (
          <PreviewModal
            result={selectedResult}
            onClose={() => setSelectedResult(null)}
          />
        )}
      </AnimatePresence>

      {/* Decorative Tricolour Footer Bar */}
      <footer className="h-2 w-full flex">
        <div className="flex-1 bg-india-saffron" />
        <div className="flex-1 bg-white" />
        <div className="flex-1 bg-india-green" />
      </footer>
    </div>
  );
};

const TabButton = ({ active, onClick, icon, label }) => (
  <button
    onClick={onClick}
    className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${active
      ? 'bg-india-navy text-white shadow-md'
      : 'text-gray-500 hover:bg-gray-100'
      }`}
  >
    {icon}
    <span>{label}</span>
  </button>
);

const StatCard = ({ label, value, icon, trend }) => (
  <div className="card-glass p-6">
    <div className="flex items-center justify-between mb-4">
      <div className="w-12 h-12 bg-white rounded-xl shadow-inner flex items-center justify-center">
        {icon}
      </div>
      <span className="text-[10px] font-bold text-india-green uppercase tracking-wider">{trend}</span>
    </div>
    <div className="text-3xl font-black text-india-navy tracking-tight">{value}</div>
    <div className="text-gray-400 text-xs font-semibold uppercase tracking-widest mt-1">{label}</div>
  </div>
);

const FilterTab = ({ active, onClick, label }) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${active ? 'bg-india-navy text-white shadow-md' : 'text-gray-500 hover:bg-gray-50'}`}
  >
    {label.toUpperCase()}
  </button>
);

const PreviewModal = ({ result, onClose }) => {
  const [modalTab, setModalTab] = useState('structured');
  const previewUrl = ocrService.getPreviewUrl(result.id);
  const isDocx = result.file_name.toLowerCase().endsWith('.docx');

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] bg-india-navy/60 backdrop-blur-sm flex items-center justify-center p-4 md:p-8"
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="bg-white w-full max-w-6xl h-full max-h-[90vh] rounded-3xl overflow-hidden flex flex-col shadow-2xl"
      >
        <div className="p-6 border-b flex items-center justify-between bg-india-navy text-white">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center">
              <Eye size={24} />
            </div>
            <div>
              <h3 className="text-xl font-bold truncate max-w-md text-white">{result.file_name}</h3>
              <p className="text-xs text-india-green font-bold tracking-widest uppercase">{result.doc_type} RECORD</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={ocrService.getDownloadUrl(result.id)}
              target="_blank"
              rel="noreferrer"
              className="p-3 bg-white/10 hover:bg-white/20 rounded-xl transition-colors text-white"
              title="Download DOCX"
            >
              <Download size={20} />
            </a>
            <button
              onClick={onClose}
              className="p-3 bg-india-saffron hover:bg-india-saffron/80 rounded-xl transition-colors shadow-lg text-white"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-gray-50">
          <div className="flex-1 border-r border-gray-200 overflow-hidden flex flex-col">
            <div className="p-4 bg-white border-b flex items-center justify-between">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">Original Document Stream</span>
            </div>
            <div className="flex-1 p-8 overflow-auto">
              {isDocx ? (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
                  <div className="w-24 h-24 bg-blue-50 text-blue-500 rounded-3xl flex items-center justify-center">
                    <FileText size={48} />
                  </div>
                  <div>
                    <h4 className="text-lg font-bold text-india-navy">DOCX Preview Unsupported</h4>
                    <p className="text-sm text-gray-500">Document previews are optimized for PDF and Images.<br />Please download to view the full content.</p>
                  </div>
                </div>
              ) : (
                <iframe
                  src={previewUrl}
                  className="w-full h-full rounded-xl shadow-lg border-4 border-white bg-white"
                  title="Document Preview"
                />
              )}
            </div>
          </div>

          <div className="w-full md:w-96 flex flex-col">
            <div className="p-4 bg-white border-b flex items-center justify-between gap-1 overflow-x-auto">
              <button
                onClick={() => setModalTab('structured')}
                className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${modalTab === 'structured' ? 'bg-india-navy text-white shadow-md' : 'text-gray-400 hover:bg-gray-100'}`}
              >
                Structured
              </button>
              <button
                onClick={() => setModalTab('raw')}
                className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${modalTab === 'raw' ? 'bg-india-navy text-white shadow-md' : 'text-gray-400 hover:bg-gray-100'}`}
              >
                Raw Text
              </button>
              <div className="flex-1" />
              <div className="px-2 py-0.5 bg-india-green/10 text-india-green rounded text-[10px] font-black italic whitespace-nowrap">VERIFIED</div>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {modalTab === 'structured' ? (
                <>
                  {Object.entries(result.structured_data || {}).map(([key, val]) => (
                    <div key={key}>
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">{key.replace(/_/g, ' ')}</label>
                      <div className="text-sm font-bold text-india-navy mt-1 bg-white p-3 rounded-xl shadow-sm border border-gray-100">
                        {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                      </div>
                    </div>
                  ))}
                </>
              ) : (
                <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 text-xs font-mono text-gray-600 whitespace-pre-wrap leading-relaxed">
                  {result.raw_text || "No raw text available for this record."}
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

const ResultRow = ({ name, type, date, confidence, onView }) => (
  <tr className="hover:bg-gray-50 transition-colors group">
    <td className="px-6 py-4 flex items-center space-x-3">
      <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center">
        <FileText size={16} className="text-gray-400" />
      </div>
      <span className="font-semibold text-india-navy text-sm max-w-[200px] truncate">{name}</span>
    </td>
    <td className="px-6 py-4">
      <span className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase ${type === 'invoice' ? 'bg-orange-50 text-orange-600' :
        type === 'contract' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'
        }`}>
        {type}
      </span>
    </td>
    <td className="px-6 py-4 text-xs text-gray-500">{date}</td>
    <td className="px-6 py-4">
      <div className="flex items-center gap-2">
        <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-india-green rounded-full"
            style={{ width: confidence }}
          />
        </div>
        <span className="text-xs font-bold text-india-navy">{confidence}</span>
      </div>
    </td>
    <td className="px-6 py-4 text-right">
      <button
        onClick={onView}
        className="p-2 hover:bg-india-navy hover:text-white rounded-lg transition-all text-india-navy opacity-0 group-hover:opacity-100 shadow-sm"
      >
        <Eye size={18} />
      </button>
    </td>
  </tr>
);

export default App;
