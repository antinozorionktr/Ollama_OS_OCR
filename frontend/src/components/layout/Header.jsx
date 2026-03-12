import React from 'react';
import { PanelRightClose, PanelRightOpen, Search, Bell, User } from 'lucide-react';
import './Header.css';

const Header = ({ toggleSidebar, isOpen }) => {
    return (
        <header className="header">
            <div className="header-left">
                <button onClick={toggleSidebar} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex' }}>
                    {isOpen ? <PanelRightClose className="menu-icon text-primary" size={24} /> : <PanelRightOpen className="menu-icon text-primary" size={24} />}
                </button>
                <h2 className="header-title">Document Management System</h2>
            </div>

            <div className="header-right">
                <div className="search-bar">
                    <Search className="search-icon" size={20} />
                    <input type="text" placeholder="Search archive..." className="search-input" />
                </div>

                <div className="header-actions">
                    <button className="notification-btn">
                        <Bell className="text-slate-army" size={20} />
                    </button>

                    <div className="divider"></div>

                    <div className="user-profile">
                        <div className="user-info">
                            <p className="user-name">Maj. Arjun Singh</p>
                            <p className="user-role">Signal Corps</p>
                        </div>
                        <div className="user-avatar-placeholder">
                            <User size={24} className="text-secondary" />
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
