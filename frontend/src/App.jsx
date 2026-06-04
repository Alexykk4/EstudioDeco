import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { PosDashboard } from './components/pos/PosDashboard';
import { DashboardView } from './components/dashboard/DashboardView';

// Mock components para rutas no implementadas aún
const Placeholder = ({ title }) => (
  <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
    <h1 className="text-2xl text-text-muted">{title}</h1>
  </div>
);

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout><PosDashboard /></MainLayout>} />
        <Route path="/ventas" element={<MainLayout><DashboardView /></MainLayout>} />
        <Route path="/gastos" element={<MainLayout><Placeholder title="Cortes y Gastos" /></MainLayout>} />
        <Route path="/estacion" element={<MainLayout><Placeholder title="Estación 304" /></MainLayout>} />
        <Route path="/catalogo" element={<MainLayout><Placeholder title="Catálogo CRUD" /></MainLayout>} />
        <Route path="/configuracion" element={<MainLayout><Placeholder title="Configuración" /></MainLayout>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
