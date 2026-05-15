# Shared grid canvas, hover tooltips, interactive click-to-modify

import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from city_graph import LocationType, RiskLevel

TH = {
    "bg": "#1A1410",
    "surface": "#221A12",
    "panel": "#2A2017",
    "panel_hi": "#33271C",
    "card": "#382A1E",
    "card_hi": "#43321F",
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
    "purple": "#9B7FAA",
}

# alias dict used by other screen files
C = dict(TH)
C["teal"]   = TH["sage"]
C["teal_l"] = TH["sage_l"]
C["teal_d"] = TH["sage_d"]
C["red"]    = TH["coral"]
C["red_l"]  = TH["coral_l"]
C["red_d"]  = TH["coral_d"]
C["blue"]   = TH["amber"]
C["blue_l"] = TH["amber_l"]
C["green"]  = TH["sage"]
C["green_l"]= TH["sage_l"]
C["white"]  = TH["text"]

# fill colours per node type
NODE_FILL = {
    "E": "#241B12",
    "R": "#3D2E1F",
    "H": "#7A4A14",
    "S": "#856425",
    "I": "#7A2E1A",
    "P": "#4D3A6B",
    "D": "#3E5C2C",
}

# glow ring colours per node type
NODE_GLOW = {
    "E": "#2D2218",
    "R": "#5C4632",
    "H": "#E8A442",
    "S": "#D4A24F",
    "I": "#D9633D",
    "P": "#9B7FAA",
    "D": "#7FAA85",
}

# fill colours for risk heatmap mode
RISK_FILL = {
    "low": "#2D4632",
    "medium": "#6E4A14",
    "high": "#7A2E1A",
}

TYPE_NAMES = {
    "E": "Empty", "R": "Residential", "H": "Hospital",
    "S": "School", "I": "Industrial",  "P": "Power Plant",
    "D": "Ambulance Depot",
}

