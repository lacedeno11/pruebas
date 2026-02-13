import React, { useState } from 'react'
import { createPortal } from 'react-dom'
import { toast } from 'react-toastify'
import { updateOTStatus } from '../services/api'

export function DetencionModal({ isOpen, onClose, otId, onSubmit }) {
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!reason.trim()) {
      toast.error('Please provide a reason for detention')
      return
    }

    setIsSubmitting(true)
    try {
      // Call the onSubmit handler with the reason
      await onSubmit(reason)
      setReason('')
    } catch (error) {
      console.error('Error submitting detention reason:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  // Render modal using React Portal for proper layering
  return createPortal(
    <div className="detention-modal-overlay" onClick={onClose}>
      <div
        className="detention-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="detention-modal-header">
          <h3>Mark OT as Detained</h3>
          <button
            className="detention-modal-close"
            onClick={onClose}
            aria-label="Close modal"
            type="button"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="detention-modal-form">
          <div className="detention-modal-body">
            <label htmlFor="detention-reason" className="detention-label">
              Reason for detention:
            </label>
            <textarea
              id="detention-reason"
              className="detention-textarea"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter the reason for marking this OT as detained..."
              rows="5"
              disabled={isSubmitting}
              autoFocus
            />
            <p className="detention-help-text">
              This information will be logged and visible to project managers
            </p>
          </div>

          <div className="detention-modal-footer">
            <button
              className="detention-btn detention-btn-cancel"
              onClick={onClose}
              disabled={isSubmitting}
              type="button"
            >
              Cancel
            </button>
            <button
              className="detention-btn detention-btn-submit"
              disabled={isSubmitting || !reason.trim()}
              type="submit"
            >
              {isSubmitting ? 'Submitting...' : 'Mark as Detained'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  )
}

// Detention Modal Styles
const detencionModalStyles = `
.detention-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.detention-modal-content {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideUp 0.3s ease-in-out;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.detention-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
  background-color: #f9f9f9;
}

.detention-modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
  font-weight: 600;
}

.detention-modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.detention-modal-close:hover {
  background-color: #f0f0f0;
  color: #d32f2f;
}

.detention-modal-close:focus {
  outline: 2px solid #2196F3;
  outline-offset: 2px;
}

.detention-modal-form {
  display: flex;
  flex-direction: column;
}

.detention-modal-body {
  padding: 16px;
  background-color: white;
}

.detention-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #333;
  line-height: 1.5;
}

.detention-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
  line-height: 1.5;
  min-height: 120px;
  transition: all 0.2s ease;
}

.detention-textarea:focus {
  outline: none;
  border-color: #2196F3;
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
}

.detention-textarea:disabled {
  background-color: #f5f5f5;
  color: #999;
  cursor: not-allowed;
}

.detention-help-text {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: #999;
  line-height: 1.4;
}

.detention-modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  background-color: #f9f9f9;
}

.detention-btn {
  padding: 10px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s ease;
  min-width: 100px;
  text-align: center;
}

.detention-btn:focus {
  outline: 2px solid #2196F3;
  outline-offset: 2px;
}

.detention-btn-cancel {
  background-color: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
}

.detention-btn-cancel:hover:not(:disabled) {
  background-color: #e0e0e0;
  border-color: #999;
}

.detention-btn-submit {
  background-color: #d32f2f;
  color: white;
}

.detention-btn-submit:hover:not(:disabled) {
  background-color: #b71c1c;
  box-shadow: 0 4px 8px rgba(211, 47, 47, 0.2);
}

.detention-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.detention-btn-submit:disabled {
  background-color: #e0e0e0;
  color: #999;
}

/* Responsive Design */
@media (max-width: 600px) {
  .detention-modal-content {
    width: 95%;
    max-width: none;
    border-radius: 8px 8px 0 0;
  }

  .detention-modal-body {
    padding: 12px;
  }

  .detention-modal-footer {
    padding: 12px;
    flex-direction: column-reverse;
  }

  .detention-btn {
    width: 100%;
  }

  .detention-textarea {
    font-size: 16px; /* Prevents zoom on iOS */
    min-height: 100px;
  }

  .detention-modal-header {
    padding: 12px;
  }

  .detention-modal-header h3 {
    font-size: 16px;
  }
}

@media (max-width: 400px) {
  .detention-modal-content {
    width: 100%;
  }

  .detention-modal-header h3 {
    font-size: 14px;
  }

  .detention-label {
    font-size: 12px;
  }

  .detention-textarea {
    font-size: 14px;
  }

  .detention-help-text {
    font-size: 11px;
  }

  .detention-btn {
    padding: 8px 12px;
    font-size: 12px;
    min-width: 80px;
  }
}
`

export default DetencionModal

