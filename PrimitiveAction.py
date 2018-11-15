#A a primitive action object holds the knowledge that the agent has about one of the 4 primitive actions, i.e.
# - Move_to
# - Grasp
# - Ungrasp
# - Hit
#More primitive actions can easily be added; they are completely implementation independent

#The agent's knowledge is stored in the form of action rules. An action rule contains a bunch of effects the rule
#is supposed to accomplish, and some preconditions that say what the agent believes should be true in order for the
#effects to occur when the motor action is carried out. See the action rule class for a more indepth explanation of
#the action rules.

#Primitive action's job is to store these action rules in an efficient way and to propogate examples to all potentially
#relevant action rules. Currently it also has functionality for making new action rules, although I'd prefer to
#move these out of this class at some point

#The data is stored in an index; __action_rule_indexes. This index contains an index for each number of effects
#an action rule can have. Within these indexes, action rules are stored in sets (the data structure) that group together
#action rules with the same index key. The index key for an action rule is simply a sorted tuple (frozen list)
#of all the property names in the effects of the action rule.

from queue import Queue
from Current_Goal import Current_Goal
from Action_Rule import Action_Rule
from Action_Rule import Effect_Set
from Action_Rule import Constraint_Set
import SharedData as Shared
from File_Writer import FileWriter
from collections import Counter
from Fact import Fact
import Example
from itertools import chain
from itertools import combinations

class Primitive_Action:

    #Constructor
    #action_type: The name of the action this primitive action represents info for, e.g. "Move_To", "Grasp", etc
    def __init__(self, action_type):

        #Set up the primitive action's necessary data
        self.__name = action_type
        #Action rules are indexed in their nodes, based on their effects
        self.__indexes = {}
        for i in range(1, Shared.MAX_EFFECT_SET_SIZE + 1): #Generate all indexes
            self.__indexes[i] = {}


        self.__dummy_node = Effect_Set_Node(Effect_Set([]), None, self)

        #Set up some data for statistical purposes
        self.__number_of_examples_processed = 0
        self.__number_of_rules = 0
        self.__counts = Counter()


    #####################################################################################################
    ### PUBLIC INTERFACE FOR PRIMITIVE ACTION
    #####################################################################################################

    #####################################################################################################
    ### LEARNING ########################################################################################
    #####################################################################################################

    #Update the knowledge in this primitive action using the given example
    def learn_from_example(self, example):
        self.__learn_from_example(example)


    #####################################################################################################
    ##### DATA RETRIEVAL ################################################################################
    #####################################################################################################

    #Taken from the python documentation
    def powerset(self, iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))


    def get_power_set_for_goal_set(self, goal_set):
        effects_sets_for_goal_set = self.__get_nodes_that_represent_goals(goal_set)
        power_set_nodes = set()
        if effects_sets_for_goal_set != []:
            for node in effects_sets_for_goal_set:
                q = Queue()
                #Using breadth first just because I wanted the practice at implementing it
                q.put(node)
                while not q.empty():
                    next_node = q.get()
                    power_set_nodes.add(next_node)
                    if next_node.get_effect_set().size() > 1:
                        for sub_node in next_node.get_subset_links():
                            if sub_node not in power_set_nodes:
                                q.put(sub_node)
        else: #Need to use the less efficient algorithm
        #Not bothering to do any optimisation unless it becomes a necessity
            ps = self.powerset(goal_set.goals())
            for s in ps:
                if len(s) > 0:
                    nodes_for_s = self.__get_nodes_that_represent_goals(Current_Goal(list(s)))
                    for node in nodes_for_s:
                        power_set_nodes.add(node)
        return power_set_nodes

    def __get_nodes_that_represent_goals(self, goal_set):
        nodes = []
        goals = goal_set.goals()
        size = len(goals)
        index_key = self.__get_index_key_for_goals(goals)
        if index_key not in self.__indexes[size]:
            return []
        index_to_search = self.__indexes[size][index_key]
        for node in index_to_search:
            if node.maps_onto_goals(goal_set): #There will always be just one with place intentions
                nodes.append(node)
        return nodes

    #Finds the index key that the action rule for the goals will be stored under
    def __get_index_key_for_goals(self, goals):
        predicate_names = []
        for goal in goals:
            predicate_names.append(goal.get_predicate())
        return tuple(sorted(predicate_names))


