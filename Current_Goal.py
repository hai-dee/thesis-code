from collections import Counter
import SharedData

#This represents a goal that has been put on the planning stack. It is either all the preconditions that
#must be satisfied for the action below it, all the goals that are not currently satisfied, or all the goals
#that the chosen action rule is expected to satisfy.
class Current_Goal:
    
    def __init__(self, goal_facts, goal_type=None, black_list=None):
        self.__sorted_goals_list = self.__make_sorted_goals_list(goal_facts)
        self.__flat_list = self.__get_flat_list_for_goals()
        self.__goal_type = goal_type
        if black_list != None:
            self.__black_list = black_list
        else:
            self.__black_list = Black_List()
            
    def add_ar_id_to_black_list(self, ar_id):
        self.__black_list.add_action_rule_to_black_list(ar_id)
        
    def get_blacklisted_ar_ids(self):
        return self.__black_list.set_of_ar_identifiers_to_exclude()
        
    def get_black_list(self):
        return self.__black_list
    
    def goal_type(self):
        return self.__goal_type
    
    def type_is_full(self):
        return self.goal_type() == "Full"
    
    def type_is_unsatisfied(self):
        return self.goal_type() == "Unsatisfied"
    
    def type_is_expected(self):
        return self.goal_type() == "Expected"
    
    def goals(self):
        return self.__flat_list
    
    def number_of_goals(self):
        return len(self.goals())    
    
    #What are all the predicates that are in the goals?
    def get_list_of_predicates(self):
        return [goal.get_predicate() for goal in self.goals()]
    
    def sorted_predicate_list(self):
        return sorted(list(set(self.get_list_of_predicates())))
    
    
    #Should be a list of sets
    def goals_sorted_by_predicate(self):
        goals = sorted(self.goals(), key=lambda goal: goal.get_predicate())        
        sorted_list = []

        current_set = None
        current_predicate = None #what predicate are we currently processing?
        
        for goal in goals:
            goal_predicate = goal.get_predicate() #What predicate does this goal have?
            if goal_predicate == current_predicate: #Does this just need to go into the same set as the previous one?
                current_set.add(goal) #This will have been intialised correctly at this point
            else:
                if current_set: #If there was a previous set of effects
                    sorted_list.append(current_set) #Put the previous one into the effects list
                current_set = set() #Need to start a new set
                current_set.add(goal) #And add this effect to it
                current_predicate = goal_predicate #And this is now the predicate we are looking for
        if current_set: #Make sure the last set makes it into the effect list
            sorted_list.append(current_set)
        return sorted_list
    
    
    def get_list_of_objects(self):
        objects = []
        for fact in self.__flat_list:
            for param in fact.get_parameters():
                if param.is_obj():
                    objects.append(param)
        return objects
    
    def get_list_of_vars(self):
        variables = []
        for fact in self.__flat_list:
            for param in fact.get_parameters():
                if param.is_var():
                    variables.append(param)
        return set(variables)
    
    def get_non_place_vars(self):
        variables = []
        for fact in self.__flat_list:
            for param in fact.get_parameters():
                if param.is_var() and param.param_type() != "place":
                    variables.append(param)
        return set(variables)        
    
    
    def stack_data_type(self):
        return "Goal"
    

    def get_goals_sorted_by_predicate(self):
        return self.__sorted_goals_list

    def get_flat_list(self):
        return self.__flat_list

    def names_in_goals(self):
        names = set()
        for fact in self.__flat_list:
            for param in fact.get_parameters():
                if param.is_value() and param.param_type() != None:
                    names.add(param.identifier())
        return names
    
    def __make_sorted_goals_list(self, goals):
        sorted_goals_list = []
        sorted_effects = sorted(goals, key=lambda effect: effect.get_predicate())
        current_set = None
        current_predicate = None #what predicate are we currently processing?
        for effect in sorted_effects:
            effect_predicate = effect.get_predicate()
            if effect_predicate == current_predicate: #Does this just need to go into the same set as the previous one?
                current_set.add(effect) #This will have been intialised correctly at this point
            else:
                if current_set: #If there was a previous set of effects
                    sorted_goals_list.append(current_set) #Put the previous one into the effects list
                current_set = set() #Need to start a new set
                current_set.add(effect) #And add this effect to it
                current_predicate = effect_predicate #And this is now the predicate we are looking for
        if current_set: #Make sure the last set makes it into the effect list
            sorted_goals_list.append(current_set)    
        return sorted_goals_list
    
    def __get_flat_list_for_goals(self):
        list_of_goals = []
        for s in self.__sorted_goals_list:
            for effect in s:
                list_of_goals.append(effect)
        return list_of_goals
    
    def print_summary(self):
        print(self.goal_type())
        for goal in self.goals():
            print(goal)
        print("Black list: " + str(self.__black_list.set_of_ar_identifiers_to_exclude()))
                  

#This class controls a list of bound action rules that have failed for the goal
class Black_List:
    
    def __init__(self):
        self.__black_list = Counter()
    
    def add_action_rule_to_black_list(self, action_rule_identifier):
        self.__black_list[action_rule_identifier] += 1
    
    def black_list_contents(self):
        return self.__black_list
    
    def set_of_ar_identifiers_to_exclude(self):
        return set([ar_id for ar_id in self.__black_list if self.__black_list[ar_id] >= SharedData.MAX_ATTEMPTS_WITH_ACTION_FOR_GOAL])