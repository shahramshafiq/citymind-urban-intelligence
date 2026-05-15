# screen_timeline.py
#Full simulation event log and summary stats
import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.base_screen import BaseScreen, C

class ScreenTimeline(BaseScreen):
    def _build_ui(self):
        
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # Title bar
        header = tk.Frame(self, bg=C["bg"])
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(14,6))
        self.title_var = tk.StringVar(value="SIMULATION TIMELINE")
        tk.Label(header, textvariable=self.title_var, bg=C["bg"], fg=C["white"],
                 font=("Courier New", 14, "bold")).pack(side="left")
        self.subtitle_var = tk.StringVar(value="All events and system decisions")
        tk.Label(header, textvariable=self.subtitle_var, bg=C["bg"], fg=C["muted2"],
                 font=("Courier New", 9)).pack(side="left", padx=16)

        # Left: full log
        log_frame = tk.Frame(self, bg=C["panel"])
        log_frame.grid(row=1, column=0, sticky="nsew", padx=(14,4), pady=(0,14))
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        tk.Label(log_frame, text="FULL EVENT LOG", bg=C["panel"], fg=C["muted2"],
                 font=("Courier New", 8)).grid(row=0, column=0, sticky="w", padx=10, pady=6)

        self.log_text = tk.Text(log_frame, bg=C["card"], fg=C["white"],
                                 font=("Courier New", 9), wrap="word",
                                 state="disabled", relief="flat", padx=8, pady=8)
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0,6))
        sb = tk.Scrollbar(log_frame, command=self.log_text.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.tag_configure("FLOOD",     foreground=C["red_l"])
        self.log_text.tag_configure("REROUTE",   foreground=C["blue_l"])
        self.log_text.tag_configure("RESCUE",    foreground=C["teal_l"])
        self.log_text.tag_configure("RISK",      foreground=C["amber_l"])
        self.log_text.tag_configure("PLACEMENT", foreground=C["green_l"])
        self.log_text.tag_configure("INFO",      foreground=C["muted2"])
        self.log_text.tag_configure("step_head", foreground=C["white"],
                                     font=("Courier New", 9, "bold"))

        # Right: summary stats
        right = tk.Frame(self, bg=C["panel"])
        right.grid(row=1, column=1, sticky="nsew", padx=(4,14), pady=(0,14))

        tk.Label(right, text="SIMULATION SUMMARY", bg=C["panel"], fg=C["muted2"],
                 font=("Courier New", 8)).pack(anchor="w", padx=12, pady=(10,4))

        self.v_step     = tk.StringVar(value="0 / 20")
        self.v_rescued  = tk.StringVar(value="0 / 5")
        self.v_flooded  = tk.StringVar(value="0")
        self.v_reroutes = tk.StringVar(value="0")
        self.v_score    = tk.StringVar(value="100")

        for label, var, col in [
            ("Steps completed",    self.v_step,     C["white"]),
            ("People rescued",     self.v_rescued,  C["teal_l"]),
            ("Roads flooded",      self.v_flooded,  C["red_l"]),
            ("Auto-reroutes",      self.v_reroutes, C["amber_l"]),
            ("City health score",  self.v_score,    C["teal_l"]),
        ]:
            card = tk.Frame(right, bg=C["card"], padx=12, pady=8)
            card.pack(fill="x", padx=12, pady=3)
            tk.Label(card, text=label, bg=C["card"], fg=C["muted2"],
                     font=("Courier New", 8)).pack(anchor="w")
            tk.Label(card, textvariable=var, bg=C["card"], fg=col,
                     font=("Courier New", 18, "bold")).pack(anchor="w")

        tk.Label(right, text="CHALLENGE MODULES", bg=C["panel"], fg=C["muted2"],
                 font=("Courier New", 8)).pack(anchor="w", padx=12, pady=(14,4))

        modules = [
            ("C1", "CSP Layout",      "Shahram",  C["blue_l"]),
            ("C2", "GA Roads",         "Shahram",  C["blue_l"]),
            ("C3", "SA Placement",    "Rafia",     C["teal_l"]),
            ("C4", "A* Routing",      "Rafia",     C["teal_l"]),
            ("C5", "K-Means + KNN",  "Sara",      C["purple"]),
        ]
        for code, name, owner, col in modules:
            f = tk.Frame(right, bg=C["card"], padx=10, pady=5)
            f.pack(fill="x", padx=12, pady=2)
            tk.Label(f, text=code, bg=C["card"], fg=col,
                     font=("Courier New", 9, "bold"), width=3).pack(side="left")
            tk.Label(f, text=name, bg=C["card"], fg=C["white"],
                     font=("Courier New", 9)).pack(side="left", padx=6)
            tk.Label(f, text=owner, bg=C["card"], fg=C["muted2"],
                     font=("Courier New", 8)).pack(side="right")

    def refresh(self):
        self.title_var.set("SIMULATION TIMELINE")
        self.subtitle_var.set("All events and system decisions — full audit trail")
        state = self.app.sim.get_state()
        self.v_step.set(f"{state['step']} / {state['total_steps']}")
        self.v_rescued.set(f"{state['rescued']} / {state['total_civilians']}")
        self.v_flooded.set(str(state["blocked_roads"]))
        self.v_reroutes.set(str(state["reroute_count"]))
        self.v_score.set(str(state["city_score"]))
        # Full log
        entries = self.app.sim.log.get_all()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        prev_step = -1
        for e in entries:
            if e["step"] != prev_step:
                self.log_text.insert("end",
                    f"\n── Step {e['step']} ─────────────────\n", "step_head")
                prev_step = e["step"]
            tag = e["event_type"]
            self.log_text.insert("end", f"  [{tag:9s}] {e['message']}\n", tag)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")
