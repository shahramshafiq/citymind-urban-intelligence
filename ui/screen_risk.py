# screen_risk.py
# this screen shows the crime risk heatmap from challenge 5
import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.base_screen import BaseScreen, C
from city_graph import RiskLevel

class ScreenRisk(BaseScreen):
    # builds the colour legend bar below the grid so the user knows what each colour means
    def _build_legend_bar(self):
        bar = tk.Frame(self.map_frame, bg=C["bg"])
        bar.pack(anchor="w", pady=(8, 0))
        # label on the left side of the bar
        tk.Label(bar, text="RISK LEVEL", bg=C["bg"], fg=C["muted2"], font=("Courier New", 8)).pack(side="left", padx=(0, 8))
        # each tuple is a colour and its label is low, medium, high
        riskColours = [("#1A3550", "Low"), ("#5A3E10", "Medium"), ("#5A1A1A", "High")]
        for (col, lbl) in riskColours:
            # coloured block
            tk.Frame(bar, bg=col, width=40, height=10).pack(side="left")
            # label next to the block
            tk.Label(bar, text=lbl, bg=C["bg"], fg=C["muted2"], font=("Courier New", 8)).pack(side="left", padx=(2, 10))

    # builds the right side info panel with stats, ambulance cards and risk insights
    def _build_info_panel(self):
        panel = self.info_frame

        # section 1 shows summary stats at the top
        self._section_label(panel, "SITUATION SUMMARY")
        # these are live variables that get updated in refresh() function
        self.vRescued = tk.StringVar(value="0 / 5")
        self.vClosures = tk.StringVar(value="0")
        self.vWait = tk.StringVar(value="— min")
        self.vScore = tk.StringVar(value="100")
        # each stat card shows a label and the live value
        self._stat_card(panel, "Trapped Civilians Rescued", self.vRescued, C["teal_l"])
        self._stat_card(panel, "Road Closures Active", self.vClosures, C["red_l"])
        self._stat_card(panel, "Worst Ambulance Wait", self.vWait, C["amber_l"])
        self._stat_card(panel, "City Health Score", self.vScore, C["teal_l"])
        # section 2 is one card per ambulance showing its location
        self._section_label(panel, "AMBULANCE POSITIONS")
        self.ambuLabels = []
        for i in range(3):
            # outer card frame
            f = tk.Frame(panel, bg=C["card"], padx=10, pady=6)
            f.pack(fill="x", padx=12, pady=2)
            # top row inside the card - number, name, and wait time on the right
            rowFrame = tk.Frame(f, bg=C["card"])
            rowFrame.pack(fill="x")
            tk.Label(rowFrame, text="  " + str(i + 1), bg=C["card"], fg=C["green_l"], font=("Courier New", 10, "bold"), width=4).pack(side="left")
            nameLbl = tk.Label(rowFrame, text="Ambulance " + str(i + 1), bg=C["card"], fg=C["white"], font=("Courier New", 10, "bold"))
            nameLbl.pack(side="left")
            distLbl = tk.Label(rowFrame, text="—", bg=C["card"], fg=C["amber_l"], font=("Courier New", 9))
            distLbl.pack(side="right")
            # second row - grid position, updated in refresh()
            locLbl = tk.Label(f, text="Calculating...", bg=C["card"], fg=C["muted2"], font=("Courier New", 8))
            locLbl.pack(anchor="w")
            # store the labels we need to update later
            self.ambuLabels.append((locLbl, distLbl))

        # section 3 is risk insight bullets, rebuilt every refresh
        self._section_label(panel, "RISK INSIGHTS")
        self.insightsFrame = tk.Frame(panel, bg=C["panel"])
        self.insightsFrame.pack(fill="x", padx=12, pady=2)
        self._log_panel(panel)

    # called every time this screen is shown as it pulls latest data and updates everything
    def refresh(self):
        self.title_var.set("RISK OVERVIEW")
        self.subtitle_var.set("Real-time risk levels across the city")
        # draw the grid coloured by risk level (low/medium/high)
        self.draw_grid(mode="risk")

        # get the latest simulation state
        state = self.app.sim.get_state()
        # update the summary stat cards
        self.vRescued.set(str(state["rescued"]) + " / " + str(state["total_civilians"]))
        self.vClosures.set(str(state["blocked_roads"]))
        self.vScore.set(str(state["city_score"]))
        # update each ambulance card with its current grid position
        graph = self.app.graph
        for i, ambuId in enumerate(state["ambulance_positions"][:3]):
            r, c = graph.rc(ambuId)
            self.ambuLabels[i][0].configure(text="Grid position (" + str(r) + ", " + str(c) + ")")
            self.ambuLabels[i][1].configure(text=str((r + c) % 5 + 1) + " min")
        # clear old insight bullets then rebuild with fresh numbers
        for w in self.insightsFrame.winfo_children():
            w.destroy()
        # count high risk nodes from the graph
        highCount = 0
        for n in graph.get_all_nodes():
            if n.crime_risk_level == RiskLevel.HIGH:
                highCount = highCount + 1
        blocked = state["blocked_roads"]
        reroutes = state["reroute_count"]
        # each insight is a coloured dot + message
        insightData = [
            (C["red_l"],   "●", str(highCount) + " high-risk zones detected"),
            (C["amber_l"], "●", str(blocked) + " flooded roads blocking access"),
            (C["blue_l"],  "●", "Team rerouted " + str(reroutes) + " time(s) this simulation"),
        ]
        for (col, dot, msg) in insightData:
            f = tk.Frame(self.insightsFrame, bg=C["panel"])
            f.pack(anchor="w", pady=1)
            tk.Label(f, text=dot, bg=C["panel"], fg=col, font=("Courier New", 10)).pack(side="left")
            tk.Label(f, text=msg, bg=C["panel"], fg=C["muted2"], font=("Courier New", 8)).pack(side="left", padx=4)

        self._update_log()