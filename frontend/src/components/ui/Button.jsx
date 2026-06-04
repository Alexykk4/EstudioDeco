import React from 'react';
import { motion } from 'framer-motion';

export function Button({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  className = '', 
  onClick, 
  disabled = false,
  fullWidth = false,
  ...props 
}) {
  const baseStyle = "inline-flex items-center justify-center font-medium rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variants = {
    primary: "bg-brand text-white hover:bg-brand-dark focus:ring-brand shadow-volt hover:shadow-volt-hover",
    secondary: "bg-brand-light text-brand-dark hover:bg-brand/20 focus:ring-brand",
    outline: "border-2 border-surface-200 bg-white text-text-main hover:border-brand hover:text-brand focus:ring-brand",
    ghost: "bg-transparent text-text-muted hover:bg-surface-50 hover:text-text-main focus:ring-surface-200",
    danger: "bg-danger text-white hover:bg-danger/90 focus:ring-danger shadow-volt hover:shadow-volt-hover",
    success: "bg-success text-white hover:bg-success/90 focus:ring-success shadow-volt hover:shadow-volt-hover",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base",
  };

  const classes = `${baseStyle} ${variants[variant]} ${sizes[size]} ${fullWidth ? 'w-full' : ''} ${className}`;

  return (
    <motion.button
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      className={classes}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      {children}
    </motion.button>
  );
}
