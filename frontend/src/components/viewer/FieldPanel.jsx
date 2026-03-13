import React, { useState } from 'react';
import { Copy, Check, FileText, List } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './FieldPanel.css';

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
        <div className="table-container">
            <span className="field-label">{label}</span>
            <div className="table-wrapper">
                <table className="extracted-table">
                    <thead>
                        <tr>
                            <th className="idx-col">#</th>
                            {headers.map((h, i) => (
                                <th key={i}>{String(h).replace(/_/g, ' ').toUpperCase()}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row, i) => (
                            <tr key={i}>
                                <td className="idx-col">{i + 1}</td>
                                {isArrayOfArrays ? (
                                    row.map((val, j) => <td key={j}>{val != null ? String(val) : ''}</td>)
                                ) : (
                                    headers.map((h, j) => (
                                        <td key={j}>{row[h] != null ? String(row[h]) : ''}</td>
                                    ))
                                )}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

const FieldCard = ({ fieldKey, fieldData, onChange, isHighlighted }) => {
    const label = FIELD_LABELS[fieldKey] || fieldKey.replace(/_/g, ' ').toUpperCase();
    const value = fieldData.value != null ? String(fieldData.value) : '';
    const isMarkdownTable = value.includes('|') && value.includes('-|-');

    return (
        <div className={`field-card ${isHighlighted ? 'highlighted' : ''}`}>
            <div className="field-info">
                <span className="field-label">{label}</span>
                {isMarkdownTable ? (
                    <div className="field-markdown-value">
                        <ReactMarkdown>{value}</ReactMarkdown>
                    </div>
                ) : (
                    <input
                        type="text"
                        className="field-input"
                        value={value}
                        onChange={(e) => onChange(fieldKey, e.target.value)}
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
        <div className="field-panel">
            {/* Extracted Fields */}
            <div className="panel-section">
                <div className="section-header-row">
                    <p className="section-label">EXTRACTED FIELDS</p>
                    <button className="reset-btn" onClick={onRerun} title="Re-run OCR">
                        RESET ALL
                    </button>
                </div>

                {isLoading ? (
                    <div className="loading-fields">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className="field-card skeleton" />
                        ))}
                    </div>
                ) : fields && Object.keys(fields).length > 0 && !showMarkdown ? (
                    <div className="fields-list">
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
                    <div className="markdown-container">
                        <ReactMarkdown>{markdown || rawText || ''}</ReactMarkdown>
                    </div>
                ) : (
                    <p className="no-fields-msg">Run extraction to see fields here.</p>
                )}
            </div>

            {/* Line Items */}
            {lineItems && lineItems.length > 0 && !showMarkdown && (
                <div className="panel-section">
                    <p className="section-label">LINE ITEMS ({lineItems.length})</p>
                    <div className="line-items-list">
                        {lineItems.slice(0, 10).map((item, idx) => {
                            const desc = item.description?.value || item.item?.value || `Item ${idx + 1}`;
                            const total = item.total?.value || item.amount?.value || '';
                            return (
                                <div key={idx} className="line-item-row">
                                    <span className="li-num">{idx + 1}</span>
                                    <span className="li-desc">{desc}</span>
                                    <span className="li-total">{total}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Raw Extracted Text */}
            {rawText && !showMarkdown && (
                <div className="panel-section">
                    <div className="section-header-row">
                        <p className="section-label">RAW EXTRACTED TEXT</p>
                        <div className="header-actions">
                            <button
                                className="copy-btn"
                                onClick={handleCopy}
                                title="Copy raw text"
                            >
                                {copied ? <Check size={14} /> : <Copy size={14} />}
                            </button>
                            <button
                                className="reset-btn"
                                onClick={() => setRawExpanded(p => !p)}
                            >
                                {rawExpanded ? 'COLLAPSE ▲' : 'EXPAND ▼'}
                            </button>
                        </div>
                    </div>
                    {rawExpanded && (
                        <div className="raw-text-box">
                            {rawText}
                        </div>
                    )}
                    {!rawExpanded && (
                        <p className="raw-text-preview">
                            {rawText.slice(0, 120)}{rawText.length > 120 ? '…' : ''}
                        </p>
                    )}
                </div>
            )}

            {/* Action Buttons */}
            <div className="panel-actions">
                <div className="btn-row">
                    <button className="btn-secondary" onClick={onSave}>
                        💾 Save Changes
                    </button>
                    <button className="btn-rerun" onClick={onRerun}>
                        🔄 Re-run OCR
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FieldPanel;
