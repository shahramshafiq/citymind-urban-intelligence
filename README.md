<div align="center">

# CityMind Urban Intelligence

An interactive city emergency simulator where five algorithms written from scratch plan a grid city, build its roads, place ambulances, route a rescue team and score crime risk.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-2E7D32?style=flat-square)
![Dependencies](https://img.shields.io/badge/Dependencies-standard%20library%20only-4B5563?style=flat-square)

</div>

## Overview

Running a city emergency response means solving several different planning problems at once: where buildings may go, which roads to build, where to station ambulances, how to reach trapped people and where crime risk is highest. CityMind puts all of these on one 10x10 grid and solves each with a classic AI technique: constraint satisfaction, a genetic algorithm, simulated annealing, A* search and K-Means with KNN. A 20-step simulation ties them together with random road floods, a rescue team and a city health score, and a Tkinter dashboard lets you edit the city while it runs. It was built as a three-person team project.

## Key Features

- **City layout by constraint satisfaction:** backtracking search with AC-3 preprocessing, MRV variable ordering, LCV value ordering and forward checking, with a min-conflicts local search and a repair pass as fallback. Rules: no industrial cell next to a school or hospital, every residential cell within 3 hops of a hospital, every power plant within 2 hops of an industrial cell.
- **Road network by genetic algorithm:** one bit per candidate road, tournament selection, elitism, crossover and mutation. Fitness penalises disconnected cells and a missing pair of edge-disjoint paths between the first hospital and the first ambulance depot, checked with a unit-capacity augmenting-path max-flow routine.
- **Ambulance placement by simulated annealing:** three ambulances placed to minimise the worst-case weighted travel cost to any residential or empty cell (a minimax objective), with Metropolis acceptance and geometric cooling. A shorter re-run happens every third step.
- **Emergency routing with A\*:** edge costs include a risk multiplier (1.0, 1.2 or 1.5) and a base cost of 0.8 between adjacent residential cells (1.0 otherwise); the heuristic is 0.8 times Euclidean distance. The route is replanned automatically when a road on it is blocked or when a road reopens.
- **Crime risk prediction:** K-Means (k=3) over population density and industrial proximity produces risk labels, a KNN classifier (k=5) predicts the final risk level per cell, and ten police units are assigned to the highest-risk cells. Both models are implemented without any library.
- **Live simulation:** 20 steps with a 30% chance per step of flooding a random road, a rescue team that saves five civilians in sequence, a timestamped event log and a city health score.
- **Editable while running:** left-click a cell to change its building type, right-click to block or unblock a neighbouring road, and choose 0.5x, 1x, 2x or 4x speed. A single change restarts the dependent modules from step 0.
- **Clean separation of concerns:** a shared `CityGraph` with an observer interface notifies the simulation and the UI of road and risk changes, and long computations run on a background thread so the window stays responsive.

## Tech Stack

| Area | Technology |
| --- | --- |
| Language | Python 3.10+ |
| Desktop UI | Tkinter (Canvas, Menu, Text) |
| Planning and search | Backtracking, AC-3, min-conflicts, genetic algorithm, simulated annealing, A* |
| Machine learning | K-Means and KNN, implemented by hand |
| Graph analysis | BFS hop counting, weighted shortest distances, unit-capacity max-flow check |
| Design | Observer pattern, background worker thread (`threading`) |
| Dependencies | None beyond the Python standard library |

## Project Structure

```text
main.py                 Entry point: starts the Tkinter app
city_graph.py           Grid graph model: nodes, roads, risk levels, observers
simulation.py           20-step simulation loop, event log, health score
challenges/
  challenge1_csp.py     City layout: backtracking, AC-3, MRV, LCV, min-conflicts
  challenge2_mst.py     Road network: genetic algorithm and max-flow check
  challenge3_sa.py      Ambulance placement: simulated annealing
  challenge4_astar.py   Emergency routing: A*
  challenge5_ml.py      Crime risk: K-Means and KNN, police deployment
ui/
  app.py                Window shell, sidebar, controls, background threading
  base_screen.py        Shared grid canvas, tooltips, click-to-edit menus
  screen_*.py           Layout, roads, risk, distance and timeline views
```

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Tkinter, which is included with the standard Python installation

No environment variables or configuration files are needed.

### Installation

```bash
git clone https://github.com/shahramshafiq/citymind-urban-intelligence.git
cd citymind-urban-intelligence
```

There are no packages to install.

### Run

```bash
python main.py
```

The window opens at 1400x880 and runs the setup pipeline (layout, roads, risk, ambulances, civilians, first route) in the background.

## Usage

- **Views:** switch between City Layout, Road Network, Risk Overview, Distance Map and Event Timeline from the left sidebar.
- **Controls:** NEXT STEP advances one simulation step, AUTO and PAUSE play the run, RESET builds a fresh city, and the speed buttons set the delay between automatic steps.
- **Edit a building:** left-click any cell and pick a type. If the edit breaks a layout rule, the City Layout view shows which rule is violated and the Repair Constraints button fixes it and restarts from step 0. If the layout is still valid, the road network, risk model, ambulance placement and route are recomputed from step 0.
- **Edit a road:** right-click a cell and choose Block or Unblock for the north, south, west or east road. The rescue route is replanned immediately.
- **Tuning:** the genetic algorithm parameters (`POP_SIZE`, `N_GENERATIONS`, `MUTATION_RATE` and others) and the simulated annealing parameters (`INITIAL_TEMP`, `COOLING_RATE` and others) are constants at the top of `challenges/challenge2_mst.py` and `challenges/challenge3_sa.py`. The grid size is set by `GRID_ROWS` and `GRID_COLS` in `ui/app.py`.
- Progress from each algorithm is also printed to the terminal with `[CSP]`, `[GA]`, `[ML]` and `[SA]` prefixes.

## Limitations and Roadmap

- No automated tests are included yet; correctness is checked inside the app through the rule status cards and the two-path verification on the Road Network view.
- Crime risk labels are synthetic: they come from K-Means clusters of population density and industrial proximity, not from real crime data.
- Some summary figures are approximations: the closures counter and city health score count roads the genetic algorithm left unbuilt together with flooded roads, and the per-ambulance wait times on the Risk Overview view are placeholders derived from grid position.
- Tuned for a 10x10 grid: A* and the annealing distance maps pick the next node with a linear scan instead of a priority queue.

## Author

**Shahram Shafiq** - [GitHub](https://github.com/shahramshafiq) | [LinkedIn](https://www.linkedin.com/in/shahramshafiq/)
