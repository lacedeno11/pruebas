import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CaseSelector from './CaseSelector';
import * as api from '../api/client';

vi.mock('../api/client');

describe('CaseSelector', () => {
  const mockCases = [
    {
      case_id: '123e4567-e89b-12d3-a456-426614174000',
      patient_id: '123e4567-e89b-12d3-a456-426614174001',
      status: 'created',
      description: 'Test Case 1',
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      case_id: '223e4567-e89b-12d3-a456-426614174000',
      patient_id: '223e4567-e89b-12d3-a456-426614174001',
      status: 'processing',
      description: 'Test Case 2',
      created_at: '2024-01-02T00:00:00Z',
    },
  ];

  const mockOnSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCases).mockResolvedValue(mockCases);
  });

  it('renders the component title', () => {
    render(<CaseSelector onSelect={mockOnSelect} />);
    expect(screen.getByText(/Case Selector/i)).toBeInTheDocument();
  });

  it('displays loading state initially', () => {
    render(<CaseSelector onSelect={mockOnSelect} />);
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  it('displays cases after loading', async () => {
    render(<CaseSelector onSelect={mockOnSelect} />);

    await waitFor(() => {
      expect(screen.getByText(/Test Case 1/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Test Case 2/i)).toBeInTheDocument();
  });

  it('calls onSelect when a case is clicked', async () => {
    render(<CaseSelector onSelect={mockOnSelect} />);

    await waitFor(() => {
      expect(screen.getByText(/Test Case 1/i)).toBeInTheDocument();
    });

    const caseItem = screen.getByText(/Test Case 1/i);
    fireEvent.click(caseItem);

    expect(mockOnSelect).toHaveBeenCalledWith(mockCases[0]);
  });

  it('displays error state on API failure', async () => {
    vi.mocked(api.getCases).mockRejectedValue(new Error('API Error'));

    render(<CaseSelector onSelect={mockOnSelect} />);

    await waitFor(() => {
      expect(screen.getByText(/Error/i)).toBeInTheDocument();
    });
  });
});
