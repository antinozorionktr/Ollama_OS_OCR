import React, { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle2, Gauge, FolderOpen } from 'lucide-react';

const StatCards = () => {
    const [stats, setStats] = useState({ total_files: 0, processed_count: 0 });

    useEffect(() => {
        fetch('/api/stats')
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(err => console.error("Stats error:", err));
    }, []);

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="group bg-white p-6 rounded-3xl border border-[#C2B280]/20 shadow-sm hover:shadow-md hover:border-[#4B5320]/30 transition-all">
                <div className="flex items-center gap-5">
                    <div className="w-14 h-14 rounded-2xl bg-amber-50 flex items-center justify-center text-amber-600 group-hover:scale-110 transition-transform">
                        <FolderOpen size={24} />
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">TOTAL VAULT FILES</p>
                        <p className="text-2xl font-black text-[#2F353B] tabular-nums tracking-tight">{stats.total_files}</p>
                    </div>
                </div>
            </div>

            <div className="group bg-white p-6 rounded-3xl border border-[#C2B280]/20 shadow-sm hover:shadow-md hover:border-[#4B5320]/30 transition-all">
                <div className="flex items-center gap-5">
                    <div className="w-14 h-14 rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600 group-hover:scale-110 transition-transform">
                        <CheckCircle2 size={24} />
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">PROCESSED DOCS</p>
                        <p className="text-2xl font-black text-[#2F353B] tabular-nums tracking-tight">{stats.processed_count}</p>
                    </div>
                </div>
            </div>

            <div className="group bg-white p-6 rounded-3xl border border-[#C2B280]/20 shadow-sm hover:shadow-md hover:border-[#4B5320]/30 transition-all">
                <div className="flex items-center gap-5">
                    <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 group-hover:scale-110 transition-transform">
                        <Gauge size={24} />
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">OPS VELOCITY</p>
                        <p className="text-2xl font-black text-[#2F353B] tabular-nums tracking-tight">420 p/h</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StatCards;
