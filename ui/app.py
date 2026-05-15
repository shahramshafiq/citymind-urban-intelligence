# ui/app.py
# Main application shell, sidebar, top bar and bottom bar
import tkinter as tk
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from city_graph import CityGraph, RiskLevel
from simulation import Simulation

TH = {
    "bg": "#1A1410",
    "surface": "#221A12",
    "panel": "#2A2017",
    "panel_hi": "#33271C",
    "card": "#382A1E",
    "border": "#3F3024",
    "border2": "#5C4732",
    "text": "#F2E5CC",
    "muted": "#7A6850",
    "muted2": "#9B8769",
    "amber": "#E8A442",
    "amber_l": "#F2C176",
    "amber_d": "#6E4A14",
    "sage": "#7FAA85",
    "sage_l": "#A6CDB1",
    "sage_d": "#2D4632",
    "coral": "#D9633D",
    "coral_l": "#EE8E72",
    "coral_d": "#5C2818",
    "ivory": "#F5EAD2",
    "rust": "#B05C3D",
    "gold": "#D4A24F",
}

GRID_ROWS = 10
GRID_COLS = 10

class CityMindApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CityMind  —  Urban Intelligence System")
        self.geometry("1400x880")
        self.minsize(1100, 720)
        self.configure(bg=TH["bg"])

        self.graph = CityGraph(GRID_ROWS, GRID_COLS)
        self.sim = Simulation(self.graph)
        self.auto_run = False
        self.sim_speed = 1000
        self._busy = False

        self._build_layout()
        self._build_topbar()
        self._build_sidebar()
        self._build_content()
        self._build_bottombar()

        # computing overlay shown while simulation runs in background
        self._overlay = tk.Label(self, text="  COMPUTING...  ", bg=TH["amber_d"], fg=TH["amber_l"], font=("Segoe UI", 11, "bold"), padx=20, pady=8)

        self.current_screen = None
        self.show_screen("layout")
        self.sim.register_observer(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # run setup in background so UI doesnt freeze
        self._run_threaded(self.sim.setup, self._on_setup_done)

    def _build_layout(self):
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.columnconfigure(0, weight=1)

    # top bar with logo, status pills and title
    def _build_topbar(self):
        bar = tk.Frame(self, bg=TH["surface"], height=58)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)

        logoBox = tk.Frame(bar, bg=TH["surface"])
        logoBox.pack(side="left", padx=(20, 4), pady=10)

        canvas = tk.Canvas(logoBox, width=28, height=28, bg=TH["surface"], highlightthickness=0)
        canvas.pack(side="left", padx=(0, 10))
        canvas.create_polygon(14, 2, 26, 14, 14, 26, 2, 14, fill=TH["amber"], outline=TH["amber_l"], width=1)
        canvas.create_polygon(14, 9, 19, 14, 14, 19, 9, 14, fill=TH["surface"], outline="")

        titleBox = tk.Frame(logoBox, bg=TH["surface"])
        titleBox.pack(side="left")
        tk.Label(titleBox, text="CITYMIND", bg=TH["surface"], fg=TH["ivory"], font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(titleBox, text="urban intelligence system", bg=TH["surface"], fg=TH["muted"], font=("Segoe UI", 8)).pack(anchor="w")

        tk.Frame(bar, bg=TH["border2"], width=1).pack(side="left", fill="y", padx=14, pady=12)

        self.pill_status = self._pill(bar, "READY",        TH["sage_l"],  TH["sage_d"])
        self.pill_step   = self._pill(bar, "STEP 00 / 20", TH["amber_l"], TH["amber_d"])
        self.pill_alert  = self._pill(bar, "0 CLOSURES",   TH["coral_l"], TH["coral_d"])

        for pill in (self.pill_status, self.pill_step, self.pill_alert):
            pill.pack(side="left", padx=4, pady=14)

        rightBox = tk.Frame(bar, bg=TH["surface"])
        rightBox.pack(side="right", padx=20, pady=10)
        tk.Label(rightBox, text="EMERGENCY OPERATIONS CENTRE", bg=TH["surface"], fg=TH["muted2"], font=("Segoe UI", 9, "bold")).pack(anchor="e")
        tk.Label(rightBox, text="LIVE  |  AI-DRIVEN", bg=TH["surface"], fg=TH["amber"], font=("Segoe UI", 7, "bold")).pack(anchor="e")

    def _pill(self, parent, text, fg, bg):
        f = tk.Frame(parent, bg=bg, padx=12, pady=4)
        lbl = tk.Label(f, text=text, bg=bg, fg=fg, font=("Segoe UI", 8, "bold"))
        lbl.pack()
        f._label = lbl
        return f

    # left sidebar with navigation buttons and building type legend
    def _build_sidebar(self):
        self.sidebar_shell = tk.Frame(self, bg=TH["panel"], width=235)
        self.sidebar_shell.grid(row=1, column=0, sticky="nsw")
        self.sidebar_shell.grid_propagate(False)
        self.sidebar_shell.rowconfigure(0, weight=1)
        self.sidebar_shell.columnconfigure(0, weight=1)

        self.sidebar_canvas = tk.Canvas(
            self.sidebar_shell,
            bg=TH["panel"],
            highlightthickness=0,
            borderwidth=0,
            yscrollincrement=24,
        )
        self.sidebar_canvas.grid(row=0, column=0, sticky="nsew")

        self.sidebar_scrollbar = tk.Scrollbar(
            self.sidebar_shell,
            orient="vertical",
            command=self.sidebar_canvas.yview,
            bg=TH["panel"],
            troughcolor=TH["surface"],
            activebackground=TH["amber_d"],
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
        )
        self.sidebar_scrollbar.grid(row=0, column=1, sticky="ns")
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scrollbar.set)

        self.sidebar = tk.Frame(self.sidebar_canvas, bg=TH["panel"])
        self._sidebar_window = self.sidebar_canvas.create_window(
            (0, 0),
            window=self.sidebar,
            anchor="nw",
        )
        self.sidebar.bind("<Configure>", self._sync_sidebar_scrollregion)
        self.sidebar_canvas.bind("<Configure>", self._sync_sidebar_width)
        self.sidebar_canvas.bind("<Enter>", self._bind_sidebar_mousewheel)
        self.sidebar_canvas.bind("<Leave>", self._unbind_sidebar_mousewheel)

        self._sidebar_label("VIEWS")
        self.nav_buttons = {}
        navItems = [
            ("layout",   "City Layout",    "CSP placement"),
            ("roads",    "Road Network",   "GA optimisation"),
            ("risk",     "Risk Overview",  "Crime heatmap"),
            ("distance", "Distance Map",   "SA coverage"),
            ("timeline", "Event Timeline", "All events"),
        ]
        for (key, title, sub) in navItems:
            self.nav_buttons[key] = self._nav_btn(self.sidebar, key, title, sub)

        self._sidebar_label("BUILDING TYPES")
        buildingTypes = [
            ("H", TH["amber"],  "Hospital"),
            ("D", TH["sage"],   "Ambulance Depot"),
            ("S", TH["gold"],   "School"),
            ("R", TH["muted2"], "Residential"),
            ("I", TH["coral"],  "Industrial"),
            ("P", "#9B7FAA",    "Power Plant"),
        ]
        for (sym, col, lbl) in buildingTypes:
            self._legend_row(self.sidebar, sym, col, lbl)

        tk.Frame(self.sidebar, bg=TH["border"], height=1).pack(fill="x", padx=14, pady=8)

        self._sidebar_label("ENTITIES")
        entityTypes = [
            ("A", TH["amber"],   "Ambulance"),
            ("T", TH["coral_l"], "Medical Team"),
            ("1", TH["sage_l"],  "Trapped Person"),
            ("x", TH["coral"],   "Flooded Road"),
        ]
        for (sym, col, lbl) in entityTypes:
            self._legend_row(self.sidebar, sym, col, lbl)

        bottom = tk.Frame(self.sidebar, bg=TH["panel"])
        bottom.pack(fill="x", padx=14, pady=12)
        tk.Label(bottom, text="CITYMIND v2.0", bg=TH["panel"], fg=TH["amber"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(bottom, text="ai-powered urban planning", bg=TH["panel"], fg=TH["muted"], font=("Segoe UI", 7)).pack(anchor="w")

    def _sync_sidebar_scrollregion(self, event=None):
        self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))

    def _sync_sidebar_width(self, event):
        self.sidebar_canvas.itemconfigure(self._sidebar_window, width=event.width)

    def _bind_sidebar_mousewheel(self, event=None):
        self.sidebar_canvas.bind_all("<MouseWheel>", self._on_sidebar_mousewheel)
        self.sidebar_canvas.bind_all("<Button-4>", self._on_sidebar_mousewheel)
        self.sidebar_canvas.bind_all("<Button-5>", self._on_sidebar_mousewheel)

    def _unbind_sidebar_mousewheel(self, event=None):
        self.sidebar_canvas.unbind_all("<MouseWheel>")
        self.sidebar_canvas.unbind_all("<Button-4>")
        self.sidebar_canvas.unbind_all("<Button-5>")

    def _on_sidebar_mousewheel(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 * int(event.delta / 120)
        self.sidebar_canvas.yview_scroll(delta, "units")

    def _sidebar_label(self, text):
        f = tk.Frame(self.sidebar, bg=TH["panel"])
        f.pack(fill="x", padx=14, pady=(14, 4))
        tk.Label(f, text=text, bg=TH["panel"], fg=TH["amber"], font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Frame(f, bg=TH["border"], height=1).pack(side="left", fill="x", expand=True, padx=8, pady=(7, 0))

    def _nav_btn(self, parent, key, title, sub):
        f = tk.Frame(parent, bg=TH["panel"], cursor="hand2")
        f.pack(fill="x", padx=10, pady=2)
        accent = tk.Frame(f, bg=TH["panel"], width=3)
        accent.pack(side="left", fill="y")

        inner = tk.Frame(f, bg=TH["panel"], padx=12, pady=10)
        inner.pack(side="left", fill="both", expand=True)

        titleLbl = tk.Label(inner, text=title, bg=TH["panel"], fg=TH["text"], font=("Segoe UI", 11, "bold"), anchor="w")
        titleLbl.pack(anchor="w")
        subLbl = tk.Label(inner, text=sub, bg=TH["panel"], fg=TH["muted"], font=("Segoe UI", 8), anchor="w")
        subLbl.pack(anchor="w")

        for w in (f, inner, titleLbl, subLbl, accent):
            w.bind("<Button-1>", lambda e, k=key: self.show_screen(k))
            w.bind("<Enter>", lambda e, fr=f, ax=accent, ti=titleLbl, su=subLbl, inn=inner: self._nav_hover(fr, ax, ti, su, inn, True))
            w.bind("<Leave>", lambda e, fr=f, ax=accent, ti=titleLbl, su=subLbl, inn=inner: self._nav_hover(fr, ax, ti, su, inn, False))

        f._inner = inner
        f._title = titleLbl
        f._sub = subLbl
        f._accent = accent
        return f

    def _nav_hover(self, frame, accent, titleLbl, subLbl, inner, entering):
        if frame is self.nav_buttons.get(self.current_screen):
            return
        bg = TH["panel_hi"] if entering else TH["panel"]
        frame.configure(bg=bg)
        inner.configure(bg=bg)
        titleLbl.configure(bg=bg)
        subLbl.configure(bg=bg)
        accent.configure(bg=TH["amber_d"] if entering else TH["panel"])

    def _legend_row(self, parent, sym, col, lbl):
        f = tk.Frame(parent, bg=TH["panel"])
        f.pack(fill="x", padx=18, pady=2)
        tk.Label(f, text=sym, bg=TH["panel"], fg=col, font=("Consolas", 9, "bold"), width=3).pack(side="left")
        tk.Label(f, text=lbl, bg=TH["panel"], fg=TH["muted2"], font=("Segoe UI", 9)).pack(side="left", padx=4)

    # main content area where all screens sit on top of each other
    def _build_content(self):
        self.content = tk.Frame(self, bg=TH["bg"])
        self.content.grid(row=1, column=0, sticky="nsew", padx=(235, 0))

        from ui.screen_layout   import ScreenLayout
        from ui.screen_roads    import ScreenRoads
        from ui.screen_risk     import ScreenRisk
        from ui.screen_distance import ScreenDistance
        from ui.screen_timeline import ScreenTimeline

        self.screens = {
            "layout": ScreenLayout(self.content, self),
            "roads": ScreenRoads(self.content, self),
            "risk": ScreenRisk(self.content, self),
            "distance": ScreenDistance(self.content, self),
            "timeline": ScreenTimeline(self.content, self),
        }
        for screen in self.screens.values():
            screen.place(relx=0, rely=0, relwidth=1, relheight=1)
            screen.lower()

    # bottom bar with step/auto/reset buttons, speed controls, progress dots
    def _build_bottombar(self):
        bar = tk.Frame(self, bg=TH["surface"], height=56)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)

        btnBox = tk.Frame(bar, bg=TH["surface"])
        btnBox.pack(side="left", padx=18, pady=10)

        self._action_btn(btnBox, "   NEXT STEP", self._next_step, TH["amber"], TH["amber_d"], TH["bg"])
        self.auto_btn = self._action_btn(btnBox, "AUTO", self._toggle_auto, TH["sage"], TH["sage_d"], TH["bg"])
        self._action_btn(btnBox, "RESET", self._reset, TH["muted2"], TH["panel"], TH["text"], minor=True)

        # speed selector buttons
        speedBox = tk.Frame(bar, bg=TH["surface"])
        speedBox.pack(side="left", padx=16, pady=10)
        tk.Label(speedBox, text="SPEED", bg=TH["surface"], fg=TH["muted"], font=("Segoe UI", 7, "bold")).pack(side="left")
        for (label, ms) in [("0.5x", 2000), ("1x", 1000), ("2x", 500), ("4x", 250)]:
            btn = tk.Button(speedBox, text=label, command=lambda m=ms: self._set_speed(m), bg=TH["panel"], fg=TH["muted2"], font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", borderwidth=0, activebackground=TH["amber_d"], activeforeground=TH["amber_l"])
            btn.pack(side="left", padx=2)

        # progress dots - one per simulation step
        self.step_frame = tk.Frame(bar, bg=TH["surface"])
        self.step_frame.pack(side="left", padx=16, pady=14)
        tk.Label(self.step_frame, text="PROGRESS", bg=TH["surface"], fg=TH["muted"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        dotBox = tk.Frame(self.step_frame, bg=TH["surface"])
        dotBox.pack(anchor="w", pady=(2, 0))
        self.step_dots = []
        for i in range(20):
            d = tk.Frame(dotBox, bg=TH["border"], width=16, height=5)
            d.pack(side="left", padx=1)
            self.step_dots.append(d)

        right = tk.Frame(bar, bg=TH["surface"])
        right.pack(side="right", padx=20, pady=10)
        self.bottom_score = tk.Label(right, text="HEALTH 100", bg=TH["surface"], fg=TH["sage_l"], font=("Consolas", 10, "bold"))
        self.bottom_score.pack(side="right", padx=12)
        self.bottom_rescued = tk.Label(right, text="RESCUED 0/5", bg=TH["surface"], fg=TH["amber_l"], font=("Consolas", 10, "bold"))
        self.bottom_rescued.pack(side="right", padx=12)

    def _action_btn(self, parent, text, cmd, fg, bg, hoverFg, minor=False):
        font = ("Segoe UI", 9, "bold") if not minor else ("Segoe UI", 9)
        btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, font=font, relief="flat", activebackground=fg, activeforeground=hoverFg, padx=14, pady=7, cursor="hand2", borderwidth=0)
        btn.pack(side="left", padx=4)
        return btn

    def _set_speed(self, ms):
        self.sim_speed = ms

    # switches the visible screen and highlights the active nav button
    def show_screen(self, key):
        if self.current_screen:
            self.screens[self.current_screen].lower()
            self._set_nav_active(self.current_screen, False)
        self.current_screen = key
        self.screens[key].lift()
        self.screens[key].refresh()
        self._set_nav_active(key, True)

    def _set_nav_active(self, key, active):
        btn = self.nav_buttons[key]
        if active:
            btn.configure(bg=TH["panel_hi"])
            btn._inner.configure(bg=TH["panel_hi"])
            btn._title.configure(bg=TH["panel_hi"], fg=TH["amber_l"])
            btn._sub.configure(bg=TH["panel_hi"])
            btn._accent.configure(bg=TH["amber"])
        else:
            btn.configure(bg=TH["panel"])
            btn._inner.configure(bg=TH["panel"])
            btn._title.configure(bg=TH["panel"], fg=TH["text"])
            btn._sub.configure(bg=TH["panel"])
            btn._accent.configure(bg=TH["panel"])

    # runs a function in a background thread so the UI stays responsive
    def _run_threaded(self, func, callback):
        self._busy = True
        self._overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.update_idletasks()
        def worker():
            func()
            self.after(0, lambda: self._on_thread_done(callback))
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_thread_done(self, callback):
        self._busy = False
        self._overlay.place_forget()
        if callback:
            callback()

    def _on_setup_done(self):
        self._update_topbar()
        if self.current_screen:
            self.screens[self.current_screen].refresh()

    def _next_step(self):
        if self._busy:
            return
        self._run_threaded(self.sim.step, self._update_topbar)

    def _toggle_auto(self):
        self.auto_run = not self.auto_run
        if self.auto_run:
            self.auto_btn.configure(text="PAUSE", fg=TH["coral_l"], bg=TH["coral_d"])
            self._auto_loop()
        else:
            self.auto_btn.configure(text="AUTO", fg=TH["sage"], bg=TH["sage_d"])

    def _auto_loop(self):
        if self._busy:
            self.after(100, self._auto_loop)
            return
        if self.auto_run and self.sim.current_step < self.sim.TOTAL_STEPS:
            self._next_step()
            self.after(self.sim_speed, self._auto_loop)
        else:
            self.auto_run = False
            self.auto_btn.configure(text="AUTO", fg=TH["sage"], bg=TH["sage_d"])

    def _reset(self):
        if self._busy:
            return
        self.auto_run = False
        self.auto_btn.configure(text="AUTO", fg=TH["sage"], bg=TH["sage_d"])
        self.graph = CityGraph(GRID_ROWS, GRID_COLS)
        self.sim = Simulation(self.graph)
        self.sim.register_observer(self)
        for screen in self.screens.values():
            screen.app = self
        self._run_threaded(self.sim.setup, self._on_setup_done)

    # updates all topbar pills, progress dots and bottom stats after each step
    def _update_topbar(self):
        state = self.sim.get_state()
        s = state["step"]
        self.pill_step._label.configure(text="STEP " + str(s).zfill(2) + " / " + str(state["total_steps"]))
        nBlocked = state["blocked_roads"]
        plural = "S" if nBlocked != 1 else " "
        self.pill_alert._label.configure(text=str(nBlocked) + " CLOSURE" + plural)

        if s == 0:
            self.pill_status._label.configure(text="READY")
        elif s >= self.sim.TOTAL_STEPS:
            self.pill_status._label.configure(text="DONE")
            self.pill_status.configure(bg=TH["amber_d"])
            self.pill_status._label.configure(bg=TH["amber_d"])
        else:
            self.pill_status._label.configure(text="RUNNING")

        for i, dot in enumerate(self.step_dots):
            if i < s - 1:
                dot.configure(bg=TH["sage"])
            elif i == s - 1:
                dot.configure(bg=TH["amber"])
            else:
                dot.configure(bg=TH["border"])

        self.bottom_rescued.configure(text="RESCUED " + str(state["rescued"]) + "/" + str(state["total_civilians"]))

        score = state["city_score"]
        if score >= 70:
            col = TH["sage_l"]
        elif score >= 40:
            col = TH["amber_l"]
        else:
            col = TH["coral_l"]
        self.bottom_score.configure(text="HEALTH " + str(score), fg=col)

        if self.current_screen:
            self.screens[self.current_screen].refresh()

    def on_sim_event(self, eventType, data):
        self.after(0, self._update_topbar)

    def _on_close(self):
        self.auto_run = False
        self.destroy()
