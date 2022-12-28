import numpy as np

"""
Framework:
Generation of new population
    To wrapper function:
        Given dimensions and number of members to generate
        Call member generator:
            Member generator:
                Do:
                    Create array of given dimensions
                    Randomly populate each index of array with either 0 or 1
                Return array
"""
def memberGenerator(nelx, nely):
    member = np.random.randint(0, 2, size=(nelx, nely))

    return member

def generateInitalPopulation(nelx, nely, numMembers):
    population = []

    for i in range(numMembers):

        population.append(memberGenerator(nelx, nely))

    return population

"""
Wrapped within an iterator:
    Evaluation
        For each member within the population:
            Pass member to fitness function:
                Fitness function (element minimization):
                    Sum the value of each array
                    Return sum
            Pair each member with fitness value
"""
def memberAndFitnessPairing(member, fitnessValue):
    memberFitnessTuple = (member, fitnessValue)

    return memberFitnessTuple

def fitnessFunction(member):
    fitnessValue = np.sum(member)

    return fitnessValue

def evaluation(population):
    memberFitnessValuePair = []

    for member in population:
        fitnessValue = fitnessFunction(member)
        memberFitnessValuePair.append(memberAndFitnessPairing(member, fitnessValue))

    return memberFitnessValuePair


"""
    Selection
        Pass member/sum array to sorting function
            Sorting function:
                Sort array of member/sum by sum
                return array
        
        Elite and cull block:
            Pass elite ratio and members to elite selector
                Elite selector:
                    Separate top ratio of memebers from the rest of the population
                    return elite population, common population

            Pass cull ratio and common population to cull function
                Cull function:
                    Given cull ratio, remove bottom % of population
                    return resulting middle population
"""
def fitnessValueKeyForSort(n):
    return n[1]

def sortMemberFitnessValuePairs(memberFitnessValuePairs):
    sortedScores = sorted(memberFitnessValuePairs, 
                            key=fitnessValueKeyForSort)

    return sortedScores

def probablilityToSelect(member):
    memberSolution = member[0]

    memberDimensions = memberSolution.shape

    obj = member[1]
    objMax = memberDimensions[0] * memberDimensions[1]

    p = 1 - (obj / objMax)

    return p

def shouldSelect(member):
    p = probablilityToSelect(member)

    probabilities = [1 - p, p]
    bools = [0, 1]

    return np.random.choice(bools, p = probabilities)


def selection(sortedPairs, numToSelect, numElite):

    if len(sortedPairs) <= 4:
        return sortedPairs

    if numElite >= len(sortedPairs):
        return sortedPairs

    numSelected = numElite
    numToSelect -= numElite

    selectedPopulation = sortedPairs[:numElite]

    toSelect = sortedPairs[numElite:]

    np.random.shuffle(toSelect)

    while(numToSelect > 0):
        if len(toSelect) < numToSelect:
            break

        np.random.shuffle(toSelect)

        for i in range(0, numToSelect):
            if shouldSelect(toSelect[i]):
                selected = toSelect.pop(i)
                selectedPopulation.append(selected)
                numToSelect -= 1

    return selectedPopulation
    
"""
    Crossover
"""
def alternateRowColSwap(memberPair):
    member1, member2 = alternateRowSwap(memberPair)

    newMemberPair = (member1, member2)

    member1, member2 = alternateColSwap(newMemberPair)

    return member1, member2

def alternateColSwap(memberPair):
    member1 = np.copy(memberPair[0])
    member2 = np.copy(memberPair[1])

    for i in range(member1.shape[1]):
        if i % 2 == 0:
            tempHold = np.copy(member1[:, i])
            member1[:, i] = member2[:, i]
            member2[:, i] = tempHold

    return member1, member2

def alternateRowSwap(memberPair):
    member1 = np.copy(memberPair[0])
    member2 = np.copy(memberPair[1])

    for i in range(member1.shape[0]):
        if i % 2 == 0:
            tempHold = np.copy(member1[i, :])
            member1[i, :] = member2[i, :]
            member2[i, :] = tempHold

    return member1, member2

def swapRandomRowBlocks(Individuals):

    Individual1, Individual2 = Individuals
    Child1 = np.empty_like(Individual1)

    Row = np.random.randint(0,Individual1.shape[0])

    Child1[0:Row, :] = Individual1[0:Row, :]
    Child1[Row:, :] = Individual2[Row:, :]

    Child2 = np.empty_like(Individual1)

    Child2[0:Row, :] = Individual2[0:Row, :]
    Child2[Row:, :] = Individual1[Row:, :]

    return Child1, Child2

def swapRandomColBlocks(Individuals):

    Individual1, Individual2 = Individuals
    Child1 = np.empty_like(Individual1)

    Col = np.random.randint(0,Individual1.shape[1])

    Child1[:, 0:Col] = Individual1[:, 0:Col]
    Child1[:, Col:] = Individual2[:, Col:]

    Child2 = np.empty_like(Individual1)

    Child2[:, 0:Col] = Individual2[:, 0:Col]
    Child2[:, Col:] = Individual1[:, Col:]

    return Child1, Child2

