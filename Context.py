import SharedData as Shared
from Fact import Fact


#World Context is an extremely simple "learner" that "learns" what is always true in the world, and thus should be ignored in preconditions
#Currently its algorithm is extremely simple, it just assumes that a fact is always true if it has never seen an example that says otherwise
#This algorithm would be extremely susceptible to noise

class Context:

    #Need to keep track of timesteps that stuff has been true for in the initial states.
    #If always true, should keep in list. As soon as data not including the fact comes through, need to drop it.

    def __init__(self):
        self.__context_data = set()
        self.__started_learning = False

    def update_context(self, initial_state_facts):
        #Case 1: Need to initialise the context. For the first time, it assumes that everything is always true
        #As it has no data to say otherwise!
        if not self.__started_learning: #This is the first piece of data to come in, just assume everything is context
            self.__context_data = set(initial_state_facts)
            self.__started_learning = True
        #Case 2: Need to remove any facts from the context that are not in the initial_states_facts list
        else:
            new_context = set()
            for fact in initial_state_facts:
                if fact in self.__context_data:
                    new_context.add(fact)
            self.__context_data = new_context

    def fact_in_context(self, fact):
        return fact in self.__context_data

    def all_facts_in_context(self):
        return list(self.__context_data)
