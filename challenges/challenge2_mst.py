# Challenge 2: Road network optimisation via Genetic Algorithm
import random
from city_graph import CityGraph, LocationType

# tunable parameters — easy to change live during demo
POP_SIZE = 60
N_GENERATIONS = 120
MUTATION_RATE = 0.04
CROSSOVER_RATE = 0.85
TOURNAMENT_K = 3
ELITES = 2

# penalty weights: i assigned big numbers so the GA can completely avoid these
LAMBDA_DISCONNECT = 1000.0
LAMBDA_TWO_PATHS = 500.0


# finds the first hospital and first ambulance depot in the graph
def findHospitalAndDepot(graph):
    hosp = None
    depot = None
    for n in graph.get_all_nodes():
        if n.location_type == LocationType.HOSPITAL and hosp is None:
            hosp = n.node_id
        elif n.location_type == LocationType.AMBU_DEPOT and depot is None:
            depot = n.node_id
    return hosp, depot


# returns node ids of all non-empty nodes
def getPlacedNodes(graph):
    result = []
    for n in graph.get_all_nodes():
        if n.location_type != LocationType.EMPTY:
            result.append(n.node_id)
    return result

# BFS to check if all mustReach nodes are reachable from the first one
def isConnected(adj, mustReach):
    if len(mustReach) == 0:
        return True
    start = mustReach[0]
    seen = {start}
    queue = [start]
    while len(queue) > 0:
        u = queue.pop(0)
        for v in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                queue.append(v)
    for nd in mustReach:
        if nd not in seen:
            return False
    return True


# counts how many mustReach nodes are NOT reachable from the first one
def countDisconnected(adj, mustReach):
    if len(mustReach) == 0:
        return 0
    start = mustReach[0]
    seen = {start}
    queue = [start]
    while len(queue) > 0:
        u = queue.pop(0)
        for v in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                queue.append(v)
    miss = 0
    for nd in mustReach:
        if nd not in seen:
            miss = miss + 1
    return miss


# Edmonds-Karp max flow with unit capacity
# we use this to check if there are 2 edge-disjoint paths between hospital and depot
# if max flow >= 2 then two independent paths exist (Menger's theorem)
def maxFlowUnitCap(adjSet, src, sink):
    if src not in adjSet or sink not in adjSet or src == sink:
        return 0

    usedEdges = set()
    flow = 0

    while True:
        # BFS to find an augmenting path
        prev = {src: None}
        q = [src]
        found = False
        while len(q) > 0:
            u = q.pop(0)
            if u == sink:
                found = True
                break
            for v in adjSet.get(u, []):
                if v not in prev:
                    if (u, v) not in usedEdges and (v, u) not in usedEdges:
                        prev[v] = u
                        q.append(v)
        if found == False:
            break

        # trace back the path and mark its edges as saturated so next BFS finds a different route
        cur = sink
        while prev[cur] is not None:
            p = prev[cur]
            usedEdges.add((p, cur))
            cur = p
        flow = flow + 1

    return flow


# builds adjacency list from a chromosome
def decodeChromosome(chrom, edgeList, mustNodes):
    adj = {}
    adjSet = {}
    for nodeId in mustNodes:
        adj[nodeId] = []
        adjSet[nodeId] = []
    for idx in range(len(chrom)):
        if chrom[idx] == 1:
            u = edgeList[idx][0]
            v = edgeList[idx][1]
            if u not in adj:
                adj[u] = []
                adjSet[u] = []
            if v not in adj:
                adj[v] = []
                adjSet[v] = []
            adj[u].append(v)
            adj[v].append(u)
            adjSet[u].append(v)
            adjSet[v].append(u)
    return adj, adjSet


# calculates fitness of a chromosome:higher is better
# penalises disconnected nodes and missing hospital-depot paths
def calcFitness(chrom, edgeList, mustNodes, hosp, depot):
    totalCost = 0.0
    for idx in range(len(chrom)):
        if chrom[idx] == 1:
            totalCost = totalCost + edgeList[idx][2]

    adj, adjSet = decodeChromosome(chrom, edgeList, mustNodes)

    miss = countDisconnected(adj, mustNodes)
    disconnectPenalty = miss * LAMBDA_DISCONNECT

    twoPathPenalty = 0.0
    if hosp is not None and depot is not None:
        flow = maxFlowUnitCap(adjSet, hosp, depot)
        if flow < 2:
            twoPathPenalty = (2 - flow) * LAMBDA_TWO_PATHS

    # negate: GA selects for higher fitness, but we want lower cost, so we flip the sign
    return -(totalCost + disconnectPenalty + twoPathPenalty)


# creates one random chromosome with a given density of 1s
def makeChromosome(m, density=0.5):
    chrom = []
    for _ in range(m):
        if random.random() < density:
            chrom.append(1)
        else:
            chrom.append(0)
    return chrom


# tournament selection:picks the best out of k random candidates
def tournamentPick(popWithFit):
    contenders = random.sample(popWithFit, min(TOURNAMENT_K, len(popWithFit)))
    contenders.sort(key=lambda x: x[1], reverse=True)
    return list(contenders[0][0])


