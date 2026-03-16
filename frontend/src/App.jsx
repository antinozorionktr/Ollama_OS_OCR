import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import UploadPage from './pages/UploadPage';
import DocumentsPage from './pages/DocumentsPage';
import DocumentViewerPage from './pages/DocumentViewerPage';
import TipsPage from './pages/TipsPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<UploadPage />} />
          {/* Future routes will go here (dashboard, documents, etc.) */}
          <Route path="dashboard" element={<div className="p-8">Dashboard Coming Soon</div>} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="documents/:id" element={<DocumentViewerPage />} />
          <Route path="tips" element={<TipsPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
