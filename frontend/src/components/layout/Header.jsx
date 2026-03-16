import React from 'react';
import { PanelRightClose, PanelRightOpen, Search, Bell, User } from 'lucide-react';

const Header = ({ toggleSidebar, isOpen }) => {
    return (
        <header className="h-16 border-b border-[#C2B280]/30 flex items-center justify-between px-8 bg-gradient-to-r from-white/80 to-[#f8fafc]/80 backdrop-blur-md sticky top-0 z-20">
            <div className="flex items-center gap-4">
                <button 
                    onClick={toggleSidebar} 
                    className="p-1 rounded-lg hover:bg-slate-100 transition-colors flex items-center justify-center text-[#4B5320]"
                >
                    {isOpen ? <PanelRightClose size={24} /> : <PanelRightOpen size={24} />}
                </button>
                <h2 className="text-[#2F353B] font-bold text-lg uppercase tracking-tight m-0">
                    Document Management System
                </h2>
            </div>

            <div className="flex items-center gap-6">
                <div className="relative flex items-center">
                    <Search className="absolute left-3 text-slate-400" size={18} />
                    <input 
                        type="text" 
                        placeholder="Search archive..." 
                        className="pl-10 pr-4 py-1.5 bg-[#C2B280]/10 border-none rounded-lg text-sm w-64 text-[#2F353B] outline-none focus:ring-2 focus:ring-[#4B5320]/20 transition-all font-inherit"
                    />
                </div>

                <div className="flex items-center gap-4">
                    <button className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-[#C2B280]/20 transition-colors text-[#2F353B]">
                        <Bell size={20} />
                    </button>

                    <div className="h-8 w-px bg-[#C2B280]/30"></div>

                    <div className="flex items-center gap-3">
                        <div className="text-right">
                            <p className="text-[11px] font-bold text-[#2F353B] m-0">Maj. Arjun Singh</p>
                            <p className="text-[9px] font-bold text-[#4B5320] m-0 uppercase opacity-70">Signal Corps</p>
                        </div>
                        <div className="w-10 h-10 rounded-full border-2 border-[#4B5320]/20 bg-[#C2B280] flex items-center justify-center shadow-sm">
                            <User size={24} className="text-white" />
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