#########################################################################################################################
#########################################################################################################################
#########################################################################################################################


    #Semi private, returns the outer index structures
    def _get_indexes(self):
        return self.__indexes

    #Returns all action rules of the specified size
    def action_rules_of_size(self, n):
        count = 0
        action_rules = [] #The list to put AR's in
        index = self.__indexes[n] #The outer index
        for key in index: #Go through each entry
            es_list = index[key]
            count += 1
            for node in es_list:

                ar_list = node.get_action_rules()
                for ar in ar_list:
                    action_rules.append(ar)
        return action_rules

    def effect_set_nodes_of_size(self, n):
        effect_set_nodes = []
        index = self.__indexes[n]
        for key in index:
            es_list = index[key]
            for node in es_list:
                effect_set_nodes.append(node)
        return effect_set_nodes

    #Which motor action is this structure for?
    def get_motor_action(self):
        return self.__name

#####################################################################################################
###CODE FOR UPDATING PRIMITIVE ACTION KNOWLEDGE WITH EXAMPLE
#####################################################################################################

    def equiv_node(self, node):
        n = node.get_effect_set().size()
        index_key = node.get_effect_set().get_index_key()
        outer_index = self.__indexes[n]
        if index_key in outer_index:
            candidates = self.__indexes[n][index_key]
            for cand_node in candidates:
                if cand_node.equivalent(node) is not None:
                    return cand_node
        return None

    def add_node_to_lattice(self, node):
        n = node.get_effect_set().size()
        index_key = node.get_effect_set().get_index_key()
        outer_index = self.__indexes[n]
        if index_key not in outer_index:
            outer_index[index_key] = set()
        outer_index[index_key].add(node)
        if n == 1:
            self.__dummy_node.link_to_superset(node)

    #Use the given example to learn more about the action rules for the given primitive action
    def __learn_from_example(self, example):
        assert example.get_action() == self.__name #If this fails, something is wrong with the class that called process_example()
        self.__number_of_examples_processed += 1

        effects = example.get_effect_facts()
        intention = example.get_intention_fact()
        gen = Fact.generalise_list_of_facts([[intention], effects])
        [[gen_intention], gen_effects] = gen #Unpack the generalised example

        for gen_effect in gen_effects:
            es_with_gen_effect = Effect_Set([gen_effect])
            node = Effect_Set_Node(es_with_gen_effect, gen_intention, self)
            node_in_lattice = self.equiv_node(node)
            if node_in_lattice == None:
                self.add_node_to_lattice(node)
                node_in_lattice = node
            node_in_lattice.apply_example_to_node(example)

    #Recursively applies the example to all nodes in the tree, adding new action rules where necessary
    def __apply_example_to_action_rule(self, node_with_ar, example):
        if node_with_ar.example_already_seen(example): #Already processed this node with this example!
            return
        node_with_ar.add_example_seen(example) #So we don't process it twice
        above_support_before = node_with_ar.get_action_rule().above_support_threshold()
        example_is_positive = node_with_ar.get_action_rule().learn_from_example(example)
        if example_is_positive:
            #Need to remove this example from the unique support of all subsets of this node
            for subset_node in node_with_ar.get_subset_links():
                subset_node.get_action_rule().remove_unique_support(example)
            Example.example_to_action_rule_counts.update([example.get_example_id()])
            FileWriter().log_example_added_to_action_rule_attempt(True, node_with_ar.get_action_rule(), example)
            above_support_after = node_with_ar.get_action_rule().above_support_threshold()
            if not above_support_before and above_support_after and node_with_ar.get_action_rule().size() < Shared.MAX_EFFECT_SET_SIZE:
                self.__generate_supersets_for_node(node_with_ar, example)
            #Apply the example to all supersets
            for superset_node in node_with_ar.get_superset_links():
                self.__apply_example_to_action_rule(superset_node, example)

