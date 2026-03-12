import React from 'react';
import { ZoomIn, ZoomOut, ChevronLeft, ChevronRight } from 'lucide-react';
import './PageViewer.css';

const PageViewer = ({
    resultId,
    page,
    totalPages,
    zoom,
    overlayEnabled,
    tokens,
    highlightedField,
    onPageChange,
    onZoomIn,
    onZoomOut,
}) => {
    const previewUrl = `/api/results/${resultId}/preview`;

    const FIELD_COLORS = {
        invoice_number: '#f59e0b',
        invoice_date: '#3b82f6',
        due_date: '#8b5cf6',
        vendor: '#10b981',
        vendor_address: '#10b981',
        bill_to: '#06b6d4',
        total_amount: '#ef4444',
        subtotal: '#f97316',
        tax: '#f97316',
        default: '#6366f1',
    };

    // Tokens for current page only
    const pageTokens = tokens.filter(t => (t.page || 1) === page);

    return (
        <div className="page-viewer">
            {/* Toolbar */}
            <div className="viewer-toolbar">
                <div className="toolbar-left">
                    <button className="toolbar-btn" onClick={onZoomOut} title="Zoom out">
                        <ZoomOut size={18} />
                    </button>
                    <span className="zoom-label">{Math.round(zoom * 100)}%</span>
                    <button className="toolbar-btn" onClick={onZoomIn} title="Zoom in">
                        <ZoomIn size={18} />
                    </button>
                </div>
                <div className="toolbar-center">
                    <button
                        className="toolbar-btn"
                        onClick={() => onPageChange(Math.max(1, page - 1))}
                        disabled={page <= 1}
                    >
                        <ChevronLeft size={18} />
                    </button>
                    <span className="page-label">Page {page} of {totalPages}</span>
                    <button
                        className="toolbar-btn"
                        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
                        disabled={page >= totalPages}
                    >
                        <ChevronRight size={18} />
                    </button>
                </div>
            </div>

            {/* Document Canvas */}
            <div className="viewer-canvas-wrapper">
                <div
                    className="viewer-canvas"
                    style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
                >
                    <img
                        src={previewUrl}
                        alt="Document"
                        className="doc-image"
                        draggable={false}
                    />

                    {/* OCR Overlay */}
                    {overlayEnabled && (
                        <svg className="doc-overlay" xmlns="http://www.w3.org/2000/svg">
                            {Object.entries(highlightedField || {}).map(([fieldKey, fieldData]) => {
                                if (!fieldData || !fieldData.bbox || (fieldData.page || 1) !== page) return null;
                                const [x1, y1, x2, y2] = fieldData.bbox;
                                const color = FIELD_COLORS[fieldKey] || FIELD_COLORS.default;
                                return (
                                    <g key={fieldKey}>
                                        <rect
                                            x={x1} y={y1}
                                            width={x2 - x1} height={y2 - y1}
                                            fill={`${color}22`}
                                            stroke={color}
                                            strokeWidth={2}
                                            rx={3}
                                        />
                                        <text
                                            x={x1 + 2} y={y1 - 4}
                                            fill={color}
                                            fontSize={10}
                                            fontWeight="bold"
                                        >
                                            {fieldKey.replace(/_/g, ' ').toUpperCase()}
                                        </text>
                                    </g>
                                );
                            })}
                        </svg>
                    )}
                </div>
            </div>
        </div>
    );
};

export default PageViewer;
