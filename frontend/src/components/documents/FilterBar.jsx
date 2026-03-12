import React from 'react';
import { Shapes, Calendar, BarChart2, ChevronDown, FilterX } from 'lucide-react';
import './FilterBar.css';

const FilterBar = () => {
    return (
        <div className="filter-bar">
            <div className="filter-group">
                <button className="filter-dropdown">
                    <Shapes size={16} className="filter-icon" />
                    <span>Document Type</span>
                    <ChevronDown size={14} className="dropdown-arrow" />
                </button>

                <button className="filter-dropdown">
                    <Calendar size={16} className="filter-icon" />
                    <span>Upload Date</span>
                    <ChevronDown size={14} className="dropdown-arrow" />
                </button>

                <button className="filter-dropdown">
                    <BarChart2 size={16} className="filter-icon" />
                    <span>Processing Status</span>
                    <ChevronDown size={14} className="dropdown-arrow" />
                </button>
            </div>

            <button className="clear-filters-btn">
                <FilterX size={16} className="clear-icon" />
                <span>CLEAR FILTERS</span>
            </button>
        </div>
    );
};

export default FilterBar;
