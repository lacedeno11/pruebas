import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Network } from 'vis-network';
import apiClient from '../api/client';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, any>;
}

interface GraphEdge {
  id: string;
  from: string;
  to: string;
  label: string;
  type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const GraphPanel: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const networkRef = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);

  useEffect(() => {
    loadGraph();
  }, [caseId]);

  useEffect(() => {
    if (graphData && networkRef.current) {
      initializeNetwork();
    }
  }, [graphData]);

  const loadGraph = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getGraphData(caseId!);
      setGraphData(data);
    } catch (err) {
      // Mock graph data for development
      const mockGraph: GraphData = {
        nodes: [
          {
            id: 'patient-1',
            label: 'Patient PT-12345',
            type: 'Patient',
            properties: { age: 65, gender: 'Male' },
          },
          {
            id: 'disease-1',
            label: 'NSCLC',
            type: 'Disease',
            properties: { code: 'C34.1', ontology: 'ICD-10' },
          },
          {
            id: 'symptom-1',
            label: 'Hemoptysis',
            type: 'Symptom',
            properties: { code: '66857006', ontology: 'SNOMED-CT' },
          },
          {
            id: 'symptom-2',
            label: 'Chest Pain',
            type: 'Symptom',
            properties: { code: '29857009', ontology: 'SNOMED-CT' },
          },
          {
            id: 'anatomy-1',
            label: 'Right Upper Lobe',
            type: 'Anatomy',
            properties: { code: '45653009', ontology: 'SNOMED-CT' },
          },
          {
            id: 'finding-1',
            label: '2.5cm Mass',
            type: 'Finding',
            properties: { size: '2.5cm' },
          },
          {
            id: 'procedure-1',
            label: 'CT Scan',
            type: 'Procedure',
            properties: { status: 'Scheduled' },
          },
          {
            id: 'procedure-2',
            label: 'Biopsy',
            type: 'Procedure',
            properties: { status: 'Planned' },
          },
        ],
        edges: [
          { id: 'e1', from: 'patient-1', to: 'disease-1', label: 'diagnosed_with', type: 'DIAGNOSED_WITH' },
          { id: 'e2', from: 'patient-1', to: 'symptom-1', label: 'presents_with', type: 'PRESENTS_WITH' },
          { id: 'e3', from: 'patient-1', to: 'symptom-2', label: 'presents_with', type: 'PRESENTS_WITH' },
          { id: 'e4', from: 'disease-1', to: 'anatomy-1', label: 'located_in', type: 'LOCATED_IN' },
          { id: 'e5', from: 'finding-1', to: 'anatomy-1', label: 'found_in', type: 'FOUND_IN' },
          { id: 'e6', from: 'finding-1', to: 'disease-1', label: 'indicates', type: 'INDICATES' },
          { id: 'e7', from: 'patient-1', to: 'procedure-1', label: 'scheduled_for', type: 'SCHEDULED_FOR' },
          { id: 'e8', from: 'patient-1', to: 'procedure-2', label: 'planned_for', type: 'PLANNED_FOR' },
        ],
      };
      setGraphData(mockGraph);
    } finally {
      setLoading(false);
    }
  };

  const initializeNetwork = () => {
    if (!networkRef.current || !graphData) return;

    // Define colors for different node types
    const nodeColors: Record<string, string> = {
      Patient: '#3B82F6',
      Disease: '#EF4444',
      Symptom: '#F59E0B',
      Anatomy: '#8B5CF6',
      Finding: '#10B981',
      Procedure: '#06B6D4',
    };

    // Prepare data for vis-network
    const nodes = graphData.nodes.map((node) => ({
      id: node.id,
      label: node.label,
      color: nodeColors[node.type] || '#6B7280',
      font: { color: '#FFFFFF' },
      shape: 'box',
      margin: 10,
    }));

    const edges = graphData.edges.map((edge) => ({
      id: edge.id,
      from: edge.from,
      to: edge.to,
      label: edge.label,
      arrows: 'to',
      color: { color: '#9CA3AF' },
      font: { size: 12, color: '#6B7280', align: 'middle' },
    }));

    const data = {
      nodes: nodes,
      edges: edges,
    };

    const options = {
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -2000,
          centralGravity: 0.3,
          springLength: 150,
          springConstant: 0.04,
        },
        stabilization: {
          iterations: 150,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
      },
      layout: {
        improvedLayout: true,
        hierarchical: {
          enabled: false,
        },
      },
    };

    // Create network
    networkInstance.current = new Network(networkRef.current, data, options);

    // Event listeners
    networkInstance.current.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = graphData.nodes.find((n) => n.id === nodeId);
        if (node) {
          setSelectedNode(node);
        }
      } else {
        setSelectedNode(null);
      }
    });
  };

  const getNodeTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      Patient: 'text-blue-700 bg-blue-100',
      Disease: 'text-red-700 bg-red-100',
      Symptom: 'text-yellow-700 bg-yellow-100',
      Anatomy: 'text-purple-700 bg-purple-100',
      Finding: 'text-green-700 bg-green-100',
      Procedure: 'text-cyan-700 bg-cyan-100',
    };
    return colors[type] || 'text-gray-700 bg-gray-100';
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p className="mt-2 text-sm text-gray-500">Loading knowledge graph...</p>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Knowledge Graph</h1>
          <p className="mt-2 text-sm text-gray-700">
            Visualize the integrated knowledge graph combining imaging, EHR, and ontology data.
          </p>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Graph Visualization */}
        <div className="lg:col-span-3">
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div
              ref={networkRef}
              style={{
                height: '600px',
                width: '100%',
              }}
              className="border border-gray-200"
            />
          </div>

          {/* Legend */}
          <div className="mt-4 bg-white shadow rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Legend</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {['Patient', 'Disease', 'Symptom', 'Anatomy', 'Finding', 'Procedure'].map((type) => (
                <div key={type} className="flex items-center">
                  <div
                    className="w-4 h-4 rounded mr-2"
                    style={{
                      backgroundColor: {
                        Patient: '#3B82F6',
                        Disease: '#EF4444',
                        Symptom: '#F59E0B',
                        Anatomy: '#8B5CF6',
                        Finding: '#10B981',
                        Procedure: '#06B6D4',
                      }[type],
                    }}
                  />
                  <span className="text-xs text-gray-700">{type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Node Details Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Node Details</h3>
              {selectedNode ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{selectedNode.label}</p>
                    <span className={`mt-1 inline-flex rounded-full px-2 text-xs font-semibold ${getNodeTypeColor(selectedNode.type)}`}>
                      {selectedNode.type}
                    </span>
                  </div>

                  {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Properties</h4>
                      <dl className="space-y-2">
                        {Object.entries(selectedNode.properties).map(([key, value]) => (
                          <div key={key} className="text-sm">
                            <dt className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</dt>
                            <dd className="text-gray-900 font-medium">{String(value)}</dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  )}

                  {/* Connected nodes */}
                  {graphData && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Connections</h4>
                      <div className="space-y-2">
                        {graphData.edges
                          .filter(
                            (edge) => edge.from === selectedNode.id || edge.to === selectedNode.id
                          )
                          .map((edge) => {
                            const connectedNodeId =
                              edge.from === selectedNode.id ? edge.to : edge.from;
                            const connectedNode = graphData.nodes.find(
                              (n) => n.id === connectedNodeId
                            );
                            const direction = edge.from === selectedNode.id ? 'to' : 'from';

                            return (
                              <div key={edge.id} className="text-xs bg-gray-50 rounded p-2">
                                <p className="text-gray-500 mb-1">{edge.label}</p>
                                <p className="text-gray-900">
                                  {direction} <span className="font-medium">{connectedNode?.label}</span>
                                </p>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
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
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No node selected</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Click on a node in the graph to view its details.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Graph Statistics */}
          {graphData && (
            <div className="mt-4 bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Statistics</h3>
                <dl className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <dt className="text-gray-500">Total Nodes</dt>
                    <dd className="text-gray-900 font-medium">{graphData.nodes.length}</dd>
                  </div>
                  <div className="flex justify-between text-sm">
                    <dt className="text-gray-500">Total Edges</dt>
                    <dd className="text-gray-900 font-medium">{graphData.edges.length}</dd>
                  </div>
                  <div className="flex justify-between text-sm">
                    <dt className="text-gray-500">Node Types</dt>
                    <dd className="text-gray-900 font-medium">
                      {new Set(graphData.nodes.map((n) => n.type)).size}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default GraphPanel;