class BaseScreen(tk.Frame):
    CELL = 42

    def __init__(self, parent, app):
        super().__init__(parent, bg=TH["bg"])
        self.app = app
        self._pulse_state = 0
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)

        self.map_frame = tk.Frame(self, bg=TH["bg"])
        self.map_frame.grid(row=0, column=0, sticky="nsew", padx=18, pady=16)

        self.info_shell = tk.Frame(self, bg=TH["panel"], width=430)
        self.info_shell.grid(row=0, column=1, sticky="nsew")
        self.info_shell.grid_propagate(False)
        self.info_shell.rowconfigure(0, weight=1)
        self.info_shell.columnconfigure(0, weight=1)

        self.info_canvas = tk.Canvas(
            self.info_shell,
            bg=TH["panel"],
            highlightthickness=0,
            borderwidth=0,
            yscrollincrement=24,
        )
        self.info_canvas.grid(row=0, column=0, sticky="nsew")

        self.info_scrollbar = tk.Scrollbar(
            self.info_shell,
            orient="vertical",
            command=self.info_canvas.yview,
            bg=TH["panel"],
            troughcolor=TH["surface"],
            activebackground=TH["amber_d"],
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
        )
        self.info_scrollbar.grid(row=0, column=1, sticky="ns")
        self.info_canvas.configure(yscrollcommand=self.info_scrollbar.set)

        self.info_frame = tk.Frame(self.info_canvas, bg=TH["panel"])
        self._info_window = self.info_canvas.create_window(
            (0, 0),
            window=self.info_frame,
            anchor="nw",
        )
        self.info_frame.bind("<Configure>", self._sync_info_scrollregion)
        self.info_canvas.bind("<Configure>", self._sync_info_width)
        self.info_canvas.bind("<Enter>", self._bind_info_mousewheel)
        self.info_canvas.bind("<Leave>", self._unbind_info_mousewheel)

        self._build_map_area()
        self._build_info_panel()

    def _sync_info_scrollregion(self, event=None):
        self.info_canvas.configure(scrollregion=self.info_canvas.bbox("all"))

    def _sync_info_width(self, event):
        self.info_canvas.itemconfigure(self._info_window, width=event.width)

    def _bind_info_mousewheel(self, event=None):
        self.info_canvas.bind_all("<MouseWheel>", self._on_info_mousewheel)
        self.info_canvas.bind_all("<Button-4>", self._on_info_mousewheel)
        self.info_canvas.bind_all("<Button-5>", self._on_info_mousewheel)

    def _unbind_info_mousewheel(self, event=None):
        self.info_canvas.unbind_all("<MouseWheel>")
        self.info_canvas.unbind_all("<Button-4>")
        self.info_canvas.unbind_all("<Button-5>")

    def _on_info_mousewheel(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 * int(event.delta / 120)
        self.info_canvas.yview_scroll(delta, "units")

    def _build_map_area(self):
        head = tk.Frame(self.map_frame, bg=TH["bg"])
        head.pack(anchor="w", fill="x", pady=(0, 12))

        self.title_var = tk.StringVar(value="City View")
        tk.Label(head, textvariable=self.title_var, bg=TH["bg"], fg=TH["ivory"], font=("Segoe UI", 18, "bold"), anchor="w").pack(anchor="w")

        # animated underline bar
        self._underline = tk.Canvas(head, bg=TH["bg"], height=3, highlightthickness=0, width=0)
        self._underline.pack(anchor="w", pady=(2, 0))
        self._underline.configure(width=44)
        self._underline.create_rectangle(0, 0, 44, 3, fill=TH["amber"], outline="")

        self.subtitle_var = tk.StringVar(value="")
        tk.Label(head, textvariable=self.subtitle_var, bg=TH["bg"], fg=TH["muted2"], font=("Segoe UI", 9), anchor="w").pack(anchor="w", pady=(8, 0))

        cols = self.app.graph.cols
        rows = self.app.graph.rows
        cw = cols * self.CELL + 2
        ch = rows * self.CELL + 2

        wrap = tk.Frame(self.map_frame, bg=TH["border2"], padx=1, pady=1)
        wrap.pack(anchor="nw")
        self.canvas = tk.Canvas(wrap, width=cw, height=ch, bg="#1E1610", highlightthickness=0, borderwidth=0)
        self.canvas.pack()
        self.canvas.bind("<Motion>",   self._on_hover)
        self.canvas.bind("<Leave>",    self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self.tooltip = tk.Label(self.map_frame, text="", bg=TH["card"], fg=TH["text"], font=("Consolas", 9), padx=10, pady=6, relief="flat", borderwidth=0, justify="left")

        hint = tk.Frame(self.map_frame, bg=TH["bg"])
        hint.pack(anchor="w", pady=(6, 0))
        tk.Label(hint, text="Left-click: change type   |   Right-click: toggle road", bg=TH["bg"], fg=TH["muted"], font=("Segoe UI", 8)).pack(side="left")

        self._build_legend_bar()

    def _build_legend_bar(self):
        pass

    def _build_info_panel(self):
        pass

    # draws the city grid - mode can be road, risk or distance
    def draw_grid(self, mode="road"):
        self.canvas.delete("all")
        graph = self.app.graph
        state = self.app.sim.get_state()
        ambu = state["ambulance_positions"]

        # grid lines
        for r in range(graph.rows + 1):
            y = r * self.CELL
            self.canvas.create_line(0, y, graph.cols * self.CELL, y, fill=TH["border"], width=1)
        for c in range(graph.cols + 1):
            x = c * self.CELL
            self.canvas.create_line(x, 0, x, graph.rows * self.CELL, fill=TH["border"], width=1)

        # open roads (drawn under nodes)
        if mode == "road":
            for edge in graph.get_all_edges():
                if not edge.blocked:
                    ra, ca = graph.rc(edge.u)
                    rb, cb = graph.rc(edge.v)
                    x1 = ca * self.CELL + self.CELL // 2
                    y1 = ra * self.CELL + self.CELL // 2
                    x2 = cb * self.CELL + self.CELL // 2
                    y2 = rb * self.CELL + self.CELL // 2
                    self.canvas.create_line(x1, y1, x2, y2, fill=TH["border2"], width=1)

        # nodes
        for node in graph.get_all_nodes():
            r, c = node.row, node.col
            x1 = c * self.CELL + 3
            y1 = r * self.CELL + 3
            x2 = x1 + self.CELL - 6
            y2 = y1 + self.CELL - 6
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            if mode == "risk":
                fill = RISK_FILL.get(node.crime_risk_level.value, TH["panel"])
            elif mode == "distance":
                fill = self._distance_fill(node, ambu, graph)
            else:
                fill = NODE_FILL.get(node.location_type.value, TH["panel"])

            tval = node.location_type.value
            if mode not in ("risk", "distance") and tval not in ("E", "R"):
                glow = NODE_GLOW[tval]
                self.canvas.create_rectangle(x1-1, y1-1, x2+1, y2+1, fill=glow, outline="")

            self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=TH["border2"], width=1, tags="node_" + str(node.node_id))

            if tval not in ("E",):
                self.canvas.create_line(x1+1, y1+1, x2-1, y1+1, fill=self._lighten(fill, 0.15), width=1)

            lbl = self._cell_label(node, mode, ambu, graph)
            if lbl:
                fg = self._cell_label_color(node, mode)
                self.canvas.create_text(cx, cy, text=lbl, fill=fg, font=("Segoe UI", 9, "bold"))

        # blocked roads shown as red dashed lines with X marker
        showX = (mode != "layout")
        for edge in graph.get_blocked_edges():
            ra, ca = graph.rc(edge.u)
            rb, cb = graph.rc(edge.v)
            x1 = ca * self.CELL + self.CELL // 2
            y1 = ra * self.CELL + self.CELL // 2
            x2 = cb * self.CELL + self.CELL // 2
            y2 = rb * self.CELL + self.CELL // 2
            if showX:
                self.canvas.create_line(x1, y1, x2, y2, fill=TH["coral"], width=3, dash=(5, 3))
                mx, my = (x1+x2)//2, (y1+y2)//2
                self.canvas.create_oval(mx-6, my-6, mx+6, my+6, fill=TH["coral_d"], outline=TH["coral_l"], width=1)
                self.canvas.create_text(mx, my, text="x", fill=TH["coral_l"], font=("Segoe UI", 8, "bold"))
            else:
                self.canvas.create_line(x1, y1, x2, y2, fill=TH["border"], width=1, dash=(2, 4))

        # active team route shown as amber dashed line
        route = state.get("current_route", [])
        for i in range(len(route) - 1):
            ra, ca = graph.rc(route[i])
            rb, cb = graph.rc(route[i+1])
            x1 = ca * self.CELL + self.CELL // 2
            y1 = ra * self.CELL + self.CELL // 2
            x2 = cb * self.CELL + self.CELL // 2
            y2 = rb * self.CELL + self.CELL // 2
            self.canvas.create_line(x1, y1, x2, y2, fill=TH["amber"], width=2, dash=(4, 3))

        # ambulances drawn as gold circles with A label
        for ambuId in ambu:
            ar, ac = graph.rc(ambuId)
            ax = ac * self.CELL + self.CELL // 2
            ay = ar * self.CELL + self.CELL // 2
            self.canvas.create_oval(ax-13, ay-13, ax+13, ay+13, fill="", outline=TH["amber_d"], width=1)
            self.canvas.create_oval(ax-10, ay-10, ax+10, ay+10, fill=TH["amber"], outline=TH["amber_d"], width=2)
            self.canvas.create_text(ax, ay, text="A", fill=TH["amber_d"], font=("Segoe UI", 8, "bold"))

        # civilians drawn as green circles with their number
        rescuedIdx = state.get("rescued_indices", [])
        for i, civId in enumerate(state.get("civilian_targets", [])):
            if i in rescuedIdx:
                continue
            cr, cc = graph.rc(civId)
            cx2 = cc * self.CELL + self.CELL // 2
            cy2 = cr * self.CELL + self.CELL // 2
            self.canvas.create_oval(cx2-9, cy2-9, cx2+9, cy2+9, fill=TH["sage"], outline=TH["sage_d"], width=2)
            self.canvas.create_text(cx2, cy2, text=str(i+1), fill=TH["sage_d"], font=("Segoe UI", 8, "bold"))

        # medical team drawn as coral circle with T label
        tp = state.get("team_position")
        if tp is not None:
            tr, tc2 = graph.rc(tp)
            tx = tc2 * self.CELL + self.CELL // 2
            ty = tr  * self.CELL + self.CELL // 2
            self.canvas.create_oval(tx-11, ty-11, tx+11, ty+11, fill=TH["coral_l"], outline=TH["coral_d"], width=2)
            self.canvas.create_text(tx, ty, text="T", fill=TH["coral_d"], font=("Segoe UI", 9, "bold"))

    def _lighten(self, hexColor, factor):
        try:
            r = int(hexColor[1:3], 16)
            g = int(hexColor[3:5], 16)
            b = int(hexColor[5:7], 16)
            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))
            return "#" + format(r, "02x") + format(g, "02x") + format(b, "02x")
        except Exception:
            return hexColor

    def _cell_label(self, node, mode, ambu, graph):
        if mode == "risk":
            return {"low": "", "medium": "M", "high": "HI"}.get(node.crime_risk_level.value, "")
        if mode == "distance" and ambu:
            d = min(abs(node.row - graph.rc(a)[0]) + abs(node.col - graph.rc(a)[1]) for a in ambu)
            return str(d)
        v = node.location_type.value
        return {"H": "H", "D": "D", "S": "S", "I": "I", "P": "P"}.get(v, "")

    def _cell_label_color(self, node, mode):
        if mode == "risk":
            risk = node.crime_risk_level.value
            return {"low": TH["sage_l"], "medium": TH["amber_l"], "high": TH["coral_l"]}.get(risk, TH["text"])
        if mode == "distance":
            return TH["text"]
        return TH["ivory"]

    def _distance_fill(self, node, ambu, graph):
        if not ambu:
            return TH["panel"]
        d = min(abs(node.row - graph.rc(a)[0]) + abs(node.col - graph.rc(a)[1]) for a in ambu)
        if d == 0:  return "#5C8A3A"
        if d == 1:  return "#4A7530"
        if d == 2:  return "#3E5C2C"
        if d <= 4:  return "#3D3E22"
        if d <= 6:  return "#3A2E1B"
        return "#2A2017"

    # left click opens a menu to change the node type
    def _on_click(self, event):
        graph = self.app.graph
        c = event.x // self.CELL
        r = event.y // self.CELL
        if 0 <= r < graph.rows and 0 <= c < graph.cols:
            node = graph.get_node_by_rc(r, c)
            if node:
                self._show_type_menu(event, node)

    def _show_type_menu(self, event, node):
        menu = tk.Menu(self, tearoff=0, bg=TH["card"], fg=TH["text"], activebackground=TH["amber_d"], activeforeground=TH["amber_l"], font=("Segoe UI", 10))
        types = [
            ("Empty",           LocationType.EMPTY),
            ("Residential",     LocationType.RESIDENTIAL),
            ("Hospital",        LocationType.HOSPITAL),
            ("School",          LocationType.SCHOOL),
            ("Industrial",      LocationType.INDUSTRIAL),
            ("Power Plant",     LocationType.POWER_PLANT),
            ("Ambulance Depot", LocationType.AMBU_DEPOT),
        ]
        current = node.location_type
        for (name, ltype) in types:
            prefix = "  > " if ltype == current else "    "
            menu.add_command(label=prefix + name, command=lambda lt=ltype, nid=node.node_id: self._set_node_type(nid, lt))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _set_node_type(self, nodeId, locType):
        self.app.graph.add_location(nodeId, locType)
        if self.app.sim.setup_done:
            hasViolation = self.app.sim.note_runtime_node_edit(nodeId, locType)
            if hasViolation:
                self.app._update_topbar()
            elif not self.app._busy:
                self.app._run_threaded(lambda: self.app.sim.recompute_after_node_change(manual_repair=False), self.app._update_topbar)
        else:
            self.refresh()

    # right click opens a menu to block or unblock adjacent roads
    def _on_right_click(self, event):
        graph = self.app.graph
        c = event.x // self.CELL
        r = event.y // self.CELL
        if not (0 <= r < graph.rows and 0 <= c < graph.cols):
            return
        node = graph.get_node_by_rc(r, c)
        if not node:
            return

        menu = tk.Menu(self, tearoff=0, bg=TH["card"], fg=TH["text"], activebackground=TH["coral_d"], activeforeground=TH["coral_l"], font=("Segoe UI", 10))

        directions = [("North", -1, 0), ("South", 1, 0), ("West", 0, -1), ("East", 0, 1)]
        for (dname, dr, dc) in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < graph.rows and 0 <= nc < graph.cols:
                nbId = graph.node_id(nr, nc)
                key = (min(node.node_id, nbId), max(node.node_id, nbId))
                edge = graph._edges.get(key)
                if edge:
                    status = "BLOCKED" if edge.blocked else "open"
                    action = "Unblock" if edge.blocked else "Block"
                    menu.add_command(label="  " + action + " road " + dname + " [" + status + "]", command=lambda u=node.node_id, v=nbId, blk=edge.blocked: self._toggle_edge(u, v, blk))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _toggle_edge(self, u, v, currentlyBlocked):
        if currentlyBlocked:
            self.app.graph.unblock_edge(u, v)
            self.app.sim.log.log(self.app.sim.current_step, "INFO", "Road (" + str(u) + "-" + str(v) + ") manually unblocked")
        else:
            self.app.graph.block_edge(u, v)
            self.app.sim.log.log(self.app.sim.current_step, "FLOOD", "Road (" + str(u) + "-" + str(v) + ") manually blocked")
        self.refresh()

    # hover shows a tooltip with node info
    def _on_hover(self, event):
        graph = self.app.graph
        c = event.x // self.CELL
        r = event.y // self.CELL
        if 0 <= r < graph.rows and 0 <= c < graph.cols:
            node = graph.get_node_by_rc(r, c)
            if node:
                risk  = node.crime_risk_level.value.upper()
                pop   = str(round(node.population_density, 2))
                tname = TYPE_NAMES.get(node.location_type.value, "?")
                mult  = str(round(node.risk_multiplier, 1)) + "x"
                text  = "(" + str(r) + ", " + str(c) + ")  -  " + tname + "\nRisk: " + risk + "    Pop: " + pop + "\nCost multiplier: " + mult
                self.tooltip.configure(text=text)
                self.tooltip.place(x=event.x + 14, y=event.y + 14)
        else:
            self.tooltip.place_forget()

    def _on_leave(self, event):
        self.tooltip.place_forget()

    # reusable UI component helpers used by all screen files
    def _section_label(self, parent, text):
        f = tk.Frame(parent, bg=TH["panel"])
        f.pack(fill="x", padx=14, pady=(14, 4))
        tk.Label(f, text=text, bg=TH["panel"], fg=TH["amber"], font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Frame(f, bg=TH["border"], height=1).pack(side="left", fill="x", expand=True, padx=8, pady=(7, 0))

    def _stat_card(self, parent, label, valueVar, accent=None):
        card = tk.Frame(parent, bg=TH["card"], padx=12, pady=10)
        card.pack(fill="x", padx=14, pady=4)
        tk.Label(card, text=label, bg=TH["card"], fg=TH["muted2"], font=("Segoe UI", 8, "bold"), anchor="w").pack(anchor="w")
        valLbl = tk.Label(card, textvariable=valueVar, bg=TH["card"], fg=accent or TH["text"], font=("Consolas", 16, "bold"))
        valLbl.pack(anchor="w", pady=(2, 0))
        return valLbl

    def _log_panel(self, parent, height=8):
        self._section_label(parent, "EVENT LOG")
        logFrame = tk.Frame(parent, bg=TH["card"])
        logFrame.pack(fill="both", expand=True, padx=14, pady=4)
        self.log_text = tk.Text(logFrame, bg=TH["card"], fg=TH["text"], font=("Consolas", 8), wrap="word", state="disabled", relief="flat", padx=8, pady=8, height=height, borderwidth=0)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("FLOOD", foreground=TH["coral_l"])
        self.log_text.tag_configure("REROUTE", foreground=TH["amber_l"])
        self.log_text.tag_configure("RESCUE", foreground=TH["sage_l"])
        self.log_text.tag_configure("RISK", foreground=TH["gold"])
        self.log_text.tag_configure("PLACEMENT", foreground=TH["sage"])
        self.log_text.tag_configure("CSP", foreground=TH["sage_l"])
        self.log_text.tag_configure("CSP_ERROR", foreground=TH["coral_l"])
        self.log_text.tag_configure("INFO", foreground=TH["muted2"])

    def _update_log(self):
        if not hasattr(self, "log_text"):
            return
        entries = self.app.sim.log.get_recent(14)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for e in reversed(entries):
            prefix = "[t=" + str(e["step"]).rjust(2) + "] "
            msg = e["message"] + "\n"
            tag = e["event_type"]
            self.log_text.insert("end", prefix, tag)
            self.log_text.insert("end", msg, tag)
        self.log_text.configure(state="disabled")

    def refresh(self):
        pass
