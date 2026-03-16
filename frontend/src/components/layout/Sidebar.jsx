import React from 'react';
import { NavLink } from 'react-router-dom';
import { Medal, LayoutDashboard, FolderOpen, Upload, FileText } from 'lucide-react';

const Sidebar = ({ isOpen }) => {
    return (
        <aside className={`
            flex flex-col relative overflow-hidden flex-shrink-0 transition-all duration-300
            ${isOpen ? 'w-72' : 'w-22'} 
            bg-gradient-to-b from-[#ff8c2d] via-white to-[#4caf50]
            backdrop-blur-xl border-r border-white/20 rounded-[3px] m-1 h-[calc(100vh-8px)]
        `}>
            <div className="absolute inset-0 pointer-events-none opacity-5 z-0 camouflage-pattern"></div>

            <div className="p-6 relative z-10 flex flex-col h-full">
                <div className={`flex items-center gap-3 mb-10 ${!isOpen ? 'justify-center' : ''}`}>
                    <div className="w-10 h-10 rounded-lg bg-[#C2B280] flex items-center justify-center shadow-lg shrink-0">
                        <Medal size={24} className="text-[#000080]" />
                    </div>
                    {isOpen && (
                        <div className="min-w-0 transition-opacity duration-300">
                            <h1 className="text-[#000080] text-lg font-extrabold leading-tight uppercase tracking-wider truncate">
                                Indian Army
                            </h1>
                            <p className="text-[#138808] text-[10px] font-bold uppercase tracking-widest opacity-80">
                                Document Portal
                            </p>
                        </div>
                    )}
                </div>

                <nav className="flex flex-col gap-2">
                    <NavLink to="/dashboard" className={({ isActive }) => `
                        flex items-center gap-3 p-3 rounded-xl transition-all duration-200 no-underline
                        ${isActive ? 'bg-[#000080] text-white shadow-md' : 'text-slate-800 font-semibold hover:bg-[#000080]/10'}
                        ${!isOpen ? 'justify-center p-3' : ''}
                    `}>
                        <LayoutDashboard size={20} />
                        {isOpen && <span className="text-sm uppercase tracking-wide">Dashboard</span>}
                    </NavLink>
                    <NavLink to="/documents" className={({ isActive }) => `
                        flex items-center gap-3 p-3 rounded-xl transition-all duration-200 no-underline
                        ${isActive ? 'bg-[#000080] text-white shadow-md' : 'text-slate-800 font-semibold hover:bg-[#000080]/10'}
                        ${!isOpen ? 'justify-center p-3' : ''}
                    `}>
                        <FolderOpen size={20} />
                        {isOpen && <span className="text-sm uppercase tracking-wide">Documents</span>}
                    </NavLink>
                    <NavLink to="/" className={({ isActive }) => `
                        flex items-center gap-3 p-3 rounded-xl transition-all duration-200 no-underline
                        ${isActive ? 'bg-[#000080] text-white shadow-md' : 'text-slate-800 font-semibold hover:bg-[#000080]/10'}
                        ${!isOpen ? 'justify-center p-3' : ''}
                    `}>
                        <Upload size={20} />
                        {isOpen && <span className="text-sm uppercase tracking-wide">Upload Document</span>}
                    </NavLink>
                    <NavLink to="/tips" className={({ isActive }) => `
                        flex items-center gap-3 p-3 rounded-xl transition-all duration-200 no-underline
                        ${isActive ? 'bg-[#000080] text-white shadow-md' : 'text-slate-800 font-semibold hover:bg-[#000080]/10'}
                        ${!isOpen ? 'justify-center p-3' : ''}
                    `}>
                        <FileText size={20} />
                        {isOpen && <span className="text-sm uppercase tracking-wide">OCR Tips</span>}
                    </NavLink>
                </nav>
            </div>
        </aside>
    );
};

export default Sidebar;