def swapRandomRowColBlocks(Individuals):

    rowCross = swapRandomRowBlocks(Individuals)
    rowColCross = swapRandomColBlocks(rowCross)

    return rowColCross


def crossoverOperationWrapper(solutionPair, alternate=1):
    crossoverSolutions = []

    if alternate == 0:
        newSolution1, newSolution2 = alternateRowSwap(solutionPair)
        newSolution3, newSolution4 = alternateColSwap(solutionPair)
        newSolution5, newSolution6 = alternateRowColSwap(solutionPair)
    else:
        newSolution1, newSolution2 = swapRandomRowBlocks(solutionPair)
        newSolution3, newSolution4 = swapRandomColBlocks(solutionPair)
        newSolution5, newSolution6 = swapRandomRowColBlocks(solutionPair)

    crossoverSolutions.append(newSolution1)
    crossoverSolutions.append(newSolution2)
    crossoverSolutions.append(newSolution3)
    crossoverSolutions.append(newSolution4)
    crossoverSolutions.append(newSolution5)
    crossoverSolutions.append(newSolution6)

    return crossoverSolutions

def crossover(shuffledPopulation, alternate=0):
    # Takes a shuffled population, we are just crossing each member along the array

    newMembers = []
    numMembers = len(shuffledPopulation)

    for i in range(numMembers):
        if i + 1 >= numMembers:
            memberPair = (shuffledPopulation[i], shuffledPopulation[0])
        else:
            memberPair = (shuffledPopulation[i], shuffledPopulation[i + 1])

        newSolutions = crossoverOperationWrapper(memberPair, alternate)
        
        for solution in newSolutions:
            newMembers.append(solution)

    return newMembers

"""
    Mutation
        Random chance of mutation, given by a probability

        Pass new generation to mutation function:
            For each member:
                Step through each element of solution:
                    For each element:
                        Flip bit based on mutation probability

        return new generation
"""
def shouldMutate():
    probability = [0.7, 0.3]
    boolInt = [0, 1]
    return np.random.choice(boolInt, p=probability)


def mutateMember(solution):
    unraveledSolution = np.ravel(solution)
    mutatedSolution = []

    for element in unraveledSolution:
        if shouldMutate():
            element = int(np.absolute(element - 1))
            mutatedSolution.append(element)
        else:
            mutatedSolution.append(element)

    mutatedSolution = np.reshape(mutatedSolution, newshape=solution.shape)

    return mutatedSolution

def mutation(newGeneration):
    mutatedPopulation = []

    for member in newGeneration:
        mutatedMember = mutateMember(member)
        mutatedPopulation.append(mutatedMember)

    return  mutatedPopulation

"""
    Main Wrapper Function
"""

def fitnessAverage(evaluatedMembers, listOfAverages = []):
    fitnessValues = []
    for solution, fitness in evaluatedMembers:
        fitnessValues.append(fitness)

    return np.average(fitnessValues)


def convergenceTest(population, goal):
    firstMember = population[0]

    print(("Top Performing Fitness Value: ", firstMember[1]))

    if np.sum(firstMember[1]) == goal:
        return True
    return False

def extractSolutions(solutionPairs):
    solutions = []

    for solution, fitness in solutionPairs:
        solutions.append(solution)

    return solutions

"""
    To-Change:
        Do not discard previous population
        Integrate child+mutated members within previous population
        Then pick top performing members
"""
def mainWrapper(nelx, nely, numPop, numIterations):
    newPopulation = generateInitalPopulation(nelx, nely, numPop)

    for x in range(numIterations):
        print("Iteration:", x)

        # Duplication
        toCross = np.copy(newPopulation)
        toMutate = np.copy(newPopulation)

        # This will be passed raw to the crossover algorithm
        np.random.shuffle(toCross)

        # Crossover & Mutation
        newCrossedMembers = crossover(toCross)
        newMutatedMembers = mutation(toMutate)

        for crossed in newCrossedMembers:
            newPopulation.append(crossed)

        for mutated in newMutatedMembers:
            newPopulation.append(mutated)

        # Evaluation
        memberFitnessValuePairs = evaluation(newPopulation)
        print("Avg fitness: ", fitnessAverage(memberFitnessValuePairs, []))

        # Selection
        sortedPopulation = sortMemberFitnessValuePairs(memberFitnessValuePairs)

        # Selection takes pop, numToSelect, and numElite
        # numToSelect is basically the population cap
        selectedPopulation = selection(sortedPopulation, 200, 40)

        if convergenceTest(selectedPopulation, 0):
            print('"Converged"')
            print(selectedPopulation[0])
            return selectedPopulation

        newPopulation = extractSolutions(selectedPopulation)

    return newPopulation


"""
What follows is Code for testing, this will be moved eventually or removed
"""
# Main Wrapper Testing
singleIteration = mainWrapper(10, 10, 1000, 1000)
# print(singleIteration)


# testArray = np.zeros(shape=(3, 3))
# testArrayPair = (testArray, 0)

# arrayShape = testArrayPair[0].shape
# maxObj = arrayShape[0] * arrayShape[1]
# print(maxObj)

# print(arrayShape[0])

# print(testArrayPair)
# print(testArrayPair[0].shape)
# print(testArrayPair[1])

# probablilityToSelect(testArray)