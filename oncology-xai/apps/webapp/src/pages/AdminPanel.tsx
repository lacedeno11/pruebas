import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';

interface Ontology {
  id: string;
  name: string;
  version: string;
  status: 'draft' | 'published' | 'archived';
  description?: string;
  createdAt: string;
  updatedAt: string;
  termCount?: number;
}

interface Proposal {
  id: string;
  ontologyId: string;
  ontologyName: string;
  type: 'create' | 'update' | 'delete';
  title: string;
  description: string;
  proposedBy: string;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
  changes?: any;
}

const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'ontologies' | 'proposals'>('ontologies');
  const [ontologies, setOntologies] = useState<Ontology[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showProposalModal, setShowProposalModal] = useState(false);

  // Form states
  const [newOntologyName, setNewOntologyName] = useState('');
  const [newOntologyDesc, setNewOntologyDesc] = useState('');
  const [proposalTitle, setProposalTitle] = useState('');
  const [proposalDesc, setProposalDesc] = useState('');
  const [selectedOntologyId, setSelectedOntologyId] = useState('');

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    try {
      setLoading(true);
      if (activeTab === 'ontologies') {
        const data = await apiClient.getOntologies();
        setOntologies(data.ontologies || []);
      } else {
        const data = await apiClient.getProposals();
        setProposals(data.proposals || []);
      }
    } catch (err) {
      // Mock data for development
      if (activeTab === 'ontologies') {
        setOntologies([
          {
            id: 'ont-001',
            name: 'ICD-10',
            version: '2024.1',
            status: 'published',
            description: 'International Classification of Diseases, 10th Revision',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            termCount: 14400,
          },
          {
            id: 'ont-002',
            name: 'SNOMED-CT',
            version: '2024.09',
            status: 'published',
            description: 'Systematized Nomenclature of Medicine - Clinical Terms',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            termCount: 350000,
          },
          {
            id: 'ont-003',
            name: 'Custom Oncology',
            version: '1.0.0',
            status: 'draft',
            description: 'Custom ontology for oncology-specific terms',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            termCount: 120,
          },
        ]);
      } else {
        setProposals([
          {
            id: 'prop-001',
            ontologyId: 'ont-003',
            ontologyName: 'Custom Oncology',
            type: 'create',
            title: 'Add EGFR mutation terms',
            description: 'Proposal to add specific EGFR mutation classifications',
            proposedBy: 'Dr. Smith',
            status: 'pending',
            createdAt: new Date().toISOString(),
          },
          {
            id: 'prop-002',
            ontologyId: 'ont-003',
            ontologyName: 'Custom Oncology',
            type: 'update',
            title: 'Update treatment protocol terms',
            description: 'Update immunotherapy related terms with new protocols',
            proposedBy: 'Dr. Johnson',
            status: 'approved',
            createdAt: new Date(Date.now() - 86400000).toISOString(),
          },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOntology = async (e: React.FormEvent) => {
    e.preventDefault();
    // In real implementation, would call API
    const newOntology: Ontology = {
      id: `ont-${Date.now()}`,
      name: newOntologyName,
      version: '1.0.0',
      status: 'draft',
      description: newOntologyDesc,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      termCount: 0,
    };
    setOntologies([newOntology, ...ontologies]);
    setShowCreateModal(false);
    setNewOntologyName('');
    setNewOntologyDesc('');
  };

  const handleCreateProposal = async (e: React.FormEvent) => {
    e.preventDefault();
    const newProposal: Proposal = {
      id: `prop-${Date.now()}`,
      ontologyId: selectedOntologyId,
      ontologyName: ontologies.find(o => o.id === selectedOntologyId)?.name || '',
      type: 'create',
      title: proposalTitle,
      description: proposalDesc,
      proposedBy: 'Current User',
      status: 'pending',
      createdAt: new Date().toISOString(),
    };
    setProposals([newProposal, ...proposals]);
    setShowProposalModal(false);
    setProposalTitle('');
    setProposalDesc('');
    setSelectedOntologyId('');
  };

  const handleApproveProposal = async (proposalId: string) => {
    try {
      await apiClient.approveProposal(proposalId);
      setProposals(
        proposals.map((p) => (p.id === proposalId ? { ...p, status: 'approved' as const } : p))
      );
    } catch (err) {
      // Mock approval
      setProposals(
        proposals.map((p) => (p.id === proposalId ? { ...p, status: 'approved' as const } : p))
      );
    }
  };

  const handlePublishOntology = async (ontologyId: string) => {
    if (!confirm('Are you sure you want to publish this ontology? It will become available to all users.')) {
      return;
    }

    try {
      await apiClient.publishOntology(ontologyId);
      setOntologies(
        ontologies.map((o) => (o.id === ontologyId ? { ...o, status: 'published' as const } : o))
      );
    } catch (err) {
      // Mock publish
      setOntologies(
        ontologies.map((o) => (o.id === ontologyId ? { ...o, status: 'published' as const } : o))
      );
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-800',
      published: 'bg-green-100 text-green-800',
      archived: 'bg-red-100 text-red-800',
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${badges[status]}`}>
        {status}
      </span>
    );
  };

  const getProposalTypeBadge = (type: string) => {
    const badges: Record<string, string> = {
      create: 'bg-blue-100 text-blue-800',
      update: 'bg-purple-100 text-purple-800',
      delete: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${badges[type]}`}>
        {type}
      </span>
    );
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-3xl font-semibold text-gray-900">Ontology Administration</h1>
          <p className="mt-2 text-sm text-gray-700">
            Manage ontologies and review change proposals.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          {activeTab === 'ontologies' ? (
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            >
              Create Ontology
            </button>
          ) : (
            <button
              onClick={() => setShowProposalModal(true)}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            >
              New Proposal
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-6 border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('ontologies')}
            className={`${
              activeTab === 'ontologies'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            } whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium`}
          >
            Ontologies
          </button>
          <button
            onClick={() => setActiveTab('proposals')}
            className={`${
              activeTab === 'proposals'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            } whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium`}
          >
            Proposals
            {proposals.filter((p) => p.status === 'pending').length > 0 && (
              <span className="ml-2 rounded-full bg-primary-100 px-2 py-1 text-xs font-medium text-primary-600">
                {proposals.filter((p) => p.status === 'pending').length}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* Content */}
      {loading ? (
        <div className="mt-8 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-2 text-sm text-gray-500">Loading...</p>
        </div>
      ) : activeTab === 'ontologies' ? (
        <div className="mt-8 overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
          <table className="min-w-full divide-y divide-gray-300">
            <thead className="bg-gray-50">
              <tr>
                <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">
                  Name
                </th>
                <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                  Version
                </th>
                <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                  Status
                </th>
                <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                  Terms
                </th>
                <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                  Updated
                </th>
                <th className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {ontologies.map((ontology) => (
                <tr key={ontology.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap py-4 pl-4 pr-3 sm:pl-6">
                    <div className="text-sm font-medium text-gray-900">{ontology.name}</div>
                    <div className="text-sm text-gray-500">{ontology.description}</div>
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {ontology.version}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm">
                    {getStatusBadge(ontology.status)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {ontology.termCount?.toLocaleString() || '—'}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {new Date(ontology.updatedAt).toLocaleDateString()}
                  </td>
                  <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    {ontology.status === 'draft' && (
                      <button
                        onClick={() => handlePublishOntology(ontology.id)}
                        className="text-primary-600 hover:text-primary-900 mr-4"
                      >
                        Publish
                      </button>
                    )}
                    <button className="text-gray-600 hover:text-gray-900">
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="mt-8 space-y-4">
          {proposals.length === 0 ? (
            <div className="text-center py-12 bg-white shadow rounded-lg">
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
              <h3 className="mt-2 text-sm font-medium text-gray-900">No proposals</h3>
              <p className="mt-1 text-sm text-gray-500">Get started by creating a new proposal.</p>
            </div>
          ) : (
            proposals.map((proposal) => (
              <div key={proposal.id} className="bg-white shadow rounded-lg">
                <div className="px-6 py-5">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <h3 className="text-lg font-medium text-gray-900">{proposal.title}</h3>
                        {getProposalTypeBadge(proposal.type)}
                        {getStatusBadge(proposal.status)}
                      </div>
                      <p className="mt-1 text-sm text-gray-500">
                        Ontology: {proposal.ontologyName} | Proposed by: {proposal.proposedBy}
                      </p>
                      <p className="mt-2 text-sm text-gray-700">{proposal.description}</p>
                      <p className="mt-2 text-xs text-gray-500">
                        Created: {new Date(proposal.createdAt).toLocaleString()}
                      </p>
                    </div>
                    {proposal.status === 'pending' && (
                      <div className="ml-4 flex-shrink-0 flex space-x-2">
                        <button
                          onClick={() => handleApproveProposal(proposal.id)}
                          className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                        >
                          Approve
                        </button>
                        <button
                          className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Create Ontology Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-screen items-end justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowCreateModal(false)}></div>

            <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <form onSubmit={handleCreateOntology}>
                <div>
                  <h3 className="text-lg font-medium leading-6 text-gray-900">
                    Create New Ontology
                  </h3>
                  <div className="mt-4">
                    <label htmlFor="ontologyName" className="block text-sm font-medium text-gray-700">
                      Name *
                    </label>
                    <input
                      type="text"
                      id="ontologyName"
                      value={newOntologyName}
                      onChange={(e) => setNewOntologyName(e.target.value)}
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border px-3 py-2"
                      placeholder="My Custom Ontology"
                    />
                  </div>
                  <div className="mt-4">
                    <label htmlFor="ontologyDesc" className="block text-sm font-medium text-gray-700">
                      Description
                    </label>
                    <textarea
                      id="ontologyDesc"
                      value={newOntologyDesc}
                      onChange={(e) => setNewOntologyDesc(e.target.value)}
                      rows={3}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border px-3 py-2"
                      placeholder="Brief description of the ontology..."
                    />
                  </div>
                </div>
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                  <button
                    type="submit"
                    className="inline-flex w-full justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:col-start-2 sm:text-sm"
                  >
                    Create
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

      {/* Create Proposal Modal */}
      {showProposalModal && (
        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-screen items-end justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowProposalModal(false)}></div>

            <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <form onSubmit={handleCreateProposal}>
                <div>
                  <h3 className="text-lg font-medium leading-6 text-gray-900">
                    Create New Proposal
                  </h3>
                  <div className="mt-4">
                    <label htmlFor="ontologySelect" className="block text-sm font-medium text-gray-700">
                      Ontology *
                    </label>
                    <select
                      id="ontologySelect"
                      value={selectedOntologyId}
                      onChange={(e) => setSelectedOntologyId(e.target.value)}
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border px-3 py-2"
                    >
                      <option value="">Select an ontology</option>
                      {ontologies.map((ont) => (
                        <option key={ont.id} value={ont.id}>
                          {ont.name} ({ont.version})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="mt-4">
                    <label htmlFor="proposalTitle" className="block text-sm font-medium text-gray-700">
                      Title *
                    </label>
                    <input
                      type="text"
                      id="proposalTitle"
                      value={proposalTitle}
                      onChange={(e) => setProposalTitle(e.target.value)}
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border px-3 py-2"
                      placeholder="Brief title for the proposal"
                    />
                  </div>
                  <div className="mt-4">
                    <label htmlFor="proposalDesc" className="block text-sm font-medium text-gray-700">
                      Description *
                    </label>
                    <textarea
                      id="proposalDesc"
                      value={proposalDesc}
                      onChange={(e) => setProposalDesc(e.target.value)}
                      required
                      rows={4}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border px-3 py-2"
                      placeholder="Detailed description of the proposed changes..."
                    />
                  </div>
                </div>
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                  <button
                    type="submit"
                    className="inline-flex w-full justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:col-start-2 sm:text-sm"
                  >
                    Create Proposal
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowProposalModal(false)}
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

export default AdminPanel;
