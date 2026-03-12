import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import UploadPage from './pages/UploadPage';
import DocumentsPage from './pages/DocumentsPage';
import DocumentViewerPage from './pages/DocumentViewerPage';

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
          <Route path="templates" element={<div className="p-8">Templates Coming Soon</div>} />
          <Route path="settings" element={<div className="p-8">Settings Coming Soon</div>} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
