# shows CSP building placement results and constraint verification

import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.base_screen import BaseScreen, TH
from city_graph import LocationType

class ScreenLayout(BaseScreen):
    # colour legend below the grid
    def _build_legend_bar(self):
        bar = tk.Frame(self.map_frame, bg=TH["bg"])
        bar.pack(anchor="w", pady=(10, 0))

        legendItems = [
            ("#7A4A14", "Hosp"),
            ("#3E5C2C", "Depot"),
            ("#856425", "School"),
            ("#7A2E1A", "Indust"),
            ("#4D3A6B", "Power"),
            ("#3D2E1F", "Resid"),
            ("#241B12", "Empty"),
        ]
        for (col, lbl) in legendItems:
            chip = tk.Frame(bar, bg=col, width=12, height=12, highlightbackground=TH["border2"], highlightthickness=1)
            chip.pack(side="left", padx=(0, 3))
            tk.Label(bar, text=lbl, bg=TH["bg"], fg=TH["muted2"], font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))

    def _build_info_panel(self):
        panel = self.info_frame

        # building count rows updated in refresh
        self._section_label(panel, "BUILDING COUNTS")
        self.countsFrame = tk.Frame(panel, bg=TH["panel"])
        self.countsFrame.pack(fill="x", padx=14, pady=4)

        # CSP rule status cards
        self._section_label(panel, "CSP CONSTRAINTS")
        self.ruleWidgets = []
        rules = [
            ("Rule 1", "No Industrial adjacent to\nSchool or Hospital"),
            ("Rule 2", "Residential within 3 hops\nof a Hospital"),
            ("Rule 3", "Power Plant within 2 hops\nof an Industrial"),
        ]
        for (tag, desc) in rules:
            f = tk.Frame(panel, bg=TH["card"], padx=12, pady=8)
            f.pack(fill="x", padx=14, pady=3)

            head = tk.Frame(f, bg=TH["card"])
            head.pack(fill="x")
            tk.Label(head, text=tag, bg=TH["card"], fg=TH["amber_l"], font=("Segoe UI", 9, "bold")).pack(side="left")
            statusLbl = tk.Label(head, text="checking", bg=TH["card"], fg=TH["muted"], font=("Segoe UI", 8, "bold"))
            statusLbl.pack(side="right")

            tk.Label(f, text=desc, bg=TH["card"], fg=TH["muted2"], font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(4, 0))
            self.ruleWidgets.append(statusLbl)

        # solver status text
        self._section_label(panel, "SOLVER STATUS")
        self.algoStatus = tk.Label(panel, text="CSP solver running on grid", bg=TH["panel"], fg=TH["sage_l"], font=("Segoe UI", 9), justify="left")
        self.algoStatus.pack(padx=14, anchor="w")

        self.repairBtn = tk.Button(
            panel,
            text="Repair Constraints",
            command=self._repair_constraints,
            bg=TH["amber_d"],
            fg=TH["amber_l"],
            activebackground=TH["amber"],
            activeforeground=TH["bg"],
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
            cursor="hand2",
        )
        self.repairBtn.pack(fill="x", padx=14, pady=(10, 6))

        self._log_panel(panel, height=6)

    def refresh(self):
        self.title_var.set("CITY LAYOUT")
        self.subtitle_var.set("Building placement from Challenge 1 (Backtracking + AC-3 + Min-Conflicts)")
        self.draw_grid(mode="layout")

        # rebuild building count rows with fresh numbers
        for w in self.countsFrame.winfo_children():
            w.destroy()
        graph = self.app.graph

        typeMap = {}
        for node in graph.get_all_nodes():
            t = node.location_type.value
            typeMap[t] = typeMap.get(t, 0) + 1

        buildingRows = [
            ("H", "Hospitals", TH["amber_l"]),
            ("D", "Ambu Depots",  TH["sage_l"]),
            ("S", "Schools", TH["gold"]),
            ("I", "Industrial",TH["coral_l"]),
            ("P", "Power Plants", TH["purple"]),
            ("R", "Residential",TH["muted2"]),
            ("E", "Empty Cells",  TH["muted"]),
        ]
        for (t, name, col) in buildingRows:
            row = tk.Frame(self.countsFrame, bg=TH["panel"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, bg=TH["panel"], fg=TH["muted2"], font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
            tk.Label(row, text=str(typeMap.get(t, 0)), bg=TH["panel"], fg=col, font=("Consolas", 10, "bold")).pack(side="right")

        self.verifyRules(graph)
        self._update_log()

    # checks all 3 CSP rules against current graph and updates the status labels
    def verifyRules(self, graph):
        assn = {}
        for n in graph.get_all_nodes():
            assn[n.node_id] = n.location_type
        # rule 1:industrial not adjacent to school or hospital
        rule1ok = True
        for nodeId in assn:
            val = assn[nodeId]
            if val == LocationType.INDUSTRIAL:
                r, c = graph.rc(nodeId)
                for (dr, dc) in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < graph.rows and 0 <= nc < graph.cols:
                        nbId = graph.node_id(nr, nc)
                        nbType = assn.get(nbId)
                        if nbType == LocationType.SCHOOL or nbType == LocationType.HOSPITAL:
                            rule1ok = False
                            break

        # rule 2:every residential within 3 hops of a hospital
        rule2ok = True
        hospList = []
        for n in assn:
            if assn[n] == LocationType.HOSPITAL:
                hospList.append(n)
        if len(hospList) > 0:
            reach = set()
            for h in hospList:
                reach.update(self.bfsWithin(graph, h, 3))
            for nodeId in assn:
                if assn[nodeId] == LocationType.RESIDENTIAL and nodeId not in reach:
                    rule2ok = False
                    break

        # rule 3:every power plant within 2 hops of an industrial
        rule3ok = True
        indList = []
        for n in assn:
            if assn[n] == LocationType.INDUSTRIAL:
                indList.append(n)
        if len(indList) > 0:
            reach = set()
            for i in indList:
                reach.update(self.bfsWithin(graph, i, 2))
            for nodeId in assn:
                if assn[nodeId] == LocationType.POWER_PLANT and nodeId not in reach:
                    rule3ok = False
                    break

        # update each rule status label
        for (lbl, ok) in zip(self.ruleWidgets, [rule1ok, rule2ok, rule3ok]):
            if ok:
                lbl.configure(text="OK", fg=TH["sage_l"])
            else:
                lbl.configure(text="VIOLATED", fg=TH["coral_l"])

        # update solver status
        allOk = rule1ok and rule2ok and rule3ok
        if allOk:
            self.algoStatus.configure(text="All constraints satisfied.\nLayout valid for use.", fg=TH["sage_l"])
        else:
            failed = []
            if not rule1ok:
                failed.append("Rule 1")
            if not rule2ok:
                failed.append("Rule 2")
            if not rule3ok:
                failed.append("Rule 3")
            self.algoStatus.configure(text="Min-Conflicts fallback used.\nViolating: " + ", ".join(failed), fg=TH["amber_l"])

    def _repair_constraints(self):
        if self.app.sim.setup_done and not self.app._busy:
            self.app._run_threaded(self.app.sim.recompute_after_node_change, self.app._update_topbar)
        else:
            self.refresh()

    # BFS that returns all nodes reachable within maxHops steps
    def bfsWithin(self, graph, src, maxHops):
        seen = {src}
        frontier = [src]
        depth = 0
        while len(frontier) > 0 and depth < maxHops:
            nextFrontier = []
            for u in frontier:
                ru, cu = graph.rc(u)
                for (dr, dc) in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = ru+dr, cu+dc
                    if 0 <= nr < graph.rows and 0 <= nc < graph.cols:
                        nb = graph.node_id(nr, nc)
                        if nb not in seen:
                            seen.add(nb)
                            nextFrontier.append(nb)
            frontier = nextFrontier
            depth = depth + 1
        return seen
