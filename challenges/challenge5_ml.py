# Challenge 5: Crime risk prediction using K-Means clustering + KNN
import math
import random
from city_graph import CityGraph, LocationType, RiskLevel

numClusters = 3
maxKmeansIter = 50
knnK = 5


def getIndustrialSpots(nodes):
    spots = []
    for n in nodes:
        if n.location_type == LocationType.INDUSTRIAL:
            spots.append((n.row, n.col))
    return spots


def getNearestIndustrialDist(node, indSpots, fallback):
    if len(indSpots) == 0:
        return fallback
    minDist = None
    for (ir, ic) in indSpots:
        dist = abs(node.row - ir) + abs(node.col - ic)
        if minDist is None or dist < minDist:
            minDist = dist
    return minDist


# proximity score: closer to industrial = higher value (0 to 1 range)
def getProximityScore(dist):
    return 1.0 / (1.0 + dist)


def extractFeatures(graph):
    nodes = graph.get_all_nodes()
    indSpots = getIndustrialSpots(nodes)
    fallbackDist = graph.rows + graph.cols
    featureList = []
    for n in nodes:
        nearestDist = getNearestIndustrialDist(n, indSpots, fallbackDist)
        indProx = getProximityScore(nearestDist)
        featureList.append((n.node_id, [n.population_density, indProx]))
    return featureList


def euclideanDist(pointA, pointB):
    total = 0.0
    for i in range(len(pointA)):
        diff = pointA[i] - pointB[i]
        total = total + (diff * diff)
    return math.sqrt(total)


def getClosestCentroid(point, centroids):
    bestIdx = 0
    bestDist = euclideanDist(point, centroids[0])
    for i in range(1, len(centroids)):
        d = euclideanDist(point, centroids[i])
        if d < bestDist:
            bestDist = d
            bestIdx = i
    return bestIdx


def recalcCentroid(members, numDims):
    newCenter = [0.0] * numDims
    for point in members:
        for d in range(numDims):
            newCenter[d] = newCenter[d] + point[d]
    for d in range(numDims):
        newCenter[d] = newCenter[d] / len(members)
    return newCenter


def runKmeans(dataPoints, k, maxIter):
    numPoints = len(dataPoints)
    if numPoints == 0:
        return []
    numDims = len(dataPoints[0])
    idxList = list(range(numPoints))
    random.shuffle(idxList)
    centroids = []
    for i in range(min(k, numPoints)):
        centroids.append(list(dataPoints[idxList[i]]))
    clusterLabels = [0] * numPoints
    for iteration in range(maxIter):
        somethingChanged = False
        for i in range(numPoints):
            newCluster = getClosestCentroid(dataPoints[i], centroids)
            if clusterLabels[i] != newCluster:
                clusterLabels[i] = newCluster
                somethingChanged = True
        # stop early if clusters stabilised - no point continuing
        if somethingChanged == False:
            break
        for c in range(len(centroids)):
            members = []
            for i in range(numPoints):
                if clusterLabels[i] == c:
                    members.append(dataPoints[i])
            if len(members) > 0:
                centroids[c] = recalcCentroid(members, numDims)
    return clusterLabels


