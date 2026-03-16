import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

const Layout = () => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen);
    };

    return (
        <div className="flex h-screen w-full overflow-hidden bg-slate-50">
            <Sidebar isOpen={isSidebarOpen} />
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative shadow-inner bg-gradient-to-br from-slate-50 to-slate-100">
                <div className="absolute inset-y-0 left-0 w-4 shadow-[inset_10px_0_15px_-10px_rgba(0,0,0,0.05)] pointer-events-none z-10" />
                <Header toggleSidebar={toggleSidebar} isOpen={isSidebarOpen} />
                <main className="flex-1 overflow-y-auto relative z-0">
                    <Outlet />
                </main>
            </div>
        </div>
    );
};

export default Layout;
