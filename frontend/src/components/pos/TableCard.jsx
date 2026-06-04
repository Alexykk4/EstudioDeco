import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { LayoutGrid } from 'lucide-react';
import { usePosStore } from '../../store';

export function TableCard({ table }) {
  const { setActiveTable, activeTableId } = usePosStore();
  
  const isOccupied = table.status === 'ocupada';
  const isActive = activeTableId === table.id;

  return (
    <Card 
      hoverable 
      onClick={() => setActiveTable(table.id)}
      className={`p-4 flex flex-col justify-between min-h-[130px] border-2 ${isActive ? 'border-brand shadow-volt-hover bg-brand-light/30' : 'border-transparent'}`}
    >
      <div className="flex flex-col sm:flex-row justify-between items-start gap-2 mb-3">
        <div className={`p-2 rounded-lg ${isOccupied ? 'bg-danger-light text-danger' : 'bg-success-light text-success'}`}>
          <LayoutGrid className="w-5 h-5" />
        </div>
        <Badge variant={isOccupied ? 'danger' : 'success'} className="text-[10px] sm:text-xs">
          {isOccupied ? 'OCUPADA' : 'DISPONIBLE'}
        </Badge>
      </div>
      
      <div>
        <h3 className="text-base font-bold text-text-main">{table.name}</h3>
        {isOccupied && (
          <p className="text-sm font-semibold text-brand mt-1">
            Total: ${(table.total || 0).toFixed(2)}
          </p>
        )}
      </div>
    </Card>
  );
}
