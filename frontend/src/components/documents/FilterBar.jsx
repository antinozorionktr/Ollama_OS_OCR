import React from 'react';
import { Shapes, Calendar, BarChart2, ChevronDown, FilterX } from 'lucide-react';

const FilterBar = () => {
    return (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 mb-6">
            <div className="flex flex-wrap items-center gap-2">
                <button className="flex items-center gap-2.5 px-4 py-2 bg-white border border-[#C2B280]/20 rounded-xl text-[10px] font-black text-[#2F353B] uppercase tracking-widest hover:border-[#4B5320]/40 hover:bg-[#C2B280]/5 transition-all group">
                    <Shapes size={14} className="text-[#4B5320] group-hover:scale-110 transition-transform" />
                    <span>Unit Type</span>
                    <ChevronDown size={12} className="opacity-30" />
                </button>

                <button className="flex items-center gap-2.5 px-4 py-2 bg-white border border-[#C2B280]/20 rounded-xl text-[10px] font-black text-[#2F353B] uppercase tracking-widest hover:border-[#4B5320]/40 hover:bg-[#C2B280]/5 transition-all group">
                    <Calendar size={14} className="text-[#4B5320] group-hover:scale-110 transition-transform" />
                    <span>Cycle Date</span>
                    <ChevronDown size={12} className="opacity-30" />
                </button>

                <button className="flex items-center gap-2.5 px-4 py-2 bg-white border border-[#C2B280]/20 rounded-xl text-[10px] font-black text-[#2F353B] uppercase tracking-widest hover:border-[#4B5320]/40 hover:bg-[#C2B280]/5 transition-all group">
                    <BarChart2 size={14} className="text-[#4B5320] group-hover:scale-110 transition-transform" />
                    <span>Scan Phase</span>
                    <ChevronDown size={12} className="opacity-30" />
                </button>
            </div>

            <button className="flex items-center justify-center gap-2 px-6 py-2 bg-rose-50 border border-rose-100 rounded-xl text-[10px] font-black text-rose-600 uppercase tracking-widest hover:bg-rose-100 transition-all active:scale-[0.98]">
                <FilterX size={14} />
                <span>FLUSH SEARCH</span>
            </button>
        </div>
    );
};

export default FilterBar;
