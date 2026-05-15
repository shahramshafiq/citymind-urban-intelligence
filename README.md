# CityMind - An Urban Intelligence System

Shahram Shafiq (24i-2541) — Challenges 1, 2 + UI core  
Rafia Ali (24i-0722) — Challenges 3, 4 + CityGraph + Event Log  
Sara Nasir (24i-0719) — Challenge 5 + Simulation loop + Integration

## Setup & Running

### Requirements

- Python 3.10 or newer
- tkinter (built-in with standard Python — no pip installs needed)

### Running directly

    python main.py

On Windows, just run `python main.py` from the project root.

## Project Structure

    citymind/
    ├── main.py                     entry point
    ├── city_graph.py               shared CityGraph (single source of truth, observer pattern)
    ├── simulation.py               20-step simulation loop + event log
    ├── challenges/
    │   ├── challenge1_csp.py       CSP: Backtracking + AC-3 + MRV + LCV + Min-Conflicts
    │   ├── challenge2_mst.py       GA: road network optimisation (filename kept for compat)
    │   ├── challenge3_sa.py        SA: ambulance placement (minimax objective)
    │   ├── challenge4_astar.py     A*: emergency routing with dynamic replanning
    │   └── challenge5_ml.py        K-Means + KNN: crime risk prediction
    └── ui/
        ├── app.py                  application shell, sidebar, controls
        ├── base_screen.py          shared grid canvas, tooltips, click-to-modify
        ├── screen_layout.py        Challenge 1 view (CSP constraints)
        ├── screen_roads.py         Challenge 2 view (GA + 2-paths check)
        ├── screen_risk.py          Challenge 5 view (crime heatmap)
        ├── screen_distance.py      Challenge 3 view (ambulance coverage)
        └── screen_timeline.py      full simulation event log

## AI Techniques (5 distinct)

    Challenge 1: Backtracking CSP + AC-3 + MRV/LCV + Min-Conflicts
    Challenge 2: Genetic Algorithm with Edmonds-Karp max-flow verification
    Challenge 3: Simulated Annealing (minimax worst-case response time)
    Challenge 4: A* with admissible Euclidean heuristic + dynamic replanning
    Challenge 5: K-Means clustering (unsupervised) + KNN classifier (supervised, from scratch, no libraries)

All algorithms are implemented from scratch with no AI/ML libraries.

## Interactive Features (live demo ready)

- Left-click any cell to change its location type (Hospital, Residential, Industrial, etc.)
- When changed during simulation, ML risk predictions and SA ambulance placement recompute automatically in the background
- Right-click any cell to block/unblock adjacent roads
- Speed control: 0.5x / 1x / 2x / 4x
- All tunable parameters are at the top of each challenge file for easy live-demo tweaks

## Runtime Node Recomputation

When you change a node type during the simulation (left-click → select type), the system:
1. Accepts the new type immediately
2. Re-runs Challenge 5 (K-Means + KNN) to update crime risk predictions for all nodes
3. Re-runs Challenge 3 (SA) from scratch to reoptimise ambulance positions for the new layout
4. Replans the medical team's A* route from its current position
5. Refreshes all UI screens

## Assumptions

1. Grid size: 10x10 (changeable via GRID_ROWS/GRID_COLS in app.py)
2. Building counts scale with grid size (see decideCounts in challenge1_csp.py)
3. Road costs: 1.0 standard, 0.8 through residential zones (per project spec)
4. Primary Hospital / Depot: first hospital and first depot found in the graph
5. Flood probability: 30% per simulation step
6. 5 civilians placed randomly on residential or empty cells
7. Crime labelling: K-Means clusters nodes into 3 groups; cluster risk assigned by ranked average feature score (lowest = Low, highest = High); KNN trains on those labels
8. SA: initial temp 50, cooling rate 0.993, min temp 0.05
9. A* heuristic: 0.8 × Euclidean distance — admissible and consistent since minimum edge cost is 0.8, so h(n) never overestimates actual path cost
10. Empty nodes are valid positions for civilians and ambulances
11. KNN k=5 for crime risk classification; training labels derived from K-Means cluster rankings

