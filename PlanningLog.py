#This is the data structure the agent uses to choose plans and keep track of plans
#This class allows the agent to choose a goal set to practice, and it keeps track of stats
#Eventually, it will try and determine whether or not the planning ability has improved over time
from Fact import Fact
from random import choice

plan_data = "PLANS.txt"

#Should be a singleton, but no need to enforce it. The agent can just create one planning log and use it
class Planning_Log:

    def __init__(self):
        self.load_plan_file_into_list(open(plan_data, "r"))

    #The data is stored internally as a dictionary of goals sets for keys and tuples of stats for values
    def load_plan_file_into_list(self, file):
        self.__goal_sets = {}
        while True:
            try:
                i = int(file.readline()) #How many facts in the goal set?
            except:
                break #HACK HACK HACK HACK (what does it even do? o.o)
            facts = []
            for i in range(i):
                predicate, *params = file.readline().split()
                fact = Fact(predicate, params)
                facts.append(fact)
            goal_set = tuple(facts)
            self.__goal_sets[goal_set] = Goal_Set_Stats()

    def choose_goal_set(self):
        return list(choice(list(self.__goal_sets.keys())))

    def update_goal_set(self, goal_set, result):
        goal_set = tuple(goal_set)
        if result == "Success":
            self.__goal_sets[goal_set].add_success()
        elif result == "Failure":
            self.__goal_sets[goal_set].add_failure()
        elif result == "Crash":
            self.__goal_sets[goal_set].add_crash()
        else:
            print("Unknown goal result")

    def print_table(self):
        for goal_set in self.__goal_sets:
            print([str(x) for x in list(goal_set)])
            print(self.__goal_sets[goal_set].history_string())

class Goal_Set_Stats:

    def __init__(self):
        self.__successes = 0
        self.__failures = 0
        self.__crashes = 0
        self.__history = []

    def add_crash(self):
        self.__history.append("x")
        self.__crashes += 1

    def add_success(self):
        self.__history.append("1")
        self.__successes += 1

    def add_failure(self):
        self.__history.append("0")
        self.__failures += 1

    def history_string(self):
        return " ".join(self.__history)
