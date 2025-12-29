import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ImagePanel from './ImagePanel';
import * as api from '../api/client';

vi.mock('../api/client');

describe('ImagePanel', () => {
  const mockCaseId = '123e4567-e89b-12d3-a456-426614174000';

  const mockImages = [
    {
      image_id: 'img-001',
      case_id: mockCaseId,
      format: 'png',
      storage_uri: 's3://bucket/image1.png',
      checksum: 'abc123',
      size_bytes: 1024000,
      stain: 'H&E',
      magnification: '20x',
      uploaded_at: '2024-01-01T00:00:00Z',
    },
    {
      image_id: 'img-002',
      case_id: mockCaseId,
      format: 'biff',
      storage_uri: 's3://bucket/image2.biff',
      checksum: 'def456',
      size_bytes: 5120000,
      stain: 'IHC',
      magnification: '40x',
      uploaded_at: '2024-01-02T00:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCaseImages).mockResolvedValue(mockImages);
  });

  it('renders the component title', () => {
    render(<ImagePanel caseId={mockCaseId} />);
    expect(screen.getByText(/Image Panel/i)).toBeInTheDocument();
  });

  it('displays images after loading', async () => {
    render(<ImagePanel caseId={mockCaseId} />);

    await waitFor(() => {
      expect(screen.getByText(/H&E/i)).toBeInTheDocument();
    });
  });

  it('displays image metadata', async () => {
    render(<ImagePanel caseId={mockCaseId} />);

    await waitFor(() => {
      expect(screen.getByText(/20x/i)).toBeInTheDocument();
      expect(screen.getByText(/40x/i)).toBeInTheDocument();
    });
  });

  it('handles empty image list', async () => {
    vi.mocked(api.getCaseImages).mockResolvedValue([]);

    render(<ImagePanel caseId={mockCaseId} />);

    await waitFor(() => {
      expect(screen.getByText(/No images/i)).toBeInTheDocument();
    });
  });
});
