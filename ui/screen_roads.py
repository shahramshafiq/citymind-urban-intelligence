# shows GA road network results and live flood/reroute events
import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.base_screen import BaseScreen, TH
from city_graph import LocationType

class ScreenRoads(BaseScreen):
    # colour legend below the grid
    def _build_legend_bar(self):
        bar = tk.Frame(self.map_frame, bg=TH["bg"])
        bar.pack(anchor="w", pady=(10, 0))

        legendItems = [
            (TH["border2"], "----", "Open road"),
            (TH["coral"], "----", "Flooded / closed"),
            (TH["amber"], "----", "Active route"),
        ]
        for (col, dash, lbl) in legendItems:
            box = tk.Frame(bar, bg=TH["bg"])
            box.pack(side="left", padx=(0, 14))
            tk.Frame(box, bg=col, width=28, height=3).pack(side="left", pady=5)
            tk.Label(box, text=lbl, bg=TH["bg"], fg=TH["muted2"], font=("Segoe UI", 8)).pack(side="left", padx=(4, 0))

    def _build_info_panel(self):
        panel = self.info_frame
        # road stat cards
        self._section_label(panel, "ROAD STATUS")
        self.vOpen = tk.StringVar(value="0")
        self.vTotal = tk.StringVar(value="0")
        self.vFloods = tk.StringVar(value="0")
        self.vReroute = tk.StringVar(value="0")
        self._stat_card(panel, "ROADS BUILT BY GA", self.vOpen, TH["sage_l"])
        self._stat_card(panel, "FLOOD EVENTS (LIVE)", self.vFloods, TH["coral_l"])
        self._stat_card(panel, "AUTO-REROUTES DONE", self.vReroute, TH["amber_l"])
        # two path verification card
        self._section_label(panel, "GA VERIFICATION")
        self.gaCard = tk.Frame(panel, bg=TH["card"], padx=12, pady=10)
        self.gaCard.pack(fill="x", padx=14, pady=4)
        tk.Label(self.gaCard, text="2-EDGE-DISJOINT PATHS", bg=TH["card"], fg=TH["muted2"], font=("Segoe UI", 8, "bold"), anchor="w").pack(anchor="w")
        tk.Label(self.gaCard, text="Hospital  -  Depot", bg=TH["card"], fg=TH["muted"], font=("Segoe UI", 8), anchor="w").pack(anchor="w")
        self.gaStatus = tk.Label(self.gaCard, text="checking...", bg=TH["card"], fg=TH["amber_l"], font=("Segoe UI", 11, "bold"))
        self.gaStatus.pack(anchor="w", pady=(4, 0))

        # active route info card
        self._section_label(panel, "ACTIVE TEAM ROUTE")
        self.routeCard = tk.Frame(panel, bg=TH["card"], padx=12, pady=10)
        self.routeCard.pack(fill="x", padx=14, pady=4)
        self.routeInfo = tk.Label(self.routeCard, text="No active route", bg=TH["card"], fg=TH["muted2"], font=("Segoe UI", 9), justify="left", wraplength=200, anchor="w")
        self.routeInfo.pack(anchor="w")
        self._log_panel(panel, height=6)

    def refresh(self):
        self.title_var.set("ROAD NETWORK")
        self.subtitle_var.set("Roads built by GA + live flood / reroute events")
        self.draw_grid(mode="road")

        state = self.app.sim.get_state()
        graph = self.app.graph
        total = len(graph.get_all_edges())
        totalBlocked = state["blocked_roads"]

        # count flood events from the log
        floodCount = 0
        for e in self.app.sim.log.get_all():
            if e["event_type"] == "FLOOD":
                floodCount = floodCount + 1

        # roads built by GA = total minus what GA blocked at setup
        gaBlocked = max(0, totalBlocked - floodCount)
        roadsBuilt = total - gaBlocked

        self.vOpen.set(str(roadsBuilt))
        self.vTotal.set(str(total))
        self.vFloods.set(str(floodCount))
        self.vReroute.set(str(state["reroute_count"]))

        self.updateGaCheck(graph)

        # show current route details
        route = state.get("current_route", [])
        cost = state.get("route_cost", 0)
        if route and len(route) > 1:
            nextCiv = len(state["rescued_indices"]) + 1
            self.routeInfo.configure(text="Heading to: Person " + str(nextCiv) + "\nHops: " + str(len(route) - 1) + "\nA* cost: " + str(round(cost, 2)) + "\nRecomputed on each\nflood event")
        else:
            self.routeInfo.configure(text="No active route")

        self._update_log()

    # checks if two independent hospital-depot paths still exist after floods
    def updateGaCheck(self, graph):
        try:
            from challenges.challenge2_mst import verify_two_paths
            hosp = None
            depot = None
            for n in graph.get_all_nodes():
                if n.location_type == LocationType.HOSPITAL and hosp is None:
                    hosp = n.node_id
                if n.location_type == LocationType.AMBU_DEPOT and depot is None:
                    depot = n.node_id
            if hosp is None or depot is None:
                self.gaStatus.configure(text="N/A", fg=TH["muted"])
                return
            ok = verify_two_paths(graph, hosp, depot)
            if ok:
                self.gaStatus.configure(text="SATISFIED", fg=TH["sage_l"])
            else:
                self.gaStatus.configure(text="LOST (flooding)", fg=TH["coral_l"])
        except Exception:
            self.gaStatus.configure(text="N/A", fg=TH["muted"])