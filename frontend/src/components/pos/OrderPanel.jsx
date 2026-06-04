import React from 'react';
import { usePosStore } from '../../store';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Trash2, Plus, Minus, CreditCard, Banknote, Receipt } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function OrderPanel() {
  const { activeTableId, tables, cart, addToCart, removeFromCart, updateQuantity, clearCart, getCartTotal } = usePosStore();
  
  const activeTable = tables.find(t => t.id === activeTableId);
  const total = getCartTotal();

  if (!activeTableId) {
    return (
      <Card className="h-full flex flex-col items-center justify-center p-8 bg-surface-50 border-dashed border-2 border-surface-200">
        <Receipt className="w-16 h-16 text-surface-200 mb-4" />
        <p className="text-text-muted font-medium text-center">Selecciona una mesa para<br/>comenzar a tomar la orden.</p>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col bg-white">
      <div className="p-6 border-b border-surface-200 bg-brand-light/20">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold text-brand-dark">{activeTable.name}</h2>
          <span className="text-sm font-semibold px-3 py-1 bg-white rounded-full text-text-muted shadow-sm">
            Orden Actual
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <AnimatePresence>
          {cart.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              className="text-center text-text-muted mt-10"
            >
              La orden está vacía.
            </motion.div>
          ) : (
            cart.map(item => (
              <motion.div 
                key={item.id}
                layout
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="flex items-center justify-between py-3 border-b border-surface-200 last:border-0"
              >
                <div className="flex-1">
                  <h4 className="font-semibold text-text-main">{item.nombre}</h4>
                  <p className="text-sm text-text-muted">${item.precio.toFixed(2)}</p>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1 bg-surface-50 rounded-lg p-1">
                    <button 
                      onClick={() => updateQuantity(item.id, Math.max(1, item.quantity - 1))}
                      className="p-1 hover:bg-white rounded shadow-sm text-text-muted hover:text-brand transition-colors"
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <span className="w-8 text-center font-medium text-sm">{item.quantity}</span>
                    <button 
                      onClick={() => updateQuantity(item.id, item.quantity + 1)}
                      className="p-1 hover:bg-white rounded shadow-sm text-text-muted hover:text-brand transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                  <button 
                    onClick={() => removeFromCart(item.id)}
                    className="p-2 text-text-muted hover:text-danger hover:bg-danger-light rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      <div className="p-6 border-t border-surface-200 bg-surface-50">
        <div className="flex justify-between items-center mb-6">
          <span className="text-text-muted font-medium">Total a pagar</span>
          <span className="text-3xl font-bold text-brand-dark">${total.toFixed(2)}</span>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <Button variant="outline" className="flex flex-col gap-2 h-auto py-3">
            <Banknote className="w-6 h-6 text-success" />
            <span className="text-xs">Efectivo</span>
          </Button>
          <Button variant="outline" className="flex flex-col gap-2 h-auto py-3">
            <CreditCard className="w-6 h-6 text-brand" />
            <span className="text-xs">Tarjeta</span>
          </Button>
        </div>
        
        <Button 
          variant="primary" 
          fullWidth 
          size="lg" 
          disabled={cart.length === 0}
          className="text-lg font-bold"
        >
          Cobrar Orden
        </Button>
      </div>
    </Card>
  );
}
