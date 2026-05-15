# simulation.py new wala
import random
import time
from city_graph import CityGraph, LocationType, RiskLevel

# Event log is displayed here
class EventLog:
    def __init__(self):
        self.entries = []
        self.police_positions = []
    # adds a new log entry with step, type, message and current timestamp
    def log(self, step, eventType, message):
        entry = {
            "step": step,
            "event_type": eventType,
            "message": message,
            "timestamp": time.strftime("%H:%M:%S"),
        }
        self.entries.append(entry)
        print("[t=" + str(step) + "] [" + eventType + "] " + message)

    # returns the last n entries
    def get_recent(self, n=10):
        return self.entries[-n:]

    def get_all(self):
        return list(self.entries)

    def clear(self):
        self.entries.clear()


# total simulation
class Simulation:
    TOTAL_STEPS = 20
    def __init__(self, graph):
        self.graph = graph
        self.log = EventLog()
        self.current_step = 0
        self.running = False
        self.speed = 1.0
        self.setup_done = False

        self.ambulance_positions = []
        self.team_position = 0
        self.civilian_targets = []
        self.rescued = []
        self.current_route = []
        self.route_cost = 0.0
        self.reroute_count = 0
        self.city_score = 100
        self.police_positions = []

        self.observers = []
        self.graph.register_observer(self)

    # basic setup
    def setup(self):
        self.log.log(0, "INFO", "CityMind simulation initialising...")
        self.runChallenge1()
        self.runChallenge2()
        self.runChallenge5()
        self.runChallenge3()
        self.placeCivilians()
        self.team_position = self.graph.node_id(0, 0)
        self._plan_next_route()
        self.setup_done = True
        self.log.log(0, "INFO", "Setup complete. Simulation ready.")
        self.notifyObservers("SETUP_COMPLETE", {})

    def runChallenge1(self):
        self.log.log(0, "INFO", "Challenge 1: Running CSP city layout planner...")

        try:
            from challenges.challenge1_csp import solve_layout, countViolations, decideCounts, identify_conflict

            layout = solve_layout(self.graph)

            if layout:
                wantCounts = decideCounts(self.graph.node_count())
                tally = countViolations(self.graph, layout, wantCounts)

                if sum(tally.values()) == 0:
                    for nodeId in layout:
                        self.graph.add_location(nodeId, layout[nodeId])

                    self.log.log(
                        0,
                        "INFO",
                        "Challenge 1: Valid CSP layout placed " + str(len(layout)) + " cells."
                    )
                else:
                    self.log.log(
                        0,
                        "CSP_ERROR",
                        "Challenge 1: Invalid CSP layout rejected. " + str(tally)
                    )
                    self.log.log(
                        0,
                        "CSP_ERROR",
                        identify_conflict(self.graph, layout)
                    )
                    self.defaultLayout()

            else:
                self.log.log(
                    0,
                    "INFO",
                    "Challenge 1: CSP returned no valid layout — using default layout."
                )
                self.defaultLayout()

        except (ImportError, NotImplementedError) as error:
            self.log.log(
                0,
                "INFO",
                "Challenge 1: Not implemented or import failed — using default layout."
            )
            self.defaultLayout()

    def runChallenge2(self):
        step = self.current_step
        self.log.log(step, "INFO", "Challenge 2: Running GA road network builder...")
        try:
            from challenges.challenge2_mst import build_road_network
            build_road_network(self.graph)
            self.log.log(step, "INFO", "Challenge 2: Road network built by GA.")
        except (ImportError, NotImplementedError):
            self.log.log(step, "INFO", "Challenge 2: Not implemented — all roads open.")

    def runChallenge3(self, quick=False):
        step = self.current_step
        self.log.log(step, "INFO", "Challenge 3: Running SA ambulance placement...")
        try:
            from challenges.challenge3_sa import place_ambulances
            prev = self.ambulance_positions if quick else None
            self.ambulance_positions = place_ambulances(self.graph, n_ambulances=3,
                                                        previous_positions=prev, quick=quick)
            self.log.log(step, "PLACEMENT", "Challenge 3: Ambulances placed at nodes " + str(self.ambulance_positions))
        except (ImportError, NotImplementedError):
            rows = self.graph.rows
            cols = self.graph.cols
            self.ambulance_positions = [
                self.graph.node_id(1, 1),
                self.graph.node_id(rows // 2, cols // 2),
                self.graph.node_id(rows - 2, cols - 2),
            ]
            self.log.log(step, "PLACEMENT", "Challenge 3: Not implemented — using default spread.")

    def runChallenge5(self):
        step = self.current_step
        self.log.log(step, "INFO", "Challenge 5: Running ML risk prediction pipeline...")
        try:
            from challenges.challenge5_ml import predict_risk, deployPolice
            predictions = predict_risk(self.graph)
            for nodeId in predictions:
                self.graph.update_risk(nodeId, predictions[nodeId])
            self.police_positions = deployPolice(self.graph)
            self.log.log(step, "POLICE",
                         "10 officers deployed to highest-risk nodes: " + str(self.police_positions))
            self.log.log(step, "RISK", "Challenge 5: Risk predictions applied to " + str(len(predictions)) + " nodes.")
        except (ImportError, NotImplementedError):
            self.log.log(step, "RISK", "Challenge 5: Not implemented — using default risk map.")
            for node in self.graph.get_all_nodes():
                if node.location_type == LocationType.INDUSTRIAL:
                    self.graph.update_risk(node.node_id, RiskLevel.HIGH)

    # randomly picks 5 civilian locations from empty or residential nodes
    def placeCivilians(self):
        candidates = []
        for n in self.graph.get_all_nodes():
            if n.location_type == LocationType.EMPTY or n.location_type == LocationType.RESIDENTIAL:
                candidates.append(n.node_id)
        random.shuffle(candidates)
        self.civilian_targets = candidates[:5]
        self.log.log(self.current_step, "INFO", "5 civilians placed at nodes " + str(self.civilian_targets))

    # fallback layout used when challenge 1 is not available
    def defaultLayout(self):
        rows = self.graph.rows
        cols = self.graph.cols
        placements = [
            (0, 2, LocationType.HOSPITAL),
            (0, cols - 1, LocationType.HOSPITAL),
            (2, 3, LocationType.AMBU_DEPOT),
            (rows - 2, cols - 3, LocationType.AMBU_DEPOT),
            (3, 5, LocationType.SCHOOL),
            (6, 2, LocationType.INDUSTRIAL),
            (6, cols - 2, LocationType.INDUSTRIAL),
            (7, 4, LocationType.POWER_PLANT),
        ]
        for (r, c, lt) in placements:
            if r >= 0 and r < rows and c >= 0 and c < cols:
                self.graph.add_location(self.graph.node_id(r, c), lt)
        for node in self.graph.get_all_nodes():
            if node.location_type == LocationType.EMPTY:
                self.graph.add_location(node.node_id, LocationType.RESIDENTIAL)

    # re-runs ML and SA when a node type is changed at runtime during the simulation
    # detects CSP state only; actual repair/restart happens from the Repair Constraints button
    def note_runtime_node_edit(self, node_id, location_type):
        self.running = False
        self.log.log(self.current_step, "INFO", "Runtime edit applied: node " + str(node_id) + " changed to " + str(location_type.value) + ".")

        try:
            from challenges.challenge1_csp import currentGraphLayout, countViolations, identify_conflict

            layout = currentGraphLayout(self.graph)
            currentCounts = {}
            for value in layout.values():
                currentCounts[value] = currentCounts.get(value, 0) + 1
            tally = countViolations(self.graph, layout, currentCounts)

            if sum(tally.values()) == 0:
                self.log.log(self.current_step, "CSP", "Runtime CSP check passed. Restarting modules from step 0.")
                self.notifyObservers("STEP_COMPLETE", {"step": self.current_step})
                return False
            else:
                self.log.log(self.current_step, "CSP_ERROR", "Runtime CSP violation detected: " + str(tally))
                self.log.log(self.current_step, "CSP_ERROR", identify_conflict(self.graph, layout))
                self.log.log(self.current_step, "INFO", "Violation is visible now. Press Repair Constraints to fix and restart from step 0.")
                self.notifyObservers("STEP_COMPLETE", {"step": self.current_step})
                return True
        except (ImportError, NotImplementedError) as error:
            self.log.log(self.current_step, "CSP_ERROR", "Runtime CSP check unavailable: " + str(error))

        self.notifyObservers("STEP_COMPLETE", {"step": self.current_step})
        return True

    # repairs constraints and resets the scenario to step 0 because the base layout has genuinely changed
    def recompute_after_node_change(self, manual_repair=True):
        self.running = False
        self.current_step = 0
        self.ambulance_positions = []
        self.team_position = self.graph.node_id(0, 0)
        self.civilian_targets = []
        self.rescued = []
        self.current_route = []
        self.route_cost = 0.0
        self.reroute_count = 0
        self.city_score = 100
        self.police_positions = []

        if manual_repair:
            self.log.log(0, "INFO", "Manual runtime repair selected — repairing CSP constraints and restarting from step 0.")
        else:
            self.log.log(0, "INFO", "Runtime layout edit is valid — restarting from step 0.")

        try:
            from challenges.challenge1_csp import repair_current_graph_layout, countViolations

            fixed = repair_current_graph_layout(self.graph)
            changed = 0
            for nodeId in fixed:
                node = self.graph.get_node(nodeId)
                if node and node.location_type != fixed[nodeId]:
                    self.graph.add_location(nodeId, fixed[nodeId])
                    changed = changed + 1

            currentCounts = {}
            for value in fixed.values():
                currentCounts[value] = currentCounts.get(value, 0) + 1
            tally = countViolations(self.graph, fixed, currentCounts)

            if sum(tally.values()) == 0:
                self.log.log(0, "CSP", "Runtime CSP repair complete. Adjusted " + str(changed) + " cells.")
            else:
                self.log.log(0, "CSP_ERROR", "Runtime CSP repair still has violations: " + str(tally))
        except (ImportError, NotImplementedError) as error:
            self.log.log(0, "CSP_ERROR", "Runtime CSP repair unavailable: " + str(error))

        for edge in self.graph.get_blocked_edges():
            self.graph.unblock_edge(edge.u, edge.v)

        self.log.log(0, "INFO", "Restarting dependent modules after runtime layout change...")
        self.runChallenge2()
        self.runChallenge5()
        self.runChallenge3(quick=False)
        self.placeCivilians()
        self.team_position = self.graph.node_id(0, 0)
        self._plan_next_route()
        self.setup_done = True
        self.updateScore()
        self.log.log(0, "INFO", "Runtime restart complete. Simulation ready at step 0.")
        self.notifyObservers("SETUP_COMPLETE", {})
        self.notifyObservers("STEP_COMPLETE", {"step": self.current_step})

    # ---- SIMULATION LOOP ----

    def step(self):
        if self.current_step >= self.TOTAL_STEPS:
            self.running = False
            self.log.log(self.current_step, "INFO", "Simulation complete.")
            self.notifyObservers("SIM_COMPLETE", {})
            return

        self.current_step = self.current_step + 1
        s = self.current_step
        self.log.log(s, "INFO", "--- Step " + str(s) + " of " + str(self.TOTAL_STEPS) + " ---")

        self._maybe_flood(s)

        if s % 5 == 0:
            self.runChallenge5()

        if s % 3 == 0:
            self.runChallenge3(quick=True)

        self._advance_team(s)
        self.updateScore()
        self.notifyObservers("STEP_COMPLETE", {"step": s})

    def _maybe_flood(self, step):
        if random.random() < 0.3:
            openEdges = []
            for e in self.graph.get_all_edges():
                # only pick from roads that are currently passable
                if e.blocked == False:
                    openEdges.append(e)
            if len(openEdges) > 0:
                chosenEdge = random.choice(openEdges)
                self.graph.block_edge(chosenEdge.u, chosenEdge.v)
                ru, cu = self.graph.rc(chosenEdge.u)
                rv, cv = self.graph.rc(chosenEdge.v)
                self.log.log(step, "FLOOD", "Road between (" + str(ru) + "," + str(cu) + ") and (" + str(rv) + "," + str(cv) + ") flooded — team rerouting.")

    def _advance_team(self, step):
        if not self.civilian_targets:
            return
        if len(self.rescued) >= len(self.civilian_targets):
            return

        MOVES_PER_STEP = 5

        for _ in range(MOVES_PER_STEP):
            target = self.current_route[-1] if self.current_route else None
            if target is None:
                return

            if not self.current_route or len(self.current_route) < 2:
                self._plan_next_route()
                return

            if len(self.current_route) > 1:
                self.team_position = self.current_route[1]
                self.current_route = self.current_route[1:]

            if self.team_position == target:
                targetIdx = self.civilian_targets.index(target)
                self.rescued.append(targetIdx)
                tr, tc = self.graph.rc(target)
                self.log.log(step, "RESCUE","Person " + str(targetIdx + 1) + " rescued at (" + str(tr) + "," + str(tc) + ")! " + str(
                                 len(self.rescued)) + "/" + str(len(self.civilian_targets)) + " saved.")
                self._plan_next_route()
                if len(self.rescued) >= len(self.civilian_targets):
                    return

    def _plan_next_route(self):
        if len(self.rescued) >= len(self.civilian_targets):
            self.current_route = []
            return
        targetIdx = None
        for i in range(len(self.civilian_targets)):
            if i not in self.rescued:
                targetIdx = i
                break
        if targetIdx is None:
            self.current_route = []
            return

        target = self.civilian_targets[targetIdx]
        path, cost = self.graph.shortest_path(self.team_position, target)
        self.current_route = path
        self.route_cost = cost
        tr, tc = self.graph.rc(target)

        if not path or cost == float("inf"):
            self.log.log(self.current_step, "REROUTE", "No available route to civilian " + str(targetIdx + 1) + " at (" + str(tr) + "," + str(tc) + "). Waiting for road changes.")
        else:
            self.log.log(self.current_step, "REROUTE", "Route planned to civilian " + str(targetIdx + 1) + " in sequence at (" + str(tr) + "," + str(tc) + "). Cost: " + str(round(cost, 1)))

    # calculates city score based on rescues, floods, and high risk zones
    def updateScore(self):
        base = 100
        # rescued fraction gives up to +40 bonus
        rescuedBonus = (len(self.rescued) / max(len(self.civilian_targets), 1)) * 40
        floodPenalty = len(self.graph.get_blocked_edges()) * 3
        riskPenalty = self.countHighRiskNodes() * 0.5
        self.city_score = max(0, min(100, int(base - floodPenalty - riskPenalty + rescuedBonus)))

    # counts how many nodes are currently high risk
    def countHighRiskNodes(self):
        count = 0
        for n in self.graph.get_all_nodes():
            if n.crime_risk_level == RiskLevel.HIGH:
                count = count + 1
        return count

    #pattern observer
    def register_observer(self, observer):
        if observer not in self.observers:
            self.observers.append(observer)

    def notifyObservers(self, eventType, data):
        for obs in self.observers:
            try:
                obs.on_sim_event(eventType, data)
            except Exception as e:
                print("[Simulation] Observer error: " + str(e))

    def on_graph_event(self, eventType, data):
        if eventType == "EDGE_BLOCKED":
            u = data["u"]
            v = data["v"]
            if len(self.current_route) >= 2:
                for i in range(len(self.current_route) - 1):
                    a = self.current_route[i]
                    b = self.current_route[i + 1]
                    if min(a, b) == min(u, v) and max(a, b) == max(u, v):
                        self.reroute_count = self.reroute_count + 1
                        self._plan_next_route()
                        self.log.log(self.current_step, "REROUTE", "Auto-reroute #" + str(self.reroute_count) + " triggered by flood.")
                        break
        elif eventType == "EDGE_UNBLOCKED":
            self.reroute_count = self.reroute_count + 1
            self._plan_next_route()
            self.log.log(self.current_step, "REROUTE", "Auto-reroute #" + str(self.reroute_count) + " triggered by reopened road.")
        elif eventType == "RISK_UPDATED":
            pass

    # states
    def get_state(self):
        return {
            "step": self.current_step,
            "total_steps": self.TOTAL_STEPS,
            "city_score": self.city_score,
            "rescued": len(self.rescued),
            "total_civilians": len(self.civilian_targets),
            "blocked_roads": len(self.graph.get_blocked_edges()),
            "reroute_count": self.reroute_count,
            "ambulance_positions": self.ambulance_positions,
            "team_position": self.team_position,
            "civilian_targets": self.civilian_targets,
            "rescued_indices": self.rescued,
            "current_route": self.current_route,
            "route_cost": self.route_cost,
            "running": self.running,
            "log": self.log.get_recent(8),
        }
