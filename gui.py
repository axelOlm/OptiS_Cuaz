from __future__ import annotations

import ctypes
import tkinter as tk
from fractions import Fraction
from tkinter import font as tkfont
from tkinter import ttk

from simplex import TOL, Problema, fmt, resolver

N_MAX, M_MAX = 8, 10

TEMAS = {
    "claro": dict(
        bg="#F3F4F1", header="#F8F9F6", panel="#FAFBF8", field="#FFFFFF", matrix="#EDF0EB",
        thead="#ECEFE9", result_col="#F3F6F3", info="#F1F5F1",
        primary="#405C50", primary_hover="#354F44", on_primary="#FFFFFF", soft="#E8EEEA",
        text="#252823", text2="#737A74", label="#666D67", aux="#858B86", faint="#929893",
        highlight="#405C50", border="#DFE2DC", border_field="#D9DDD7", sep="#E2E5DF",
        border_active="#71877B", ring="#DCE7E1", danger="#7B514C",
        ok_bg="#E8EEEA", ok_fg="#405C50", warn_bg="#F4EBD9", warn_fg="#7A5C22",
        err_bg="#F4E6E4", err_fg="#7B514C",
    ),
    "oscuro": dict(
        bg="#141715", header="#191D1B", panel="#1C211F", field="#232927", matrix="#1A1F1D",
        thead="#242B28", result_col="#212926", info="#1F2623",
        primary="#6F9A86", primary_hover="#7FAA96", on_primary="#0F1512", soft="#26332D",
        text="#E6E9E5", text2="#9AA39D", label="#A3ABA5", aux="#858D87", faint="#6E766F",
        highlight="#9CC4AF", border="#2B322F", border_field="#333B37", sep="#2A312E",
        border_active="#7FA390", ring="#314039", danger="#D69A93",
        ok_bg="#1F2E27", ok_fg="#9CC4AF", warn_bg="#33291A", warn_fg="#D9B77A",
        err_bg="#352220", err_fg="#E0A9A2",
    ),
}

SIGNOS = {"≤": "<=", "≥": ">=", "=": "="}
SIGNOS_INV = {v: k for k, v in SIGNOS.items()}

EJEMPLOS = {
    "Primal · Wyndor Glass": dict(tipo="max", metodo="primal", c=[3, 5],
                                  A=[[1, 0], [0, 2], [3, 2]], s=["<=", "<=", "<="], b=[4, 12, 18]),
    "Dual · Minimización": dict(tipo="min", metodo="dual", c=[2, 3],
                                A=[[1, 1], [1, 2]], s=[">=", ">="], b=[5, 8]),
    "No acotado": dict(tipo="max", metodo="primal", c=[1, 1],
                       A=[[1, -1], [1, -2]], s=["<=", "<="], b=[1, 2]),
    "Infactible": dict(tipo="min", metodo="dual", c=[1, 1],
                       A=[[1, 1], [1, 1]], s=[">=", "<="], b=[5, 2]),
}


def num(s: str) -> float:
    s = s.strip().replace(",", ".")
    if not s:
        return 0.0
    try:
        return float(Fraction(s))
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"Valor no válido: «{s}»")


