import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

import './Layout.css';

const Layout = () => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen);
    };

    return (
        <div className="app-container">
            <Sidebar isOpen={isSidebarOpen} />
            <div className="main-wrapper">
                <Header toggleSidebar={toggleSidebar} isOpen={isSidebarOpen} />
                <main className="content-area">
                    <Outlet />
                </main>
            </div>
        </div>
    );
};

export default Layout;
