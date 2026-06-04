import React from 'react';

export function Badge({ children, variant = 'default', className = '' }) {
  const variants = {
    default: "bg-surface-200 text-text-main",
    success: "bg-success-light text-success",
    danger: "bg-danger-light text-danger",
    primary: "bg-brand-light text-brand-dark",
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}
