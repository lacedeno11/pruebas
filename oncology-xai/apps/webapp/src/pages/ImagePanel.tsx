import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../api/client';

interface Image {
  id: string;
  filename: string;
  uploadedAt: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  thumbnailUrl?: string;
  imageUrl?: string;
  results?: {
    detections?: Array<{
      label: string;
      confidence: number;
      bbox: [number, number, number, number];
    }>;
    segmentation?: string;
  };
}

const ImagePanel: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const [images, setImages] = useState<Image[]>([]);
  const [selectedImage, setSelectedImage] = useState<Image | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    loadImages();
  }, [caseId]);

  useEffect(() => {
    if (selectedImage && canvasRef.current) {
      drawImageWithOverlay();
    }
  }, [selectedImage, showOverlay]);

  const loadImages = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getImages(caseId!);
      setImages(data.images || []);
    } catch (err) {
      // Mock data for development
      setImages([
        {
          id: 'img-001',
          filename: 'chest_xray.png',
          uploadedAt: new Date().toISOString(),
          status: 'completed',
          imageUrl: 'https://via.placeholder.com/512x512/4A90E2/FFFFFF?text=Chest+X-Ray',
          results: {
            detections: [
              { label: 'Nodule', confidence: 0.92, bbox: [100, 150, 200, 250] },
              { label: 'Opacity', confidence: 0.78, bbox: [300, 100, 400, 200] },
            ],
          },
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    try {
      setUploading(true);
      const uploadedImage = await apiClient.uploadImage(caseId!, file);
      setImages([uploadedImage, ...images]);
    } catch (err) {
      // Mock upload for development
      const mockImage: Image = {
        id: `img-${Date.now()}`,
        filename: file.name,
        uploadedAt: new Date().toISOString(),
        status: 'uploaded',
        imageUrl: URL.createObjectURL(file),
      };
      setImages([mockImage, ...images]);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleProcessImage = async (image: Image) => {
    try {
      setProcessing(true);
      const updatedImage = await apiClient.processImage(caseId!, image.id);
      setImages(images.map(img => img.id === image.id ? updatedImage : img));
      if (selectedImage?.id === image.id) {
        setSelectedImage(updatedImage);
      }
    } catch (err) {
      // Mock processing for development
      setTimeout(() => {
        const processedImage: Image = {
          ...image,
          status: 'completed',
          results: {
            detections: [
              { label: 'Tumor', confidence: 0.89, bbox: [150, 120, 280, 250] },
            ],
          },
        };
        setImages(images.map(img => img.id === image.id ? processedImage : img));
        if (selectedImage?.id === image.id) {
          setSelectedImage(processedImage);
        }
        setProcessing(false);
      }, 2000);
      return;
    }
    setProcessing(false);
  };

  const drawImageWithOverlay = () => {
    if (!selectedImage || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new window.Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      if (showOverlay && selectedImage.results?.detections) {
        selectedImage.results.detections.forEach((detection) => {
          const [x1, y1, x2, y2] = detection.bbox;

          // Draw bounding box
          ctx.strokeStyle = '#FF6B6B';
          ctx.lineWidth = 3;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

          // Draw label background
          ctx.fillStyle = '#FF6B6B';
          const label = `${detection.label} ${(detection.confidence * 100).toFixed(0)}%`;
          const metrics = ctx.measureText(label);
          ctx.fillRect(x1, y1 - 25, metrics.width + 10, 25);

          // Draw label text
          ctx.fillStyle = '#FFFFFF';
          ctx.font = '14px Arial';
          ctx.fillText(label, x1 + 5, y1 - 8);
        });
      }
    };
    img.src = selectedImage.imageUrl || '';
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, string> = {
      uploaded: 'bg-gray-100 text-gray-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${badges[status]}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Image Analysis</h1>
          <p className="mt-2 text-sm text-gray-700">
            Upload medical images and process them with AI models.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload Image'}
          </button>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Image List */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Images</h3>
              {loading ? (
                <div className="text-center py-4">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              ) : images.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">No images uploaded yet</p>
              ) : (
                <div className="space-y-3">
                  {images.map((image) => (
                    <div
                      key={image.id}
                      onClick={() => setSelectedImage(image)}
                      className={`cursor-pointer rounded-lg border-2 p-3 transition-colors ${
                        selectedImage?.id === image.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {image.filename}
                        </p>
                        {getStatusBadge(image.status)}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(image.uploadedAt).toLocaleString()}
                      </p>
                      {image.status === 'uploaded' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleProcessImage(image);
                          }}
                          disabled={processing}
                          className="mt-2 w-full inline-flex justify-center items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-primary-700 bg-primary-100 hover:bg-primary-200 focus:outline-none disabled:opacity-50"
                        >
                          {processing ? 'Processing...' : 'Process Image'}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Image Viewer */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              {selectedImage ? (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium text-gray-900">
                      {selectedImage.filename}
                    </h3>
                    {selectedImage.results && (
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={showOverlay}
                          onChange={(e) => setShowOverlay(e.target.checked)}
                          className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span className="ml-2 text-sm text-gray-700">Show Overlays</span>
                      </label>
                    )}
                  </div>

                  {/* Canvas for image with overlays */}
                  <div className="border border-gray-300 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center" style={{ minHeight: '400px' }}>
                    <canvas ref={canvasRef} className="max-w-full h-auto" />
                  </div>

                  {/* Results Panel */}
                  {selectedImage.results && (
                    <div className="mt-6">
                      <h4 className="text-md font-medium text-gray-900 mb-3">Detection Results</h4>
                      <div className="space-y-2">
                        {selectedImage.results.detections?.map((detection, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div>
                              <p className="text-sm font-medium text-gray-900">{detection.label}</p>
                              <p className="text-xs text-gray-500">
                                BBox: [{detection.bbox.join(', ')}]
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-semibold text-primary-600">
                                {(detection.confidence * 100).toFixed(1)}%
                              </p>
                              <p className="text-xs text-gray-500">confidence</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12">
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
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No image selected</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Select an image from the list or upload a new one.
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

export default ImagePanel;
