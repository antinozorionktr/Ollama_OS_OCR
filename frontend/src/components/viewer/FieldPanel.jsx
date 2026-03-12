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

const FieldCard = ({ fieldKey, fieldData, onClick, isHighlighted }) => {
    const label = FIELD_LABELS[fieldKey] || fieldKey.replace(/_/g, ' ').toUpperCase();
    const value = fieldData.value != null ? String(fieldData.value) : '—';

    return (
        <div
            className={`field-card ${isHighlighted ? 'highlighted' : ''}`}
            onClick={() => onClick(fieldKey)}
        >
            <div className="field-info">
                <span className="field-label">{label}</span>
                <span className="field-value">{value}</span>
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
            {/* Document Metadata */}
            <div className="panel-section meta-section">
                <p className="section-label">DOCUMENT METADATA</p>
                <div className="meta-row">
                    <div className="meta-item">
                        <span className="meta-label">TYPE</span>
                        <span className="meta-value doc-type-badge">{documentType || 'Unknown'}</span>
                    </div>
                </div>
            </div>

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
                        {Object.entries(fields).map(([key, data]) => (
                            <FieldCard
                                key={key}
                                fieldKey={key}
                                fieldData={data}
                                onClick={onFieldClick}
                                isHighlighted={highlightedKey === key}
                            />
                        ))}
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
                <button
                    className={`btn-approve ${isApproved ? 'approved' : ''}`}
                    onClick={onApprove}
                    disabled={isApproved}
                >
                    {isApproved ? '✓ Document Approved' : '⊕ Approve Document'}
                </button>
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