class Effect_Set_Node:

    def __init__(self, effect_set, intention, prim):
        self.__prim_action = prim
        self.__intention = intention #This is part of the key
        self.__effect_set = effect_set #This is part of the key
        self.__super_set_links = set()
        self.__sub_set_links = set()
        self.__action_rules = [] #What are all the action rules that have this effect set?
        self.__examples_processed = set() #To help reduce double visiting that then results in redundant superset generation
        self.__support = 0
        self.__best_ar_support_above = False
        self.__combined = False
        self.__examples_seen = set()
        self.__examples_supporting = set()
        self.__subsumed_examples_supporting = set()

    def process_subsumed_example(self, example):
        ex_id = example.get_example_id()
        self.__subsumed_examples_supporting.add(ex_id)
        for ar in self.__action_rules:
            ar.remove_unique_support(example)

    #Some heuristics might have been used outside the class to ensure that this node is only passed examples
    #with a reasonable chance of success
    def apply_example_to_node(self, example):
        if example.get_example_id() in self.__examples_seen:
            return False#Don't want to process the same example twice!
        self.__examples_seen.add(example.get_example_id())
        bindings = self.__example_supports_es_node(example)
        if bindings != None: #If the example supports the node

            for node in self.get_subset_links():
                node.process_subsumed_example(example)

            self.__examples_supporting.add(example.get_example_id())
            #1) Increment the support
            self.__support += 1
            #2) Check if superset generation needs to be carried out
            if self.just_gone_above_support_threshold():
                self.__combined = True
                sibbling_nodes = self.__get_sibblings()

                #############################################################################################################
                #############################################################################################################
                for sibbling in sibbling_nodes:
                    new_cands = self.make_combined_nodes(sibbling)
                    for cand in new_cands:
                        equiv_node = self.__prim_action.equiv_node(cand)
                        if equiv_node is not None:
                            self.link_to_superset(equiv_node)
                            sibbling.link_to_superset(equiv_node)
                        else:
                            self.link_to_superset(cand)
                            sibbling.link_to_superset(cand)
                            self.__prim_action.add_node_to_lattice(cand)

                #############################################################################################################
                #############################################################################################################
            #3) Make a list of the relevant constraints from the example
            bindings = self.__reverse_dict(bindings)
            present_params = bindings.keys()
            relevant_constraints = example.constraints_with_params(present_params)
            generalised_constraints = set(self.__generalise_constraints(relevant_constraints, bindings))
            target_ar = self.__find_action_rule_with_constraints(generalised_constraints, bindings)
            if target_ar != None:
                target_ar.learn_from_example(example)
                if target_ar.support() >= Shared.MIN_ES_SUPPORT_TO_COMBINE:
                    for supernode in self.get_superset_links():
                        supernode.apply_example_to_node(example)
            else:
                new_ar = self.__add_new_action_rule(Constraint_Set(generalised_constraints))
                new_ar.learn_from_example(example)

    def get_support(self):
        return self.__support

    def best_bindings_score(self):
        best_score = 0
        for action_rule in self.get_action_rules():
            score_for_ar = action_rule.score_for_bindings()
            if score_for_ar > best_score:
                best_score = score_for_ar
        return best_score

    def get_unique_support(self):
        return self.__support - len(self.__subsumed_examples_supporting)

    def best_ar_support_above_threshold(self):
        if self.__best_ar_support_above == True:
            return True
        else:
            for ar in self.get_action_rules():
                if ar.support() >= Shared.MIN_ES_SUPPORT_TO_COMBINE:
                    return True
        return False

    def just_gone_above_support_threshold(self):
        if self.__combined == True:
            return False #Already done!
        if self.__support < Shared.MIN_ES_SUPPORT_TO_COMBINE:
            return False
        if self.best_ar_support_above_threshold():
            self.__combined = True
            return True
        else:
            return False

    #Checks whether or not the example supports this node
    #If it does, then return the bindings to map the example to the node
    #Otherwise, return None
    def __example_supports_es_node(self, example):
        mappings = {}
        example_intention_params = example.get_intention_fact().get_parameters()
        node_intention_params = self.get_intention().get_parameters()
        for i in range(len(example_intention_params)):
            p1 = example_intention_params[i]
            p2 = node_intention_params[i]
            mappings[p2] = p1
        bindings = self.get_effect_set().example_supports_effect_set(example, mappings)
        return bindings

    def __generalise_constraints(self, concrete_constraints, bindings):
        to_return = []
        for con in concrete_constraints:
            gen = con.get_generalised_copy_with_dictionary(bindings)
            to_return.append(gen)
        return to_return

    def __get_sibblings(self):
        sibblings = set()
        for subset in self.get_subset_links():
            sibs = subset.get_superset_links()
            for sib in sibs:
                sibblings.add(sib)
        above_threshold = set()
        for sib in sibblings:
            if sib.get_support() > Shared.MIN_ES_SUPPORT_TO_COMBINE:
                above_threshold.add(sib)
        return above_threshold

    def __reverse_dict(self, dic):
        new = {}
        for key in dic:
            new[dic[key]] = key
        return new


    #Use an awful hack to get the combined nodes.
    #Because this code will never be used again after this, and this is the final revision, it can't hurt...
    #Done via the action rule objects. Make dummy action rule objects and then extract the info out of them!
    #I trust you will forgive me for the shortcut pondy...
    def make_combined_nodes(self, other):

        new_nodes = []
        dummy_ar1 = Action_Rule(self.get_intention(), [], self.get_effect_set())
        dummy_ar2 = Action_Rule(other.get_intention(), [], other.get_effect_set())
        new_ars = dummy_ar1.get_combined_action_rules(dummy_ar2)
        for ar in new_ars:
            es = ar.get_effect_set()
            intent = ar.get_intention()
            node = Effect_Set_Node(es, intent, self.__prim_action)
            new_nodes.append(node)
        return new_nodes

    #THIS IS POTENTIALLY A BOTTLE NECK
    def __find_action_rule_with_constraints(self, constraints, bindings):
        constraints = Constraint_Set(constraints).get_constraints() #Hack to make it so that the +'s are there so that it works
        for ar in self.get_action_rules():
            constraint_set = ar.get_constraint_set().get_constraints()
            if constraint_set == constraints:
                return ar
        return None

    #Get all the action rules that have this effect set
    def get_action_rules(self):
        return self.__action_rules

    def __add_new_action_rule(self, constraint_set):
        ar = Action_Rule(self.get_intention(), constraint_set, self.get_effect_set())
        self.__action_rules.append(ar)
        return ar

    def example_already_seen(self, example):
        return example in self.__examples_processed

    def add_example_seen(self, example):
        self.__examples_processed.add(example)

    def get_superset_links(self):
        return self.__super_set_links

    def get_subset_links(self):
        return self.__sub_set_links

    #Links the node to a superset.
    #Also links the superset to this node
    def link_to_superset(self, other):
        self.__super_set_links.add(other)
        other.__sub_set_links.add(self)

    def get_intention(self):
        return self.__intention

    def get_effect_set(self):
        return self.__effect_set

    def get_superset_ids(self):
        return [node.get_action_rule().get_id() for node in self.__super_set_links]

    def get_subset_ids(self):
        return [node.get_action_rule().get_id() for node in self.__sub_set_links]

    def get_example_ids(self):
        return self.get_action_rule().positive_example_ids()

    #Do these two nodes contain an equivalent intention and effect set?
    def equivalent(self, other):
        intent1 = self.get_intention()
        intent2 = other.get_intention()
        es1 = self.get_effect_set()
        es2 = other.get_effect_set()
        #Are the intentions equivalent?
        if intent1.get_predicate() != intent2.get_predicate():
            return None
        #Are the effect sets equivalent?
        mappings = {}
        for i in range(len(intent1.get_parameters())):
            p1 = intent1.get_parameters()[i]
            p2 = intent2.get_parameters()[i]
            mappings[p1] = p2
        equiv_mapping = es1.equivalent(es2, mappings)
        if equiv_mapping is not None:
            return equiv_mapping
        else:
            return None

    #TODO define this properly!!
    def above_combine_threshold(self):
        return self.__support > 8

   #goals is a list of effects.
    def maps_onto_goals(self, goal_set):
        goals = goal_set.goals()
        goal_effect_set = Effect_Set(goals) #Exploit the effect set type to make this easy!
        return self.get_effect_set().equivalent(goal_effect_set, {}, True) is not None

    ################################################################################################################################
    ###### QUALITY HEURISTICS
    ################################################################################################################################

    #Currently just uses lots of magic numbers. Need to clean this up once confirmed this is the right approach

    def is_suitable(self):
        return (self.has_sufficient_support()) and (not self.is_subsumed()) and (self.has_good_action_rules())

    def subsumed_but_suitable_otherwise(self):
        return (self.has_sufficient_support()) and (self.is_subsumed()) and (self.has_good_action_rules())

    #Definition: At least 50% of the supporting examples are unique
    def is_subsumed(self):
        return ((self.get_unique_support() / self.get_support()) <= 0.5)

    def var_count(self):
        return len(set(list(self.get_effect_set().get_all_var_params()) + list(self.get_intention().get_parameters())))

    ##Definition: The effect set has at least 5 supporting examples
    #def has_sufficient_support(self):
        #return self.get_support() >= Shared.MIN_ES_SUPPORT_FOR_PLANNING

    ##Definiton: At least one action rule returned true
    #def has_good_action_rules(self):
        #for ar in self.get_action_rules():
            #if ar.score_for_bindings() >= 0.5 and ar.unique_support() >= Shared.MIN_AR_SUPPORT_FOR_PLANNING:
                #return True
        #return False

    def best_action_rule_score(self):
        if self.get_action_rules():
            return max([ar.quality_score() for ar in self.get_action_rules()])
        else:
            print("I have no action rules....")
            return 0

    def best_action_rule(self):
        if self.get_action_rules():
            return max(self.get_action_rules(), key=lambda ar : ar.quality_score())
        else:
            return None
