import React from 'react';
import { motion } from 'framer-motion';

export function Card({ children, className = '', hoverable = false, onClick, ...props }) {
  const base = "bg-white rounded-2xl border border-surface-200 shadow-volt overflow-hidden";
  const hoverStyle = hoverable ? "transition-all cursor-pointer hover:shadow-volt-hover hover:border-brand-light" : "";
  
  const Comp = hoverable ? motion.div : 'div';
  const animationProps = hoverable ? { whileHover: { y: -2 } } : {};

  return (
    <Comp
      className={`${base} ${hoverStyle} ${className}`}
      onClick={onClick}
      {...animationProps}
      {...props}
    >
      {children}
    </Comp>
  );
}
