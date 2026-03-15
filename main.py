"""
main.py
Aplicación principal del POS Estudio Deco.
CustomTkinter con diseño Soft UI / Pastel.
"""

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image
from pathlib import Path
from datetime import datetime

from modules.database import (
    init_db, listar_tiendas, obtener_productos, validar_nip,
    registrar_venta, registrar_gasto, obtener_resumen_dia,
    registrar_corte, obtener_stock,
    registrar_ingreso, set_fondo_apertura, get_fondo_apertura,
    obtener_ventas_turno,
)
from modules.printer import imprimir_ticket, preview_ticket_text
from modules.pdf_report import generar_corte_pdf
from modules.email_sender import enviar_corte_email
from modules.sync_sheets import sync_worker

# ──────────────────────────────────────────────
#  CONSTANTES DE DISEÑO (con buen contraste)
# ──────────────────────────────────────────────
AZUL_PASTEL    = "#7986CB"   # indigo pastel
MORADO_PASTEL  = "#7E57C2"   # morado pastel principal
ROSA_PASTEL    = "#BA68C8"   # orquidea pastel
FONDO          = "#EDE7F6"   # lavanda suave
FONDO_CARD     = "#FDFBFF"   # blanco con tinte lavanda
TEXTO          = "#212121"
TEXTO_CLARO    = "#7B6B9A"   # morado grisaceo
TEXTO_BLANCO   = "#FFFFFF"
ROJO_ALERTA    = "#E57373"   # rojo pastel
VERDE          = "#81C784"   # verde pastel
AMARILLO_STOCK = "#FFD54F"   # ambar pastel

LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"
WINDOW_W = 1280
WINDOW_H = 780


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── Configuración de ventana ──
        self.title("✦ Estudio Deco – Punto de Venta")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.configure(fg_color=FONDO)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # ── Estado ──
        self.usuario_actual = None          # {id, nombre, perfil}
        self.carrito: list[dict] = []       # items en el carrito
        self.tiendas = []
        self.propina_activa = ctk.BooleanVar(value=False)
        self.propina_opcion = ctk.StringVar(value="10%")
        self.propina_custom_var = ctk.StringVar(value="")

        # ── Inicializar BD ──
        init_db()
        self.tiendas = listar_tiendas()

        # ── Construir GUI ──
        self._build_header()
        self._build_body()
        self._build_cart_panel()

        # ── Sync en background ──
        sync_worker.start()

    # ══════════════════════════════════════════
    #  HEADER (logo + info usuario)
    # ══════════════════════════════════════════
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=FONDO_CARD, corner_radius=0, height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Logo
        if LOGO_PATH.exists():
            logo_img = ctk.CTkImage(
                light_image=Image.open(LOGO_PATH),
                size=(50, 50),
            )
            ctk.CTkLabel(header, image=logo_img, text="").pack(side="left", padx=15)

        ctk.CTkLabel(
            header, text="Estudio Deco",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            header, text="Punto de Venta",
            font=ctk.CTkFont(size=13),
            text_color=TEXTO_CLARO,
        ).pack(side="left")

        # Botones derecha
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=15)

        self.lbl_usuario = ctk.CTkLabel(
            btn_frame, text="Sin usuario",
            font=ctk.CTkFont(size=12), text_color=TEXTO_CLARO,
        )
        self.lbl_usuario.pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="🔑 Cambiar usuario", width=140,
            fg_color=MORADO_PASTEL, hover_color="#7E57C2",
            text_color=TEXTO_BLANCO,
            command=self._pedir_nip,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="🏦 Abrir Caja", width=110,
            fg_color=VERDE, hover_color="#66BB6A",
            text_color=TEXTO_BLANCO,
            command=self._abrir_caja_modal,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="💰 Ingreso", width=100,
            fg_color="#26A69A", hover_color="#00897B",
            text_color=TEXTO_BLANCO,
            command=self._registrar_ingreso_modal,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="📊 Corte de Caja", width=130,
            fg_color=AZUL_PASTEL, hover_color="#5C6BC0",
            text_color=TEXTO_BLANCO,
            command=self._hacer_corte,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="💸 Registrar Gasto", width=130,
            fg_color=ROSA_PASTEL, hover_color="#AB47BC",
            text_color=TEXTO_BLANCO,
            command=self._registrar_gasto_modal,
        ).pack(side="left", padx=5)

    # ══════════════════════════════════════════
    #  BODY (pestañas de tiendas)
    # ══════════════════════════════════════════
    def _build_body(self):
        self.body = ctk.CTkFrame(self, fg_color=FONDO)
        self.body.pack(fill="both", expand=True, side="left", padx=(10, 0), pady=10)

        self.tabview = ctk.CTkTabview(
            self.body,
            fg_color=FONDO_CARD,
            segmented_button_fg_color=AZUL_PASTEL,
            segmented_button_selected_color=MORADO_PASTEL,
            segmented_button_selected_hover_color="#7E57C2",
            segmented_button_unselected_color=AZUL_PASTEL,
            segmented_button_unselected_hover_color="#B39DDB",
            corner_radius=15,
        )
        self.tabview.pack(fill="both", expand=True)

        for tienda in self.tiendas:
            tab = self.tabview.add(tienda["nombre"])
            if tienda["precio_abierto"]:
                self._build_mack_tab(tab, tienda)
            else:
                self._build_product_grid(tab, tienda)

    def _build_product_grid(self, parent, tienda: dict):
        """Cuadrícula de productos para una tienda normal."""
        # Frame con scroll
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        productos = obtener_productos(tienda["id"])
        if not productos:
            ctk.CTkLabel(
                scroll, text="No hay productos cargados aún.",
                font=ctk.CTkFont(size=14), text_color=TEXTO_CLARO,
            ).pack(pady=40)
            return

        # Agrupar por categoría
        from collections import defaultdict
        categorias = defaultdict(list)
        for p in productos:
            cat = p.get("categoria_producto")
            cat_name = cat.strip().capitalize() if cat and cat.strip() else "Otros"
            categorias[cat_name].append(p)

        colors_by_cat = {
            "Bebidas": "#E8EAF6",   # indigo claro
            "Extras": "#FCE4EC",    # rosa claro
            "Roles": "#FFF3E0",     # naranja claro
            "Talleres": "#E0F7FA",  # cyan claro
            "Individuales": "#F1F8E9" # verde claro
        }

        for cat_name, prods in categorias.items():
            # Header de Categoría
            ctk.CTkLabel(
                scroll, text=cat_name,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=MORADO_PASTEL
            ).pack(anchor="w", padx=10, pady=(15, 5))
            
            # Contenedor de la categoría
            bg_color = colors_by_cat.get(cat_name, "transparent")
            cat_frame = ctk.CTkFrame(scroll, fg_color=bg_color, corner_radius=10)
            cat_frame.pack(fill="x", padx=5, pady=5)
            
            # Grid layout for this category
            for i in range(4):
                cat_frame.grid_columnconfigure(i, weight=1)

            for i, prod in enumerate(prods):
                row = i // 4
                col = i % 4

                es_abierto = bool(prod.get("es_precio_abierto"))

                card = ctk.CTkFrame(cat_frame, fg_color=FONDO_CARD, corner_radius=12, width=180, height=110)
                card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
                card.grid_propagate(False)

                stock = prod["stock_local"]
                stock_min = prod["stock_minimo"]
                agotado = (stock <= 0) and not es_abierto

                # Nombre
                ctk.CTkLabel(
                    card, text=prod["nombre"][:20],
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=TEXTO,
                    wraplength=160,
                ).pack(pady=(8, 2))

                # Precio
                precio_txt = "Precio libre" if es_abierto else f"${prod['precio']:.2f}"
                ctk.CTkLabel(
                    card, text=precio_txt,
                    font=ctk.CTkFont(size=12),
                    text_color=MORADO_PASTEL,
                ).pack()

                # Stock badge (solo para productos normales)
                if not es_abierto:
                    if agotado:
                        badge_color = ROJO_ALERTA
                        badge_text = "AGOTADO"
                        badge_text_color = TEXTO_BLANCO
                    elif stock <= stock_min:
                        badge_color = AMARILLO_STOCK
                        badge_text = f"⚠ Stock: {stock}"
                        badge_text_color = TEXTO
                    else:
                        badge_color = VERDE
                        badge_text = f"Stock: {stock}"
                        badge_text_color = TEXTO_BLANCO

                    ctk.CTkLabel(
                        card, text=badge_text,
                        font=ctk.CTkFont(size=10),
                        fg_color=badge_color, corner_radius=8,
                        text_color=badge_text_color,
                    ).pack(pady=2)

                # Botón agregar
                if es_abierto:
                    cmd = lambda p=prod, t=tienda: self._modal_precio_abierto(t, nombre_sugerido=p["nombre"])
                else:
                    cmd = lambda p=prod, t=tienda: self._agregar_al_carrito(p, t)

                btn = ctk.CTkButton(
                    card, text="+ Agregar", height=28,
                    fg_color=MORADO_PASTEL if not agotado else "#CCCCCC",
                    hover_color="#7E57C2" if not agotado else "#CCCCCC",
                    text_color=TEXTO_BLANCO,
                    font=ctk.CTkFont(size=11),
                    command=cmd,
                    state="normal" if not agotado else "disabled",
                )
                btn.pack(pady=(2, 6))


    def _build_mack_tab(self, parent, tienda: dict):
        """Tab especial para Mack: botón de precio abierto."""
        center = ctk.CTkFrame(parent, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            center, text="🛍️ Tienda Mack",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            center, text="Precio abierto – teclea el monto a cobrar",
            font=ctk.CTkFont(size=13), text_color=TEXTO_CLARO,
        ).pack(pady=(0, 20))

        ctk.CTkButton(
            center, text="＄ Agregar Venta Mack",
            width=260, height=55, corner_radius=15,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=MORADO_PASTEL, hover_color="#7E57C2",
            text_color=TEXTO_BLANCO,
            command=lambda t=tienda: self._modal_precio_abierto(t),
        ).pack()

    # ══════════════════════════════════════════
    #  CARRITO (panel derecho)
    # ══════════════════════════════════════════
    def _build_cart_panel(self):
        self.cart_panel = ctk.CTkFrame(self, fg_color=FONDO_CARD, width=355, corner_radius=15)
        self.cart_panel.pack(fill="y", side="right", padx=10, pady=10)
        self.cart_panel.pack_propagate(False)

        ctk.CTkLabel(
            self.cart_panel, text="🛒 Ticket Virtual",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(15, 5))

        # Lista de items
        self.cart_scroll = ctk.CTkScrollableFrame(
            self.cart_panel, fg_color="transparent",
        )
        self.cart_scroll.pack(fill="both", expand=True, padx=8, pady=5)

        # ── Subtotal + Propina + Total ──
        totales_frame = ctk.CTkFrame(self.cart_panel, fg_color=FONDO, corner_radius=10)
        totales_frame.pack(fill="x", padx=10, pady=(2, 0))

        sub_row = ctk.CTkFrame(totales_frame, fg_color="transparent")
        sub_row.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(sub_row, text="Subtotal:", font=ctk.CTkFont(size=12),
                     text_color=TEXTO_CLARO).pack(side="left")
        self.lbl_subtotal = ctk.CTkLabel(sub_row, text="$0.00",
                                          font=ctk.CTkFont(size=12), text_color=TEXTO_CLARO)
        self.lbl_subtotal.pack(side="right")

        prop_row = ctk.CTkFrame(totales_frame, fg_color="transparent")
        prop_row.pack(fill="x", padx=10, pady=0)
        ctk.CTkLabel(prop_row, text="Propina:", font=ctk.CTkFont(size=12),
                     text_color=TEXTO_CLARO).pack(side="left")
        self.lbl_propina_monto = ctk.CTkLabel(prop_row, text="$0.00",
                                               font=ctk.CTkFont(size=12), text_color=VERDE)
        self.lbl_propina_monto.pack(side="right")

        self.lbl_total = ctk.CTkLabel(
            self.cart_panel, text="Total: $0.00",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=MORADO_PASTEL,
        )
        self.lbl_total.pack(pady=(4, 2))

        # ── Sección de propina ──
        prop_frame = ctk.CTkFrame(self.cart_panel, fg_color=FONDO, corner_radius=10)
        prop_frame.pack(fill="x", padx=10, pady=(0, 4))

        check_row = ctk.CTkFrame(prop_frame, fg_color="transparent")
        check_row.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkCheckBox(
            check_row, text="🪙 Agregar propina",
            variable=self.propina_activa,
            fg_color=VERDE, hover_color="#66BB6A",
            font=ctk.CTkFont(size=12),
            command=self._toggle_propina,
        ).pack(side="left")

        self.propina_controls = ctk.CTkFrame(prop_frame, fg_color="transparent")
        self.propina_controls.pack(fill="x", padx=8, pady=(0, 6))

        self.combo_propina = ctk.CTkComboBox(
            self.propina_controls,
            values=["10%", "15%", "20%", "Personalizada"],
            variable=self.propina_opcion,
            width=130,
            font=ctk.CTkFont(size=12),
            command=lambda _: self._refrescar_carrito(),
        )
        self.combo_propina.pack(side="left", padx=(0, 6))

        self.entry_propina_custom = ctk.CTkEntry(
            self.propina_controls,
            textvariable=self.propina_custom_var,
            placeholder_text="$ monto",
            width=100,
            font=ctk.CTkFont(size=12),
        )
        self.entry_propina_custom.pack(side="left")
        self.entry_propina_custom.bind("<KeyRelease>", lambda e: self._refrescar_carrito())
        # Start hidden
        self.propina_controls.pack_forget()

        # Método de pago
        self.metodo_var = ctk.StringVar(value="Efectivo")
        metodo_frame = ctk.CTkFrame(self.cart_panel, fg_color="transparent")
        metodo_frame.pack(pady=4)
        for m in ["Efectivo", "Tarjeta", "Transferencia", "Mixto"]:
            ctk.CTkRadioButton(
                metodo_frame, text=m, variable=self.metodo_var, value=m,
                fg_color=MORADO_PASTEL, hover_color="#7E57C2",
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=6)

        # Botones
        btn_frame = ctk.CTkFrame(self.cart_panel, fg_color="transparent")
        btn_frame.pack(pady=(4, 12))

        ctk.CTkButton(
            btn_frame, text="🗑 Vaciar", width=100,
            fg_color=ROJO_ALERTA, hover_color="#EF5350",
            text_color=TEXTO_BLANCO,
            command=self._vaciar_carrito,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="💵 Cobrar", width=160,
            fg_color=VERDE, hover_color="#66BB6A",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXTO_BLANCO,
            command=self._cobrar,
        ).pack(side="left", padx=5)

    def _calcular_propina(self, subtotal: float) -> float:
        """Calcula el monto de propina según la opción seleccionada."""
        if not self.propina_activa.get():
            return 0.0
        opt = self.propina_opcion.get()
        if opt == "10%":
            return round(subtotal * 0.10, 2)
        elif opt == "15%":
            return round(subtotal * 0.15, 2)
        elif opt == "20%":
            return round(subtotal * 0.20, 2)
        elif opt == "Personalizada":
            try:
                return max(0.0, float(self.propina_custom_var.get()))
            except ValueError:
                return 0.0
        return 0.0

    def _toggle_propina(self):
        """Muestra u oculta controles de propina."""
        if self.propina_activa.get():
            self.propina_controls.pack(fill="x", padx=8, pady=(0, 6))
        else:
            self.propina_controls.pack_forget()
        self._refrescar_carrito()

    def _refrescar_carrito(self):
        """Redibuja la lista del carrito."""
        for w in self.cart_scroll.winfo_children():
            w.destroy()

        for idx, item in enumerate(self.carrito):
            row = ctk.CTkFrame(self.cart_scroll, fg_color=FONDO, corner_radius=8)
            row.pack(fill="x", pady=3, padx=2)

            nombre_lbl = item["nombre"][:20]
            ctk.CTkLabel(
                row, text=nombre_lbl,
                font=ctk.CTkFont(size=12),
                text_color=TEXTO,
            ).pack(side="left", padx=8, pady=6)

            precio_final = item["precio_unitario"]
            descuento_pct = item.get("descuento_pct", 0.0)
            precio_original = item.get("precio_original", precio_final)

            sub = item["cantidad"] * precio_final
            sub_text = f"x{item['cantidad']}  ${sub:,.2f}"
            if descuento_pct > 0:
                sub_text += f"  (-{descuento_pct:.0f}%)"

            ctk.CTkLabel(
                row, text=sub_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=VERDE if descuento_pct > 0 else MORADO_PASTEL,
            ).pack(side="right", padx=(0, 4), pady=6)

            ctk.CTkButton(
                row, text="✕", width=26, height=26,
                fg_color=ROJO_ALERTA, hover_color="#EF5350",
                text_color=TEXTO_BLANCO,
                font=ctk.CTkFont(size=10),
                command=lambda i=idx: self._quitar_del_carrito(i),
            ).pack(side="right", padx=2, pady=4)

            ctk.CTkButton(
                row, text="✏", width=26, height=26,
                fg_color=AZUL_PASTEL, hover_color="#5C6BC0",
                text_color=TEXTO_BLANCO,
                font=ctk.CTkFont(size=11),
                command=lambda i=idx: self._modal_editar_item(i),
            ).pack(side="right", padx=2, pady=4)

        subtotal = sum(i["cantidad"] * i["precio_unitario"] for i in self.carrito)
        propina = self._calcular_propina(subtotal)
        total = subtotal + propina

        self.lbl_subtotal.configure(text=f"${subtotal:,.2f}")
        self.lbl_propina_monto.configure(
            text=f"${propina:,.2f}" if propina > 0 else "$0.00"
        )
        self.lbl_total.configure(text=f"Total: ${total:,.2f}")

    # ══════════════════════════════════════════
    #  ACCIONES DEL CARRITO
    # ══════════════════════════════════════════
    def _agregar_al_carrito(self, producto: dict, tienda: dict):
        # Verificar stock actualizado
        stock = obtener_stock(producto["id"])
        if stock <= 0:
            messagebox.showwarning("Agotado", f"'{producto['nombre']}' está agotado.")
            return

        if stock <= producto.get("stock_minimo", 5):
            messagebox.showinfo(
                "Stock bajo",
                f"⚠ '{producto['nombre']}' tiene solo {stock} unidades.",
            )

        # Buscar la cantidad total en carrito para no exceder stock
        en_carrito = sum(1 for i in self.carrito if i.get("producto_id") == producto["id"])
        if en_carrito + 1 > stock:
            messagebox.showwarning("Sin stock", "No hay suficiente stock.")
            return

        nombre_final = producto["nombre"]
        categoria = producto.get("categoria_producto", "").strip().capitalize()
        if tienda["id"] == 1 and categoria != "Extras" and "(Frío)" not in nombre_final and "(Caliente)" not in nombre_final:
            nombre_final += " (Frío)"

        self.carrito.append({
            "producto_id": producto["id"],
            "tienda_id": tienda["id"],
            "nombre": nombre_final,
            "cantidad": 1,
            "precio_unitario": producto["precio"],
            "es_precio_abierto": False,
            "categoria_producto": categoria
        })
        self._refrescar_carrito()
        
        # Auto-abrir modal para personalizar al agregar a carrito
        self._modal_editar_item(len(self.carrito) - 1)

    def _quitar_del_carrito(self, idx: int):
        if 0 <= idx < len(self.carrito):
            self.carrito.pop(idx)
            self._refrescar_carrito()

    def _modal_editar_item(self, idx: int):
        """Modal para editar nombre, precio y descuento de un item del carrito."""
        item = self.carrito[idx]
        modal = ctk.CTkToplevel(self)
        modal.title("Editar artículo")
        modal.geometry("380x320")
        modal.configure(fg_color=FONDO)
        modal.grab_set()
        modal.resizable(False, False)

        ctk.CTkLabel(
            modal, text="✏ Editar artículo",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(20, 10))

        nombre_actual = item.get("nombre", "")
        clean_nombre = nombre_actual.replace(" (Frío)", "").replace(" (Caliente)", "")
        is_c = "(Caliente)" in nombre_actual
        is_f = "(Frío)" in nombre_actual
        tienda_id = item.get("tienda_id")
        
        parts = clean_nombre.split(" - ", 1)
        base_nombre = parts[0].strip()
        cliente_nombre = parts[1].strip() if len(parts) > 1 else ""

        ctk.CTkLabel(modal, text="Descripción:", text_color=TEXTO, anchor="w").pack(anchor="w", padx=50)
        entry_nombre = ctk.CTkEntry(modal, width=280)
        entry_nombre.insert(0, base_nombre)
        entry_nombre.configure(state="disabled")
        entry_nombre.pack(pady=(2, 8))

        label_cliente = "Nombre en vaso / Cliente:" if tienda_id == 1 else "Nota / Cliente:"
        ctk.CTkLabel(modal, text=label_cliente, text_color=TEXTO, anchor="w").pack(anchor="w", padx=50)
        entry_cliente = ctk.CTkEntry(modal, width=280)
        entry_cliente.insert(0, cliente_nombre)
        entry_cliente.pack(pady=(2, 8))

        combo_temp = None
        categoria = item.get("categoria_producto", "")
        if tienda_id == 1 and categoria != "Extras":
            ctk.CTkLabel(modal, text="Temperatura:", text_color=TEXTO, anchor="w").pack(anchor="w", padx=50)
            combo_temp = ctk.CTkComboBox(modal, values=[" (Frío)", " (Caliente)", ""])
            if is_c:
                combo_temp.set(" (Caliente)")
            elif not is_f and not is_c:
                combo_temp.set(" (Frío)") # Default a Frío, indicado por el usuario
            elif is_f:
                combo_temp.set(" (Frío)")
            else:
                combo_temp.set("")
            combo_temp.pack(pady=(2, 8))

        # Selector de Extras (solo para tienda 1)
        combo_extras = None
        extra_map = {}
        if tienda_id == 1:
            todos_productos = obtener_productos(1)
            lista_extras = [p for p in todos_productos if p.get("categoria_producto", "").strip().lower() == "extras" and p.get("stock_local", 0) > 0]
            if lista_extras:
                ctk.CTkLabel(modal, text="Agregar Extra:", text_color=TEXTO, anchor="w").pack(anchor="w", padx=50)
                nombres_extras = ["Ninguno"]
                for p in lista_extras:
                    nom = f"{p['nombre']} (+${p['precio']})"
                    nombres_extras.append(nom)
                    extra_map[nom] = p
                combo_extras = ctk.CTkComboBox(modal, values=nombres_extras)
                combo_extras.set("Ninguno")
                combo_extras.pack(pady=(2, 8))

        precio_orig = item.get("precio_original", item["precio_unitario"])
        ctk.CTkLabel(modal, text=f"Precio unitario (original: ${precio_orig:,.2f}):",
                     text_color=TEXTO, anchor="w").pack(anchor="w", padx=50)
        entry_precio = ctk.CTkEntry(modal, width=280)
        entry_precio.insert(0, str(precio_orig))
        entry_precio.pack(pady=(2, 8))

        ctk.CTkLabel(modal, text="Descuento %  (0 = sin descuento):",
                     text_color=TEXTO, anchor="w").pack(anchor="w", padx=50)
        entry_desc = ctk.CTkEntry(modal, width=280, placeholder_text="Ej: 10")
        entry_desc.insert(0, str(item.get("descuento_pct", 0)))
        entry_desc.pack(pady=(2, 8))

        def guardar():
            try:
                nuevo_precio_base = float(entry_precio.get().replace(",", ""))
                if nuevo_precio_base < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Precio inválido.", parent=modal)
                return
            try:
                descuento = float(entry_desc.get() or "0")
                if not (0 <= descuento <= 100):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Descuento debe ser entre 0 y 100.", parent=modal)
                return
            
            nuevo_cliente = entry_cliente.get().strip()
            nuevo_nombre = base_nombre + (f" - {nuevo_cliente}" if nuevo_cliente else "")
            temp_val = combo_temp.get() if combo_temp else ""
            precio_final = round(nuevo_precio_base * (1 - descuento / 100), 2)

            self.carrito[idx]["nombre"] = nuevo_nombre + temp_val
            self.carrito[idx]["precio_original"] = nuevo_precio_base
            self.carrito[idx]["precio_unitario"] = precio_final
            self.carrito[idx]["descuento_pct"] = descuento
            
            # Verificar si seleccionó un Extra
            if combo_extras and combo_extras.get() != "Ninguno" and combo_extras.get() in extra_map:
                p_extra = extra_map[combo_extras.get()]
                self.carrito.append({
                    "producto_id": p_extra["id"],
                    "tienda_id": 1,
                    "nombre": f"+ {p_extra['nombre']}",
                    "cantidad": 1,
                    "precio_unitario": p_extra["precio"],
                    "es_precio_abierto": False,
                    "categoria_producto": "Extras"
                })

            self._refrescar_carrito()
            modal.destroy()

        ctk.CTkButton(
            modal, text="✓ Guardar cambios", width=200,
            fg_color=MORADO_PASTEL, hover_color="#7E57C2",
            text_color=TEXTO_BLANCO,
            command=guardar,
        ).pack(pady=10)

    def _vaciar_carrito(self):
        if self.carrito:
            if messagebox.askyesno("Confirmar", "¿Vaciar todo el carrito?"):
                self.carrito.clear()
                self.propina_activa.set(False)
                self._toggle_propina()
                self._refrescar_carrito()

    # ══════════════════════════════════════════
    #  MODAL: PRECIO ABIERTO (MACK)
    # ══════════════════════════════════════════
    def _modal_precio_abierto(self, tienda: dict, nombre_sugerido: str = ""):
        modal = ctk.CTkToplevel(self)
        modal.title("Precio Abierto")
        modal.geometry("380x260")
        modal.configure(fg_color=FONDO)
        modal.grab_set()
        modal.resizable(False, False)

        ctk.CTkLabel(
            modal, text="Ingresa el monto a cobrar",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(25, 5))

        ctk.CTkLabel(
            modal, text="(Descripción del artículo)",
            font=ctk.CTkFont(size=11), text_color=TEXTO_CLARO,
        ).pack()

        entry_desc = ctk.CTkEntry(modal, width=280, placeholder_text="Ej: Bolsa de mano azul")
        if nombre_sugerido:
            entry_desc.insert(0, nombre_sugerido)
        entry_desc.pack(pady=8)

        entry_monto = ctk.CTkEntry(
            modal, width=280, placeholder_text="$ Monto",
            font=ctk.CTkFont(size=16),
        )
        entry_monto.pack(pady=5)

        def confirmar():
            try:
                monto = float(entry_monto.get())
                if monto <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Ingresa un monto válido.", parent=modal)
                return

            desc = entry_desc.get().strip() or nombre_sugerido or "Artículo"
            self.carrito.append({
                "producto_id": None,
                "tienda_id": tienda["id"],
                "nombre": desc,
                "cantidad": 1,
                "precio_unitario": monto,
                "es_precio_abierto": True,
            })
            self._refrescar_carrito()
            modal.destroy()

        ctk.CTkButton(
            modal, text="✓ Agregar al carrito", width=200,
            fg_color=MORADO_PASTEL, hover_color="#7E57C2",
            text_color=TEXTO_BLANCO,
            command=confirmar,
        ).pack(pady=15)


    # ══════════════════════════════════════════
    #  SEGURIDAD: NIP
    # ══════════════════════════════════════════
    def _pedir_nip(self, callback=None):
        """Modal que pide NIP de 4 dígitos."""
        modal = ctk.CTkToplevel(self)
        modal.title("Autenticación")
        modal.geometry("360x250")
        modal.configure(fg_color=FONDO_CARD)
        modal.resizable(False, False)
        modal.transient(self)

        ctk.CTkLabel(
            modal, text="🔑 Ingresa tu NIP",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(30, 10))

        entry_nip = ctk.CTkEntry(
            modal, width=220, height=45, show="●",
            font=ctk.CTkFont(size=22), justify="center",
            placeholder_text="● ● ● ●",
            border_color=MORADO_PASTEL,
            border_width=2,
        )
        entry_nip.pack(pady=10)

        lbl_error = ctk.CTkLabel(modal, text="", text_color=ROJO_ALERTA,
                                  font=ctk.CTkFont(size=12, weight="bold"))
        lbl_error.pack()

        def validar(event=None):
            nip = entry_nip.get().strip()
            if len(nip) != 4 or not nip.isdigit():
                lbl_error.configure(text="⚠ El NIP debe ser de 4 dígitos")
                return

            usuario = validar_nip(nip)
            if usuario:
                self.usuario_actual = usuario
                self.lbl_usuario.configure(
                    text=f"👤 {usuario['nombre']} ({usuario['perfil']})",
                    text_color=MORADO_PASTEL,
                )
                modal.destroy()
                if callback:
                    self.after(100, callback)
            else:
                lbl_error.configure(text="❌ NIP incorrecto")
                entry_nip.delete(0, "end")

        entry_nip.bind("<Return>", validar)

        ctk.CTkButton(
            modal, text="Validar", width=180, height=38,
            fg_color=MORADO_PASTEL, hover_color="#7E57C2",
            text_color=TEXTO_BLANCO,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=validar,
        ).pack(pady=12)

        # Forzar foco DESPUÉS de que el modal esté visible
        modal.after(200, lambda: modal.lift())
        modal.after(300, lambda: modal.grab_set())
        modal.after(400, lambda: entry_nip.focus_force())

    # ══════════════════════════════════════════
    #  COBRAR
    # ══════════════════════════════════════════
    def _cobrar(self):
        if not self.carrito:
            messagebox.showinfo("Carrito vacío", "Agrega productos antes de cobrar.")
            return

        # Verificar que haya usuario autenticado
        if not self.usuario_actual:
            self._pedir_nip(callback=self._procesar_cobro)
            return

        self._procesar_cobro()

    def _procesar_cobro(self):
        if not self.usuario_actual:
            return

        try:
            items_venta = list(self.carrito)

            # Agregar propina como ítem si aplica
            subtotal = sum(i["cantidad"] * i["precio_unitario"] for i in items_venta)
            propina_monto = self._calcular_propina(subtotal)
            if propina_monto > 0:
                tienda_id_ref = items_venta[0]["tienda_id"] if items_venta else 1
                items_venta.append({
                    "producto_id": None,
                    "tienda_id": tienda_id_ref,
                    "nombre": f"Propina ({self.propina_opcion.get()})",
                    "cantidad": 1,
                    "precio_unitario": propina_monto,
                    "es_precio_abierto": True,
                })

            if self.metodo_var.get() == "Mixto":
                self._modal_cobro_mixto(items_venta)
                return
            elif self.metodo_var.get() == "Efectivo":
                self._modal_efectivo_cambio(items_venta)
                return

            venta = registrar_venta(
                usuario_id=self.usuario_actual["id"],
                metodo_pago=self.metodo_var.get(),
                items=items_venta,
                efectivo_recibido=recibido
            )

            # Intentar imprimir
            cajero  = self.usuario_actual["nombre"]
            impreso = imprimir_ticket(venta, cajero)

            # Limpiar carrito, propina y refrescar stock
            self.carrito.clear()
            self.propina_activa.set(False)
            self._toggle_propina()
            self._refrescar_carrito()
            self._refrescar_todas_las_tabs()

            # Mostrar preview del ticket en pantalla
            self._mostrar_preview_ticket(venta, cajero, impreso)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar la venta:\n{e}")

    def _modal_efectivo_cambio(self, items_venta):
        total_a_pagar = sum(i["cantidad"] * i["precio_unitario"] for i in items_venta)

        modal = ctk.CTkToplevel(self)
        modal.title("Cobro en Efectivo")
        modal.geometry("380x350")
        modal.configure(fg_color=FONDO)
        modal.grab_set()
        modal.resizable(False, False)

        ctk.CTkLabel(
            modal, text="💵 Pago en Efectivo",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            modal, text=f"Total a pagar: ${total_a_pagar:,.2f}",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXTO,
        ).pack(pady=(0, 15))

        frame = ctk.CTkFrame(modal, fg_color="transparent")
        frame.pack(pady=5)

        ctk.CTkLabel(frame, text="Efectivo Recibido:", text_color=TEXTO).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        recibido_var = ctk.StringVar(value="")
        entry_recibido = ctk.CTkEntry(frame, textvariable=recibido_var, width=120, font=ctk.CTkFont(size=14))
        entry_recibido.grid(row=0, column=1, padx=10, pady=5)
        
        lbl_cambio = ctk.CTkLabel(modal, text="Cambio: $0.00", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXTO_CLARO)
        lbl_cambio.pack(pady=15)

        def autocalculate(*_):
            try:
                recibido = float(recibido_var.get().replace(",", "") or 0)
                cambio = recibido - total_a_pagar
                if cambio >= 0:
                    lbl_cambio.configure(text=f"Cambio: ${cambio:,.2f}", text_color=VERDE)
                else:
                    lbl_cambio.configure(text=f"Faltan: ${abs(cambio):,.2f}", text_color=ROJO_ALERTA)
            except:
                lbl_cambio.configure(text="Cambio: $0.00", text_color=TEXTO_CLARO)

        recibido_var.trace_add("write", autocalculate)
        entry_recibido.focus()

        def confirmar():
            try:
                recibido = float(recibido_var.get().replace(",", "") or 0)
                if recibido < total_a_pagar:
                    messagebox.showerror("Error", "El efectivo recibido es menor al total.", parent=modal)
                    return
            except Exception:
                messagebox.showerror("Error", "Monto inválido.", parent=modal)
                return

            venta = registrar_venta(
                usuario_id=self.usuario_actual["id"],
                metodo_pago="Efectivo",
                items=items_venta,
            )
            cajero = self.usuario_actual["nombre"]
            impreso = imprimir_ticket(venta, cajero)

            self.carrito.clear()
            self.propina_activa.set(False)
            self._toggle_propina()
            self._refrescar_carrito()
            self._refrescar_todas_las_tabs()

            modal.destroy()
            self._mostrar_preview_ticket(venta, cajero, impreso)

        ctk.CTkButton(
            modal, text="✓ Cobrar", width=180,
            fg_color=VERDE, hover_color="#66BB6A", text_color=TEXTO_BLANCO,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=confirmar,
        ).pack(pady=10)

    def _modal_cobro_mixto(self, items_venta):
        total_a_pagar = sum(i["cantidad"] * i["precio_unitario"] for i in items_venta)

        modal = ctk.CTkToplevel(self)
        modal.title("Pago Mixto")
        modal.geometry("380x320")
        modal.configure(fg_color=FONDO)
        modal.grab_set()
        modal.resizable(False, False)

        ctk.CTkLabel(
            modal, text="⚖️ Pago Mixto",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            modal, text=f"Total a pagar: ${total_a_pagar:,.2f}",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXTO,
        ).pack(pady=(0, 10))

        frame = ctk.CTkFrame(modal, fg_color="transparent")
        frame.pack(pady=5)

        ctk.CTkLabel(frame, text="Efectivo:", text_color=TEXTO).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        efectivo_var = ctk.StringVar(value="")
        entry_efectivo = ctk.CTkEntry(frame, textvariable=efectivo_var, width=120)
        entry_efectivo.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Tarjeta:", text_color=TEXTO).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        tarjeta_var = ctk.StringVar(value=f"{total_a_pagar:.2f}")
        entry_tarjeta = ctk.CTkEntry(frame, textvariable=tarjeta_var, width=120)
        entry_tarjeta.grid(row=1, column=1, padx=10, pady=5)

        def autocalculate(*_):
            try:
                ef = float(efectivo_var.get().replace(",", "") or 0)
                if ef > total_a_pagar: ef = total_a_pagar
                tarjeta_var.set(f"{total_a_pagar - ef:.2f}")
            except:
                pass

        efectivo_var.trace_add("write", autocalculate)

        def confirmar():
            try:
                ef = float(efectivo_var.get().replace(",", "") or 0)
                tar = float(tarjeta_var.get().replace(",", "") or 0)
                if abs((ef + tar) - total_a_pagar) > 0.01:
                    messagebox.showerror("Error", "La suma de efectivo y tarjeta no cuadra con el total.", parent=modal)
                    return
            except Exception:
                messagebox.showerror("Error", "Montos inválidos.", parent=modal)
                return

            venta = registrar_venta(
                usuario_id=self.usuario_actual["id"],
                metodo_pago="Mixto",
                items=items_venta,
                monto_efectivo=ef,
                monto_tarjeta=tar,
            )
            cajero = self.usuario_actual["nombre"]
            impreso = imprimir_ticket(venta, cajero)

            self.carrito.clear()
            self.propina_activa.set(False)
            self._toggle_propina()
            self._refrescar_carrito()
            self._refrescar_todas_las_tabs()

            modal.destroy()
            self._mostrar_preview_ticket(venta, cajero, impreso)

        ctk.CTkButton(
            modal, text="✓ Cobrar", width=180,
            fg_color=VERDE, hover_color="#66BB6A", text_color=TEXTO_BLANCO,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=confirmar,
        ).pack(pady=20)


    def _mostrar_preview_ticket(self, venta: dict, cajero: str, impreso: bool):
        """Modal que muestra el ticket impreso en pantalla con diseño elegante."""
        win = ctk.CTkToplevel(self)
        win.title(f"Ticket {venta['folio']}")
        win.geometry("560x700")
        win.configure(fg_color=FONDO_CARD)
        win.resizable(False, True)
        win.grab_set()
        win.transient(self)

        # ── Chip de estado ────────────────────────────────────────────────────
        estado_color = VERDE if impreso else AMARILLO_STOCK
        estado_texto = "  Ticket enviado a impresora  " if impreso else "  Guardado en sistema — sin impresora fisica  "
        ctk.CTkLabel(
            win, text=estado_texto,
            fg_color=estado_color, corner_radius=8,
            text_color=TEXTO_BLANCO,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(pady=(18, 6), padx=24, fill="x")

        # ── Vista del ticket ──────────────────────────────────────────────────
        txt = ctk.CTkTextbox(
            win,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#FAFAF8",
            text_color="#2D2D2D",
            corner_radius=10,
            border_width=1,
            border_color="#E0E0E8",
            wrap="none",
            activate_scrollbars=True,
        )
        txt.pack(fill="both", expand=True, padx=20, pady=(4, 6))
        txt.insert("1.0", preview_ticket_text(venta, cajero))
        txt.configure(state="disabled")

        # ── Botones ───────────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=(2, 18))

        if not impreso:
            ctk.CTkButton(
                btn_frame, text="Reintentar impresion", width=180,
                fg_color=AZUL_PASTEL, hover_color="#5C6BC0",
                text_color=TEXTO_BLANCO, font=ctk.CTkFont(size=12),
                command=lambda: imprimir_ticket(venta, cajero),
            ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Cerrar", width=140,
            fg_color=MORADO_PASTEL, hover_color="#7E57C2",
            text_color=TEXTO_BLANCO,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=win.destroy,
        ).pack(side="left")

        win.bind("<Escape>", lambda e: win.destroy())
        win.after(150, lambda: win.lift())
        win.after(250, lambda: win.focus_force())

    def _refrescar_todas_las_tabs(self):
        """Reconstruye las grids de productos para reflejar stock actualizado."""
        for tienda in self.tiendas:
            tab_name = tienda["nombre"]
            try:
                tab = self.tabview.tab(tab_name)
                for w in tab.winfo_children():
                    w.destroy()
                if tienda["precio_abierto"]:
                    self._build_mack_tab(tab, tienda)
                else:
                    self._build_product_grid(tab, tienda)
            except Exception:
                pass

    # ══════════════════════════════════════════
    #  REGISTRAR GASTO
    # ══════════════════════════════════════════
    def _registrar_gasto_modal(self):
        if not self.usuario_actual:
            self._pedir_nip(callback=self._registrar_gasto_modal)
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Registrar Gasto / Salida")
        modal.geometry("420x350")
        modal.configure(fg_color=FONDO)
        modal.grab_set()
        modal.resizable(False, False)

        ctk.CTkLabel(
            modal, text="💸 Registrar Salida de Dinero",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(20, 10))

        # Tienda
        ctk.CTkLabel(modal, text="Tienda:", text_color=TEXTO).pack(anchor="w", padx=50)
        tienda_nombres = ["General (sin tienda)"] + [t["nombre"] for t in self.tiendas]
        combo_tienda = ctk.CTkComboBox(modal, values=tienda_nombres, width=300)
        combo_tienda.pack(pady=5)
        combo_tienda.set(tienda_nombres[0])

        # Concepto
        ctk.CTkLabel(modal, text="Concepto:", text_color=TEXTO).pack(anchor="w", padx=50)
        entry_concepto = ctk.CTkEntry(modal, width=300, placeholder_text="Ej: Compra de leche")
        entry_concepto.pack(pady=5)

        # Monto
        ctk.CTkLabel(modal, text="Monto:", text_color=TEXTO).pack(anchor="w", padx=50)
        entry_monto = ctk.CTkEntry(modal, width=300, placeholder_text="$ 0.00")
        entry_monto.pack(pady=5)

        def guardar():
            concepto = entry_concepto.get().strip()
            if not concepto:
                messagebox.showerror("Error", "Ingresa un concepto.", parent=modal)
                return
            try:
                monto = float(entry_monto.get())
                if monto <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Monto inválido.", parent=modal)
                return

            sel = combo_tienda.get()
            tienda_id = None
            if sel != "General (sin tienda)":
                for t in self.tiendas:
                    if t["nombre"] == sel:
                        tienda_id = t["id"]
                        break

            registrar_gasto(self.usuario_actual["id"], tienda_id, concepto, monto)
            messagebox.showinfo("Gasto registrado", f"${monto:,.2f} – {concepto}", parent=modal)
            modal.destroy()

        ctk.CTkButton(
            modal, text="✓ Guardar Gasto", width=200,
            fg_color=ROSA_PASTEL, hover_color="#AB47BC",
            text_color=TEXTO_BLANCO,
            command=guardar,
        ).pack(pady=20)

    # ══════════════════════════════════════════
    #  ABRIR CAJA (Fondo inicial)
    # ══════════════════════════════════════════
    def _abrir_caja_modal(self):
        if not self.usuario_actual:
            self._pedir_nip(callback=self._abrir_caja_modal)
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Abrir Caja")
        modal.geometry("380x220")
        modal.configure(fg_color=FONDO)
        modal.grab_set()
        modal.resizable(False, False)

        ctk.CTkLabel(
            modal, text="🏦  Fondo de Caja Inicial",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(20, 10))

        ctk.CTkLabel(modal, text="Monto del fondo de apertura:", text_color=TEXTO).pack(anchor="w", padx=50)
        entry_fondo = ctk.CTkEntry(modal, width=300, placeholder_text="$ 0.00")
        entry_fondo.pack(pady=5)
        fondo_actual = get_fondo_apertura()
        if fondo_actual > 0:
            entry_fondo.insert(0, str(fondo_actual))

        def guardar():
            try:
                monto = float(entry_fondo.get().replace(",", "") or 0)
                if monto < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Monto inválido.", parent=modal)
                return
            set_fondo_apertura(monto)
            messagebox.showinfo("Caja Abierta", f"Fondo registrado: ${monto:,.2f}", parent=modal)
            modal.destroy()

        ctk.CTkButton(
            modal, text="✓ Guardar Fondo", width=200,
            fg_color=VERDE, hover_color="#66BB6A",
            text_color=TEXTO_BLANCO,
            command=guardar,
        ).pack(pady=20)

    # ══════════════════════════════════════════
    #  REGISTRAR INGRESO
    # ══════════════════════════════════════════
    def _registrar_ingreso_modal(self):
        if not self.usuario_actual:
            self._pedir_nip(callback=self._registrar_ingreso_modal)
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Registrar Ingreso")
        modal.geometry("420x320")
        modal.configure(fg_color=FONDO)
        modal.grab_set()
        modal.resizable(False, False)

        ctk.CTkLabel(
            modal, text="💰  Registrar Ingreso",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(20, 10))

        ctk.CTkLabel(modal, text="Concepto:", text_color=TEXTO).pack(anchor="w", padx=50)
        entry_concepto = ctk.CTkEntry(modal, width=300, placeholder_text="Ej: Anticipo taller")
        entry_concepto.pack(pady=5)

        ctk.CTkLabel(modal, text="Monto:", text_color=TEXTO).pack(anchor="w", padx=50)
        entry_monto = ctk.CTkEntry(modal, width=300, placeholder_text="$ 0.00")
        entry_monto.pack(pady=5)

        ctk.CTkLabel(modal, text="Método de pago:", text_color=TEXTO).pack(anchor="w", padx=50)
        combo_metodo = ctk.CTkComboBox(modal, values=["Efectivo", "Tarjeta"], width=300)
        combo_metodo.set("Efectivo")
        combo_metodo.pack(pady=5)

        def guardar():
            concepto = entry_concepto.get().strip()
            if not concepto:
                messagebox.showerror("Error", "Ingresa un concepto.", parent=modal)
                return
            try:
                monto = float(entry_monto.get())
                if monto <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Monto inválido.", parent=modal)
                return
            metodo = combo_metodo.get()
            registrar_ingreso(self.usuario_actual["id"], concepto, monto, metodo)
            messagebox.showinfo("Ingreso registrado", f"${monto:,.2f} – {concepto} ({metodo})", parent=modal)
            modal.destroy()

        ctk.CTkButton(
            modal, text="✓ Guardar Ingreso", width=200,
            fg_color="#26A69A", hover_color="#00897B",
            text_color=TEXTO_BLANCO,
            command=guardar,
        ).pack(pady=20)

    # ══════════════════════════════════════════
    #  CORTE DE CAJA
    # ══════════════════════════════════════════
    def _hacer_corte(self):
        if not self.usuario_actual:
            self._pedir_nip(callback=self._hacer_corte)
            return

        if self.usuario_actual["perfil"] not in ("Administrador",):
            messagebox.showwarning(
                "Sin permisos",
                "Solo un Administrador puede hacer el corte de caja.",
            )
            return

        resumen = obtener_resumen_dia()

        modal = ctk.CTkToplevel(self)
        modal.title("Corte de Caja")
        modal.geometry("600x700")
        modal.configure(fg_color=FONDO)
        modal.grab_set()
        modal.resizable(False, False)

        # ── Título ──
        ctk.CTkLabel(
            modal, text="📊 Corte de Caja",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=MORADO_PASTEL,
        ).pack(pady=(15, 3))

        # ── Resumen del turno ──
        desde_str = resumen.get("desde", "")[-8:]  # HH:MM:SS
        ef_total  = resumen.get("total_efectivo", resumen.get("efectivo_esperado", 0))
        tar_total = resumen.get("total_tarjeta", 0)
        tar_neto  = resumen.get("tarjeta_esperado", tar_total - resumen["total_gastos"])
        total_gen = resumen.get("total_esperado", ef_total + tar_neto)
        ctk.CTkLabel(
            modal,
            text=(
                f"Turno desde {desde_str}   "
                f"Ventas: ${resumen['total_ventas']:,.2f}  ({resumen['num_ventas']} tickets)   "
                f"Efectivo: ${ef_total:,.2f}   Tarjeta: ${tar_total:,.2f}   "
                f"Gastos (tarjeta): -${resumen['total_gastos']:,.2f}   "
                f"Total: ${total_gen:,.2f}"
            ),
            font=ctk.CTkFont(size=10), text_color=TEXTO_CLARO, wraplength=560,
        ).pack(pady=(0, 8))

        # ── Fondo de caja (pre-llenado desde apertura) ──
        fondo_frame = ctk.CTkFrame(modal, fg_color=FONDO_CARD, corner_radius=10)
        fondo_frame.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(
            fondo_frame, text="🏦  Fondo de caja inicial:",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXTO,
        ).pack(side="left", padx=15, pady=8)
        fondo_apertura = resumen.get("fondo_apertura", get_fondo_apertura())
        fondo_var = ctk.StringVar(value=str(fondo_apertura))
        ctk.CTkEntry(
            fondo_frame, textvariable=fondo_var, width=130,
            font=ctk.CTkFont(size=13), justify="right",
        ).pack(side="right", padx=15, pady=8)

        # ── Billetes y Monedas ──
        BILLETES = [1000, 500, 200, 100, 50, 20]
        MONEDAS  = [10, 5, 2, 1, 0.5]
        bill_vars = {d: ctk.StringVar(value="0") for d in BILLETES}
        coin_vars = {d: ctk.StringVar(value="0") for d in MONEDAS}

        cols_frame = ctk.CTkFrame(modal, fg_color="transparent")
        cols_frame.pack(fill="x", padx=20, pady=4)
        cols_frame.grid_columnconfigure(0, weight=1)
        cols_frame.grid_columnconfigure(1, weight=1)

        def _build_denom_card(parent, titulo, denoms, vars_dict, label_fmt):
            card = ctk.CTkFrame(parent, fg_color=FONDO_CARD, corner_radius=10)
            ctk.CTkLabel(
                card, text=titulo,
                font=ctk.CTkFont(size=12, weight="bold"), text_color=MORADO_PASTEL,
            ).pack(pady=(10, 4))
            for d in denoms:
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=14, pady=2)
                ctk.CTkLabel(
                    row, text=label_fmt(d), width=65,
                    text_color=TEXTO, font=ctk.CTkFont(size=12), anchor="w",
                ).pack(side="left")
                ctk.CTkEntry(
                    row, textvariable=vars_dict[d], width=75,
                    justify="center", font=ctk.CTkFont(size=12),
                ).pack(side="right")
            ctk.CTkLabel(card, text="").pack(pady=3)
            return card

        bill_card = _build_denom_card(
            cols_frame, "💵  Billetes", BILLETES, bill_vars,
            lambda d: f"${d:,}",
        )
        bill_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        coin_card = _build_denom_card(
            cols_frame, "🪙  Monedas", MONEDAS, coin_vars,
            lambda d: f"${int(d)}" if d == int(d) else f"${d}",
        )
        coin_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # ── Totales en vivo ──
        totales_frame = ctk.CTkFrame(modal, fg_color=FONDO_CARD, corner_radius=10)
        totales_frame.pack(fill="x", padx=20, pady=8)

        def _fila(parent, etiqueta, valor_inicial, bold=False, color=TEXTO):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=15, pady=1)
            ctk.CTkLabel(
                f, text=etiqueta, text_color=TEXTO_CLARO,
                font=ctk.CTkFont(size=11, weight="bold" if bold else "normal"),
                anchor="w",
            ).pack(side="left")
            lbl = ctk.CTkLabel(
                f, text=valor_inicial, text_color=color,
                font=ctk.CTkFont(size=11, weight="bold" if bold else "normal"),
                anchor="e",
            )
            lbl.pack(side="right")
            return lbl

        lbl_contado  = _fila(totales_frame, "Total contado:", "$0.00")
        lbl_fondo_r  = _fila(totales_frame, "Menos fondo de caja:", "-$0.00")
        lbl_real     = _fila(totales_frame, "Efectivo real (ventas):", "$0.00", bold=True)
        _fila(totales_frame, "Efectivo esperado (sistema):",
              f"${resumen['efectivo_esperado']:,.2f}", color=TEXTO_CLARO)
        lbl_dif      = _fila(totales_frame, "Diferencia:", "$0.00", bold=True)
        ctk.CTkLabel(totales_frame, text="").pack(pady=2)

        def _actualizar(*_):
            try:
                fondo = float(fondo_var.get().replace(",", "") or 0)
            except Exception:
                fondo = 0.0
            total = 0.0
            for d, v in bill_vars.items():
                try: total += d * int(v.get() or 0)
                except Exception: pass
            for d, v in coin_vars.items():
                try: total += d * int(v.get() or 0)
                except Exception: pass
            real = total - fondo
            dif  = real - resumen["efectivo_esperado"]
            lbl_contado.configure(text=f"${total:,.2f}")
            lbl_fondo_r.configure(text=f"-${fondo:,.2f}")
            lbl_real.configure(text=f"${real:,.2f}")
            signo = "+" if dif >= 0 else ""
            lbl_dif.configure(
                text=f"{signo}${dif:,.2f}",
                text_color=VERDE if dif >= 0 else ROJO_ALERTA,
            )

        fondo_var.trace_add("write", _actualizar)
        for v in bill_vars.values(): v.trace_add("write", _actualizar)
        for v in coin_vars.values(): v.trace_add("write", _actualizar)

        # ── Confirmar ──
        def confirmar_corte():
            try:
                fondo = float(fondo_var.get().replace(",", "") or 0)
            except Exception:
                messagebox.showerror("Error", "Fondo de caja inválido.", parent=modal)
                return

            total = 0.0
            desglose = {}
            for d, v in bill_vars.items():
                try:
                    qty = int(v.get() or 0)
                    if qty > 0:
                        desglose[f"B{d}"] = qty
                    total += d * qty
                except Exception:
                    pass
            for d, v in coin_vars.items():
                try:
                    qty = int(v.get() or 0)
                    if qty > 0:
                        desglose[f"M{d}"] = qty
                    total += d * qty
                except Exception:
                    pass

            efectivo_real = total - fondo
            cajero   = self.usuario_actual["nombre"]
            resultado = registrar_corte(
                self.usuario_actual["id"], efectivo_real,
                fondo_caja=fondo, desglose=desglose,
            )

            # Obtener ventas del turno para incluir en el PDF
            ventas = obtener_ventas_turno()
            ruta_pdf = generar_corte_pdf(resultado, cajero, ventas_turno=ventas)

            # Enviar PDF por correo en hilo separado
            def _on_email_ok(msg_email):
                self.after(0, lambda: messagebox.showinfo(
                    "Email", f"📧 {msg_email}"))

            def _on_email_error(msg_email):
                self.after(0, lambda: messagebox.showwarning(
                    "Email", f"⚠ {msg_email}"))

            enviar_corte_email(
                ruta_pdf, resultado, cajero,
                callback_ok=_on_email_ok,
                callback_error=_on_email_error,
            )

            dif   = resultado["diferencia"]
            signo = "+" if dif >= 0 else ""
            msg   = (
                f"Corte guardado ✅\n\n"
                f"Total contado:       ${total:,.2f}\n"
                f"Fondo de caja:      -${fondo:,.2f}\n"
                f"Efectivo real:       ${efectivo_real:,.2f}\n"
                f"Esperado:            ${resultado['efectivo_esperado']:,.2f}\n"
                f"Diferencia:          {signo}${dif:,.2f}\n\n"
                f"PDF: {ruta_pdf}\n"
                f"📧 Enviando correo..."
            )
            messagebox.showinfo("Corte Completo", msg)
            modal.destroy()

        ctk.CTkButton(
            modal, text="✓ Confirmar Corte", width=220, height=42,
            fg_color=VERDE, hover_color="#66BB6A", text_color=TEXTO_BLANCO,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=confirmar_corte,
        ).pack(pady=(4, 18))


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
