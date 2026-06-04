import React, { useEffect } from 'react';
import { usePosStore } from '../../store';
import { TableCard } from './TableCard';
import { motion } from 'framer-motion';

export function TableGrid() {
  const { tables, fetchTables, isLoadingTables } = usePosStore();

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05
      }
    }
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  };

  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold text-text-main mb-6 flex items-center gap-2">
        Selecciona una Mesa
      </h2>
      {isLoadingTables ? (
        <div className="text-text-muted py-10 text-center">Cargando mesas desde el servidor...</div>
      ) : (
        <motion.div 
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-4"
        >
          {tables.map(table => (
            <motion.div key={table.id} variants={item}>
              <TableCard table={table} />
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
