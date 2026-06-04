import React, { useEffect, useState } from 'react';
import { TableGrid } from './TableGrid';
import { OrderPanel } from './OrderPanel';
import { usePosStore } from '../../store';

export function PosDashboard() {
  const { products, fetchProducts, addToCart, activeTableId } = usePosStore();
  const [activeCategory, setActiveCategory] = useState(null);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Extract unique categories, ignoring falsy ones, defaults to "General"
  const categories = [...new Set(products.map(p => p.categoria || 'General'))];
  const displayCategory = activeCategory || categories[0];
  
  const filteredProducts = products.filter(p => (p.categoria || 'General') === displayCategory);

  return (
    <div className="flex gap-6 h-full">
      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar pb-6">
        <TableGrid />
        
        <div className="mt-8">
          <h2 className="text-xl font-bold text-text-main mb-4">Catálogo de Productos</h2>
          <div className="flex gap-2 overflow-x-auto pb-4 custom-scrollbar mb-4">
            {categories.map(cat => (
              <button 
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-4 py-2 rounded-xl font-medium whitespace-nowrap transition-colors ${displayCategory === cat ? 'bg-brand text-white shadow-md' : 'bg-white border border-surface-200 text-text-muted hover:border-brand hover:text-brand'}`}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {filteredProducts.map(prod => (
              <button 
                key={prod.id}
                onClick={() => {
                  if (activeTableId) addToCart({ ...prod, precio: prod.precio_unitario || prod.precio });
                  else alert("Selecciona una mesa primero.");
                }}
                className="p-4 bg-white border border-surface-200 rounded-xl hover:border-brand hover:shadow-md transition-all text-left flex flex-col justify-between min-h-[100px]"
              >
                <span className="font-semibold text-text-main line-clamp-2">{prod.nombre}</span>
                <span className="text-brand font-bold mt-2">${(prod.precio_unitario || prod.precio || 0).toFixed(2)}</span>
              </button>
            ))}
            {filteredProducts.length === 0 && (
              <p className="text-text-muted col-span-full">No hay productos en esta categoría.</p>
            )}
          </div>
        </div>
      </div>
      
      <div className="w-[400px] flex-shrink-0 h-full pb-6">
        <OrderPanel />
      </div>
    </div>
  );
}
