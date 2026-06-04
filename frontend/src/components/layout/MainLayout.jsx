import React from 'react';
import { Sidebar } from './Sidebar';

export function MainLayout({ children }) {
  return (
    <div className="min-h-screen bg-surface-50 flex">
      <Sidebar />
      <main className="flex-1 ml-64 p-6 h-screen overflow-hidden">
        <div className="w-full h-full">
          {children}
        </div>
      </main>
    </div>
  );
}
