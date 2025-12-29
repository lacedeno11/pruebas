import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import GraphPanel from './GraphPanel';
import * as api from '../api/client';

vi.mock('../api/client');
vi.mock('vis-network/standalone', () => ({
  Network: vi.fn().mockImplementation(() => ({
    on: vi.fn(),
    fit: vi.fn(),
    destroy: vi.fn(),
  })),
  DataSet: vi.fn().mockImplementation(() => ({
    add: vi.fn(),
    remove: vi.fn(),
    clear: vi.fn(),
  })),
}));

describe('GraphPanel', () => {
  const mockCaseId = '123e4567-e89b-12d3-a456-426614174000';

  const mockGraphData = {
    nodes: [
      { id: 'node1', label: 'Adenocarcinoma', type: 'diagnosis' },
      { id: 'node2', label: 'EGFR', type: 'biomarker' },
      { id: 'node3', label: 'Acinar Pattern', type: 'pattern' },
    ],
    edges: [
      { from: 'node1', to: 'node2', label: 'hasMarker' },
      { from: 'node1', to: 'node3', label: 'hasPattern' },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCaseGraph).mockResolvedValue(mockGraphData);
  });

  it('renders the component title', () => {
    render(<GraphPanel caseId={mockCaseId} />);
    expect(screen.getByText(/Graph/i)).toBeInTheDocument();
  });

  it('renders graph container', async () => {
    const { container } = render(<GraphPanel caseId={mockCaseId} />);

    await waitFor(() => {
      const graphContainer = container.querySelector('#graph-container');
      expect(graphContainer).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    render(<GraphPanel caseId={mockCaseId} />);
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  it('handles API error gracefully', async () => {
    vi.mocked(api.getCaseGraph).mockRejectedValue(new Error('Graph API Error'));

    render(<GraphPanel caseId={mockCaseId} />);

    await waitFor(() => {
      expect(screen.getByText(/Error/i)).toBeInTheDocument();
    });
  });
});
