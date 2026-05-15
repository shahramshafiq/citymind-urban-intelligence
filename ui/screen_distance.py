# This screen shows how well the ambulances are covering the city.
# Each cell shows the distance, in hops, to the nearest ambulance.
import tkinter as tk
import sys
import os

# Allows this file to import project files correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.base_screen import BaseScreen, C


class ScreenDistance(BaseScreen):
    """
    Displays the ambulance coverage distance map.
    """

    def _build_legend_bar(self):
        """
        Builds the small legend above the map.
        It explains what the numbers and colors mean.
        """
        legend_bar = tk.Frame(self.map_frame, bg=C["bg"])
        legend_bar.pack(anchor="w", pady=(8, 0))

        tk.Label(legend_bar,text="Numbers = hops to nearest ambulance  |  ",bg=C["bg"],
            fg=C["muted2"],font=("Courier New", 8)).pack(side="left")

        tk.Label(
            legend_bar,text="Darker green = closer",bg=C["bg"],
            fg=C["green_l"],font=("Courier New", 8)).pack(side="left")

    def _build_info_panel(self):
        """
        Builds the right-side information panel.
        This panel shows coverage stats and ambulance positions.
        """
        panel = self.info_frame

        self._section_label(panel, "COVERAGE STATS")

        self.worst_wait_var = tk.StringVar(value="—")
        self.average_wait_var = tk.StringVar(value="—")
        self.covered_nodes_var = tk.StringVar(value="—")

        self._stat_card(
            panel,
            "Worst Wait (hops)",
            self.worst_wait_var,
            C["red_l"]
        )

        self._stat_card(
            panel,
            "Average Wait (hops)",
            self.average_wait_var,
            C["amber_l"]
        )

        self._stat_card(
            panel,
            "Nodes within 3 hops",
            self.covered_nodes_var,
            C["teal_l"]
        )

        self._section_label(panel, "AMBULANCE UNITS")

        self.ambulance_frame = tk.Frame(panel, bg=C["panel"])
        self.ambulance_frame.pack(fill="x", padx=12)

        self._section_label(panel, "SA OPTIMISATION NOTE")

        note_box = tk.Frame(panel, bg=C["card"], padx=10, pady=8)
        note_box.pack(fill="x", padx=12, pady=3)

        tk.Label(
            note_box,
            text=(
                "Ambulance positions are\n"
                "optimised by Simulated\n"
                "Annealing (Challenge 3)\n"
                "to minimise worst-case\n"
                "response distance."
            ),
            bg=C["card"],
            fg=C["muted2"],
            font=("Courier New", 9),
            justify="left"
        ).pack(anchor="w")

        self._log_panel(panel)

    def _bfs_from(self, graph, start):
        dist = {start: 0}
        q = [start]
        while q:
            u = q.pop(0)
            for nb, _ in graph.get_neighbors(u):
                if nb not in dist:
                    dist[nb] = dist[u] + 1
                    q.append(nb)
        return dist

    def _nearest_bfs_dist(self, node_id):
        if not hasattr(self, "_bfs_maps") or not self._bfs_maps:
            return 9999
        best = 9999
        for dmap in self._bfs_maps:
            d = dmap.get(node_id, 9999)
            if d < best:
                best = d
        return best

    def _cell_label(self, node, mode, ambu, graph):
        if mode == "distance" and ambu:
            d = self._nearest_bfs_dist(node.node_id)
            return str(d) if d < 9999 else "?"
        return super()._cell_label(node, mode, ambu, graph)

    def _distance_fill(self, node, ambu, graph):
        if not ambu:
            return C["panel"]
        d = self._nearest_bfs_dist(node.node_id)
        if d == 0:   return "#5C8A3A"
        if d == 1:   return "#4A7530"
        if d == 2:   return "#3E5C2C"
        if d <= 4:   return "#3D3E22"
        if d <= 6:   return "#3A2E1B"
        return "#2A2017"

    def refresh(self):
        self.title_var.set("DISTANCE MAP")
        self.subtitle_var.set("Hops from each cell to nearest ambulance (road network)")

        state = self.app.sim.get_state()
        graph = self.app.graph
        ambulance_positions = state["ambulance_positions"]

        # BFS maps must be computed before draw_grid so overridden methods can use them
        self._bfs_maps = []
        for ambu_id in ambulance_positions:
            self._bfs_maps.append(self._bfs_from(graph, ambu_id))

        self.draw_grid(mode="distance")

        if ambulance_positions:
            all_distances = []
            for node in graph.get_all_nodes():
                all_distances.append(self._nearest_bfs_dist(node.node_id))

            reachable = [d for d in all_distances if d < 9999]
            if reachable:
                worst_distance = max(reachable)
                average_distance = sum(reachable) / len(reachable)
            else:
                worst_distance = 0
                average_distance = 0.0
            nodes_within_three_hops = sum(1 for d in all_distances if d <= 3)

            self.worst_wait_var.set(str(worst_distance))
            self.average_wait_var.set(f"{average_distance:.1f}")
            self.covered_nodes_var.set(f"{nodes_within_three_hops} / {len(all_distances)}")
        else:
            self.worst_wait_var.set("—")
            self.average_wait_var.set("—")
            self.covered_nodes_var.set("—")

        for widget in self.ambulance_frame.winfo_children():
            widget.destroy()

        for index, ambulance_id in enumerate(ambulance_positions[:3]):
            row, col = graph.rc(ambulance_id)
            ambulance_card = tk.Frame(self.ambulance_frame, bg=C["card"], padx=8, pady=5)
            ambulance_card.pack(fill="x", pady=2)
            tk.Label(ambulance_card, text=f"A{index + 1}  ({row}, {col})", bg=C["card"],
                fg=C["amber_l"], font=("Courier New", 10, "bold")).pack(side="left")

        self._update_log()