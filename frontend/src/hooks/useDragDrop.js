import { useState, useCallback } from 'react'
import { updateOTStatus } from '../services/api'
import { toast } from 'react-toastify'

export function useDragDrop() {
  const [draggingId, setDraggingId] = useState(null)
  const [originalData, setOriginalData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleDragStart = useCallback((event) => {
    const { active } = event
    setDraggingId(active.id)
    setOriginalData({
      id: active.id,
      currentStatus: active.data.current?.status
    })
  }, [])

  const handleDragOver = useCallback((event) => {
    const { active, over } = event
    
    if (!over) return
    
    // Provide visual feedback during drag
    // This would be handled by dnd-kit's DragOverlay
  }, [])

  const handleDragEnd = useCallback(async (event) => {
    const { active, over } = event
    
    // Reset dragging state
    setDraggingId(null)

    // If no drop target or dropped in same position
    if (!over || active.id === over.id) {
      return
    }

    const otId = active.id
    const newStatus = over.id // Assuming column IDs match status names

    // Optimistic update - show loading
    setIsLoading(true)

    try {
      // Call API to update OT status
      const result = await updateOTStatus(otId, newStatus)
      
      // If dropping to DETENIDA, additional modal will be shown by parent component
      // But we still call the API here
      
      setIsLoading(false)
      toast.success(`OT moved to ${newStatus}`)
      
    } catch (error) {
      // Rollback on error
      setIsLoading(false)
      toast.error(`Failed to update OT status: ${error.message}`)
      
      // Parent component should handle the rollback
      // by refreshing the OT data from the server
    }
  }, [])

  return {
    draggingId,
    isLoading,
    handleDragStart,
    handleDragOver,
    handleDragEnd
  }
}

export default useDragDrop

