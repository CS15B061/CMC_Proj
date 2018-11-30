from generate_graph import *
import numpy as np
from copy import deepcopy
import matplotlib.pyplot as plt
import pdb
from selection_functions import minmax

'''
TSP solver using genetic algorithm
'''

class TSPPopulation(object):

    def __init__(self, 
                graph,seed=None,vertices=None,
                initial_popsize = 500,
                mutation_rate=0.02,
                crossover_point_rate = 0.5):
        self.graph = graph
        self.vertices = vertices
        if self.vertices is None:
            self.vertices = list(range(self.graph.n))
        self.n = len(self.vertices)
        self.rg = np.random.RandomState(seed)

        self.mutation_rate = mutation_rate
        
        self.crossover_point_rate = crossover_point_rate

        self.pop_size = initial_popsize

        self.reset()

        
    @property
    def gen_size(self):
        return self.current_pop.shape[0]
    
    def reset(self):
        self.current_pop = np.vstack([self.rg.permutation(self.vertices) for _ in range(self.pop_size)])
        self.costs = np.empty((len(self.current_pop)))
        self.evalpop()
    
    #Evaluate cost of solutions
    def evalpop(self):
        self.costs = np.zeros(self.gen_size)
        for i, p in enumerate(self.current_pop):
            #Sum up the weights of path
            for j in range(self.n-1):
                self.costs[i] += self.graph.get_dist(p[j],p[j+1])
            #self.costs[i] += self.graph.get_dist(p[0],p[-1])
    
    #Mutate ind
    def mutate(self,ind,mutate_rate=None, copy_ind=False):
        if mutate_rate is None:
            mutate_rate = self.mutation_rate
        if copy_ind:
            new_ind = deepcopy(ind)
        else:
            new_ind = ind
        
        for point in range(self.n):
            if self.rg.rand() < mutate_rate:
                #Swap two vertices in permutation
                swap_point = self.rg.randint(self.n)
                a,b = ind[point], ind[swap_point]
                new_ind[point], new_ind[swap_point] = b,a
        
        return new_ind
            
    def crossover(self, ind1, ind2, crossover_point_rate = None):
        if crossover_point_rate is None:
            crossover_point_rate = self.crossover_point_rate
        
        cross_points = self.rg.binomial(1,crossover_point_rate,self.n).astype(np.bool)
        keep_points = ind1[~cross_points]
        swap_points = ind2[np.isin(ind2,keep_points,invert=True)]
        new_ind = np.concatenate((keep_points,swap_points))

        return new_ind


class TSPSolver(TSPPopulation):
    def __init__(self,graph,vertices=None,crossover_rate = 0.1,fitness=None,
                selection_fun = None,cut_frac=1.0,percentile=50, *args, **kwargs):

        self.crossover_rate = crossover_rate
        self.fitness = fitness
        self.cut_frac = cut_frac
        self.percentile = percentile
        if self.fitness is None:
            self.fitness = lambda cost: np.exp(self.n*2/cost)
        
        self.selection_fun = selection_fun
        if self.selection_fun is None:
            self.selection_fun = minmax
        
        super(TSPSolver,self).__init__(graph=graph,vertices=vertices,*args, **kwargs)
        self.max_pop=self.pop_size
        self.evalpop()
        self.bestperf = []

    
    def evolve(self):
        #Compute fitness
        fitness = self.fitness(self.costs)
        bestsoln = np.argmax(fitness)
        

        #Select population
        select_index = self.selection_fun(fitness=fitness,gen_size=self.gen_size, cut_frac=self.cut_frac, percentile=self.percentile)
        if not (bestsoln in select_index):
            select_index = np.append(select_index,bestsoln)
        
        self.current_pop = self.current_pop[select_index]

        self.evalpop()
        fitness = self.fitness(self.costs)
        bestsoln = np.argmax(fitness)

        new_pop = self.current_pop.copy()

        #Perform Crossovers
        for i in range(self.gen_size):
            ind = self.current_pop[i]
            ind2 = self.rg.randint(self.gen_size)
            ind2 = self.current_pop[ind2]

            if self.rg.rand() < self.crossover_rate:
                new_ind = self.crossover(ind,ind2)
                if self.max_pop is None or self.gen_size<self.max_pop:
                    new_pop = np.append(new_pop,[new_ind], axis=0)
                elif i != bestsoln:
                    new_pop[i,:] = new_ind
            #Perform mutation
            if i != bestsoln:
                new_pop[i,:] = self.mutate(ind)
        
        self.current_pop = new_pop
        self.evalpop()

    #Return best of current population
    def get_best_soln(self):
        bestsoln = np.argmin(self.costs)
        return self.costs[bestsoln], self.current_pop[bestsoln]
    
    #Training to evolve
    def train(self, iters=500, plot=False, plotresult=False, debug=True):
        for i in range(iters):
            self.evolve()
            best = self.get_best_soln()
            self.bestperf.append(best[0])

            if debug:
                print("Gen:",str(i+1),"Best Cost:", best[0])

            if plot:
                self.graph.plot(best[1],best[0])

        if plotresult:
            plt.clf()
            plt.xlabel('Generations')
            plt.ylabel('Cost')
            plt.plot(np.arange(len(self.bestperf)),self.bestperf)
        