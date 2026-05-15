# Challenge 3: Ambulance placement using Simulated Annealing (minimax objective)
import random
import math
from city_graph import CityGraph, LocationType

# parameters for full SA run
INITIAL_TEMP = 50.0
COOLING_RATE = 0.993
MIN_TEMP = 0.05
ITERS_PER_TEMP = 8

# smaller parameters for quick re-evaluation during simulation steps
REEVAL_TEMP = 15.0
REEVAL_COOLING_RATE = 0.98
REEVAL_MIN_TEMP = 0.5
REEVAL_ITERS_PER_TEMP = 5
UNREACHABLE_PENALTY = 1000.0


def getWeightedDistances(graph, start_node):
    distances = {start_node: 0.0}
    frontier = [(0.0, start_node)]
    while frontier:
        best_index = 0
        for index in range(1, len(frontier)):
            if frontier[index][0] < frontier[best_index][0]:
                best_index = index

        current_cost, current_node = frontier.pop(best_index)
        if current_cost != distances.get(current_node):
            continue

        for neighbor_id, road_cost in graph.get_neighbors(current_node):
            new_cost = current_cost + road_cost
            if new_cost < distances.get(neighbor_id, float("inf")):
                distances[neighbor_id] = new_cost
                frontier.append((new_cost, neighbor_id))
    return distances


def calculateEnergy(graph, ambulance_positions, citizen_nodes):
    # energy = worst-case weighted travel cost to nearest ambulance (minimax)
    if not citizen_nodes or not ambulance_positions:
        return UNREACHABLE_PENALTY

    ambulance_distance_maps = []
    for ambulance_node in ambulance_positions:
        distance_map = getWeightedDistances(graph, ambulance_node)
        ambulance_distance_maps.append(distance_map)

    worst_distance = 0.0
    unreachable_count = 0
    for citizen in citizen_nodes:
        nearest_ambulance_distance = float("inf")
        for distance_map in ambulance_distance_maps:
            distance = distance_map.get(citizen, float("inf"))
            if distance < nearest_ambulance_distance:
                nearest_ambulance_distance = distance
        if nearest_ambulance_distance == float("inf"):
            unreachable_count = unreachable_count + 1
        elif nearest_ambulance_distance > worst_distance:
            worst_distance = nearest_ambulance_distance

    return worst_distance + (unreachable_count * UNREACHABLE_PENALTY)


def createNeighborState(graph, current_positions, all_nodes):
    # moves one randomly selected ambulance to a nearby or random free node
    new_positions = list(current_positions)
    ambulance_index = random.randint(0, len(new_positions) - 1)
    current_node = new_positions[ambulance_index]

    neighbors = graph.get_neighbors(current_node)
    possible_moves = []
    for neighbor_id, cost in neighbors:
        if neighbor_id not in new_positions:
            possible_moves.append(neighbor_id)

    if possible_moves:
        new_positions[ambulance_index] = random.choice(possible_moves)
    else:
        free_nodes = []
        for node_id in all_nodes:
            if node_id not in new_positions:
                free_nodes.append(node_id)
        if free_nodes:
            new_positions[ambulance_index] = random.choice(free_nodes)

    return new_positions


def runSimulatedAnnealing(graph, number_of_ambulances, starting_positions, initial_temp, cooling_rate, min_temp, iterations_per_temp):
    all_nodes = []
    for node in graph.get_all_nodes():
        all_nodes.append(node.node_id)

    citizen_nodes = []
    for node in graph.get_all_nodes():
        if node.location_type == LocationType.RESIDENTIAL:
            citizen_nodes.append(node.node_id)
        elif node.location_type == LocationType.EMPTY:
            citizen_nodes.append(node.node_id)

    if not citizen_nodes:
        citizen_nodes = list(all_nodes)

    if starting_positions and len(starting_positions) == number_of_ambulances:
        current_positions = list(starting_positions)
    else:
        random.shuffle(all_nodes)
        current_positions = all_nodes[:number_of_ambulances]

    current_energy = calculateEnergy(graph, current_positions, citizen_nodes)
    best_positions = list(current_positions)
    best_energy = current_energy
    temperature = initial_temp

    while temperature > min_temp:
        for _ in range(iterations_per_temp):
            neighbor_positions = createNeighborState(graph, current_positions, all_nodes)
            neighbor_energy = calculateEnergy(graph, neighbor_positions, citizen_nodes)
            difference = neighbor_energy - current_energy

            if difference < 0:
                current_positions = neighbor_positions
                current_energy = neighbor_energy
            else:
                # Metropolis criterion: sometimes accept worse solutions so we don't get stuck in local minima
                # probability shrinks as temperature drops, so we become stricter over time
                acceptance_probability = math.exp(-difference / temperature)
                if random.random() < acceptance_probability:
                    current_positions = neighbor_positions
                    current_energy = neighbor_energy

            # track the global best separately because current state can go backward
            if current_energy < best_energy:
                best_energy = current_energy
                best_positions = list(current_positions)

        temperature *= cooling_rate

    return best_positions, best_energy


def place_ambulances(graph: CityGraph, n_ambulances=3, previous_positions=None, quick=False):
    if quick and previous_positions:
        positions, energy = runSimulatedAnnealing(
            graph, n_ambulances, previous_positions,
            REEVAL_TEMP, REEVAL_COOLING_RATE, REEVAL_MIN_TEMP, REEVAL_ITERS_PER_TEMP
        )
        print(f"[SA] Quick re-evaluation completed. Worst-case weighted cost = {round(energy, 2)}")
    else:
        positions, energy = runSimulatedAnnealing(
            graph, n_ambulances, None,
            INITIAL_TEMP, COOLING_RATE, MIN_TEMP, ITERS_PER_TEMP
        )
        print(f"[SA] Full run completed. Worst-case weighted cost = {round(energy, 2)}")

    return positions
