import React from 'react';
import FilterBar from '../components/documents/FilterBar';
import DocumentTable from '../components/documents/DocumentTable';
import './DocumentsPage.css';

const DocumentsPage = () => {
    return (
        <div className="documents-page">
            <FilterBar />

            <div className="documents-content-scroll">
                <DocumentTable />
            </div>
        </div>
    );
};

export default DocumentsPage;