def txt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("OptiSolver Desktop")
        root.geometry("1180x740")
        root.minsize(960, 620)

        familias = set(tkfont.families())
        self.fam = next((f for f in ("DM Sans", "Segoe UI", "Helvetica") if f in familias), "TkDefaultFont")

        self.tema = "claro"
        self.t = TEMAS[self.tema]
        self.reg, self.refreshers, self.scrolls = [], [], {}
        self.res = None
        self.p = None
        self.metodo = "primal"
        self.idx = 0
        self.en_resultados = False
        self.sidebar = False
        self.n = self.m = 0
        self.c_entries, self.a_entries, self.s_vars, self.b_entries = [], [], [], []

        self.var_tipo = tk.StringVar(value="max")
        self.var_metodo = tk.StringVar(value="primal")
        self.var_n = tk.StringVar(value="2")
        self.var_m = tk.StringVar(value="3")
        self.var_obj = tk.StringVar()
        self.var_vista = tk.StringVar(value="una")
        self.var_frac = tk.BooleanVar(value=True)
        self.var_tipo.trace_add("write", self._actualiza_tipo)
        self._actualiza_tipo()

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self._build()
        self.rebuild_matrix()
        self.apply_theme()
        root.bind("<Control-Return>", lambda e: self.ejecutar())
        root.bind_all("<MouseWheel>", self._rueda)

    # ---------- utilidades ----------
    def f(self, size=10, bold=False):
        return (self.fam, size, "bold" if bold else "normal")

    def R(self, w, **m):
        self.reg.append((w, m))
        self._paint(w, m)
        return w

    def _paint(self, w, m):
        try:
            w.configure(**{k: self.t[v] for k, v in m.items()})
        except tk.TclError:
            pass

    def _actualiza_tipo(self, *_):
        self.var_obj.set("→ máx" if self.var_tipo.get() == "max" else "→ mín")

    def _rueda(self, e):
        try:
            w = self.root.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return
        while w is not None:
            cv = self.scrolls.get(str(w))
            if cv is not None:
                paso = -1 if e.delta > 0 else 1
                if e.state & 1:
                    cv.xview_scroll(paso, "units")
                elif cv.yview() != (0.0, 1.0):
                    cv.yview_scroll(paso, "units")
                return
            w = w.master

    def segmented(self, parent, var, opciones, cmd=None):
        box = self.R(tk.Frame(parent, padx=1, pady=1), bg="border_field")
        labels = []

        def pintar():
            for lb, val in labels:
                if not lb.winfo_exists():
                    continue
                sel = var.get() == val
                lb.configure(bg=self.t["primary"] if sel else self.t["field"],
                             fg=self.t["on_primary"] if sel else self.t["text2"],
                             font=self.f(9, sel))

        for texto, val in opciones:
            lb = tk.Label(box, text=texto, padx=14, pady=6, cursor="hand2")
            lb.pack(side="left", fill="x", expand=True)
            lb.bind("<Button-1>", lambda e, v=val: (var.set(v), cmd() if cmd else None))
            labels.append((lb, val))
        var.trace_add("write", lambda *a: pintar())
        self.refreshers.append(pintar)
        pintar()
        return box

    def boton(self, parent, texto, cmd, tipo="primario", fondo="panel", px=16, py=8):
        b = tk.Button(parent, text=texto, command=cmd, relief="flat", bd=0, cursor="hand2",
                      padx=px, pady=py, highlightthickness=0 if tipo == "primario" else 1)
        if tipo == "primario":
            b.configure(font=self.f(10, True))
            m = dict(bg="primary", fg="on_primary", activebackground="primary_hover",
                     activeforeground="on_primary", highlightbackground="primary")
            base, hover = "primary", "primary_hover"
        else:
            b.configure(font=self.f(10))
            fg = "danger" if tipo == "peligro" else "text"
            m = dict(bg=fondo, fg=fg, activebackground="soft", activeforeground=fg,
                     highlightbackground="border_field")
            base, hover = fondo, "soft"
        self.R(b, **m)
        b.bind("<Enter>", lambda e: b.configure(bg=self.t[hover]))
        b.bind("<Leave>", lambda e: b.configure(bg=self.t[base]))
        return b

    def entrada(self, parent, ancho=6):
        e = tk.Entry(parent, width=ancho, justify="center", relief="flat", highlightthickness=1,
                     font=self.f(10))
        return self.R(e, bg="field", fg="text", insertbackground="text",
                      highlightbackground="border_field", highlightcolor="border_active",
                      selectbackground="ring", selectforeground="text")

    def menu_signo(self, parent, var):
        mb = tk.Menubutton(parent, textvariable=var, width=3, relief="flat", cursor="hand2",
                           font=self.f(10, True), highlightthickness=1)
        self.R(mb, bg="field", fg="text", activebackground="soft", activeforeground="text",
               highlightbackground="border_field")
        menu = tk.Menu(mb, tearoff=0, font=self.f(10))
        self.R(menu, bg="field", fg="text", activebackground="soft", activeforeground="text")
        for s in SIGNOS:
            menu.add_command(label=s, command=lambda s=s: var.set(s))
        mb["menu"] = menu
        return mb

    def area_scroll(self, parent, fondo):
        cont = self.R(tk.Frame(parent), bg=fondo)
        cv = self.R(tk.Canvas(cont, highlightthickness=0, bd=0, xscrollincrement=20,
                              yscrollincrement=20), bg=fondo)
        vs = ttk.Scrollbar(cont, orient="vertical", command=cv.yview, style="OS.Vertical.TScrollbar")
        hs = ttk.Scrollbar(cont, orient="horizontal", command=cv.xview, style="OS.Horizontal.TScrollbar")
        cv.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        cont.grid_rowconfigure(0, weight=1)
        cont.grid_columnconfigure(0, weight=1)
        cv.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        inner = self.R(tk.Frame(cv), bg=fondo)
        win = cv.create_window(0, 0, window=inner, anchor="nw")

        def ajustar(_=None):
            cv.itemconfigure(win, width=max(cv.winfo_width(), inner.winfo_reqwidth()))
            cv.configure(scrollregion=cv.bbox("all"))

        inner.bind("<Configure>", ajustar)
        cv.bind("<Configure>", ajustar)
        self.scrolls[str(cont)] = cv
        self.scrolls[str(cv)] = cv
        return cont, inner

    # ---------- construcción ----------
    def _build(self):
        self.R(self.root, bg="bg")

        self.header = self.R(tk.Frame(self.root), bg="header")
        self.header.pack(fill="x")
        tit = self.R(tk.Frame(self.header), bg="header")
        tit.pack(side="left", padx=24, pady=10)
        self.R(tk.Label(tit, text="OptiSolver Desktop", font=self.f(15, True)),
               bg="header", fg="text").pack(anchor="w")
        self.R(tk.Label(tit, text="Olmedo Ramírez Axel Yahir", font=self.f(7)),
               bg="header", fg="faint").pack(anchor="w")
        self.btn_tema = self.boton(self.header, "Tema oscuro", self.cambiar_tema, "ghost", "header", 12, 5)
        self.btn_tema.pack(side="right", padx=(0, 24), pady=14)
        self.btn_datos = self.boton(self.header, "Mostrar datos", self.toggle_sidebar, "ghost", "header", 12, 5)
        self.R(tk.Frame(self.root, height=1), bg="sep").pack(fill="x")

        self.body = self.R(tk.Frame(self.root), bg="bg")
        self.body.pack(fill="both", expand=True)
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(1, weight=1)

        self.panel = self.R(tk.Frame(self.body, highlightthickness=1), bg="panel", highlightbackground="border")
        self.panel.pack_propagate(False)
        self.panel.place(relx=0.5, rely=0.5, anchor="center", width=640, relheight=0.94)
        self._build_panel()

        self.results = self.R(tk.Frame(self.body), bg="bg")
        self._build_results()

    def _build_panel(self):
        p = self.R(tk.Frame(self.panel), bg="panel")
        p.pack(fill="both", expand=True, padx=22, pady=20)

        def campo(texto):
            return self.R(tk.Label(p, text=texto, font=self.f(9, True), anchor="w"), bg="panel", fg="label")

        self.R(tk.Label(p, text="Configuración del problema", font=self.f(13, True), anchor="w"),
               bg="panel", fg="text").pack(fill="x")
        self.R(tk.Label(p, text="Define la función objetivo, las restricciones y el método.",
                        font=self.f(9), anchor="w", justify="left", wraplength=360),
               bg="panel", fg="text2").pack(fill="x", pady=(2, 14))

        campo("Optimización").pack(fill="x")
        self.segmented(p, self.var_tipo, [("Maximizar", "max"), ("Minimizar", "min")]).pack(fill="x", pady=(4, 12))
        campo("Método").pack(fill="x")
        self.segmented(p, self.var_metodo, [("Simplex Primal", "primal"), ("Simplex Dual", "dual")]
                       ).pack(fill="x", pady=(4, 12))

        dims = self.R(tk.Frame(p), bg="panel")
        dims.pack(fill="x", pady=(0, 12))
        for texto, var, mx in (("Variables (n)", self.var_n, N_MAX), ("Restricciones (m)", self.var_m, M_MAX)):
            g = self.R(tk.Frame(dims), bg="panel")
            g.pack(side="left", padx=(0, 24))
            self.R(tk.Label(g, text=texto, font=self.f(9, True)), bg="panel", fg="label").pack(anchor="w")
            sp = tk.Spinbox(g, from_=1, to=mx, textvariable=var, width=5, justify="center", relief="flat",
                            highlightthickness=1, font=self.f(10), command=self.rebuild_matrix)
            self.R(sp, bg="field", fg="text", buttonbackground="thead", insertbackground="text",
                   highlightbackground="border_field", highlightcolor="border_active")
            sp.bind("<Return>", lambda e: self.rebuild_matrix())
            sp.bind("<FocusOut>", lambda e: self.rebuild_matrix())
            sp.pack(anchor="w", pady=(4, 0))

        campo("Función objetivo y restricciones").pack(fill="x")

        inf = self.R(tk.Frame(p), bg="panel")
        inf.pack(side="bottom", fill="x")
        self.lbl_error = self.R(tk.Label(inf, text="", font=self.f(9), anchor="w", justify="left",
                                         wraplength=360), bg="panel", fg="danger")
        self.lbl_error.pack(fill="x")
        self.boton(inf, "Resolver", self.ejecutar).pack(fill="x", pady=(4, 8))
        fila = self.R(tk.Frame(inf), bg="panel")
        fila.pack(fill="x")
        mb = tk.Menubutton(fila, text="Cargar ejemplo ▾", relief="flat", cursor="hand2",
                           font=self.f(10), padx=14, pady=8, highlightthickness=1)
        self.R(mb, bg="panel", fg="text", activebackground="soft", activeforeground="text",
               highlightbackground="border_field")
        menu = tk.Menu(mb, tearoff=0, font=self.f(10))
        self.R(menu, bg="field", fg="text", activebackground="soft", activeforeground="text")
        for nombre in EJEMPLOS:
            menu.add_command(label=nombre, command=lambda n=nombre: self.cargar(n))
        mb["menu"] = menu
        mb.pack(side="left")
        self.boton(fila, "Limpiar", self.limpiar, "peligro").pack(side="right")

        marco = self.R(tk.Frame(p, highlightthickness=1), bg="matrix", highlightbackground="border_field")
        marco.pack(fill="both", expand=True, pady=(4, 12))
        cont, self.mat = self.area_scroll(marco, "matrix")
        cont.pack(fill="both", expand=True)

    def _build_results(self):
        r = self.results
        self.banner = tk.Label(r, anchor="w", justify="left", font=self.f(10, True), padx=16, pady=10)
        self.banner.pack(fill="x", padx=24, pady=(20, 10))
        self.banner.bind("<Configure>", lambda e: self.banner.configure(wraplength=max(e.width - 32, 100)))

        self.resumen = self.R(tk.Frame(r), bg="bg")
        self.resumen.pack(fill="x", padx=24)

        nav = self.R(tk.Frame(r), bg="bg")
        nav.pack(fill="x", padx=24, pady=(16, 6))
        self.segmented(nav, self.var_vista, [("Una", "una"), ("Todas", "todas")],
                       cmd=self.render_tablas).pack(side="right")
        chk = tk.Checkbutton(nav, text="Fracciones", variable=self.var_frac, command=self.refrescar,
                             font=self.f(9), cursor="hand2", relief="flat", bd=0, highlightthickness=0)
        self.R(chk, bg="bg", fg="label", activebackground="bg", activeforeground="label",
               selectcolor="field").pack(side="right", padx=16)
        self.boton(nav, "◀", lambda: self.ir(-1), "ghost", "bg", 10, 4).pack(side="left")
        self.lbl_iter = self.R(tk.Label(nav, font=self.f(10, True), width=14), bg="bg", fg="text")
        self.lbl_iter.pack(side="left")
        self.boton(nav, "▶", lambda: self.ir(1), "ghost", "bg", 10, 4).pack(side="left")
        self.chips = self.R(tk.Frame(nav), bg="bg")
        self.chips.pack(side="left", padx=12)

        self.tabs_cont, self.tabs = self.area_scroll(r, "bg")
        self.tabs_cont.pack(fill="both", expand=True, padx=24, pady=(4, 20))

    # ---------- matriz de entrada ----------
    def _dims(self):
        def v(var, mx, ant):
            try:
                x = int(var.get())
            except ValueError:
                x = ant or 1
            x = max(1, min(mx, x))
            var.set(str(x))
            return x
        return v(self.var_n, N_MAX, self.n), v(self.var_m, M_MAX, self.m)

    def rebuild_matrix(self):
        n, m = self._dims()
        if self.c_entries and (n, m) == (self.n, self.m):
            return
        snap = self.leer_texto() if self.c_entries else None
        for w in self.mat.winfo_children():
            w.destroy()
        self.n, self.m = n, m
        self.mat.configure(padx=12, pady=12)
        self.c_entries, self.a_entries, self.s_vars, self.b_entries = [], [], [], []

        def cab(texto, c):
            self.R(tk.Label(self.mat, text=texto, font=self.f(9, True)), bg="matrix", fg="label"
                   ).grid(row=0, column=c, padx=3, pady=(0, 4))

        for j in range(n):
            cab(f"x{j + 1}", j + 1)
        cab("signo", n + 1)
        cab("b", n + 2)

        self.R(tk.Label(self.mat, text="Z =", font=self.f(10, True)), bg="matrix", fg="highlight"
               ).grid(row=1, column=0, padx=(0, 6), pady=3)
        for j in range(n):
            e = self.entrada(self.mat)
            e.grid(row=1, column=j + 1, padx=3, pady=3)
            self.c_entries.append(e)
        self.R(tk.Label(self.mat, textvariable=self.var_obj, font=self.f(9)), bg="matrix", fg="text2"
               ).grid(row=1, column=n + 1, columnspan=2, padx=3)

        self.R(tk.Frame(self.mat, height=1), bg="sep").grid(row=2, column=0, columnspan=n + 3,
                                                           sticky="ew", pady=6)
        for i in range(m):
            self.R(tk.Label(self.mat, text=f"R{i + 1}", font=self.f(9, True)), bg="matrix", fg="label"
                   ).grid(row=3 + i, column=0, padx=(0, 6), pady=3)
            fila = []
            for j in range(n):
                e = self.entrada(self.mat)
                e.grid(row=3 + i, column=j + 1, padx=3, pady=3)
                fila.append(e)
            self.a_entries.append(fila)
            sv = tk.StringVar(value="≤")
            self.s_vars.append(sv)
            self.menu_signo(self.mat, sv).grid(row=3 + i, column=n + 1, padx=3, pady=3)
            eb = self.entrada(self.mat)
            eb.grid(row=3 + i, column=n + 2, padx=3, pady=3)
            self.b_entries.append(eb)

        if snap:
            self.llenar(snap)

    def leer_texto(self):
        return dict(c=[e.get() for e in self.c_entries],
                    A=[[e.get() for e in f] for f in self.a_entries],
                    s=[v.get() for v in self.s_vars],
                    b=[e.get() for e in self.b_entries])

    @staticmethod
    def _poner(e, valor):
        e.delete(0, "end")
        e.insert(0, valor)

    def llenar(self, d):
        for j in range(min(self.n, len(d["c"]))):
            self._poner(self.c_entries[j], d["c"][j])
        for i in range(min(self.m, len(d["b"]))):
            for j in range(min(self.n, len(d["A"][i]))):
                self._poner(self.a_entries[i][j], d["A"][i][j])
            self.s_vars[i].set(d["s"][i])
            self._poner(self.b_entries[i], d["b"][i])

    def cargar(self, nombre):
        ex = EJEMPLOS[nombre]
        self.var_tipo.set(ex["tipo"])
        self.var_metodo.set(ex["metodo"])
        self.var_n.set(str(len(ex["c"])))
        self.var_m.set(str(len(ex["b"])))
        self.rebuild_matrix()
        self.llenar(dict(c=[txt(v) for v in ex["c"]],
                         A=[[txt(v) for v in f] for f in ex["A"]],
                         s=[SIGNOS_INV[s] for s in ex["s"]],
                         b=[txt(v) for v in ex["b"]]))
        self.lbl_error.configure(text="")

    def limpiar(self):
        for e in self.c_entries + self.b_entries + [x for f in self.a_entries for x in f]:
            e.delete(0, "end")
        for v in self.s_vars:
            v.set("≤")
        self.lbl_error.configure(text="")

    # ---------- resolución ----------
    def ejecutar(self):
        try:
            p = Problema(
                self.var_tipo.get(),
                [num(e.get()) for e in self.c_entries],
                [[num(e.get()) for e in f] for f in self.a_entries],
                [SIGNOS[v.get()] for v in self.s_vars],
                [num(e.get()) for e in self.b_entries],
            )
            res = resolver(p, self.var_metodo.get())
        except ValueError as ex:
            self.lbl_error.configure(text=str(ex))
            return
        self.lbl_error.configure(text="")
        self.p, self.res, self.metodo, self.idx = p, res, self.var_metodo.get(), 0
        self.var_vista.set("una")
        self.mostrar_resultados()

    def mostrar_resultados(self):
        if not self.en_resultados:
            self.panel.place_forget()
            self.panel.configure(width=420)
            self.panel.grid(row=0, column=0, sticky="ns", padx=(16, 0), pady=16)
            self.results.grid(row=0, column=1, sticky="nsew")
            self.btn_datos.pack(side="right", padx=(0, 8), pady=14)
            self.en_resultados = True
        self.sidebar = False
        self.panel.grid_remove()
        self.btn_datos.configure(text="Mostrar datos")
        self.pintar_resultado()

    def toggle_sidebar(self):
        self.sidebar = not self.sidebar
        if self.sidebar:
            self.panel.grid()
        else:
            self.panel.grid_remove()
        self.btn_datos.configure(text="Ocultar datos" if self.sidebar else "Mostrar datos")

    def cambiar_tema(self):
        self.tema = "oscuro" if self.tema == "claro" else "claro"
        self.t = TEMAS[self.tema]
        self.apply_theme()

    def apply_theme(self):
        t = self.t
        self.reg = [(w, m) for w, m in self.reg if w.winfo_exists()]
        for w, m in self.reg:
            self._paint(w, m)
        for fn in self.refreshers:
            fn()
        for o in ("Vertical", "Horizontal"):
            nombre = f"OS.{o}.TScrollbar"
            self.style.configure(nombre, troughcolor=t["bg"], background=t["border_field"],
                                 bordercolor=t["bg"], arrowcolor=t["aux"], lightcolor=t["border_field"],
                                 darkcolor=t["border_field"], relief="flat")
            self.style.map(nombre, background=[("active", t["border_active"])])
        self.btn_tema.configure(text="Tema oscuro" if self.tema == "claro" else "Tema claro")
        if self.res:
            self.pintar_resultado()

    # ---------- resultados ----------
    def pintar_resultado(self):
        res = self.res
        tipos = {
            "optimo": ("ok", "Solución óptima encontrada"),
            "no_acotado": ("err", "Solución no acotada"),
            "infactible": ("err", "Problema infactible"),
            "metodo_inadecuado": ("warn", "Método no aplicable a este problema"),
        }
        k, titulo = tipos[res.estado]
        self.banner.configure(text=titulo if res.estado == "optimo" else f"{titulo}\n{res.mensaje}",
                              bg=self.t[f"{k}_bg"], fg=self.t[f"{k}_fg"])
        self.refrescar()

    def refrescar(self):
        if not self.res:
            return
        self._resumen()
        self.render_tablas()

    def tarjeta(self, col, titulo, valor, detalle, grande=True):
        t = self.t
        c = tk.Frame(self.resumen, bg=t["info"], highlightthickness=1, highlightbackground=t["border"])
        c.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
        self.resumen.grid_columnconfigure(col, weight=1, uniform="card")
        tk.Label(c, text=titulo, font=self.f(8, True), bg=t["info"], fg=t["label"], anchor="w"
                 ).pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(c, text=valor, font=self.f(18 if grande else 11, True), bg=t["info"],
                 fg=t["highlight"], anchor="w").pack(fill="x", padx=14)
        tk.Label(c, text=detalle, font=self.f(9), bg=t["info"], fg=t["text2"], anchor="w",
                 justify="left", wraplength=260).pack(fill="x", padx=14, pady=(0, 10))

    def _resumen(self):
        for w in self.resumen.winfo_children():
            w.destroy()
        res = self.res
        if res.estado != "optimo":
            return
        fr = self.var_frac.get()
        self.tarjeta(0, "VALOR ÓPTIMO  Z*", fmt(res.z, fr),
                     "Maximización" if self.p.tipo == "max" else "Minimización")
        self.tarjeta(1, "VECTOR ÓPTIMO  x*", "(" + ", ".join(fmt(v, fr) for v in res.x) + ")",
                     " · ".join(f"x{j + 1} = {fmt(v, fr)}" for j, v in enumerate(res.x)))
        self.tarjeta(2, "VARIABLES BÁSICAS", ", ".join(res.basicas),
                     " · ".join(f"{k} = {fmt(v, fr)}" for k, v in res.basicas.items()), grande=False)

    def titulo(self, i, N):
        if i == 0:
            return "Tabla inicial"
        if i == N - 1:
            return "Tabla final"
        return f"Iteración {i}"

    def ir(self, d):
        if self.res and self.res.historial:
            self.idx = max(0, min(len(self.res.historial) - 1, self.idx + d))
            self.var_vista.set("una")
            self.render_tablas()

    def ir_a(self, k):
        self.idx = k
        self.var_vista.set("una")
        self.render_tablas()

    def render_tablas(self):
        t = self.t
        for w in self.tabs.winfo_children():
            w.destroy()
        for w in self.chips.winfo_children():
            w.destroy()
        hist = self.res.historial if self.res else []
        N = len(hist)
        if not N:
            self.lbl_iter.configure(text="")
            tk.Label(self.tabs, text="No se generaron tablas para este caso.", font=self.f(10),
                     bg=t["bg"], fg=t["text2"]).pack(anchor="w", pady=8)
            return
        self.idx = max(0, min(N - 1, self.idx))
        self.lbl_iter.configure(text=self.titulo(self.idx, N))

        if 1 < N <= 20:
            for i in range(N):
                sel = i == self.idx
                lb = tk.Label(self.chips, text=str(i), width=3, pady=3, cursor="hand2", font=self.f(9, sel),
                              bg=t["primary"] if sel else t["field"],
                              fg=t["on_primary"] if sel else t["text2"],
                              highlightthickness=1, highlightbackground=t["border_field"])
                lb.pack(side="left", padx=2)
                lb.bind("<Button-1>", lambda e, k=i: self.ir_a(k))

        if self.var_vista.get() == "una":
            self.tabla(hist[self.idx], self.idx, N)
        else:
            for i, it in enumerate(hist):
                self.tabla(it, i, N)
        cv = self.scrolls[str(self.tabs_cont)]
        self.root.after_idle(lambda: cv.yview_moveto(0))

    def tabla(self, it, idx, N):
        t, fr = self.t, self.var_frac.get()
        T, cols, m = it.tableau, it.columnas, len(it.basicas)
        fp, cp = it.fila_pivote, it.col_pivote
        nc = len(cols)

        bloque = tk.Frame(self.tabs, bg=t["bg"])
        bloque.pack(anchor="w", pady=(0, 20))
        if self.var_vista.get() == "todas":
            tk.Label(bloque, text=self.titulo(idx, N), font=self.f(11, True), bg=t["bg"],
                     fg=t["text"]).pack(anchor="w")
        if it.texto:
            tk.Label(bloque, text=it.texto, font=self.f(9), bg=t["bg"], fg=t["text2"], justify="left",
                     anchor="w").pack(anchor="w", pady=(0, 6))

        theta_col = theta_fila = None
        if fp is not None and cp is not None:
            if self.metodo == "primal":
                theta_col = [T[i, -1] / T[i, cp] if T[i, cp] > TOL else None for i in range(m)]
            else:
                theta_fila = [T[-1, j] / -T[fp, j] if T[fp, j] < -TOL else None for j in range(nc)]

        grid = tk.Frame(bloque, bg=t["sep"], padx=1, pady=1)
        grid.pack(anchor="w")

        def cell(r, c, texto, bg, fg, bold=False):
            tk.Label(grid, text=texto, bg=bg, fg=fg, font=self.f(10, bold), width=7, padx=8, pady=7
                     ).grid(row=r, column=c, padx=1, pady=1, sticky="nsew")

        def color(i, j):
            if i == fp and j == cp:
                return t["primary"], t["on_primary"], True
            if (cp is not None and j == cp) or (fp is not None and i == fp):
                if fp is None:
                    return t["err_bg"], t["err_fg"], False
                return t["soft"], t["text"], False
            if i == m:
                return t["info"], t["highlight"], True
            if j == nc:
                return t["result_col"], t["text"], False
            return t["field"], t["text"], False

        cell(0, 0, "Base", t["thead"], t["label"], True)
        for j, nombre in enumerate(cols + ["b"]):
            activo = j == cp
            cell(0, j + 1, nombre, t["soft"] if activo else t["thead"],
                 t["highlight"] if activo else t["label"], True)
        if theta_col is not None:
            cell(0, nc + 2, "θ", t["thead"], t["label"], True)

        for i in range(m + 1):
            nombre = it.basicas[i] if i < m else "Z"
            salida = i == fp
            cell(i + 1, 0, nombre, t["soft"] if salida else t["thead"],
                 t["highlight"] if salida else t["text"], True)
            for j in range(nc + 1):
                bg, fg, b = color(i, j)
                cell(i + 1, j + 1, fmt(T[i, j], fr), bg, fg, b)
            if theta_col is not None:
                v = theta_col[i] if i < m else None
                elegido = i == fp
                cell(i + 1, nc + 2, "—" if v is None else fmt(v, fr), t["field"],
                     t["highlight"] if elegido else t["text2"], elegido)

        if theta_fila is not None:
            cell(m + 2, 0, "θ", t["thead"], t["label"], True)
            for j in range(nc):
                v = theta_fila[j]
                cell(m + 2, j + 1, "—" if v is None else fmt(v, fr), t["field"],
                     t["highlight"] if j == cp else t["text2"], j == cp)
            cell(m + 2, nc + 1, "", t["field"], t["text2"])

        if self.p.tipo == "min":
            tk.Label(bloque, text="En minimización la fila Z corresponde a −Z (se resuelve máx −Z).",
                     font=self.f(8), bg=t["bg"], fg=t["faint"]).pack(anchor="w", pady=(4, 0))


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()