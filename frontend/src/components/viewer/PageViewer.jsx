import React from 'react';
import { ZoomIn, ZoomOut, ChevronLeft, ChevronRight } from 'lucide-react';

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
    const pageTokens = tokens ? tokens.filter(t => (t.page || 1) === page) : [];

    return (
        <div className="flex flex-col h-full bg-slate-200 shadow-inner overflow-hidden">
            {/* Toolbar */}
            <div className="h-12 bg-white/80 backdrop-blur-md border-b border-[#C2B280]/20 flex items-center justify-between px-6 shrink-0 z-10">
                <div className="flex items-center gap-4 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                    <button 
                        className="text-slate-400 hover:text-[#4B5320] transition-colors"
                        onClick={onZoomOut} 
                        title="Zoom out"
                    >
                        <ZoomOut size={16} />
                    </button>
                    <span className="text-[10px] font-black text-[#2F353B] min-w-[40px] text-center">
                        {Math.round(zoom * 100)}%
                    </span>
                    <button 
                        className="text-slate-400 hover:text-[#4B5320] transition-colors"
                        onClick={onZoomIn} 
                        title="Zoom in"
                    >
                        <ZoomIn size={16} />
                    </button>
                </div>

                <div className="flex items-center gap-2 bg-[#2F353B] px-4 py-1 rounded-full shadow-lg">
                    <button
                        className="text-white/50 hover:text-white disabled:opacity-20 transition-colors"
                        onClick={() => onPageChange(Math.max(1, page - 1))}
                        disabled={page <= 1}
                    >
                        <ChevronLeft size={16} />
                    </button>
                    <span className="text-white text-[10px] font-black uppercase tracking-widest min-w-[100px] text-center">
                        Unit {page} <span className="opacity-30">/</span> {totalPages}
                    </span>
                    <button
                        className="text-white/50 hover:text-white disabled:opacity-20 transition-colors"
                        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
                        disabled={page >= totalPages}
                    >
                        <ChevronRight size={16} />
                    </button>
                </div>
            </div>

            {/* Document Canvas */}
            <div className="flex-1 overflow-auto p-12 flex justify-center items-start scrollbar-thin">
                <div
                    className="relative bg-white shadow-2xl transition-transform duration-200 ease-out origin-top"
                    style={{ transform: `scale(${zoom})` }}
                >
                    <img
                        src={previewUrl}
                        alt="Document"
                        className="block max-w-none shadow-sm"
                        draggable={false}
                    />

                    {/* OCR Overlay */}
                    {overlayEnabled && (
                        <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
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
                                            rx={2}
                                        />
                                        <g transform={`translate(${x1}, ${y1 - 12})`}>
                                            <rect
                                                x={0} y={0}
                                                width={fieldKey.length * 6 + 8} height={12}
                                                fill={color}
                                                rx={2}
                                            />
                                            <text
                                                x={4} y={9}
                                                fill="white"
                                                fontSize={8}
                                                fontWeight="black"
                                                className="uppercase"
                                            >
                                                {fieldKey.replace(/_/g, ' ')}
                                            </text>
                                        </g>
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
