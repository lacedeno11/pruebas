import React from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { caseId } = useParams();

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path);
  };

  const navLinkClass = (path: string) => {
    const base = "px-3 py-2 rounded-md text-sm font-medium transition-colors";
    return isActive(path)
      ? `${base} bg-primary-700 text-white`
      : `${base} text-gray-300 hover:bg-primary-600 hover:text-white`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation Bar */}
      <nav className="bg-primary-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link to="/" className="text-white text-xl font-bold">
                  Oncology XAI
                </Link>
              </div>
              <div className="ml-10 flex items-center space-x-4">
                <Link to="/" className={navLinkClass('/')}>
                  Cases
                </Link>
                <Link to="/admin/ontologies" className={navLinkClass('/admin')}>
                  Admin
                </Link>
              </div>
            </div>
            <div className="flex items-center">
              <span className="text-gray-300 text-sm">Dev Mode</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Case Sub-Navigation (shown when viewing a specific case) */}
      {caseId && (
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex space-x-8">
              <Link
                to={`/cases/${caseId}/images`}
                className={`${
                  isActive(`/cases/${caseId}/images`)
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Images
              </Link>
              <Link
                to={`/cases/${caseId}/ehr`}
                className={`${
                  isActive(`/cases/${caseId}/ehr`)
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                EHR
              </Link>
              <Link
                to={`/cases/${caseId}/graph`}
                className={`${
                  isActive(`/cases/${caseId}/graph`)
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Knowledge Graph
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
};

export default Layout;