# single point crossover between two parents
def crossover(p1, p2):
    if random.random() > CROSSOVER_RATE:
        return list(p1), list(p2)
    if len(p1) < 2:
        return list(p1), list(p2)
    cut = random.randint(1, len(p1) - 1)
    c1 = p1[:cut] + p2[cut:]
    c2 = p2[:cut] + p1[cut:]
    return c1, c2


# randomly flips bits in the chromosome based on mutation rate
def mutate(chrom):
    for i in range(len(chrom)):
        if random.random() < MUTATION_RATE:
            chrom[i] = 1 - chrom[i]
    return chrom


# main GA loop:evolves chromosomes over N_GENERATIONS to find the best road network
def runGA(edgeList, mustNodes, hosp, depot):
    m = len(edgeList)
    if m == 0:
        return [], 0.0

    # start with a diverse population - mix of dense and sparse chromosomes
    population = []
    for i in range(POP_SIZE):
        d = 0.3 + 0.5 * (i / max(1, POP_SIZE - 1))
        population.append(makeChromosome(m, density=d))

    popWithFit = []
    for c in population:
        popWithFit.append((c, calcFitness(c, edgeList, mustNodes, hosp, depot)))

    bestChrom = max(popWithFit, key=lambda x: x[1])[0]
    bestFit = max(popWithFit, key=lambda x: x[1])[1]

    for gen in range(N_GENERATIONS):
        # keep the top ELITES chromosomes unchanged into the next generation
        popWithFit.sort(key=lambda x: x[1], reverse=True)
        newPop = []
        for i in range(min(ELITES, len(popWithFit))):
            newPop.append(list(popWithFit[i][0]))

        # fill the rest with crossover and mutation
        while len(newPop) < POP_SIZE:
            p1 = tournamentPick(popWithFit)
            p2 = tournamentPick(popWithFit)
            c1, c2 = crossover(p1, p2)
            c1 = mutate(c1)
            c2 = mutate(c2)
            newPop.append(c1)
            if len(newPop) < POP_SIZE:
                newPop.append(c2)

        popWithFit = []
        for c in newPop:
            popWithFit.append((c, calcFitness(c, edgeList, mustNodes, hosp, depot)))

        genBestFit = max(popWithFit, key=lambda x: x[1])[1]
        if genBestFit > bestFit:
            bestFit = genBestFit
            bestChrom = list(max(popWithFit, key=lambda x: x[1])[0])

        if gen % 25 == 0:
            print("[GA] gen " + str(gen) + ": best fitness = " + str(round(bestFit, 2)))

    print("[GA] final best fitness = " + str(round(bestFit, 2)))
    return bestChrom, bestFit


# main entry point which simulation.py called
def build_road_network(graph):
    print("[GA] Building road network with Genetic Algorithm...")

    # collect all candidate edges as (u, v, cost) tuples
    rawEdges = graph.get_all_edges()
    edgeList = []
    for e in rawEdges:
        edgeList.append((e.u, e.v, e.base_cost))

    if len(edgeList) == 0:
        print("[GA] No edges available — nothing to do.")
        return

    # all nodes must stay reachable since the team and civilians can be anywhere
    mustNodes = []
    for n in graph.get_all_nodes():
        mustNodes.append(n.node_id)

    if len(mustNodes) < 2:
        print("[GA] Fewer than 2 nodes — leaving all roads open.")
        return

    hosp, depot = findHospitalAndDepot(graph)
    if hosp is None or depot is None:
        print("[GA] Warning: missing hospital or depot — 2-paths constraint will be skipped.")

    bestChrom, bestFit = runGA(edgeList, mustNodes, hosp, depot)
    # block all edges the GA decided not to use
    blocked = 0
    for idx in range(len(bestChrom)):
        if bestChrom[idx] == 0:
            u = edgeList[idx][0]
            v = edgeList[idx][1]
            graph.block_edge(u, v)
            blocked = blocked + 1

    # calculate total cost of chosen roads
    chosenCost = 0.0
    for i in range(len(bestChrom)):
        if bestChrom[i] == 1:
            chosenCost = chosenCost + edgeList[i][2]
    print("[GA] Built " + str(sum(bestChrom)) + " roads (cost=" + str(round(chosenCost, 2)) + "), blocked " + str(blocked) + " unused.")

    if hosp is not None and depot is not None:
        ok = verify_two_paths(graph, hosp, depot)
        if ok:
            print("[GA] Two edge-disjoint paths between Hospital and Depot: YES")
        else:
            print("[GA] Two edge-disjoint paths between Hospital and Depot: NO")


# checks if there are at least 2 independent paths between hospital and depot
def verify_two_paths(graph, hospitalId, depotId):
    adjSet = {}
    for n in graph.get_all_nodes():
        adjSet[n.node_id] = []
    for edge in graph.get_all_edges():
        if edge.blocked == False:
            adjSet[edge.u].append(edge.v)
            adjSet[edge.v].append(edge.u)
    flow = maxFlowUnitCap(adjSet, hospitalId, depotId)
    return flow >= 2