import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { OT, OTStatus } from '@/types';
import KanbanOTCard from './KanbanOTCard';

export interface KanbanColumnProps {
  status: OTStatus;
  ots: OT[];
  color: string;
  label: string;
  borderColor: string;
}

/**
 * Individual Kanban column component
 * Represents a single status column (e.g., PREPLANIFICADA, PLANIFICADA, etc.)
 */
export function KanbanColumn({
  status,
  ots,
  color,
  label,
  borderColor,
}: KanbanColumnProps) {
  // Use useDroppable to make this column a drop target
  const { setNodeRef, isOver } = useDroppable({
    id: status,
  });

  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-200px)]">
      {/* Column Header */}
      <div
        className={`
          ${color} rounded-t-lg p-4 border-l-4 ${borderColor}
          flex items-center justify-between shrink-0
        `}
      >
        <div className="flex items-center gap-3">
          {/* Status label */}
          <h3 className="font-semibold text-gray-800 text-sm">{label}</h3>

          {/* OT count badge */}
          <span
            className="
              bg-white text-gray-800 text-xs font-bold rounded-full
              h-6 w-6 flex items-center justify-center
            "
          >
            {ots.length}
          </span>
        </div>

        {/* Add button for future feature */}
        <button
          className="
            text-gray-600 hover:text-gray-800 transition-colors
            text-lg leading-none
          "
          title="Agregar OT (próximamente)"
          disabled
        >
          +
        </button>
      </div>

      {/* Column Content - Droppable Area */}
      <div
        ref={setNodeRef}
        className={`
          flex-1 ${color} rounded-b-lg p-3
          border-2 ${borderColor} border-dashed
          overflow-y-auto overflow-x-hidden
          transition-all duration-200
          ${isOver ? 'bg-opacity-75 ring-2 ring-offset-2' : 'bg-opacity-100'}
        `}
        data-drop-zone={status}
      >
        <div className="space-y-3">
          {/* OT Cards */}
          <SortableContext
            items={ots.map((ot) => ot.id)}
            strategy={verticalListSortingStrategy}
          >
            {ots.map((ot) => (
              <KanbanOTCard key={ot.id} ot={ot} />
            ))}
          </SortableContext>

          {/* Empty state message */}
          {ots.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <p className="text-sm">No hay OTs en este estado</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default KanbanColumn;

