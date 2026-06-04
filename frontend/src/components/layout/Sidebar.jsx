import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutGrid, TrendingUp, Wallet, Settings, LogOut, Package, Coffee } from 'lucide-react';
import { usePosStore } from '../../store';

export function Sidebar() {
  const user = usePosStore(state => state.user);

  const navItems = [
    { to: '/', icon: LayoutGrid, label: 'Mesas' },
    { to: '/ventas', icon: TrendingUp, label: 'Ventas del Día' },
    { to: '/gastos', icon: Wallet, label: 'Cortes y Gastos' },
    { to: '/estacion', icon: Coffee, label: 'Estación 304' },
  ];

  if (user?.role === 'Administrador') {
    navItems.push(
      { to: '/catalogo', icon: Package, label: 'Catálogo' },
      { to: '/configuracion', icon: Settings, label: 'Configuración' }
    );
  }

  return (
    <aside className="w-64 bg-white border-r border-surface-200 flex flex-col h-screen fixed left-0 top-0">
      <div className="p-6">
        <h1 className="text-xl font-bold text-brand flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center text-white">
            E
          </div>
          Estudio Deco
        </h1>
      </div>

      <nav className="flex-1 px-4 space-y-1 mt-6">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium transition-colors ${
                isActive 
                  ? 'bg-brand-light text-brand-dark' 
                  : 'text-text-muted hover:bg-surface-50 hover:text-text-main'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-surface-200">
        <div className="flex items-center gap-3 px-3 py-3 rounded-xl bg-surface-50 mb-4">
          <div className="w-8 h-8 rounded-full bg-brand-light flex items-center justify-center text-brand-dark font-bold">
            {user?.name?.charAt(0) || 'U'}
          </div>
          <div>
            <p className="text-sm font-semibold text-text-main">{user?.name || 'Usuario'}</p>
            <p className="text-xs text-text-muted">{user?.role || 'Cajero'}</p>
          </div>
        </div>
        <button 
          onClick={() => usePosStore.getState().setUser(null)}
          className="flex w-full items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-danger hover:bg-danger-light transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Cerrar Sesión
        </button>
      </div>
    </aside>
  );
}
