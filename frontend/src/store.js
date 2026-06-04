import { create } from 'zustand';

export const usePosStore = create((set, get) => ({
  // User Session
  user: { name: 'Admin', role: 'Administrador' }, // Mock para dev
  setUser: (user) => set({ user }),

  // Tables State
  tables: [],
  isLoadingTables: false,
  fetchTables: async () => {
    set({ isLoadingTables: true });
    try {
      const res = await fetch('/api/mesas');
      const data = await res.json();
      
      const mappedTables = data.map(m => ({
        id: m.id,
        name: m.nombre,
        status: m.estado,
        orderId: m.orden_id,
        total: m.total || 0
      }));
      
      set({ tables: mappedTables, isLoadingTables: false });
    } catch (e) {
      console.error("Error fetching tables", e);
      set({ isLoadingTables: false });
    }
  },

  // Products State
  products: [],
  fetchProducts: async () => {
    try {
      const res = await fetch('/api/catalog');
      const data = await res.json();
      set({ products: data });
    } catch (e) {
      console.error("Error fetching products", e);
    }
  },

  setTableStatus: (id, status, orderId = null) => set((state) => ({
    tables: state.tables.map(t => t.id === id ? { ...t, status, orderId } : t)
  })),

  // Active Order State
  activeTableId: null,
  setActiveTable: (id) => set({ activeTableId: id }),
  
  cart: [],
  addToCart: (product) => set((state) => {
    const existing = state.cart.find(item => item.id === product.id);
    if (existing) {
      return { cart: state.cart.map(item => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item) };
    }
    return { cart: [...state.cart, { ...product, quantity: 1 }] };
  }),
  removeFromCart: (productId) => set((state) => ({
    cart: state.cart.filter(item => item.id !== productId)
  })),
  updateQuantity: (productId, quantity) => set((state) => ({
    cart: state.cart.map(item => item.id === productId ? { ...item, quantity } : item)
  })),
  clearCart: () => set({ cart: [], activeTableId: null }),

  getCartTotal: () => {
    return get().cart.reduce((total, item) => total + (item.precio * item.quantity), 0);
  }
}));

