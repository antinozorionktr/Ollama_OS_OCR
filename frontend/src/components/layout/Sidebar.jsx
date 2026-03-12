import React from 'react';
import { NavLink } from 'react-router-dom';
import { Medal, LayoutDashboard, FolderOpen, Upload, FileText, Settings, HelpCircle } from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({ isOpen }) => {
    return (
        <aside className={`sidebar ${isOpen ? '' : 'collapsed'}`}>
            <div className="sidebar-camo-overlay camouflage-pattern"></div>

            <div className="sidebar-content">
                <div className="sidebar-header">
                    <div className="logo-icon-wrapper">
                        <Medal size={24} className="logo-icon" />
                    </div>
                    <div className="logo-text">
                        <h1>Indian Army</h1>
                        <p>Document Portal</p>
                    </div>
                </div>

                <nav className="sidebar-nav">
                    <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <LayoutDashboard size={20} />
                        <span>Dashboard</span>
                    </NavLink>
                    <NavLink to="/documents" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <FolderOpen size={20} />
                        <span>Documents</span>
                    </NavLink>
                    <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <Upload size={20} />
                        <span>Upload Document</span>
                    </NavLink>
                    <NavLink to="/templates" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <FileText size={20} />
                        <span>Templates</span>
                    </NavLink>
                    <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <Settings size={20} />
                        <span>Settings</span>
                    </NavLink>
                </nav>
            </div>

            <div className="sidebar-footer">
                <a href="#" className="nav-link">
                    <HelpCircle size={20} />
                    <span>Support</span>
                </a>
            </div>
        </aside>
    );
};

export default Sidebar;
