import React, { useState } from 'react';
import { Copy, Check, FileText, List, RotateCw, Save } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const FIELD_LABELS = {
    invoice_number: 'INVOICE NUMBER',
    invoice_date: 'INVOICE DATE',
    due_date: 'DUE DATE',
    vendor: 'VENDOR NAME',
    vendor_address: 'VENDOR ADDRESS',
    bill_to: 'BILL TO',
    bill_to_address: 'BILL TO ADDRESS',
    total_amount: 'TOTAL AMOUNT',
    subtotal: 'SUBTOTAL',
    tax: 'TAX',
};

const DataTable = ({ label, data }) => {
    if (!Array.isArray(data) || data.length === 0) return null;
    
    // Check if it's array of objects or array of arrays
    const isArrayOfArrays = Array.isArray(data[0]);
    let headers = [];
    let rows = [];

    if (isArrayOfArrays) {
        // Assume first row is headers if it contains strings
        const potentialHeaders = data[0];
        const allStrings = potentialHeaders.every(h => typeof h === 'string');
        if (allStrings && data.length > 1) {
            headers = potentialHeaders;
            rows = data.slice(1);
        } else {
            headers = potentialHeaders.map((_, i) => `COL ${i + 1}`);
            rows = data;
        }
    } else {
        headers = Object.keys(data[0]);
        rows = data;
    }

    return (
        <div className="mb-6">
            <span className="text-[10px] font-black text-[#4B5320] uppercase tracking-widest block mb-2 opacity-60 px-1">{label}</span>
            <div className="bg-white rounded-xl border border-[#C2B280]/20 overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full border-collapse text-[11px] font-bold uppercase tracking-tight">
                        <thead>
                            <tr className="bg-slate-50 border-b border-[#C2B280]/10">
                                <th className="w-8 py-2 px-3 text-center text-slate-400 border-r border-slate-100">#</th>
                                {headers.map((h, i) => (
                                    <th key={i} className="py-2 px-4 text-left text-slate-600 whitespace-nowrap">{String(h).replace(/_/g, ' ')}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {rows.map((row, i) => (
                                <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                                    <td className="w-8 py-2 px-3 text-center text-slate-300 border-r border-slate-100">{i + 1}</td>
                                    {isArrayOfArrays ? (
                                        row.map((val, j) => <td key={j} className="py-2 px-4 text-[#2F353B]">{val != null ? String(val) : ''}</td>)
                                    ) : (
                                        headers.map((h, j) => (
                                            <td key={j} className="py-2 px-4 text-[#2F353B]">{row[h] != null ? String(row[h]) : ''}</td>
                                        ))
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

const FieldCard = ({ fieldKey, fieldData, onChange, isHighlighted }) => {
    const label = FIELD_LABELS[fieldKey] || fieldKey.replace(/_/g, ' ').toUpperCase();
    const value = fieldData.value != null ? String(fieldData.value) : '';
    const isMarkdownTable = value.includes('|') && value.includes('-|-');

    return (
        <div className={`p-4 rounded-xl border transition-all ${isHighlighted ? 'bg-emerald-50 border-emerald-200' : 'bg-white border-[#C2B280]/20 hover:border-[#4B5320]/30'}`}>
            <div className="space-y-2">
                <span className="text-[10px] font-black text-[#4B5320] uppercase tracking-widest opacity-60 block">{label}</span>
                {isMarkdownTable ? (
                    <div className="prose prose-sm max-w-none text-[#2F353B] font-medium leading-relaxed prose-table:border prose-table:rounded-lg prose-th:px-3 prose-td:px-3 prose-th:py-2 prose-td:py-2">
                        <ReactMarkdown>{value}</ReactMarkdown>
                    </div>
                ) : (
                    <input
                        type="text"
                        className="w-full bg-transparent border-none p-0 text-sm font-bold text-[#2F353B] focus:ring-0 placeholder:opacity-30"
                        value={value}
                        onChange={(e) => onChange(fieldKey, e.target.value)}
                        placeholder="ENTER VALUE..."
                    />
                )}
            </div>
        </div>
    );
};

const FieldPanel = ({
    documentType,
    fields,
    lineItems,
    rawText,
    isLoading,
    isApproved,
    onApprove,
    onSave,
    onRerun,
    onFieldClick,
    highlightedKey,
    showMarkdown,
    markdown,
}) => {
    const [rawExpanded, setRawExpanded] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        if (!rawText) return;
        navigator.clipboard.writeText(rawText);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="flex flex-col h-full bg-slate-50/30">
            <div className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-thin">
                {/* Extracted Fields */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between border-b border-[#C2B280]/10 pb-2">
                        <h2 className="text-[#4B5320] font-black tracking-[0.2em] text-[10px] flex items-center gap-2">
                            <FileText size={14} /> EXTRACTED DATA
                        </h2>
                        <button 
                            className="text-[9px] font-black text-rose-500 hover:text-rose-600 bg-rose-50 px-2.5 py-1 rounded transition-colors uppercase tracking-widest"
                            onClick={onRerun}
                        >
                            Reset Buffer
                        </button>
                    </div>

                    {isLoading ? (
                        <div className="grid grid-cols-1 gap-3">
                            {[1, 2, 3, 4].map(i => (
                                <div key={i} className="h-20 bg-white border border-slate-100 rounded-xl animate-pulse" />
                            ))}
                        </div>
                    ) : fields && Object.keys(fields).length > 0 && !showMarkdown ? (
                        <div className="space-y-3">
                            {Object.entries(fields).map(([key, data]) => {
                                const isTable = Array.isArray(data.value) || Array.isArray(data);
                                const tableData = Array.isArray(data.value) ? data.value : (Array.isArray(data) ? data : null);
                                
                                if (isTable && tableData) {
                                    return (
                                        <DataTable 
                                            key={key} 
                                            label={FIELD_LABELS[key] || key.replace(/_/g, ' ').toUpperCase()} 
                                            data={tableData} 
                                        />
                                    );
                                }

                                return (
                                    <FieldCard
                                        key={key}
                                        fieldKey={key}
                                        fieldData={data}
                                        onChange={onFieldClick}
                                        isHighlighted={highlightedKey === key}
                                    />
                                );
                            })}
                        </div>
                    ) : showMarkdown ? (
                        <div className="prose prose-sm max-w-none p-6 bg-white rounded-2xl border border-[#C2B280]/20 shadow-sm leading-relaxed text-[#2F353B] font-medium">
                            <ReactMarkdown>{markdown || rawText || ''}</ReactMarkdown>
                        </div>
                    ) : (
                        <div className="py-12 text-center bg-white rounded-2xl border border-dashed border-[#C2B280]/30">
                            <p className="text-slate-400 font-bold uppercase tracking-widest text-[10px]">No fields identified in current unit.</p>
                        </div>
                    )}
                </div>

                {/* Line Items */}
                {lineItems && lineItems.length > 0 && !showMarkdown && (
                    <div className="space-y-4">
                        <h2 className="text-[#4B5320] font-black tracking-[0.2em] text-[10px] flex items-center gap-2 border-b border-[#C2B280]/10 pb-2">
                            <List size={14} /> TABULAR ENTITIES ({lineItems.length})
                        </h2>
                        <div className="space-y-2">
                            {lineItems.slice(0, 10).map((item, idx) => {
                                const desc = item.description?.value || item.item?.value || `Sequence ${idx + 1}`;
                                const total = item.total?.value || item.amount?.value || '';
                                return (
                                    <div key={idx} className="flex items-center gap-4 p-4 bg-white rounded-xl border border-[#C2B280]/10 hover:border-[#4B5320]/20 transition-all group">
                                        <span className="w-8 text-[10px] font-black text-slate-300 group-hover:text-[#4B5320] transition-colors">{(idx + 1).toString().padStart(2, '0')}</span>
                                        <span className="flex-1 text-xs font-bold text-[#2F353B] truncate uppercase">{desc}</span>
                                        <span className="text-xs font-black text-[#4B5320] tabular-nums">{total}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Raw Extracted Text */}
                {rawText && !showMarkdown && (
                    <div className="space-y-3">
                        <div className="flex items-center justify-between border-b border-[#C2B280]/10 pb-2">
                            <p className="text-[#4B5320] font-black tracking-[0.2em] text-[10px]">RAW SIGNALS</p>
                            <div className="flex items-center gap-2">
                                <button
                                    className={`p-1.5 rounded transition-all ${copied ? 'bg-emerald-50 text-emerald-600' : 'text-slate-400 hover:text-[#4B5320] hover:bg-slate-100'}`}
                                    onClick={handleCopy}
                                    title="Copy raw text"
                                >
                                    {copied ? <Check size={14} /> : <Copy size={14} />}
                                </button>
                                <button
                                    className="text-[9px] font-black text-[#4B5320] uppercase border border-[#4B5320]/20 px-2 py-1 rounded hover:bg-[#4B5320]/5"
                                    onClick={() => setRawExpanded(p => !p)}
                                >
                                    {rawExpanded ? 'CLOSE' : 'REVEAL'}
                                </button>
                            </div>
                        </div>
                        <div className={`
                            bg-[#2F353B] rounded-2xl p-4 font-mono text-[11px] text-[#C2B280]/80 leading-relaxed overflow-hidden transition-all duration-300
                            ${rawExpanded ? 'max-h-[1000px]' : 'max-h-24'}
                        `}>
                            {rawText}
                            {!rawExpanded && rawText.length > 200 && (
                                <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-[#2F353B] to-transparent" />
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Action Buttons */}
            <div className="p-6 bg-white border-t border-[#C2B280]/20 shrink-0">
                <div className="grid grid-cols-2 gap-3">
                    <button 
                        className="flex items-center justify-center gap-2 py-3.5 bg-white border-2 border-[#4B5320] text-[#4B5320] rounded-xl font-black uppercase text-[10px] tracking-widest hover:bg-[#4B5320]/5 transition-all active:scale-[0.98]"
                        onClick={onSave}
                    >
                        <Save size={16} /> Save Changes
                    </button>
                    <button 
                        className="flex items-center justify-center gap-2 py-3.5 bg-[#4B5320] text-white rounded-xl font-black uppercase text-[10px] tracking-widest hover:bg-[#3A4310] shadow-lg shadow-[#4B5320]/20 transition-all active:scale-[0.98]"
                        onClick={onRerun}
                    >
                        <RotateCw size={16} /> Re-extract
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FieldPanel;
