import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../api/client';

interface Entity {
  id: string;
  text: string;
  type: string;
  start: number;
  end: number;
  confidence: number;
  ontologyMappings?: Array<{
    ontology: string;
    code: string;
    label: string;
    score: number;
  }>;
}

interface EHRData {
  text: string;
  entities?: Entity[];
  extractedAt?: string;
}

const EHRPanel: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const [ehrData, setEhrData] = useState<EHRData>({ text: '' });
  const [isEditing, setIsEditing] = useState(false);
  const [draftText, setDraftText] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);

  useEffect(() => {
    loadEHR();
  }, [caseId]);

  const loadEHR = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getEHR(caseId!);
      setEhrData(data);
      setDraftText(data.text || '');
    } catch (err) {
      // Mock data for development
      const mockEHR: EHRData = {
        text: `Patient: 65-year-old male\nChief Complaint: Persistent cough and chest pain\n\nHistory: Patient presents with a 3-month history of persistent cough, hemoptysis, and chest pain. Previous smoker (40 pack-years). Recent chest X-ray revealed a 2.5cm mass in the right upper lobe.\n\nDiagnosis: Suspected non-small cell lung cancer (NSCLC)\n\nTreatment Plan: CT scan scheduled, biopsy planned, oncology consultation`,
        entities: [
          {
            id: 'ent-001',
            text: 'non-small cell lung cancer',
            type: 'Disease',
            start: 290,
            end: 318,
            confidence: 0.95,
            ontologyMappings: [
              {
                ontology: 'ICD-10',
                code: 'C34.1',
                label: 'Malignant neoplasm of upper lobe, bronchus or lung',
                score: 0.92,
              },
              {
                ontology: 'SNOMED-CT',
                code: '254637007',
                label: 'Non-small cell lung cancer',
                score: 0.98,
              },
            ],
          },
          {
            id: 'ent-002',
            text: 'hemoptysis',
            type: 'Symptom',
            start: 130,
            end: 140,
            confidence: 0.88,
            ontologyMappings: [
              {
                ontology: 'SNOMED-CT',
                code: '66857006',
                label: 'Hemoptysis',
                score: 0.99,
              },
            ],
          },
          {
            id: 'ent-003',
            text: 'chest pain',
            type: 'Symptom',
            start: 146,
            end: 156,
            confidence: 0.91,
            ontologyMappings: [
              {
                ontology: 'SNOMED-CT',
                code: '29857009',
                label: 'Chest pain',
                score: 0.97,
              },
            ],
          },
        ],
        extractedAt: new Date().toISOString(),
      };
      setEhrData(mockEHR);
      setDraftText(mockEHR.text);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveEHR = async () => {
    try {
      setSaving(true);
      await apiClient.submitEHR(caseId!, draftText);
      setEhrData({ ...ehrData, text: draftText, entities: undefined });
      setIsEditing(false);
    } catch (err) {
      // Mock save for development
      setEhrData({ text: draftText, entities: undefined });
      setIsEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleExtractEntities = async () => {
    try {
      setExtracting(true);
      const result = await apiClient.extractEntities(caseId!);
      setEhrData({ ...ehrData, entities: result.entities, extractedAt: new Date().toISOString() });
    } catch (err) {
      // Mock extraction - reuse existing entities
      setTimeout(() => {
        setEhrData({
          ...ehrData,
          extractedAt: new Date().toISOString(),
        });
        setExtracting(false);
      }, 2000);
      return;
    }
    setExtracting(false);
  };

  const getHighlightedText = () => {
    if (!ehrData.entities || ehrData.entities.length === 0) {
      return ehrData.text;
    }

    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    // Sort entities by start position
    const sortedEntities = [...ehrData.entities].sort((a, b) => a.start - b.start);

    sortedEntities.forEach((entity, idx) => {
      // Add text before entity
      if (entity.start > lastIndex) {
        parts.push(
          <span key={`text-${idx}`}>{ehrData.text.substring(lastIndex, entity.start)}</span>
        );
      }

      // Add highlighted entity
      const entityTypeColors: Record<string, string> = {
        Disease: 'bg-red-200 hover:bg-red-300',
        Symptom: 'bg-yellow-200 hover:bg-yellow-300',
        Medication: 'bg-blue-200 hover:bg-blue-300',
        Procedure: 'bg-green-200 hover:bg-green-300',
        Anatomy: 'bg-purple-200 hover:bg-purple-300',
      };

      parts.push(
        <span
          key={`entity-${idx}`}
          className={`${entityTypeColors[entity.type] || 'bg-gray-200 hover:bg-gray-300'} cursor-pointer rounded px-1 transition-colors`}
          onClick={() => setSelectedEntity(entity)}
        >
          {entity.text}
        </span>
      );

      lastIndex = entity.end;
    });

    // Add remaining text
    if (lastIndex < ehrData.text.length) {
      parts.push(<span key="text-end">{ehrData.text.substring(lastIndex)}</span>);
    }

    return <>{parts}</>;
  };

  const getEntityTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      Disease: 'text-red-700 bg-red-100',
      Symptom: 'text-yellow-700 bg-yellow-100',
      Medication: 'text-blue-700 bg-blue-100',
      Procedure: 'text-green-700 bg-green-100',
      Anatomy: 'text-purple-700 bg-purple-100',
    };
    return colors[type] || 'text-gray-700 bg-gray-100';
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p className="mt-2 text-sm text-gray-500">Loading EHR data...</p>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Electronic Health Record</h1>
          <p className="mt-2 text-sm text-gray-700">
            View and extract medical entities from patient EHR data.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none space-x-2">
          {isEditing ? (
            <>
              <button
                onClick={handleSaveEHR}
                disabled={saving}
                className="inline-flex items-center justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save EHR'}
              </button>
              <button
                onClick={() => {
                  setIsEditing(false);
                  setDraftText(ehrData.text);
                }}
                className="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Edit EHR
              </button>
              <button
                onClick={handleExtractEntities}
                disabled={extracting || !ehrData.text}
                className="inline-flex items-center justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {extracting ? 'Extracting...' : 'Extract Entities'}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* EHR Text */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">EHR Text</h3>
              {isEditing ? (
                <textarea
                  value={draftText}
                  onChange={(e) => setDraftText(e.target.value)}
                  rows={20}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border px-3 py-2 font-mono"
                  placeholder="Paste or type patient EHR text here..."
                />
              ) : ehrData.text ? (
                <div className="prose max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700 leading-relaxed">
                    {getHighlightedText()}
                  </pre>
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-sm text-gray-500">No EHR text available. Click "Edit EHR" to add.</p>
                </div>
              )}

              {ehrData.extractedAt && (
                <p className="mt-4 text-xs text-gray-500">
                  Entities extracted on {new Date(ehrData.extractedAt).toLocaleString()}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Entities Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Extracted Entities</h3>
              {ehrData.entities && ehrData.entities.length > 0 ? (
                <div className="space-y-3">
                  {ehrData.entities.map((entity) => (
                    <div
                      key={entity.id}
                      onClick={() => setSelectedEntity(entity)}
                      className={`cursor-pointer rounded-lg border-2 p-3 transition-colors ${
                        selectedEntity?.id === entity.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <p className="text-sm font-medium text-gray-900">{entity.text}</p>
                        <span className={`ml-2 inline-flex rounded-full px-2 text-xs font-semibold ${getEntityTypeColor(entity.type)}`}>
                          {entity.type}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Confidence: {(entity.confidence * 100).toFixed(0)}%
                      </p>
                      {entity.ontologyMappings && entity.ontologyMappings.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {entity.ontologyMappings.map((mapping, idx) => (
                            <div key={idx} className="text-xs bg-gray-50 rounded p-2">
                              <p className="font-medium text-gray-700">{mapping.ontology}: {mapping.code}</p>
                              <p className="text-gray-600">{mapping.label}</p>
                              <p className="text-gray-500">Match: {(mapping.score * 100).toFixed(0)}%</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
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
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No entities</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {ehrData.text ? 'Click "Extract Entities" to analyze the text' : 'Add EHR text first'}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EHRPanel;
