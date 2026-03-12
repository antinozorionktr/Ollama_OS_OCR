import React, { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle2, Gauge, FolderOpen } from 'lucide-react';
import './StatCards.css';

const StatCards = () => {
    const [stats, setStats] = useState({ total_files: 0, processed_count: 0 });

    useEffect(() => {
        fetch('/api/stats')
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(err => console.error("Stats error:", err));
    }, []);

    return (
        <div className="stat-cards-container">
            <div className="stat-card">
                <div className="stat-icon-wrapper orange">
                    <FolderOpen size={24} className="stat-icon" />
                </div>
                <div className="stat-details">
                    <p className="stat-label">TOTAL VAULT FILES</p>
                    <p className="stat-value">{stats.total_files}</p>
                </div>
            </div>

            <div className="stat-card">
                <div className="stat-icon-wrapper green">
                    <CheckCircle2 size={24} className="stat-icon" />
                </div>
                <div className="stat-details">
                    <p className="stat-label">PROCESSED DOCS</p>
                    <p className="stat-value">{stats.processed_count}</p>
                </div>
            </div>

            <div className="stat-card">
                <div className="stat-icon-wrapper blue">
                    <Gauge size={24} className="stat-icon" />
                </div>
                <div className="stat-details">
                    <p className="stat-label">OPS VELOCITY</p>
                    <p className="stat-value">420 p/h</p>
                </div>
            </div>
        </div>
    );
};

export default StatCards;
