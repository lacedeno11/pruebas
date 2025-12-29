import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';

interface Case {
  id: string;
  patientId: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
}

const CaseSelector: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newPatientId, setNewPatientId] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getCases();
      setCases(data.cases || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load cases');
      // Mock data for development
      setCases([
        {
          id: 'case-001',
          patientId: 'PT-12345',
          description: 'Lung cancer patient - initial diagnosis',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
        {
          id: 'case-002',
          patientId: 'PT-67890',
          description: 'Breast cancer follow-up',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPatientId.trim()) return;

    try {
      setCreating(true);
      const newCase = await apiClient.createCase({
        patientId: newPatientId,
        description: newDescription,
      });

      // Navigate to the new case's image panel
      navigate(`/cases/${newCase.id}/images`);
    } catch (err: any) {
      // For development, create a mock case
      const mockCase: Case = {
        id: `case-${Date.now()}`,
        patientId: newPatientId,
        description: newDescription,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      setCases([mockCase, ...cases]);
      setShowCreateModal(false);
      setNewPatientId('');
      setNewDescription('');
      navigate(`/cases/${mockCase.id}/images`);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteCase = async (caseId: string) => {
    if (!confirm('Are you sure you want to delete this case?')) return;

    try {
      await apiClient.deleteCase(caseId);
      setCases(cases.filter(c => c.id !== caseId));
    } catch (err: any) {
      // For development, just remove from list
      setCases(cases.filter(c => c.id !== caseId));
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-3xl font-semibold text-gray-900">Patient Cases</h1>
          <p className="mt-2 text-sm text-gray-700">
            Manage patient cases and access imaging, EHR, and knowledge graph data.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            Create New Case
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-4 rounded-md bg-yellow-50 p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">API Connection Issue</h3>
              <div className="mt-2 text-sm text-yellow-700">
                <p>Using mock data for development. Error: {error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cases List */}
      {loading ? (
        <div className="mt-8 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-2 text-sm text-gray-500">Loading cases...</p>
        </div>
      ) : cases.length === 0 ? (
        <div className="mt-8 text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No cases</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by creating a new patient case.</p>
        </div>
      ) : (
        <div className="mt-8 overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
          <table className="min-w-full divide-y divide-gray-300">
            <thead className="bg-gray-50">
              <tr>
                <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">
                  Patient ID
                </th>
                <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                  Description
                </th>
                <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                  Created
                </th>
                <th className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {cases.map((caseItem) => (
                <tr key={caseItem.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                    {caseItem.patientId}
                  </td>
                  <td className="px-3 py-4 text-sm text-gray-500">
                    {caseItem.description || '—'}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {formatDate(caseItem.createdAt)}
                  </td>
                  <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    <button
                      onClick={() => navigate(`/cases/${caseItem.id}/images`)}
                      className="text-primary-600 hover:text-primary-900 mr-4"
                    >
                      Open
                    </button>
                    <button
                      onClick={() => handleDeleteCase(caseItem.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Case Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-screen items-end justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowCreateModal(false)}></div>

            <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <form onSubmit={handleCreateCase}>
                <div>
                  <h3 className="text-lg font-medium leading-6 text-gray-900">
                    Create New Case
                  </h3>
                  <div className="mt-4">
                    <label htmlFor="patientId" className="block text-sm font-medium text-gray-700">
                      Patient ID *
                    </label>
                    <input
                      type="text"
                      id="patientId"
                      value={newPatientId}
                      onChange={(e) => setNewPatientId(e.target.value)}
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border px-3 py-2"
                      placeholder="PT-12345"
                    />
                  </div>
                  <div className="mt-4">
                    <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                      Description
                    </label>
                    <textarea
                      id="description"
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                      rows={3}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border px-3 py-2"
                      placeholder="Brief case description..."
                    />
                  </div>
                </div>
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                  <button
                    type="submit"
                    disabled={creating}
                    className="inline-flex w-full justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:col-start-2 sm:text-sm disabled:opacity-50"
                  >
                    {creating ? 'Creating...' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="mt-3 inline-flex w-full justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-base font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:col-start-1 sm:mt-0 sm:text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CaseSelector;
