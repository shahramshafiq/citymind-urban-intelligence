# Challenge 4: A* emergency routing with dynamic replanning
# f(n) = g(n) + h(n) where h = 0.8 * Euclidean distance
# Admissible: minimum edge cost in this network is 0.8 (residential-residential, low risk).
# Each hop costs at least 0.8, so h(n) = 0.8 * euclid(n, goal) <= 0.8 * hops <= actual cost.
# Consistent: h(n) <= cost(n,n') + h(n') holds because cost(n,n') >= 0.8 and by the
# triangle inequality 0.8*euclid(n,goal) <= 0.8*1 + 0.8*euclid(n',goal).
from city_graph import CityGraph


def astar(graph, start_node, target_node):
    if start_node == target_node:
        return [start_node], 0.0

    # counter breaks ties when two nodes have equal f-scores, keeping the list stable
    counter = 0
    open_list = [(0.0, counter, start_node)]
    g_score = {start_node: 0.0}
    came_from = {}
    visited_nodes = set()

    while open_list:
        best_index = 0
        for index in range(1, len(open_list)):
            if open_list[index][0] < open_list[best_index][0]:
                best_index = index

        current_f_score, _, current_node = open_list.pop(best_index)

        if current_node == target_node:
            path = [target_node]
            node = target_node
            while node in came_from:
                node = came_from[node]
                path.append(node)
            path.reverse()
            return path, g_score[target_node]

        if current_node in visited_nodes:
            continue
        visited_nodes.add(current_node)

        for neighbor_id, road_cost in graph.get_neighbors(current_node):
            if neighbor_id in visited_nodes:
                continue
            new_cost = g_score[current_node] + road_cost
            if new_cost < g_score.get(neighbor_id, float("inf")):
                g_score[neighbor_id] = new_cost
                came_from[neighbor_id] = current_node
                estimated_cost = 0.8 * graph.euclidean_distance(neighbor_id, target_node)
                total_estimated_cost = new_cost + estimated_cost
                counter += 1
                # re-insert with updated f-score; the old entry will be skipped via the visited_nodes check
                open_list.append((total_estimated_cost, counter, neighbor_id))

    return [], float("inf")


def plan_route_to(graph: CityGraph, start_node, target_node):
    return astar(graph, start_node, target_node)
