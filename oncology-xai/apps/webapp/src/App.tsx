import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import CaseSelector from './pages/CaseSelector';
import ImagePanel from './pages/ImagePanel';
import EHRPanel from './pages/EHRPanel';
import GraphPanel from './pages/GraphPanel';
import AdminPanel from './pages/AdminPanel';

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          {/* Case Management */}
          <Route path="/" element={<CaseSelector />} />

          {/* Case Detail Pages */}
          <Route path="/cases/:caseId/images" element={<ImagePanel />} />
          <Route path="/cases/:caseId/ehr" element={<EHRPanel />} />
          <Route path="/cases/:caseId/graph" element={<GraphPanel />} />

          {/* Admin */}
          <Route path="/admin/ontologies" element={<AdminPanel />} />

          {/* Default redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;
