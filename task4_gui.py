#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import io
import os

try:
    import graphviz
    GRAPHVIZ_OK = True
except ImportError:
    GRAPHVIZ_OK = False

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

from task3_dfa import build_dfa, minimize_dfa, get_transition_table, DFAResult
from task2_followpos import followpos_table_str

C = {
    "bg":           "#0A1628",
    "surface":      "#111F35",
    "surface2":     "#172843",
    "surface3":     "#1E3354",
    "border":       "#243D5E",
    "border_light": "#2E5080",
    "accent":       "#F5C518",
    "accent_hover": "#FFD740",
    "accent_dim":   "#A07C10",
    "blue":         "#1E88E5",
    "blue_light":   "#42A5F5",
    "blue_dark":    "#1050A0",
    "success":      "#00E676",
    "success_bg":   "#081F0F",
    "success_dim":  "#0D3018",
    "error":        "#FF3D57",
    "error_bg":     "#1F0508",
    "error_dim":    "#3A0810",
    "warning":      "#FFB300",
    "text":         "#DCE9FF",
    "text_dim":     "#6A88AA",
    "text_muted":   "#3A5570",
    "white":        "#FFFFFF",
    "tbl_header":   "#0D2040",
    "tbl_row":      "#132030",
    "tbl_row_alt":  "#172843",
}

IS_WIN = os.name == "nt"
FONT_MONO   = ("Consolas",    11) if IS_WIN else ("Courier New", 11)
FONT_MONO_S = ("Consolas",    10) if IS_WIN else ("Courier New", 10)
FONT_UI     = ("Segoe UI",     9) if IS_WIN else ("Helvetica",    9)
FONT_UI_B   = ("Segoe UI",     9, "bold") if IS_WIN else ("Helvetica", 9, "bold")
FONT_SUB    = ("Segoe UI",     8)         if IS_WIN else ("Helvetica",  8)
FONT_HEAD   = ("Segoe UI",    10, "bold") if IS_WIN else ("Helvetica", 10, "bold")
FONT_TAB    = ("Segoe UI",    10, "bold") if IS_WIN else ("Helvetica", 10, "bold")

EXAMPLES = ["(a|b)*a", "ab*c", "(a|b)+", "a?b", "(ab|cd)*e", "a(b|c)*d"]


class HoverButton(tk.Button):
    def __init__(self, master, bg_normal, bg_hover, fg_normal=None, fg_hover=None, **kwargs):
        self._bg_n = bg_normal
        self._bg_h = bg_hover
        self._fg_n = fg_normal or C["text"]
        self._fg_h = fg_hover  or C["white"]
        super().__init__(master, bg=bg_normal, fg=self._fg_n,
                         activebackground=bg_hover, activeforeground=self._fg_h,
                         relief="flat", bd=0, cursor="hand2", **kwargs)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _): self.config(bg=self._bg_h, fg=self._fg_h)
    def _on_leave(self, _): self.config(bg=self._bg_n, fg=self._fg_n)


def make_scrollable_table(parent, columns, col_weights=None):
    """Build a header + scrollable body table, return (outer_frame, inner_frame, header_frame)."""
    outer = tk.Frame(parent, bg=C["surface2"])
    outer.pack(fill="both", expand=True)

    header_frame = tk.Frame(outer, bg=C["tbl_header"])
    header_frame.pack(fill="x")
    weights = col_weights or [1] * len(columns)
    for i, col in enumerate(columns):
        tk.Label(header_frame, text=col, font=FONT_UI_B,
                 bg=C["tbl_header"], fg=C["accent"],
                 anchor="w", padx=12, pady=8).grid(row=0, column=i, sticky="ew")
        header_frame.columnconfigure(i, weight=weights[i])

    scroll_wrap = tk.Frame(outer, bg=C["surface2"])
    scroll_wrap.pack(fill="both", expand=True)
    canvas = tk.Canvas(scroll_wrap, bg=C["surface2"], highlightthickness=0)
    vsb    = ttk.Scrollbar(scroll_wrap, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=C["surface2"])
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
    canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    return outer, inner, header_frame, canvas


class RegexDFAApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Converter — Regex to DFA")
        self.geometry("1340x900")
        self.minsize(1100, 760)
        self.configure(bg=C["bg"])

        self._dfa         = None
        self._raw_pil     = None
        self._graph_image = None
        self._png_bytes   = None
        self._zoom        = 1.0
        self._img_x       = 0
        self._img_y       = 0
        self._drag_start  = None

        self._build_styles()
        self._build_ui()
        self._set_status("Ready — enter a regex and press Convert", "normal")

    def _build_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TNotebook", background=C["bg"], borderwidth=0, tabmargins=[0,0,0,0])
        s.configure("TNotebook.Tab",
                    background=C["surface2"], foreground=C["text_dim"],
                    font=FONT_TAB, padding=(18, 9), borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", C["surface3"])],
              foreground=[("selected", C["accent"])],
              expand=[("selected", [0,0,0,0])])
        s.configure("TScrollbar", background=C["surface3"],
                    troughcolor=C["surface"], borderwidth=0, arrowsize=11)
        s.map("TScrollbar", background=[("active", C["border_light"])])

    def _build_ui(self):
        self._build_topbar()
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=52)
        body.columnconfigure(1, weight=48)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=C["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=10)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        self._build_control_panel(left)
        self._build_graph_area(left)

        right = tk.Frame(body, bg=C["surface"], highlightthickness=1,
                         highlightbackground=C["border"])
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=10)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)
        self._build_info_panel(right)

        self._build_statusbar()

    def _build_topbar(self):
        bar = tk.Frame(self, bg=C["surface"], height=58)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        lg = tk.Frame(bar, bg=C["surface"])
        lg.pack(side="left", padx=(18, 0), pady=10)
        tk.Label(lg, text="⬡", font=("Segoe UI", 20),
                 bg=C["surface"], fg=C["accent"]).pack(side="left", padx=(0, 10))
        ts = tk.Frame(lg, bg=C["surface"])
        ts.pack(side="left")
        tk.Label(ts, text="Smart Converter",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(anchor="w")
        tk.Label(ts, text="Regex to DFA",
                 font=FONT_SUB, bg=C["surface"], fg=C["text_dim"]).pack(anchor="w")

        tk.Frame(bar, bg=C["accent"], width=2, height=26).pack(
            side="left", padx=18, pady=16)

        for lbl, cmd in [("⬇ Export PNG", self._download_png),
                          ("ℹ About",       self._show_about)]:
            HoverButton(bar, C["surface2"], C["surface3"],
                        fg_normal=C["text_dim"], fg_hover=C["accent"],
                        text=lbl, command=cmd,
                        font=FONT_UI, padx=14, pady=8
                        ).pack(side="right", padx=4, pady=10)
        tk.Frame(bar, bg=C["border"], height=1).pack(side="bottom", fill="x")

    def _build_control_panel(self, parent):
        panel = tk.Frame(parent, bg=C["surface"], highlightthickness=1,
                         highlightbackground=C["border"])
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Frame(panel, bg=C["accent"], height=3).pack(fill="x", side="top")

        hdr = tk.Frame(panel, bg=C["surface"], pady=10)
        hdr.pack(fill="x", padx=16)
        tk.Label(hdr, text="Regular Expression",
                 font=("Segoe UI", 12, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(side="left")
        tk.Label(hdr, text="  Converter",
                 font=("Segoe UI", 12),
                 bg=C["surface"], fg=C["accent"]).pack(side="left")

        r1 = tk.Frame(panel, bg=C["surface"])
        r1.pack(fill="x", padx=16, pady=(0, 10))
        inp = tk.Frame(r1, bg=C["surface3"], highlightthickness=1,
                       highlightbackground=C["border_light"])
        inp.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(inp, text="∑*", font=("Segoe UI", 10, "bold"),
                 bg=C["surface3"], fg=C["text_muted"], padx=10).pack(side="left")
        self._regex_var = tk.StringVar(value="(aa|b)*a")
        self._entry = tk.Entry(inp, textvariable=self._regex_var,
                               font=("Consolas", 13) if IS_WIN else ("Courier New", 13),
                               bg=C["surface3"], fg=C["accent"],
                               insertbackground=C["accent"],
                               relief="flat", bd=0, highlightthickness=0)
        self._entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        self._entry.bind("<Return>", lambda e: self._on_convert())
        HoverButton(r1, C["accent"], C["accent_hover"],
                    fg_normal=C["bg"], fg_hover=C["bg"],
                    text="Convert", command=self._on_convert,
                    font=("Segoe UI", 10, "bold"), padx=24, pady=9
                    ).pack(side="left")

        ex_row = tk.Frame(panel, bg=C["surface"])
        ex_row.pack(fill="x", padx=16, pady=(0, 10))
        tk.Label(ex_row, text="Examples:", font=FONT_UI_B,
                 bg=C["surface"], fg=C["text_dim"]).pack(side="left", padx=(0, 8))
        for ex in EXAMPLES:
            HoverButton(ex_row, C["surface2"], C["surface3"],
                        fg_normal=C["text_dim"], fg_hover=C["accent"],
                        text=ex, command=lambda e=ex: self._use_example(e),
                        font=("Consolas", 8) if IS_WIN else ("Courier New", 8),
                        padx=8, pady=4).pack(side="left", padx=2)

        opt = tk.Frame(panel, bg=C["surface"])
        opt.pack(fill="x", padx=16, pady=(0, 12))
        self._minimize_var = tk.BooleanVar(value=False)
        chk_f = tk.Frame(opt, bg=C["surface2"], highlightthickness=1,
                         highlightbackground=C["border"])
        chk_f.pack(side="left", padx=(0, 16))
        tk.Checkbutton(chk_f, text=" Hopcroft Minimization",
                       variable=self._minimize_var,
                       bg=C["surface2"], fg=C["text_dim"],
                       selectcolor=C["accent_dim"],
                       activebackground=C["surface2"],
                       activeforeground=C["text"],
                       font=FONT_UI, relief="flat", bd=0,
                       cursor="hand2", padx=10, pady=7).pack()

        test_f = tk.Frame(opt, bg=C["surface3"], highlightthickness=1,
                          highlightbackground=C["border_light"])
        test_f.pack(side="left", padx=(0, 10))
        tk.Label(test_f, text="Test:", font=FONT_UI_B,
                 bg=C["surface3"], fg=C["text_dim"], padx=8).pack(side="left")
        self._test_var = tk.StringVar()
        self._test_entry = tk.Entry(test_f, textvariable=self._test_var, width=16,
                                    font=FONT_MONO_S,
                                    bg=C["surface3"], fg=C["text_dim"],
                                    insertbackground=C["accent"],
                                    relief="flat", bd=0)
        self._test_entry.pack(side="left", ipady=7, padx=(0, 10))
        self._test_entry.insert(0, "e.g. aba")
        self._test_entry.bind("<FocusIn>",  self._clear_ph)
        self._test_entry.bind("<FocusOut>", self._restore_ph)
        self._test_entry.bind("<Return>",   lambda e: self._on_test())
        HoverButton(opt, C["blue_dark"], C["blue"],
                    fg_normal=C["text_dim"], fg_hover=C["white"],
                    text="Test", command=self._on_test,
                    font=FONT_UI_B, padx=18, pady=7).pack(side="left")

    def _build_graph_area(self, parent):
        wrap = tk.Frame(parent, bg=C["surface"], highlightthickness=1,
                        highlightbackground=C["border"])
        wrap.grid(row=1, column=0, sticky="nsew")
        tk.Frame(wrap, bg=C["blue"], height=3).pack(fill="x")

        tb = tk.Frame(wrap, bg=C["surface2"], pady=7)
        tb.pack(fill="x")
        tk.Label(tb, text="DFA Graph", font=FONT_HEAD,
                 bg=C["surface2"], fg=C["text"]).pack(side="left", padx=14)
        zf = tk.Frame(tb, bg=C["surface2"])
        zf.pack(side="left", padx=10)
        for txt, cmd in [("−", self._zoom_out), ("+", self._zoom_in)]:
            HoverButton(zf, C["surface3"], C["border_light"],
                        fg_normal=C["text"], fg_hover=C["accent"],
                        text=txt, command=cmd,
                        font=("Segoe UI", 12, "bold"), width=2,
                        padx=2, pady=2).pack(side="left", padx=2)
        for txt, cmd in [("Reset", self._zoom_reset), ("Fit", self._auto_layout)]:
            HoverButton(zf, C["surface3"], C["border_light"],
                        fg_normal=C["text_dim"], fg_hover=C["text"],
                        text=txt, command=cmd,
                        font=FONT_UI, padx=8, pady=3).pack(side="left", padx=2)
        self._zoom_label = tk.Label(tb, text="100%", font=FONT_UI,
                                    bg=C["surface2"], fg=C["text_dim"])
        self._zoom_label.pack(side="left", padx=8)
        HoverButton(tb, C["accent_dim"], C["accent"],
                    fg_normal=C["bg"], fg_hover=C["bg"],
                    text="⬇ Export PNG", command=self._download_png,
                    font=FONT_UI_B, padx=12, pady=4).pack(side="right", padx=12)

        cf = tk.Frame(wrap, bg=C["bg"])
        cf.pack(fill="both", expand=True, padx=2, pady=2)
        self._canvas = tk.Canvas(cf, bg="#000000", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        self._placeholder_text = self._canvas.create_text(
            500, 280,
            text="Enter a regex and press Convert\nto visualize the DFA",
            fill=C["text_muted"], font=("Segoe UI", 12), justify="center")

        leg = tk.Frame(wrap, bg=C["surface2"], height=34)
        leg.pack(fill="x", side="bottom")
        leg.pack_propagate(False)
        for col, lbl in [("#FFFFFF", "Start"), (C["success"], "Accept"),
                         (C["error"], "Dead"),  (C["text_dim"], "Normal")]:
            tk.Label(leg, text="●", font=("Segoe UI", 10),
                     bg=C["surface2"], fg=col).pack(side="left", padx=(12, 3))
            tk.Label(leg, text=lbl, font=("Segoe UI", 8),
                     bg=C["surface2"], fg=C["text_dim"]).pack(side="left", padx=(0, 8))

        self._canvas.bind("<Configure>",     self._on_canvas_resize)
        self._canvas.bind("<ButtonPress-1>", self._pan_start)
        self._canvas.bind("<B1-Motion>",     self._pan_move)
        self._canvas.bind("<MouseWheel>",    self._mouse_wheel)

    def _build_info_panel(self, parent):
        tk.Frame(parent, bg=C["accent"], height=3).pack(fill="x", side="top")

        hdr = tk.Frame(parent, bg=C["surface"], pady=10)
        hdr.pack(fill="x", padx=14)
        tk.Label(hdr, text="DFA Details",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(side="left")

        cg = tk.Frame(parent, bg=C["surface"])
        cg.pack(fill="x", padx=10, pady=(0, 8))
        for i in range(3):
            cg.columnconfigure(i, weight=1)

        def make_card(row, col, icon, label, attr, acc):
            card = tk.Frame(cg, bg=C["surface2"], highlightthickness=1,
                            highlightbackground=C["border"])
            card.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            top = tk.Frame(card, bg=C["surface2"])
            top.pack(fill="x", padx=10, pady=(7, 2))
            tk.Label(top, text=icon, font=("Segoe UI", 12),
                     bg=C["surface2"], fg=acc).pack(side="left")
            tk.Label(top, text=" " + label, font=("Segoe UI", 7, "bold"),
                     bg=C["surface2"], fg=C["text_muted"]).pack(side="left")
            val = tk.Label(card, text="—",
                           font=("Consolas", 13, "bold") if IS_WIN else ("Courier New", 13, "bold"),
                           bg=C["surface2"], fg=C["text_dim"],
                           anchor="w", padx=12)
            val.pack(fill="x", pady=(0, 9))
            setattr(self, attr, val)

        make_card(0, 0, "◈", "STATES",  "_card_states", C["blue_light"])
        make_card(0, 1, "∑", "ALPHABET","_card_alpha",  C["accent"])
        make_card(0, 2, "▶", "START",   "_card_start",  "#FFFFFF")
        make_card(1, 0, "✔", "ACCEPT",  "_card_accept", C["success"])
        make_card(1, 1, "✘", "DEAD",    "_card_dead",   C["error"])
        make_card(1, 2, "#", "END-POS", "_card_endpos", C["warning"])

        self._test_result_frame = tk.Frame(parent, bg=C["surface2"],
                                           highlightthickness=1,
                                           highlightbackground=C["border"])
        self._test_result_frame.pack(fill="x", padx=10, pady=(0, 8))
        self._test_result_label = tk.Label(
            self._test_result_frame, text="No test run yet.",
            font=("Segoe UI", 10, "bold"),
            bg=C["surface2"], fg=C["text_muted"],
            anchor="w", padx=14, pady=9)
        self._test_result_label.pack(fill="x")

        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._followpos_tab   = ttk.Frame(nb)
        self._transitions_tab = ttk.Frame(nb)
        self._syntax_tab      = ttk.Frame(nb)
        self._min_tab         = ttk.Frame(nb)
        nb.add(self._followpos_tab,   text="  FollowPos  ")
        nb.add(self._transitions_tab, text="  Transitions  ")
        nb.add(self._syntax_tab,      text="  Syntax Tree  ")
        nb.add(self._min_tab,         text="  Minimization  ")

        self._build_followpos_tab()
        self._build_transitions_tab()
        self._build_syntax_tab()
        self._build_min_tab()

    def _tab_header(self, parent, icon_text, title, subtitle):
        f = tk.Frame(parent, bg=C["surface2"], pady=7)
        f.pack(fill="x")
        tk.Label(f, text=icon_text + "  " + title, font=FONT_HEAD,
                 bg=C["surface2"], fg=C["accent"], padx=12).pack(side="left")
        tk.Label(f, text=subtitle, font=FONT_SUB,
                 bg=C["surface2"], fg=C["text_dim"], padx=4).pack(side="left")

    def _build_followpos_tab(self):
        wrap = tk.Frame(self._followpos_tab, bg=C["bg"])
        wrap.pack(fill="both", expand=True)
        self._tab_header(wrap, "∮", "FollowPos Table", "Position → Symbol → Follow positions")

        self._fp_inner_ref = None
        self._fp_canvas_ref = None

        _, self._fp_inner_ref, _, self._fp_canvas_ref = make_scrollable_table(
            wrap, ["Pos", "Symbol", "FollowPos"], col_weights=[1, 1, 3])
        self._fp_placeholder = tk.Label(self._fp_inner_ref,
                                        text="Convert a regex to populate this table",
                                        font=FONT_UI, bg=C["surface2"],
                                        fg=C["text_muted"], pady=20)
        self._fp_placeholder.pack()

    def _build_transitions_tab(self):
        wrap = tk.Frame(self._transitions_tab, bg=C["bg"])
        wrap.pack(fill="both", expand=True)
        self._tab_header(wrap, "⇒", "Transition Table", "δ(state, symbol) → next state")
        self._trans_wrap = wrap

    def _build_syntax_tab(self):
        wrap = tk.Frame(self._syntax_tab, bg=C["bg"])
        wrap.pack(fill="both", expand=True)
        self._tab_header(wrap, "🌲", "Syntax Tree", "Augmented parse tree with positions")

        tw = tk.Frame(wrap, bg=C["surface2"])
        tw.pack(fill="both", expand=True)
        self._text_syntax = tk.Text(
            tw, font=FONT_MONO,
            bg=C["surface2"], fg=C["text"],
            wrap="none", relief="flat", bd=0,
            padx=14, pady=10,
            insertbackground=C["accent"],
            selectbackground=C["blue_dark"],
            selectforeground=C["white"])
        sy = ttk.Scrollbar(tw, orient="vertical",   command=self._text_syntax.yview)
        sx = ttk.Scrollbar(tw, orient="horizontal", command=self._text_syntax.xview)
        self._text_syntax.config(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right",  fill="y")
        sx.pack(side="bottom", fill="x")
        self._text_syntax.pack(side="left", fill="both", expand=True)
        self._text_syntax.tag_config("comment",   foreground=C["text_muted"])
        self._text_syntax.tag_config("node_op",   foreground=C["blue_light"])
        self._text_syntax.tag_config("node_char", foreground=C["accent"])
        self._text_syntax.tag_config("node_end",  foreground=C["error"])
        self._text_syntax.tag_config("pos_num",   foreground=C["success"])
        self._text_syntax.tag_config("branch",    foreground=C["text_dim"])
        self._text_syntax.config(state="normal")
        self._text_syntax.insert("end", "// Convert a regex to see the syntax tree", "comment")
        self._text_syntax.config(state="disabled")

    def _build_min_tab(self):
        wrap = tk.Frame(self._min_tab, bg=C["bg"])
        wrap.pack(fill="both", expand=True)
        self._tab_header(wrap, "⚙", "Minimization", "Hopcroft partition refinement")
        self._min_wrap = wrap

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=C["surface"], height=28)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=C["border"], height=1).pack(fill="x", side="top")
        self._status_dot   = tk.Label(bar, text="●", font=("Segoe UI", 8),
                                      bg=C["surface"], fg=C["text_dim"])
        self._status_dot.pack(side="left", padx=(12, 4))
        self._status_label = tk.Label(bar, text="Ready", font=FONT_UI,
                                      bg=C["surface"], fg=C["text_dim"])
        self._status_label.pack(side="left")

    def _set_status(self, msg, kind="normal"):
        c = {"normal": C["text_dim"], "success": C["success"],
             "error": C["error"], "warning": C["warning"], "busy": C["accent"]
             }.get(kind, C["text_dim"])
        self._status_dot.config(fg=c)
        self._status_label.config(text=msg, fg=c)

    def _use_example(self, ex):
        self._regex_var.set(ex)
        self._entry.icursor("end")

    def _clear_ph(self, e):
        if self._test_entry.get() == "e.g. aba":
            self._test_entry.delete(0, "end")
            self._test_entry.config(fg=C["text"])

    def _restore_ph(self, e):
        if not self._test_entry.get():
            self._test_entry.insert(0, "e.g. aba")
            self._test_entry.config(fg=C["text_dim"])

    def _on_convert(self):
        pattern = self._regex_var.get().strip()
        if not pattern:
            messagebox.showwarning("Input Required", "Please enter a regular expression.")
            return
        self._set_status("Processing…", "busy")
        self.update_idletasks()
        try:
            dfa = build_dfa(pattern)
            if self._minimize_var.get():
                dfa = minimize_dfa(dfa)
            self._dfa = dfa
            self._update_all_views()
            self._set_status(
                f"DFA ready — {len(dfa.states)} state{'s' if len(dfa.states)!=1 else ''}",
                "success")
        except Exception as exc:
            self._set_status("Error during conversion", "error")
            messagebox.showerror("Parse Error", str(exc))

    def _on_test(self):
        if self._dfa is None:
            messagebox.showinfo("No DFA", "Please convert a regex first.")
            return
        raw = self._test_var.get().strip()
        if raw == "e.g. aba":
            raw = ""
        ok = self._simulate(raw)
        if ok:
            self._test_result_frame.config(highlightbackground=C["success"],
                                           bg=C["success_bg"])
            self._test_result_label.config(
                text=f"✔  ACCEPTED  —  \"{raw}\"",
                bg=C["success_bg"], fg=C["success"])
            self._set_status(f'"{raw}" was ACCEPTED', "success")
        else:
            self._test_result_frame.config(highlightbackground=C["error"],
                                           bg=C["error_bg"])
            self._test_result_label.config(
                text=f"✘  REJECTED  —  \"{raw}\"",
                bg=C["error_bg"], fg=C["error"])
            self._set_status(f'"{raw}" was REJECTED', "error")

    def _simulate(self, s):
        dfa, state = self._dfa, self._dfa.start
        for ch in s:
            if ch not in dfa.alphabet:
                return False
            state = dfa.transitions.get(state, {}).get(ch, dfa.dead)
            if state is None:
                return False
        return dfa.is_accept(state)

    def _pan_start(self, e): self._drag_start = (e.x, e.y)

    def _pan_move(self, e):
        if self._drag_start and self._graph_image:
            self._img_x += e.x - self._drag_start[0]
            self._img_y += e.y - self._drag_start[1]
            self._drag_start = (e.x, e.y)
            self._place_image()

    def _mouse_wheel(self, e):
        if e.delta > 0: self._zoom_in()
        else:           self._zoom_out()

    def _on_canvas_resize(self, e):
        if self._graph_image:
            self._place_image()
        else:
            self._canvas.coords(self._placeholder_text, e.width // 2, e.height // 2)

    def _place_image(self):
        self._canvas.delete("img")
        cx = self._canvas.winfo_width()  // 2 + self._img_x
        cy = self._canvas.winfo_height() // 2 + self._img_y
        self._canvas.create_image(cx, cy, image=self._graph_image,
                                   anchor="center", tags="img")

    def _zoom_in(self):
        self._zoom = min(self._zoom * 1.2, 6.0)
        self._zoom_label.config(text=f"{int(self._zoom*100)}%")
        self._render_image()

    def _zoom_out(self):
        self._zoom = max(self._zoom / 1.2, 0.1)
        self._zoom_label.config(text=f"{int(self._zoom*100)}%")
        self._render_image()

    def _zoom_reset(self):
        self._zoom = 1.0; self._img_x = 0; self._img_y = 0
        self._zoom_label.config(text="100%")
        self._render_image()

    def _auto_layout(self): self._zoom_reset()

    def _render_image(self):
        if not PIL_OK or self._raw_pil is None:
            return
        w = max(1, int(self._raw_pil.width  * self._zoom))
        h = max(1, int(self._raw_pil.height * self._zoom))
        self._graph_image = ImageTk.PhotoImage(
            self._raw_pil.resize((w, h), Image.LANCZOS))
        self._place_image()

    def _download_png(self):
        if self._png_bytes is None:
            messagebox.showinfo("No Graph", "Convert a regex first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
            initialfile="dfa_graph.png", title="Export DFA Graph")
        if path:
            with open(path, "wb") as f:
                f.write(self._png_bytes)
            self._set_status(f"Exported → {os.path.basename(path)}", "success")

    def _update_all_views(self):
        dfa = self._dfa
        self._card_states.config(text=str(len(dfa.states)), fg=C["blue_light"])
        self._card_alpha.config(text="  ".join(dfa.alphabet) or "—", fg=C["accent"])
        self._card_start.config(text=dfa.name(dfa.start), fg=C["white"])
        self._card_accept.config(
            text=", ".join(dfa.name(s) for s in dfa.accept) or "—",
            fg=C["success"])
        self._card_dead.config(
            text=dfa.name(dfa.dead) if dfa.dead is not None else "—",
            fg=C["error"])
        self._card_endpos.config(text=str(dfa.end_pos), fg=C["warning"])

        self._update_graph()
        self._update_followpos_table(dfa)
        self._update_transitions_table(dfa)
        self._update_syntax_tree()
        self._update_min_table(dfa)

    def _update_followpos_table(self, dfa):
        for w in self._fp_inner_ref.winfo_children():
            w.destroy()
        for pos in sorted(dfa.followpos):
            sym   = dfa.pos_map[pos].value
            fp    = sorted(dfa.followpos[pos])
            fp_str = "{" + ", ".join(str(p) for p in fp) + "}" if fp else "∅"
            idx   = pos - 1
            bg    = C["tbl_row"] if idx % 2 == 0 else C["tbl_row_alt"]
            row_f = tk.Frame(self._fp_inner_ref, bg=bg)
            row_f.pack(fill="x")
            for ci, (val, wt) in enumerate(zip([str(pos), repr(sym), fp_str], [1, 1, 3])):
                fg = C["warning"] if ci == 0 else C["accent"] if ci == 1 else C["text"]
                tk.Label(row_f, text=val, font=FONT_MONO_S, bg=bg, fg=fg,
                         anchor="w", padx=12, pady=7).grid(row=0, column=ci, sticky="ew")
                row_f.columnconfigure(ci, weight=wt)
        self._fp_canvas_ref.configure(scrollregion=self._fp_canvas_ref.bbox("all"))

    def _update_transitions_table(self, dfa):
        for w in self._trans_wrap.winfo_children()[1:]:
            w.destroy()

        cols = ["State"] + dfa.alphabet
        outer = tk.Frame(self._trans_wrap, bg=C["surface2"])
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=C["tbl_header"])
        header.pack(fill="x")
        for i, col in enumerate(cols):
            tk.Label(header, text=col, font=FONT_UI_B,
                     bg=C["tbl_header"], fg=C["accent"],
                     anchor="w", padx=12, pady=8).grid(row=0, column=i, sticky="ew")
            header.columnconfigure(i, weight=1)

        sw = tk.Frame(outer, bg=C["surface2"])
        sw.pack(fill="both", expand=True)
        canv = tk.Canvas(sw, bg=C["surface2"], highlightthickness=0)
        vsb  = ttk.Scrollbar(sw, orient="vertical", command=canv.yview)
        canv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canv, bg=C["surface2"])
        wid   = canv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canv.configure(scrollregion=canv.bbox("all")))
        canv.bind("<Configure>",  lambda e: canv.itemconfig(wid, width=e.width))
        canv.bind("<MouseWheel>", lambda e: canv.yview_scroll(-1 if e.delta > 0 else 1, "units"))

        for idx, s in enumerate(dfa.states):
            bg = C["tbl_row"] if idx % 2 == 0 else C["tbl_row_alt"]
            if dfa.is_accept(s):   bg = C["success_dim"]
            elif dfa.is_dead(s):   bg = C["error_dim"]
            elif s == dfa.start:   bg = C["blue_dark"]
            row_f = tk.Frame(inner, bg=bg)
            row_f.pack(fill="x")
            cells = [dfa.name(s)] + [
                dfa.name(dfa.transitions.get(s, {}).get(a))
                if dfa.transitions.get(s, {}).get(a) is not None else "—"
                for a in dfa.alphabet
            ]
            for ci, val in enumerate(cells):
                fg = C["text"]
                if ci == 0:
                    if dfa.is_accept(s): fg = C["success"]
                    elif dfa.is_dead(s): fg = C["error"]
                    elif s == dfa.start: fg = C["blue_light"]
                elif val != "—":
                    tgt = dfa.transitions.get(s, {}).get(dfa.alphabet[ci - 1])
                    if tgt is not None and dfa.is_accept(tgt):
                        fg = C["success"]
                tk.Label(row_f, text=val, font=FONT_MONO_S, bg=bg, fg=fg,
                         anchor="w", padx=12, pady=7).grid(row=0, column=ci, sticky="ew")
                row_f.columnconfigure(ci, weight=1)

    def _update_syntax_tree(self):
        from task1_parser import parse_regex
        pattern = self._regex_var.get().strip()
        root    = parse_regex(pattern)
        self._text_syntax.config(state="normal")
        self._text_syntax.delete("1.0", "end")
        self._text_syntax.insert("end", f"// Augmented Syntax Tree — {pattern}\n", "comment")
        self._text_syntax.insert("end", "\n")

        def dump(node, prefix="", is_last=True):
            if node is None:
                return
            conn = "└── " if is_last else "├── "
            ext  = "    " if is_last else "│   "
            self._text_syntax.insert("end", prefix, "branch")
            self._text_syntax.insert("end", conn,   "branch")
            if node.ntype == "CHAR":
                self._text_syntax.insert("end", f"CHAR({node.value!r})", "node_char")
                self._text_syntax.insert("end", "  pos=", "branch")
                self._text_syntax.insert("end", str(node.pos), "pos_num")
            elif node.ntype == "END":
                self._text_syntax.insert("end", "END(#)", "node_end")
                self._text_syntax.insert("end", "  pos=", "branch")
                self._text_syntax.insert("end", str(node.pos), "pos_num")
            else:
                self._text_syntax.insert("end", node.ntype, "node_op")
            self._text_syntax.insert("end", "\n")
            kids = [c for c in (node.left, node.right) if c]
            for i, child in enumerate(kids):
                dump(child, prefix + ext, i == len(kids) - 1)

        dump(root)
        self._text_syntax.config(state="disabled")

    def _update_min_table(self, dfa):
        for w in self._min_wrap.winfo_children()[1:]:
            w.destroy()

        outer = tk.Frame(self._min_wrap, bg=C["surface2"])
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=C["tbl_header"])
        header.pack(fill="x")
        for i, col in enumerate(["Property", "Value"]):
            tk.Label(header, text=col, font=FONT_UI_B,
                     bg=C["tbl_header"], fg=C["accent"],
                     anchor="w", padx=12, pady=8).grid(row=0, column=i, sticky="ew")
            header.columnconfigure(i, weight=1)

        rows = [
            ("Status",        ("✔ Applied" if dfa.minimized else "✘ Not applied",
                               C["success"] if dfa.minimized else C["error"])),
            ("States",        (str(len(dfa.states)), C["blue_light"])),
            ("Alphabet",      ("{ " + ", ".join(dfa.alphabet) + " }", C["accent"])),
            ("Start state",   (dfa.name(dfa.start) + "  =  " + str(sorted(dfa.start)), C["text"])),
            ("Accepting",     (", ".join(dfa.name(s) for s in dfa.accept), C["success"])),
        ]
        if dfa.dead is not None:
            rows.append(("Dead state", (dfa.name(dfa.dead), C["error"])))
        rows.append(("End-marker pos", (str(dfa.end_pos), C["warning"])))

        body_f = tk.Frame(outer, bg=C["surface2"])
        body_f.pack(fill="x")
        for idx, (prop, (val, val_fg)) in enumerate(rows):
            bg = C["tbl_row"] if idx % 2 == 0 else C["tbl_row_alt"]
            row_f = tk.Frame(body_f, bg=bg)
            row_f.pack(fill="x")
            tk.Label(row_f, text=prop, font=FONT_UI_B, bg=bg, fg=C["text_dim"],
                     anchor="w", padx=12, pady=9).grid(row=0, column=0, sticky="ew")
            tk.Label(row_f, text=val,  font=FONT_MONO_S, bg=bg, fg=val_fg,
                     anchor="w", padx=12, pady=9).grid(row=0, column=1, sticky="ew")
            row_f.columnconfigure(0, weight=1)
            row_f.columnconfigure(1, weight=2)

    def _update_graph(self):
        self._canvas.delete("all")
        if not GRAPHVIZ_OK:
            self._canvas.create_text(
                self._canvas.winfo_width() // 2 or 400,
                self._canvas.winfo_height() // 2 or 300,
                text="graphviz not installed\npip install graphviz",
                fill=C["text_dim"], font=("Segoe UI", 13), justify="center")
            return

        dfa = self._dfa
        dot = graphviz.Digraph(engine="dot")
        dot.attr(rankdir="LR", bgcolor="black", fontname="Consolas",
                 nodesep="0.9", ranksep="1.3", pad="0.5")

        for state in dfa.states:
            sn = dfa.name(state)
            if dfa.is_dead(state):
                nc, fc, lc, sh = "#FF3D57", "#1A0008", "#FF3D57", "circle"
            elif dfa.is_accept(state):
                nc, fc, lc, sh = "#00E676", "#001A08", "#00E676", "doublecircle"
            elif state == dfa.start:
                nc, fc, lc, sh = "#FFFFFF", "#0A0A0A", "#FFFFFF", "circle"
            else:
                nc, fc, lc, sh = "#42A5F5", "#050F1A", "#42A5F5", "circle"
            dot.node(sn, sn, shape=sh, color=nc, fillcolor=fc,
                     style="filled", fontcolor=lc,
                     fontname="Consolas", fontsize="12", penwidth="2.2")

        dot.node("__s__", "", shape="point", width="0", color="white")
        dot.edge("__s__", dfa.name(dfa.start), color="white", penwidth="1.6")

        for state, trans in dfa.transitions.items():
            grouped = {}
            for sym, tgt in trans.items():
                grouped.setdefault(tgt, []).append(sym)
            for tgt, syms in grouped.items():
                lbl  = ", ".join(sorted(syms))
                ecol = "#F5C518" if tgt != state else "#5A4400"
                dot.edge(dfa.name(state), dfa.name(tgt),
                         label=lbl, fontsize="10",
                         fontname="Consolas", fontcolor="#F5C518",
                         color=ecol, penwidth="1.5")

        try:
            self._png_bytes = dot.pipe(format="png")
        except Exception as exc:
            messagebox.showerror("Graphviz Error", str(exc))
            return

        self._raw_pil = Image.open(io.BytesIO(self._png_bytes))
        self._zoom = 1.0; self._img_x = 0; self._img_y = 0
        self._zoom_label.config(text="100%")
        self._render_image()

    def _show_about(self):
        messagebox.showinfo(
            "About — Smart Converter",
            "Smart Converter  ·  Regex to DFA\n\n"
            "Converts regular expressions to deterministic finite automata\n"
            "using the direct construction (followpos) method.\n\n"
            "Built with Python, Tkinter, and Graphviz.\n"
            "© 2025 Theory of Computation Project")


def main():
    if not GRAPHVIZ_OK:
        print("[!] pip install graphviz  +  Graphviz binaries from graphviz.org")
    if not PIL_OK:
        print("[!] pip install pillow")
    app = RegexDFAApp()
    app.mainloop()


if __name__ == "__main__":
    main()