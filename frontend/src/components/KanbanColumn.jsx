/**
 * Kanban Column Component
 * 
 * Droppable column component for a specific OT status in the Kanban board.
 * Uses @dnd-kit/sortable for sortable vertical context and drag-drop support.
 */

import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import OTCard from './OTCard';
import { getStatusColor, getStatusLabel } from '../utils/formatters';
import { OT_STATUSES } from '../utils/constants';

/**
 * SortableOTCard - Wrapper component that makes OTCard sortable/draggable
 * 
 * @param {Object} props - Component props
 * @param {Object} props.ot - OT object to display
 * @param {boolean} props.isDragging - Whether card is being dragged
 * @returns {JSX.Element} Sortable OT card
 */
function SortableOTCard({ ot, isDragging }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: ot.id.toString() });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSortableDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="mb-3"
    >
      <OTCard ot={ot} isDragging={isDragging || isSortableDragging} />
    </div>
  );
}

/**
 * KanbanColumn component for displaying OTs in a specific status column.
 * 
 * @param {Object} props - Component props
 * @param {string} props.status - OT status (e.g., 'PREPLANIFICADA', 'FINALIZADA')
 * @param {Array} props.ots - Array of OT objects for this status
 * @param {boolean} props.isDragging - Whether any card in this column is being dragged
 * @returns {JSX.Element} Droppable column with sortable cards
 * 
 * @example
 * <KanbanColumn
 *   status="PLANIFICADA"
 *   ots={filteredOTs}
 *   isDragging={false}
 * />
 */
export default function KanbanColumn({ status, ots = [], isDragging = false }) {
  // Get status color styling
  const statusColor = getStatusColor(status);
  
  // Get human-readable status label
  const statusLabel = getStatusLabel(status);

  // Setup droppable zone for this column
  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: `droppable-${status}`,
  });

  // Setup sortable context for vertical drag-and-drop within column
  const sortableIds = ots.map((ot) => ot.id.toString());

  return (
    <div
      className={`
        kanban-column
        flex flex-col
        w-full min-w-80 max-w-md
        rounded-lg border-2
        transition-all duration-200
        ${statusColor.bg} ${statusColor.border}
        ${isOver ? 'ring-2 ring-offset-2 ring-blue-400 scale-105' : ''}
        p-4
        h-full min-h-96
      `}
    >
      {/* Column Header */}
      <div
        className={`
          kanban-column-header
          flex items-center justify-between gap-2
          mb-4 pb-3
          border-b-2 ${statusColor.border}
        `}
      >
        <h2
          className={`
            text-lg font-bold
            ${statusColor.text}
          `}
        >
          {statusLabel}
        </h2>
        <span
          className={`
            px-3 py-1 rounded-full text-sm font-semibold
            ${statusColor.badgeBg} ${statusColor.badgeText}
          `}
        >
          {ots.length}
        </span>
      </div>

      {/* Droppable Cards Container */}
      <SortableContext
        items={sortableIds}
        strategy={verticalListSortingStrategy}
      >
        <div
          ref={setDroppableRef}
          className={`
            kanban-column-droppable
            flex-1 overflow-y-auto space-y-3
            transition-colors duration-200
            ${isOver ? 'bg-blue-50 rounded-lg p-2' : ''}
          `}
        >
          {ots.length > 0 ? (
            ots.map((ot) => (
              <SortableOTCard
                key={ot.id}
                ot={ot}
                isDragging={isDragging}
              />
            ))
          ) : (
            <div
              className={`
                empty-state
                flex items-center justify-center
                h-32
                rounded-lg
                text-center
                ${statusColor.bg}
                opacity-50
              `}
            >
              <p className={`${statusColor.text} font-semibold`}>
                No orders in this status
              </p>
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

