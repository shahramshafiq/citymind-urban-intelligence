# Challenge 1: City Layout via CSP (Backtracking + AC-3 + MRV + LCV + Min-Conflicts)
import random
from city_graph import CityGraph, LocationType

# decides how many of each building type we need based on grid size
def decideCounts(numCells):
    counts = {
        LocationType.HOSPITAL:    max(2, numCells // 50),
        LocationType.AMBU_DEPOT:  max(2, numCells // 50),
        LocationType.SCHOOL:      max(1, numCells // 80),
        LocationType.INDUSTRIAL:  max(2, numCells // 50),
        LocationType.POWER_PLANT: max(1, numCells // 80),
        LocationType.RESIDENTIAL: max(8, numCells // 4),
    }
    # fill remaining cells with empty so the grid is always full
    used = sum(counts.values())
    counts[LocationType.EMPTY] = max(0, numCells - used)
    return counts


# returns all grid neighbours of a node
def getGridNeighbours(graph, nodeId):
    r, c = graph.rc(nodeId)
    neighbours = []
    for (dr, dc) in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr = r + dr
        nc = c + dc
        if nr >= 0 and nr < graph.rows and nc >= 0 and nc < graph.cols:
            neighbours.append(graph.node_id(nr, nc))
    return neighbours


# BFS that returns all nodes reachable within maxHops steps from src
# we use this instead of shortest_path because roads aren't built yet at this stage
def bfsHops(graph, src, maxHops):
    seen = {src: 0}
    frontier = [src]
    depth = 0
    while len(frontier) > 0 and depth < maxHops:
        nextFrontier = []
        for u in frontier:
            ru, cu = graph.rc(u)
            for (dr, dc) in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr = ru + dr
                nc = cu + dc
                if nr >= 0 and nr < graph.rows and nc >= 0 and nc < graph.cols:
                    nb = graph.node_id(nr, nc)
                    if nb not in seen:
                        seen[nb] = depth + 1
                        nextFrontier.append(nb)
        frontier = nextFrontier
        depth = depth + 1
    return seen


#constraint checks are appplied here
# checks if placing val at var doesn't violate the adjacency rule
# industrial cannot be next to schools or hospitals and vice versa
def adjacencyOk(graph, assignment, var, val):
    neighbours = getGridNeighbours(graph, var)
    if val == LocationType.INDUSTRIAL:
        for nb in neighbours:
            t = assignment.get(nb)
            if t == LocationType.SCHOOL or t == LocationType.HOSPITAL:
                return False
    if val == LocationType.SCHOOL or val == LocationType.HOSPITAL:
        for nb in neighbours:
            if assignment.get(nb) == LocationType.INDUSTRIAL:
                return False
    return True


# checks that every residential node is within 3 hops of a hospital
def residentialCoverageOk(graph, assignment):
    hospCells = []
    for n in assignment:
        if assignment[n] == LocationType.HOSPITAL:
            hospCells.append(n)
    if len(hospCells) == 0:
        hasResidential = False
        for v in assignment.values():
            if v == LocationType.RESIDENTIAL:
                hasResidential = True
        return hasResidential == False
    reachable = set()
    for h in hospCells:
        reachable.update(bfsHops(graph, h, 3).keys())
    for n in assignment:
        if assignment[n] == LocationType.RESIDENTIAL and n not in reachable:
            return False
    return True


# checks that every power plant is within 2 hops of an industrial zone
def powerPlantCoverageOk(graph, assignment):
    indCells = []
    for n in assignment:
        if assignment[n] == LocationType.INDUSTRIAL:
            indCells.append(n)
    if len(indCells) == 0:
        hasPowerPlant = False
        for v in assignment.values():
            if v == LocationType.POWER_PLANT:
                hasPowerPlant = True
        return hasPowerPlant == False
    reachable = set()
    for i in indCells:
        reachable.update(bfsHops(graph, i, 2).keys())
    for n in assignment:
        if assignment[n] == LocationType.POWER_PLANT and n not in reachable:
            return False
    return True


# counts how many times each rule is violated - used by min conflicts
def countViolations(graph, assignment, wantCounts):
    tally = {"adjacency": 0, "residential": 0, "power": 0, "cardinality": 0}

    # rule 1:adjacency
    for nodeId in assignment:
        val = assignment[nodeId]
        if val == LocationType.INDUSTRIAL:
            for nb in getGridNeighbours(graph, nodeId):
                t = assignment.get(nb)
                if t == LocationType.SCHOOL or t == LocationType.HOSPITAL:
                    tally["adjacency"] = tally["adjacency"] + 1

    # rule 2:residential reach
    hospCells = []
    for n in assignment:
        if assignment[n] == LocationType.HOSPITAL:
            hospCells.append(n)
    reach3 = set()
    for h in hospCells:
        reach3.update(bfsHops(graph, h, 3).keys())
    for n in assignment:
        if assignment[n] == LocationType.RESIDENTIAL and n not in reach3:
            tally["residential"] = tally["residential"] + 1

    # rule 3:power plant reach
    indCells = []
    for n in assignment:
        if assignment[n] == LocationType.INDUSTRIAL:
            indCells.append(n)
    reach2 = set()
    for i in indCells:
        reach2.update(bfsHops(graph, i, 2).keys())
    for n in assignment:
        if assignment[n] == LocationType.POWER_PLANT and n not in reach2:
            tally["power"] = tally["power"] + 1

    # cardinality:check we have enough of each type
    got = {}
    for v in assignment.values():
        got[v] = got.get(v, 0) + 1
    for t in wantCounts:
        miss = max(0, wantCounts[t] - got.get(t, 0))
        tally["cardinality"] = tally["cardinality"] + miss

    return tally


def _scoreViolations(graph, assignment, wantCounts=None):
    if wantCounts is None:
        got = {}
        for v in assignment.values():
            got[v] = got.get(v, 0) + 1
        wantCounts = got
    return sum(countViolations(graph, assignment, wantCounts).values())


# AC3 application
# checks if two neighbouring values are compatible with each other
def pairOk(v1, v2):
    if v1 == LocationType.INDUSTRIAL and (v2 == LocationType.SCHOOL or v2 == LocationType.HOSPITAL):
        return False
    if v2 == LocationType.INDUSTRIAL and (v1 == LocationType.SCHOOL or v1 == LocationType.HOSPITAL):
        return False
    return True


# removes values from domains that can never work
# this shrinks the search space before backtracking starts
def runAC3(graph, domains):
    queue = []
    for nodeId in domains:
        for nb in getGridNeighbours(graph, nodeId):
            queue.append((nodeId, nb))

    while len(queue) > 0:
        (xi, xj) = queue.pop(0)
        badValues = []
        for vi in domains[xi]:
            compatible = False
            for vj in domains[xj]:
                if pairOk(vi, vj):
                    compatible = True
                    break
            if compatible == False:
                badValues.append(vi)
        for b in badValues:
            domains[xi].remove(b)
        if len(domains[xi]) == 0:
            return False
        if len(badValues) > 0:
            # a domain shrank, so xi's other neighbours might now have newly inconsistent values - re-check them
            for nb in getGridNeighbours(graph, xi):
                if nb != xj:
                    queue.append((nb, xi))
    return True


# BT HELPERS
# MRV
def pickNextVar(domains, assignment):
    unassigned = []
    for v in domains:
        if v not in assignment:
            unassigned.append(v)
    if len(unassigned) == 0:
        return None
    bestVar = unassigned[0]
    bestLen = len(domains[unassigned[0]])
    for v in unassigned:
        if len(domains[v]) < bestLen:
            bestLen = len(domains[v])
            bestVar = v
    return bestVar

# LCV
def orderValues(graph, var, domains, assignment):
    neighbours = []
    for nb in getGridNeighbours(graph, var):
        if nb not in assignment:
            neighbours.append(nb)
    if len(neighbours) == 0:
        return list(domains[var])
    scored = []
    for i, val in enumerate(domains[var]):
        cost = 0
        for nb in neighbours:
            for nv in domains[nb]:
                if pairOk(val, nv) == False:
                    cost = cost + 1
        scored.append((cost, i, val))
    scored.sort(key=lambda t: (t[0], t[1]))
    result = []
    for (cost, i, val) in scored:
        result.append(val)
    return result


# forward checking
def forwardCheck(graph, var, val, domains, assignment):
    snapshot = {}
    for nb in getGridNeighbours(graph, var):
        if nb in assignment:
            continue
        toRemove = []
        for nv in domains[nb]:
            if pairOk(val, nv) == False:
                toRemove.append(nv)
        if len(toRemove) > 0:
            snapshot[nb] = list(domains[nb])
            for x in toRemove:
                domains[nb].remove(x)
            if len(domains[nb]) == 0:
                # this assignment killed a neighbour's domain - restore and fail
                for k in snapshot:
                    domains[k] = snapshot[k]
                return None
    return snapshot


# restores domain values that were removed during forward checking
def restoreDomains(domains, snapshot):
    for k in snapshot:
        domains[k] = snapshot[k]


# main backtracking function
def runBacktrack(graph, domains, assignment, wantCounts, countUsed, maxSteps, stepBox):
    if stepBox[0] >= maxSteps:
        return None
    stepBox[0] = stepBox[0] + 1

    # pick the next variable using MRV
    var = pickNextVar(domains, assignment)
    if var is None:
        # all nodes assigned - check the global constraints
        if residentialCoverageOk(graph, assignment) and powerPlantCoverageOk(graph, assignment):
            return dict(assignment)
        return None

    # try each value in LCV order
    for val in orderValues(graph, var, domains, assignment):
        used = countUsed.get(val, 0)
        # cardinality cap: don't place more of this type than the target count
        if val in wantCounts and used >= wantCounts[val]:
            continue
        if adjacencyOk(graph, assignment, var, val) == False:
            continue

        assignment[var] = val
        countUsed[val] = used + 1
        snapshot = forwardCheck(graph, var, val, domains, assignment)

        if snapshot is not None:
            result = runBacktrack(graph, domains, assignment, wantCounts, countUsed, maxSteps, stepBox)
            if result is not None:
                return result
            restoreDomains(domains, snapshot)

        del assignment[var]
        countUsed[val] = used

    return None


# MIN CONF FALLBACK
# creates a random starting assignment that respects the cardinality counts
def makeRandomAssignment(graph, wantCounts):
    cells = []
    for n in graph.get_all_nodes():
        cells.append(n.node_id)
    random.shuffle(cells)
    assignment = {}
    idx = 0
    for buildingType in wantCounts:
        for _ in range(wantCounts[buildingType]):
            if idx < len(cells):
                assignment[cells[idx]] = buildingType
                idx = idx + 1
    while idx < len(cells):
        assignment[cells[idx]] = LocationType.EMPTY
        idx = idx + 1
    return assignment


# finds all cells that are currently part of a violation
def getViolatingCells(graph, assignment, wantCounts):
    bad = set()

    # adjacency violations
    for nodeId in assignment:
        val = assignment[nodeId]
        if val == LocationType.INDUSTRIAL:
            for nb in getGridNeighbours(graph, nodeId):
                t = assignment.get(nb)
                if t == LocationType.SCHOOL or t == LocationType.HOSPITAL:
                    bad.add(nodeId)
                    bad.add(nb)

    # residential reach violations
    hospCells = []
    for n in assignment:
        if assignment[n] == LocationType.HOSPITAL:
            hospCells.append(n)
    reach3 = set()
    for h in hospCells:
        reach3.update(bfsHops(graph, h, 3).keys())
    for n in assignment:
        if assignment[n] == LocationType.RESIDENTIAL and n not in reach3:
            bad.add(n)

    # power plant reach violations
    indCells = []
    for n in assignment:
        if assignment[n] == LocationType.INDUSTRIAL:
            indCells.append(n)
    reach2 = set()
    for i in indCells:
        reach2.update(bfsHops(graph, i, 2).keys())
    for n in assignment:
        if assignment[n] == LocationType.POWER_PLANT and n not in reach2:
            bad.add(n)

    return list(bad)


# min-conflicts local search - keeps swapping cells to reduce violations
def runMinConflicts(graph, wantCounts, maxIter=8000):
    assignment = makeRandomAssignment(graph, wantCounts)
    bestSeen = dict(assignment)
    bestScore = sum(countViolations(graph, assignment, wantCounts).values())

    for _ in range(maxIter):
        tally = countViolations(graph, assignment, wantCounts)
        total = sum(tally.values())
        if total == 0:
            return assignment, tally
        if total < bestScore:
            bestScore = total
            bestSeen = dict(assignment)

        # try to fix a conflicted cell first, otherwise pick randomly
        badCells = getViolatingCells(graph, assignment, wantCounts)
        allCells = list(assignment.keys())
        if len(badCells) > 0:
            cellA = random.choice(badCells)
        else:
            cellA = random.choice(allCells)

        # try 8 candidate swaps and pick the one that lowers the score most
        bestSwapCell = None
        bestSwapScore = total
        for _ in range(8):
            cellB = random.choice(allCells)
            if cellB == cellA:
                continue
            assignment[cellA], assignment[cellB] = assignment[cellB], assignment[cellA]
            newTotal = sum(countViolations(graph, assignment, wantCounts).values())
            assignment[cellA], assignment[cellB] = assignment[cellB], assignment[cellA]
            if newTotal < bestSwapScore:
                bestSwapScore = newTotal
                bestSwapCell = cellB

        if bestSwapCell is not None and bestSwapScore < total:
            assignment[cellA], assignment[bestSwapCell] = assignment[bestSwapCell], assignment[cellA]

    finalTally = countViolations(graph, bestSeen, wantCounts)
    return bestSeen, finalTally


# prints which rule had the most violations after min-conflicts finishes
def reportBlockingRule(tally):
    if not tally:
        return
    worstRule = None
    worstCount = -1
    for k in tally:
        if tally[k] > worstCount:
            worstCount = tally[k]
            worstRule = k
    if tally[worstRule] == 0:
        print("[CSP] Min-Conflicts found a fully valid layout.")
        return
    ruleNames = {
        "adjacency":   "Rule 1 (Industrial adjacent to School/Hospital)",
        "residential": "Rule 2 (Residential not within 3 hops of Hospital)",
        "power":       "Rule 3 (Power Plant not within 2 hops of Industrial)",
        "cardinality": "Cardinality target (not enough buildings of some type)",
    }
    print("[CSP] Most-violated constraint: " + ruleNames[worstRule] + " (" + str(tally[worstRule]) + " violations)")
def isLayoutValid(graph, layout, wantCounts):
    if not layout:
        return False

    tally = countViolations(graph, layout, wantCounts)
    return sum(tally.values()) == 0


def repairRule1Adjacency(graph, layout):
    """
    Fixes Rule 1:
    Industrial cannot be directly next to School or Hospital.

    It keeps building counts same by swapping Industrial cells
    with safe Empty cells.
    """
    fixed = dict(layout)

    for _ in range(300):
        conflictIndustrial = None

        for nodeId in fixed:
            if fixed[nodeId] == LocationType.INDUSTRIAL:
                for nb in getGridNeighbours(graph, nodeId):
                    if fixed.get(nb) == LocationType.SCHOOL or fixed.get(nb) == LocationType.HOSPITAL:
                        conflictIndustrial = nodeId
                        break

            if conflictIndustrial is not None:
                break

        if conflictIndustrial is None:
            return fixed

        safeEmpty = None

        for candidate in fixed:
            if fixed[candidate] != LocationType.EMPTY:
                continue

            safe = True
            for nb in getGridNeighbours(graph, candidate):
                if fixed.get(nb) == LocationType.SCHOOL or fixed.get(nb) == LocationType.HOSPITAL:
                    safe = False
                    break

            if safe:
                safeEmpty = candidate
                break

        if safeEmpty is None:
            return fixed

        fixed[conflictIndustrial], fixed[safeEmpty] = fixed[safeEmpty], fixed[conflictIndustrial]

    return fixed


def repairLayout(graph, layout, wantCounts=None, maxPasses=250):
    """
    Repairs all CSP rules by swapping cell types.

    Swaps preserve the number of each location type, which is important for
    generated layouts. If wantCounts is not supplied, the current layout counts
    are treated as the target, making this useful after manual UI edits too.
    """
    if not layout:
        return layout

    fixed = dict(layout)
    flexibleCounts = wantCounts is None

    if flexibleCounts:
        hasHospital = False
        hasResidential = False
        hasIndustrial = False
        hasPowerPlant = False
        for value in fixed.values():
            if value == LocationType.HOSPITAL:
                hasHospital = True
            elif value == LocationType.RESIDENTIAL:
                hasResidential = True
            elif value == LocationType.INDUSTRIAL:
                hasIndustrial = True
            elif value == LocationType.POWER_PLANT:
                hasPowerPlant = True

        if hasResidential and not hasHospital:
            for nodeId in fixed:
                if fixed[nodeId] == LocationType.EMPTY:
                    fixed[nodeId] = LocationType.HOSPITAL
                    break
            else:
                for nodeId in fixed:
                    if fixed[nodeId] == LocationType.RESIDENTIAL:
                        fixed[nodeId] = LocationType.HOSPITAL
                        break

        if hasPowerPlant and not hasIndustrial:
            for nodeId in fixed:
                if fixed[nodeId] == LocationType.EMPTY:
                    fixed[nodeId] = LocationType.INDUSTRIAL
                    break
            else:
                for nodeId in fixed:
                    if fixed[nodeId] == LocationType.POWER_PLANT:
                        fixed[nodeId] = LocationType.INDUSTRIAL
                        break

    if wantCounts is None and not flexibleCounts:
        wantCounts = {}
        for value in fixed.values():
            wantCounts[value] = wantCounts.get(value, 0) + 1

    scoreCounts = None if flexibleCounts else wantCounts
    bestScore = _scoreViolations(graph, fixed, scoreCounts)
    if bestScore == 0:
        return fixed

    cells = list(fixed.keys())

    for _ in range(maxPasses):
        badCells = getViolatingCells(graph, fixed, scoreCounts)
        if len(badCells) == 0:
            break

        bestMove = None
        bestReplacement = None
        bestMoveScore = bestScore

        # Try every useful swap involving a violating cell. The grid is small
        # enough that this is still fast, and it gives the repair pass teeth.
        for cellA in badCells:
            for cellB in cells:
                if cellA == cellB:
                    continue
                if fixed[cellA] == fixed[cellB]:
                    continue

                fixed[cellA], fixed[cellB] = fixed[cellB], fixed[cellA]
                newScore = _scoreViolations(graph, fixed, scoreCounts)
                fixed[cellA], fixed[cellB] = fixed[cellB], fixed[cellA]

                if newScore < bestMoveScore:
                    bestMoveScore = newScore
                    bestMove = (cellA, cellB)
                    bestReplacement = None

        if flexibleCounts:
            usefulTypes = [
                LocationType.RESIDENTIAL,
                LocationType.HOSPITAL,
                LocationType.SCHOOL,
                LocationType.INDUSTRIAL,
                LocationType.POWER_PLANT,
                LocationType.AMBU_DEPOT,
                LocationType.EMPTY,
            ]
            candidateCells = set(badCells)
            for bad in badCells:
                candidateCells.update(bfsHops(graph, bad, 3).keys())

            for cell in candidateCells:
                oldValue = fixed[cell]
                for newValue in usefulTypes:
                    if newValue == oldValue:
                        continue
                    fixed[cell] = newValue
                    newScore = _scoreViolations(graph, fixed, scoreCounts)
                    fixed[cell] = oldValue

                    if newScore < bestMoveScore:
                        bestMoveScore = newScore
                        bestMove = None
                        bestReplacement = (cell, newValue)

        if bestMove is None and bestReplacement is None:
            # We may be on a plateau. Try a small random kick, but keep it only
            # if it does not make the layout much worse.
            cellA = random.choice(badCells)
            cellB = random.choice(cells)
            if cellA == cellB or fixed[cellA] == fixed[cellB]:
                continue
            fixed[cellA], fixed[cellB] = fixed[cellB], fixed[cellA]
            kickedScore = _scoreViolations(graph, fixed, scoreCounts)
            if kickedScore <= bestScore + 1:
                bestScore = kickedScore
            else:
                fixed[cellA], fixed[cellB] = fixed[cellB], fixed[cellA]
            continue

        if bestReplacement is not None:
            cell, newValue = bestReplacement
            fixed[cell] = newValue
        else:
            a, b = bestMove
            fixed[a], fixed[b] = fixed[b], fixed[a]
        bestScore = bestMoveScore

        if bestScore == 0:
            break

    return fixed


def currentGraphLayout(graph):
    layout = {}
    for node in graph.get_all_nodes():
        layout[node.node_id] = node.location_type
    return layout


def repair_current_graph_layout(graph):
    layout = currentGraphLayout(graph)
    return repairLayout(graph, layout)

#MY WORK STARTS HERE, SIMULATION.PY CALLS THIS
def solve_layout(graph):
    numCells = graph.node_count()
    wantCounts = decideCounts(numCells)

    allTypes = [
        LocationType.EMPTY,
        LocationType.RESIDENTIAL,
        LocationType.HOSPITAL,
        LocationType.SCHOOL,
        LocationType.INDUSTRIAL,
        LocationType.POWER_PLANT,
        LocationType.AMBU_DEPOT,
    ]

    domains = {}
    for n in graph.get_all_nodes():
        domains[n.node_id] = list(allTypes)

    if runAC3(graph, domains) == False:
        print("[CSP] AC-3 wiped a domain — going straight to Min-Conflicts.")
        result, tally = runMinConflicts(graph, wantCounts)

        result = repairRule1Adjacency(graph, result)
        result = repairLayout(graph, result, wantCounts)
        tally = countViolations(graph, result, wantCounts)

        reportBlockingRule(tally)

        if isLayoutValid(graph, result, wantCounts):
            return result

        print("[CSP] Min-Conflicts could not produce a fully valid layout.")
        print("[CSP] Final violations: " + str(tally))
        print("[CSP] " + identify_conflict(graph, result))
        return None

    print("[CSP] Running backtracking with AC-3 + MRV + LCV + Forward Checking...")
    stepBox = [0]

    found = runBacktrack(
        graph,
        domains,
        {},
        wantCounts,
        {},
        maxSteps=20000,
        stepBox=stepBox
    )

    if found is not None:
        tally = countViolations(graph, found, wantCounts)

        if sum(tally.values()) == 0:
            print("[CSP] Backtracking found a valid layout in " + str(stepBox[0]) + " steps.")
            return found

        print("[CSP] Backtracking returned invalid layout. Violations: " + str(tally))

    print("[CSP] Backtracking exhausted " + str(stepBox[0]) + " steps without success.")
    print("[CSP] Switching to Min-Conflicts local search...")

    bestResult = None
    bestTally = None
    bestScore = float("inf")

    for _ in range(5):
        result, tally = runMinConflicts(graph, wantCounts)
        result = repairRule1Adjacency(graph, result)
        result = repairLayout(graph, result, wantCounts)
        tally = countViolations(graph, result, wantCounts)
        score = sum(tally.values())

        if score < bestScore:
            bestResult = result
            bestTally = tally
            bestScore = score

        if score == 0:
            break

    result = bestResult
    tally = bestTally

    reportBlockingRule(tally)

    if isLayoutValid(graph, result, wantCounts):
        print("[CSP] Min-Conflicts produced a valid layout after repair.")
        return result

    print("[CSP] No fully valid CSP layout found.")
    print("[CSP] Final violations: " + str(tally))
    print("[CSP] " + identify_conflict(graph, result))
    return None

# check for which rule is violated
def identify_conflict(graph, layout):
    if not layout:
        return "Empty layout."
    # check rule 1 :industrial next to school or hospital
    for nodeId in layout:
        val = layout[nodeId]
        if val == LocationType.INDUSTRIAL:
            r, c = graph.rc(nodeId)
            for nb in getGridNeighbours(graph, nodeId):
                t = layout.get(nb)
                if t == LocationType.SCHOOL or t == LocationType.HOSPITAL:
                    rb, cb = graph.rc(nb)
                    return "CONFLICT: Industrial at (" + str(r) + "," + str(c) + ") adjacent to " + str(t.value) + " at (" + str(rb) + "," + str(cb) + ") - violates Rule 1."

    # check rule 2 :residential within 3 hops of a hospital
    hospCells = []
    for n in layout:
        if layout[n] == LocationType.HOSPITAL:
            hospCells.append(n)
    reach3 = set()
    for h in hospCells:
        reach3.update(bfsHops(graph, h, 3).keys())
    for nodeId in layout:
        if layout[nodeId] == LocationType.RESIDENTIAL and nodeId not in reach3:
            r, c = graph.rc(nodeId)
            return "CONFLICT: Residential at (" + str(r) + "," + str(c) + ") is more than 3 hops from any Hospital - violates Rule 2."

    # check rule 3 :power plant within 2 hops of industrial
    indCells = []
    for n in layout:
        if layout[n] == LocationType.INDUSTRIAL:
            indCells.append(n)
    reach2 = set()
    for i in indCells:
        reach2.update(bfsHops(graph, i, 2).keys())
    for nodeId in layout:
        if layout[nodeId] == LocationType.POWER_PLANT and nodeId not in reach2:
            r, c = graph.rc(nodeId)
            return "CONFLICT: Power Plant at (" + str(r) + "," + str(c) + ") is more than 2 hops from any Industrial - violates Rule 3."

    return "No conflicts detected."


# kept so existing test scripts that import these names don't break
def _decide_cardinality(n_cells):
    return decideCounts(n_cells)

def _bfs_hops(graph, src, max_hops):
    return bfsHops(graph, src, max_hops)

def _grid_neighbors(graph, nid):
    return getGridNeighbours(graph, nid)

def _violation_count(graph, assignment, want_counts):
    return countViolations(graph, assignment, want_counts)