def getMedian(sortedList):
    return sortedList[len(sortedList) // 2]


# median-based thresholds: more robust than mean because population density isn't normally distributed
def getRiskForNode(feats, popMedian, indMedian):
    highPop = feats[0] > popMedian
    highInd = feats[1] > indMedian
    if highPop and highInd:
        return RiskLevel.HIGH
    elif highPop or highInd:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


def generateCrimeLabels(featureList):
    if len(featureList) == 0:
        return []
    allPops = []
    allProxs = []
    for (nid, feats) in featureList:
        allPops.append(feats[0])
        allProxs.append(feats[1])
    allPops.sort()
    allProxs.sort()
    popMedian = getMedian(allPops)
    indMedian = getMedian(allProxs)
    riskLabels = []
    for (nid, feats) in featureList:
        level = getRiskForNode(feats, popMedian, indMedian)
        riskLabels.append(level)
    return riskLabels


def generateCrimeLabelsFromClusters(clusterLabels, rawVecs):
    clusterSums = {}
    clusterCounts = {}
    for i in range(len(clusterLabels)):
        c = clusterLabels[i]
        if c not in clusterSums:
            clusterSums[c] = 0.0
            clusterCounts[c] = 0
        clusterSums[c] = clusterSums[c] + rawVecs[i][0] + rawVecs[i][1]
        clusterCounts[c] = clusterCounts[c] + 1
    clusterAvg = {}
    for c in clusterSums:
        clusterAvg[c] = clusterSums[c] / clusterCounts[c]
    sortedClusters = sorted(clusterAvg.keys(), key=lambda c: clusterAvg[c])
    clusterRiskMap = {}
    for rank, c in enumerate(sortedClusters):
        if rank == 0:
            clusterRiskMap[c] = RiskLevel.LOW
        elif rank == len(sortedClusters) - 1:
            clusterRiskMap[c] = RiskLevel.HIGH
        else:
            clusterRiskMap[c] = RiskLevel.MEDIUM
    riskLabels = []
    for i in range(len(clusterLabels)):
        riskLabels.append(clusterRiskMap[clusterLabels[i]])
    return riskLabels


# KNN
# stores all labelled training examples and at prediction time finds
# the k nearest neighbours by euclidean distance, then majority-votes their labels
def buildKnn(trainingVecs, trainingLabels):
    # nothing to precompute - KNN is a lazy learner, we just keep the data
    examples = []
    for i in range(len(trainingVecs)):
        examples.append((trainingVecs[i], trainingLabels[i]))
    return examples


def getMajorityVote(labelList):
    # counts votes and returns the label that appears most often
    counts = {}
    for lbl in labelList:
        if lbl not in counts:
            counts[lbl] = 0
        counts[lbl] = counts[lbl] + 1
    bestLabel = None
    bestCount = -1
    for lbl in counts:
        if counts[lbl] > bestCount:
            bestCount = counts[lbl]
            bestLabel = lbl
    return bestLabel


def classifyOne(examples, query, k):
    # compute distance from query to every training example
    distancePairs = []
    for (vec, lbl) in examples:
        d = euclideanDist(query, vec)
        distancePairs.append((d, lbl))
    # sort ascending by distance so the k closest are at the front
    distancePairs.sort(key=lambda pair: pair[0])
    # collect labels of the k nearest neighbours
    neighbourLabels = []
    for i in range(min(k, len(distancePairs))):
        neighbourLabels.append(distancePairs[i][1])
    return getMajorityVote(neighbourLabels)


def getClusterSizes(clusterLabels):
    sizes = {}
    for cl in clusterLabels:
        if cl not in sizes:
            sizes[cl] = 0
        sizes[cl] = sizes[cl] + 1
    return sizes


# simulation.py calls this - the full ML pipeline
def predict_risk(graph):
    print("[ML] Extracting features (population_density, industrial_proximity)...")
    featureList = extractFeatures(graph)
    if len(featureList) == 0:
        return {}

    rawVecs = []
    for (nid, vec) in featureList:
        rawVecs.append(vec)

    print("[ML] Running K-Means clustering (k=" + str(numClusters) + ")...")
    clusterLabels = runKmeans(rawVecs, numClusters, maxKmeansIter)
    sizes = getClusterSizes(clusterLabels)
    print("[ML] Cluster sizes: " + str(sizes))

    print("[ML] Generating synthetic crime labels from cluster features...")
    riskLabels = generateCrimeLabelsFromClusters(clusterLabels, rawVecs)

    print("[ML] Building KNN classifier (k=" + str(knnK) + ")...")
    # store all labelled examples so KNN can query them at prediction time
    knnExamples = buildKnn(rawVecs, riskLabels)
    print("[ML] Predicting risk for all nodes...")
    predictions = {}
    highCount = 0
    medCount = 0
    lowCount = 0
    for (nid, featVec) in featureList:
        pred = classifyOne(knnExamples, featVec, knnK)
        predictions[nid] = pred
        if pred == RiskLevel.HIGH:
            highCount = highCount + 1
        elif pred == RiskLevel.MEDIUM:
            medCount = medCount + 1
        else:
            lowCount = lowCount + 1
    print("[ML] Done: High=" + str(highCount) + ", Medium=" + str(medCount) + ", Low=" + str(lowCount))
    return predictions

def deployPolice(graph, n=10):
    # rank all nodes by risk level and i will pick the top 10 police to deploy
    riskOrder = {RiskLevel.HIGH: 0, RiskLevel.MEDIUM: 1, RiskLevel.LOW: 2}
    allNodes = graph.get_all_nodes()
    sortedNodes = sorted(allNodes, key=lambda node: riskOrder[node.crime_risk_level])
    officerPositions = []
    for node in sortedNodes:
        if len(officerPositions) >= n:
            break
        officerPositions.append(node.node_id)
    return officerPositions