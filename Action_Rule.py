import time
import itertools
import copy
import collections
import logging

from utils.graph import Digraph

from Fact import Fact
import SharedData as Shared
import Bound_Action

class Action_Rule:

    cur_id = 0 #TODO: Refactor this into an ID generator module.

    def __init__(self, intention, constraint_set, effect_set):
        #TODO: Refactor this into an ID generator module.
        self.__id = Action_Rule.cur_id
        Action_Rule.cur_id += 1

        self.__supersets_above_threshold = False
        self.__examples_learnt_from = 0
        self.__intention = intention
        self.__intention_param_type = None
        self.__intention_param = None
        self.__initial_param = None
        self.__initial_param_type = None
        if intention.get_parameters():
            if len(intention.get_parameters()) == 2:
                self.__intention_param = intention.get_parameters()[1] #The intention param is always the second one
                self.__initial_param = intention.get_parameters()[0] #The initial param is always the first one
                self.__intention_param_type = intention.get_parameters()[1].param_type()
                self.__initial_param_type = intention.get_parameters()[0].param_type()
            elif len(intention.get_parameters()) == 1:
                self.__initial_param = intention.get_parameters()[0] #The initial param is always the first one
                self.__initial_param_type = intention.get_parameters()[0].param_type()
            else:
                logging.warning("This intention had ", intention.get_parameters(), "parameters which was unexpetcted.")
        self.__effect_set = effect_set
        self.__precondition_table = Precondition_Table() #Create an empty precondition table
        self.__supporting_positive_examples = {} #Examples that match the effects. Keys are Examples. Binding dictionarys are values.
        self.__unique_examples = []
        self.__examples_added = set() #Need to have this as well. There is too much redundancy in this class
        self.__negative_examples_identified = set()
        self.__constraints = constraint_set
        #self.__contraditing_negative_examples = set() #Examples that match the frequent preconditions but not the effects

        #PLANNING EVALUATION
        self.__expected_successes = 10
        self.__unexpected_failures  = 10
        self.__unexpected_successes = 0
        self.__expected_failures = 0


    ########################################################################################################################
    ### GENERAL PUBLIC INTERFACE FOR THE ACTION RULE
    ########################################################################################################################

    def quality_score(self):
        if self.unique_support() >= 2:
            return ((self.planning_success_percentage() * self.score_for_bindings()) * 1000) + self.unique_support()
        else:
            return 0

    def planning_success_percentage(self):
        if self.__expected_successes +self.__unexpected_failures == 0:
            return 1 #prevent a divide by 0 error
        return self.__expected_successes / (self.__expected_successes + self.__unexpected_failures)

    def add_expected_success(self):
        self.__expected_successes += 2

    def add_unexpected_failure(self):
        self.__unexpected_failures += 1

    def get_effect_set(self):
        return self.effect_set()

    def effect_set(self):
        return self.__effect_set

    #Unique identifier for the action rule
    def get_id(self):
        return self.__id

    def vars_in_effects(self):
        return self.__effect_set.get_all_var_params()

    def vars_in_intention(self):
        return self.__intention.get_parameters()

    def vars_in_ar(self):
        return set(list(self.vars_in_effects()) + list(self.vars_in_intention()))

    def score_for_bindings(self):
        return Action_Rule_Connection_Rater(self).get_connection_rating()

    def get_intention_params(self):
        return self.__intention.get_parameters()

    def has_intention_params(self):
        return bool(self.__intention_param)

    def get_set_of_vars(self):
        return self.__effect_set.get_all_var_params() | self.__intention.get_all_var_params() #checked

    def get_constraint_set(self):
        return self.__constraints

    #How much support does this action rule have? i.e. how many positive examples are there?
    def support(self):
        return self.__examples_learnt_from

    def unique_support(self):
        return len(self.__unique_examples)

    #Does this example have at least a certain number of supporting examples?
    def above_support_threshold(self):
        return self.__examples_learnt_from >= Shared.MIN_ES_SUPPORT_TO_COMBINE

    #Does this example have at least a certain percentage of supporting examples that aren't
    #also support of supersets?
    def above_unique_support_thresold(self):
        if self.__supersets_above_threshold:
            return self.unique_support() / self.support() >= Shared.MINIMUM_THRESHOLD_FOR_UNIQUE_SUPPORT
        else:
            return self.support() >= Shared.RELIABLE_FOR_PLANNING_THRESHOLD

    #The planner only cares about action rules with good enough support!
    def has_reliable_support(self):
        return self.support() >= Shared.RELIABLE_FOR_PLANNING_THRESHOLD

    #What is the agent attempting to accomplish when this action rule occurs?
    def get_intention(self):
        return self.__intention #checked

    def initial_param(self):
        return self.__initial_param

    def intention_param(self):
        return self.__intention_param

    def intention_param_type(self):
        return self.__intention_param_type


    def get_reliable_preconditions(self):
        return self.__precondition_table.get_reliable_preconditions()

    #######################################################################################################################
    #### USED BY THE PLANNER
    ##
    def get_effect_predicate_list(self):
        return self.__effect_set.get_predicate_list()
    ##
    #Note: This method uses heuristics to determine the best case for how many of the given goals in the goal object can be bound to the action rule
    #the more accurate the better, but it is not allowed to underestimate.
    def maximum_goals_matched(self, goal):
        ar_predicates = collections.Counter(self.get_effect_predicate_list())
        goal_predicates = collections.Counter(goal.get_list_of_predicates())
        unmatched_predicates = goal_predicates - ar_predicates
        return goal.number_of_goals() - sum(unmatched_predicates.values())
    ##
    ##
    ##
    #######################################################################################################################


    #Gets the effects this action rule is trying to learn preconditions for
    def get_effects(self):
        return self.__effect_set.get_effects()

    def get_constraints(self):
        return list(self.__constraints.get_constraints())

    #Note that there is no extra cost for calling this as well as add_example() as I have used caching
    def example_supports_action_rule(self, example):
        return self.__example_supports_action_rule(self, example)

    def summary(self):
        intention_string = str(self.get_intention())
        precondition_strings = self.get_precondition_strings()
        non_precondition_strings = ""
        constraint_strings = [str(x) for x in self.get_constraints()]
        effect_strings = [str(x) for x in self.get_effects()]
        return "Intention " + intention_string + "\nConstraints: " + str(constraint_strings) + "\nPreconditions: " + str(precondition_strings) + "\nEffects: " + str(effect_strings) + "\n" + "ID " + str(self.get_id()) + " | Quality " + str(self.quality_score()) + " | Unique Support: " + str(self.unique_support()) + "/" + str(self.support()) + "\n"

    #Attempt to add the given example to this action rule. If the example is successfully added, true is returned
    def learn_from_example(self, example):
        example_positive = self.__learn_from_example(example)
        return example_positive

    #Are both these action rules learning the same thing? (i.e. are the intention and effects the same)
    def is_equivalent(self, other):
        return self.__action_rules_are_equivalent(other)

    #A key to identify this action rule in the index
    def index_key(self):
        return self.__effect_set.get_index_key()

    #The size of an action rule is how many effects it contains?
    def size(self):
        return self.__effect_set.size()

    def positive_example_ids(self):
        ids = []
        for example in self.__supporting_positive_examples:
            ids.append(example.get_example_id())
        return ids

    #Used for nice file output...
    def get_effect_strings(self):
        return self.__effect_set.get_effect_strings()

    #Used for nice file output...
    def get_precondition_strings(self):
        return self.__precondition_table.get_precondition_strings()

    def get_constraint_strings(self):
        return self.__constraints.get_constraint_strings()

    def remove_unique_support(self, example):
        try:
            self.__unique_examples.remove(example)
        except:
            pass

    #What are all the possible action rules that can be contained by combining these 2 action rules?
    def get_combined_action_rules(self, other):
        return self.__get_combined_action_rules_of_size(other, self.size() + 1)


    def preconditions_match(self, current_state, goals):
        "todo"

    @staticmethod
    def generate_size_1_action_rules(example):
        action_rules = []
        intention_fact = example.get_intention_fact()
        for effect in example.get_effect_facts():
            [[gen_intention_fact], gen_effect] = Fact.generalise_list_of_facts([[intention_fact], [effect]])
            new_ar = Action_Rule(gen_intention_fact, None, Effect_Set(gen_effect))
            action_rules.append(new_ar)
        return action_rules

    #goals is a list of effects.
    def maps_onto_goals(self, goals):
        goal_effect_set = Effect_Set(goals)
        result = self.__effect_set.equivalent(goal_effect_set, {})
        if result is None:
            return False
        else:
            return True

    ########################################################################################################################
    ### Public methods that assist the planner
    ########################################################################################################################
    def best_action_rule_to_goals_mapping(self, agent_goal):
        return self.__effect_set.best_way_to_bind_goals_to_effects(agent_goal)

    #We don't want bound action rules that bind a subset of the goals that another binds.
    #I think this will only return the better bindings
    def get_possible_bound_action_rules(self, goals):
        permutations_of_effects = self.__effect_set.find_possible_effect_permutations_for_goals(goals.get_goals_sorted_by_predicate())
        permutations_of_effects.sort(key=lambda perm: perm.count(None)) #We want to check the ones with fewest None's first.
        bound_rules = []
        prev_perm = None
        for perm in permutations_of_effects:
            none_count = perm.count(None)
            if bound_rules != [] and prev_perm.count(None) < none_count:
                return bound_rules #Because we have bound rules with a lower none count already
            else:
                binding_information = self.__effect_set.bind_permutation_to_goals(perm, goals.get_flat_list())
                if binding_information != None:
                    (equivalent_variables, goals_bound) = binding_information
                    bound_rules.append(Bound_Action.Bound_Action(self, equivalent_variables,goals_bound))
            prev_perm = perm
        return bound_rules

    def get_possible_bindings(self, goals):
        permutations = self.__effect_set.find_possible_effect_permutations_for_goals(goals.get_goals_sorted_by_predicate())

    ########################################################################################################################
    ### VARIOUS STRING OUTPUT METHODS FOR ACTION RULE (USEFUL FOR DATA FILE GENERATION)
    ########################################################################################################################

    def get_effect_strings(self):
        effect_strings = []
        for effect in self.get_effects():
            effect_strings.append(effect.string_representation())
        return effect_strings

    ########################################################################################################################
    ### CODE FOR COMBINING ACTION RULES TO MAKE NEW ACTION RULES
    ########################################################################################################################

    #Returns a list of the combined action rules
    #If there are none, an empty list is returned
    def __get_combined_action_rules_of_size(self, other, size):
        assert size - 1 == self.size()
        #Are self and other the same? In that case, we want to make a version of other that has fresh variable names
        #This is to prevent weird things happening.
        if self.get_effect_set() == other.get_effect_set():
            effects_in_other = other.get_effects()
            intention_in_other = other.get_intention()
            facts_for_other = [[intention_in_other], effects_in_other]
            [[new_intent], new_facts] = Fact.assign_fresh_variables_to_list_of_facts(facts_for_other)
            other = Action_Rule(new_intent, None, Effect_Set(new_facts))

        combined_action_rules = []

        #Set up the necessary data
        es1 = self.get_effects()
        es2 = other.get_effects()
        intent1 = self.get_intention()
        intent2 = other.get_intention()

        #Check whether or not it is even possible to get successful merges
        es1_predicates = collections.Counter(self.get_effect_predicate_list())
        es2_predicates = collections.Counter(other.get_effect_predicate_list())
        left_overs_in_es1 = sum((es1_predicates - es2_predicates).values())
        if left_overs_in_es1 != 0 and left_overs_in_es1 != 1:
            return []


        #Now generate the effects for possible merged ars
        implicit_tree = self.__make_implicit_tree_dictionary(es1, es2)
        es1_index = [None] + list(implicit_tree.keys())
        bindings = {}
        if len(intent1.get_parameters()) == 2:
            bindings[intent1.get_parameters()[0]] = intent2.get_parameters()[0]
            bindings[intent1.get_parameters()[1]] = intent2.get_parameters()[1]
        elif len(intent1.get_parameters()) == 1:
            bindings[intent1.get_parameters()[0]] = intent2.get_parameters()[0]
        remaining_for_es2 = es2 + [None]
        merged_effects = self.__generate_merged_effects(implicit_tree, es1_index, remaining_for_es2, bindings)
        for merged_list in merged_effects:
            facts_for_rule = [[intent2], merged_list]
            returnval = Fact.assign_fresh_variables_to_list_of_facts(facts_for_rule)
            [[new_intent], new_effects] = returnval
            new_effects = set(list(new_effects))
            new_action_rule = Action_Rule(new_intent, None, Effect_Set(new_effects))
            combined_action_rules.append(new_action_rule)
        rules_of_correct_size = []
        for rule in combined_action_rules:
            if rule.size() == size:
                rules_of_correct_size.append(rule)
        return rules_of_correct_size


    def __make_predicate_dictionary(self, effects):

        d = dict()
        for effect in effects:
            predicate = effect.get_predicate()
            if predicate not in d:
                d[predicate] = set()
            d[predicate].add(effect)
        return d

    #What are all the possible facts from es2 that could be merged onto each fact from es1?
    #Returns an ordered dictionary
    #Order is important for the further processing, i.e. the agent wants to know that it will
    #always get the elements in the same order
    def __make_implicit_tree_dictionary(self, es1, es2):
        d = {}
        predicate_dictionary_for_es2 = self.__make_predicate_dictionary(es2)
        for effect in es1:
            predicate = effect.get_predicate()
            if predicate in predicate_dictionary_for_es2:
                d[effect] = predicate_dictionary_for_es2[predicate]
            else:
                d[effect] = set()
            d[effect].add(None)
        return d

    def __generate_merged_effects(self, implicit_tree, es1_index, remaining_for_es2, bindings):
        merged_action_rules = []
        self.__recursively_find_merged_effects(es1_index, implicit_tree, merged_action_rules, None, None, [], None, 0, bindings, remaining_for_es2)
        return merged_action_rules

    def __recursively_find_merged_effects(self, es1_index, implicit_tree, merged_action_rules, e1, e2, merged_effects, p_mergeless_effect_in_es1, level, bindings, remaining_for_es2):
        #Process what should happen in this call
        if level != 0: #This means we have just started the program
            if e2 == None: #We are wanting to match p_effect1 onto nothing
                #As long as we haven't already got a p_effect1 unmerged, we can do this
                if p_mergeless_effect_in_es1 == None:
                    p_mergeless_effect_in_es1 = e1
                else:
                    return
            else:
                #Note that the p_bindings an p_merged_effects are going to be updated by the merge_effects() method
                if not self.__merge_effects(e1, e2, bindings, merged_effects):
                    return #Don't do anything else on this call
        #Now figure out what should be done next
        if level == len(implicit_tree): #If we are at the lowest level
            if p_mergeless_effect_in_es1 != None:
                merge_less_effect_in_es2 = list(remaining_for_es2)[0]
                new_action_rules = self.__action_rules_for_merged_effects(merged_effects, bindings, p_mergeless_effect_in_es1, merge_less_effect_in_es2)
                #This method might have more than one merged action rule, because restrictions on the unmerged facts are a bit looser
                #Is the contents of updated_merged_effects a valid
                for action_rule in new_action_rules:
                    merged_action_rules.append(action_rule)
        else: #Recursive case
            #What are all the possibilities at the next level?
            next_es1_fact = es1_index[level + 1]
            for es2_fact in implicit_tree[next_es1_fact]: #What are all the facts from es2 that could map onto the es1 fact?
                if es2_fact in remaining_for_es2: #It hasn't already been mapped elsewhere
                    copy_of_merged_effects = copy.deepcopy(merged_effects)
                    copy_of_bindings = copy.deepcopy(bindings)
                    copy_of_remaining_for_es2 = copy.deepcopy(remaining_for_es2)
                    copy_of_remaining_for_es2.remove(es2_fact)
                    self.__recursively_find_merged_effects(es1_index, implicit_tree, merged_action_rules, next_es1_fact, es2_fact, copy_of_merged_effects, p_mergeless_effect_in_es1, level+1, copy_of_bindings, copy_of_remaining_for_es2)

    def __merge_effects(self, e1, e2, existing_bindings, existing_merged_effects):
        assert e1.get_predicate() == e2.get_predicate()
        params1 = e1.get_parameters()
        params2 = e2.get_parameters()
        if len(params1) != len(params2):
            return False
        params_from_es2_bound = existing_bindings.values()
        for i in range(len(params1)):
            p1 = params1[i]
            p2 = params2[i]
            if p1.param_type() != p2.param_type():
                return False #This will tell the other method a contradiction has been hit (in this case conflicting types)
            if p1 in existing_bindings:
                if existing_bindings[p1] != p2:
                    return False
            else:
                if p2 in params_from_es2_bound:
                    return False
                else:
                    existing_bindings[p1] = p2
        merged_e1 = e1.get_specific_copy_with_dictionary(existing_bindings)
        existing_merged_effects.append(merged_e1)
        return True

    def __action_rules_for_merged_effects(self, merged_effects, bindings, un_merged_in_es1, un_merged_in_es2):
        #This method's main role is to handle the fact that there might be more than one way of dealing with
        #any bindings that haven't yet been processed
        possible_ars = []
        invalid_binding = None #Is there anyway of merging that would cause only n facts?
        if un_merged_in_es1.get_predicate() == un_merged_in_es2.get_predicate():
            bindings_copy = copy.deepcopy(bindings)
            if self.__merge_effects(un_merged_in_es1, un_merged_in_es2, bindings_copy, []) == True:
                invalid_binding = bindings_copy
        #What are all the unbound variables in es1?
        remaining_1 = [var for var in un_merged_in_es1.get_parameters() if var not in bindings.keys()]
        remaining_2 = [var for var in un_merged_in_es2.get_parameters() if var not in bindings.keys()]
        #And what are all the binding permutations for these unbound variables?
        if remaining_1 != [] and remaining_2 != []:
            extended_bindings = self.__get_extended_bindings(remaining_1, remaining_2, bindings)
            if extended_bindings:
                for extended_binding in extended_bindings:
                    if extended_binding != invalid_binding:
                        copy_merged_effects = copy.deepcopy(merged_effects)
                        es1_fact = un_merged_in_es1.get_specific_copy_with_dictionary(extended_binding)
                        copy_merged_effects.append(es1_fact)
                        copy_merged_effects.append(un_merged_in_es2)
                        possible_ars.append(copy_merged_effects)
                return possible_ars
        if bindings != invalid_binding:
            es1_fact = un_merged_in_es1.get_specific_copy_with_dictionary(bindings)
            merged_effects.append(es1_fact)
            merged_effects.append(un_merged_in_es2)
            possible_ars.append(merged_effects)
        return possible_ars

    def __get_extended_bindings(self, vars1, vars2, existing_bindings):
        possible_bindings_dictionary = {}
        type_dict_for_2 = self.__make_type_dictionary(vars2)
        for var in vars1:
            typ = var.param_type()
            if typ in type_dict_for_2:
                possible_bindings_dictionary[var] = type_dict_for_2[typ]
                possible_bindings_dictionary[var].add(None)
        if possible_bindings_dictionary != {}:
            vars_in_keys = [None] + list(possible_bindings_dictionary.keys())
            extended_bindings = []
            self.__recursively_generate_bindings(vars_in_keys, possible_bindings_dictionary, 0, None, None, existing_bindings, extended_bindings)
            return extended_bindings
        else:
            return None


    def __make_type_dictionary(self, variables):
        d = dict()
        for variable in variables:
            var_type = variable.param_type()
            if var_type not in d:
                d[var_type] = set()
            d[var_type].add(variable)
        return d

    def __recursively_generate_bindings(self, keys, implicit_tree, level, param1, param2, current_binding, all_bindings):
        updated_binding = current_binding
        if level != 0:
            #Process the current state
            if param2 is not None:
                updated_binding = copy.deepcopy(current_binding) #Only copy when we need to
                updated_binding[param1] = param2
        #The base case
        if level == len(implicit_tree):
            all_bindings.append(updated_binding)
        #Else the recursive case
        else:
            new_param1 = keys[level+1]
            for new_param2 in implicit_tree[new_param1]:
                if new_param2 is None or (new_param2 not in current_binding.values()):
                    self.__recursively_generate_bindings(keys, implicit_tree, level+1, new_param1, new_param2, updated_binding, all_bindings)





#######################################################################################################################################################################
#######################################################################################################################################################################
#######################################################################################################################################################################


    #What are all the unique parameters in this action rule?
    def __get_all_parameters_in_action_rule(self):
        intention_params = set(self.get_intention().get_all_var_params())
        effect_params = set(self.__effect_set.get_all_var_params())
        return intention_params | effect_params

    #Mappings goes from self -> other
    def __generate_all_possible_mappings(self, other, mappings):
        vars_1 = self.__get_all_parameters_in_action_rule()
        vars_2 = other.__get_all_parameters_in_action_rule()
        #Need to remove any vars that are already mapped
        for key in mappings:
            vars_1.remove(key)
            vars_2.remove(mappings[key])
        possible_mappings = []
        self.__get_all_possible_mappings_recursively(mappings, vars_1, vars_2, possible_mappings)
        return possible_mappings

    #Note: Current_mapping_to_extend must be cloned every time it is extended...
    #The vars_1, vars_2 lists say what the left overs are... they must be cloned and updated each time
    #Recursion stops when no more extensions can be made, i.e. vars_1 is an empty list
    def __get_all_possible_mappings_recursively(self, current_mapping_to_extend, vars_1, vars_2, possible_mappings):
        possible_mappings.append(current_mapping_to_extend) #This also gets the "no mappings" case.
        if vars_1: #This is the recursive case, this list being empty is the base case
            for var_1 in vars_1:
                for var_2 in vars_2:
                    #Only want to add to mapping if var_1 and var_2 are of the same type
                    if var_1.param_type() == var_2.param_type():
                        cloned_mapping = copy.deepcopy(current_mapping_to_extend)
                        cloned_mapping[var_1] = var_2
                        cloned_vars_1 = copy.deepcopy(vars_1)
                        cloned_vars_1.remove(var_1)
                        cloned_vars_2 = copy.deepcopy(vars_2)
                        cloned_vars_2.remove(var_2)
                        self.__get_all_possible_mappings_recursively(cloned_mapping, cloned_vars_1, cloned_vars_2, possible_mappings)

    ########################################################################################################################
    ### CODE FOR CHECKING IF 2 ACTION RULES ARE EQUIVALENT
    ########################################################################################################################
    def __action_rules_are_equivalent(self, other):
        if self.__intention_param_type != other.__intention_param_type:
            return False #Intention params differ
        if self.index_key() != other.index_key():
            return False #They don't have the same predicates
        #Now that the quick checks are out of the way, the effect sets need to be checked for equivalency
        mappings = {}
        if self.__intention_param: #If there are intention params
            mappings[self.__intention_param] = other.__intention_param
            mappings[self.__initial_param] = other.__initial_param
        result = self.__effect_set.equivalent(other.__effect_set, mappings)
        return result

    ########################################################################################################################
    ### CODE FOR CHECKING IF AN ACTION RULE IS SUPPORTED BY AN EXAMPLE
    ########################################################################################################################

    def __example_supports_action_rule(self, example):
        if example in self.__supporting_positive_examples:
            return True
        else:
            #The intention params must match, and should be bound to one another
            #The intention param types must match
            mappings = {}
            if self.has_intention_params():
                params_in_example = example.get_intention_params()
                params_in_action_rule = self.get_intention_params()
                for i in range(len(params_in_example)):
                    p1 = params_in_example[i]
                    p2 = params_in_action_rule[i]
                    if p1.param_type() != p2.param_type():
                        logging.warning("intention params are different types!")
                        return False
                    else:
                        mappings[p2] = p1
            #And it must match the effect set...
            bindings = self.__effect_set.example_supports_effect_set(example, mappings)
            if bindings is not None: # {} means no bindings were needed
                self.__supporting_positive_examples[example] = bindings #Need to ensure this doesn't cause problems
                self.__unique_examples.append(example)
                return True
            else:
                return False


    ########################################################################################################################
    ### CODE FOR THE ACTION RULE TO LEARN FROM AN EXAMPLE
    ########################################################################################################################
    def __learn_from_example(self, example):
        if example not in self.__examples_added and self.__example_supports_action_rule(example):
            bindings = self.__supporting_positive_examples[example]
            self.__precondition_table.update_table(example, bindings)
            self.__examples_learnt_from += 1
            self.__examples_added.add(example)
            return True
        else:
            self.__negative_examples_identified.add(example)
            return False


######################################################################################################################################################
######################################################################################################################################################
## The constraints of an Action rule are stored in a Constraint_Set object
######################################################################################################################################################
######################################################################################################################################################

#Starting off by assuming that there will never be very many constraints, and thus there is no need to
class Constraint_Set:

    def __init__(self, constraints):
        self.__constraints = []
        for constraint in constraints:
            self.__constraints.append(Fact("+" + str(constraint.get_predicate()),constraint.get_parameters()))

    def get_constraints(self):
        return self.__constraints

    def get_constraint_strings(self):
        return [str(x) for x in self.__constraints]

    #Not going to bother doing constraint equivalence at this stage

    #this is NOT a permutation problem, it is simply a set equivalence problem
    def concrete_constraints_match_example_with_bindings(self, concrete_constraints, bindings):
        #The bindings (which are for the action rule) need to be applied to the concrete constraints
        #And then if the set of bound constraints is equivalent to the constraints inside this object, it will work
        bound_constraints = set()
        for constraint in concrete_constraints:
            bound_constraints.add(constraint.get_generalised_copy_with_dictionary(bindings))
        return bound_constraints == self.__constraints


######################################################################################################################################################
######################################################################################################################################################
## The effects of an Action_Rule are stored in an Effect_Set object. The Effect_Set class is a private inner
## class, only used to help the Action_Rule. Other classes will only interface with the Action_Rule
##
## Effect_Set stores its effects in a sorted list, sorted by the predicate name. Because some effects will
## have the same predicate name, the effect set stores the effects in a list of sets, where there is a set
## for each predicate that has at least one effect in the effect set. This allows the effects to be sorted
## where order is defined, and for effects of the same predicate to be easily grouped together (as matching
## operations will generally require the effects to be grouped by predicate)
##
## An effect set has a key, which is a sorted tuple of the predicate names in the effect set (duplicates
## included).
##
## Some caching is used to try and speed up operations, although at the cost of higher space usage. In
## particular, the effect set caches all permutations of a sorted list of all its effects (remember that
## order is not defined between 2 effects with the same predicate. Therefore, this allows there to be
## several valid sorted orderings of the effect set).
######################################################################################################################################################
######################################################################################################################################################

class Effect_Set:

    next_id = 0

    ############################################################################################
    ###CODE FOR THE CONSTRUCTOR
    ############################################################################################
    def __init__(self, effects):
        self.__id = Effect_Set.next_id
        Effect_Set.next_id += 1
        self.__size = len(effects) #Because counting it later is a pain
        self.__cached_index_key = None
        self.__cached_sorted_permutations = None
        self.__cached_return_value_for_get_effects = None
        self.__cached_predicate_list = None
        self.__effects = None #The next step will initialise them, just putting this here to make it easy to glance at name
        self.__add_effects(effects) #Add the effects into the structure

    def get_id(self):
        return self.__id

    #Returns a copy of this effect set - same variable names.
    #def make_copy(self):
    #    return Action_Rule.Effect_Set([effect.__get_copy_of_fact() for effect in self.get_effects()])

    #The effects are sorted by their predicate into sets (effects with the same predicate are stored in the same set), and then
    #those sets are sorted in a list.
    #This allows for more efficient computation of the expensive operations, i.e. the permutation stuff, as it means they
    #won't need to sort the effects before being able to do what they need to do.
    def __add_effects(self, effects):
        self.__effects = list()
        sorted_effects = sorted(effects, key=lambda effect: effect.get_predicate())
        current_set = None
        current_predicate = None #what predicate are we currently processing?
        for effect in sorted_effects:
            effect_predicate = effect.get_predicate()
            if effect_predicate == current_predicate: #Does this just need to go into the same set as the previous one?
                current_set.add(effect) #This will have been intialised correctly at this point
            else:
                if current_set: #If there was a previous set of effects
                    self.__effects.append(current_set) #Put the previous one into the effects list
                current_set = set() #Need to start a new set
                current_set.add(effect) #And add this effect to it
                current_predicate = effect_predicate #And this is now the predicate we are looking for
        if current_set: #Make sure the last set makes it into the effect list
            self.__effects.append(current_set)


    ############################################################################################
    ###METHODS USED BY ACTION_RULE TO USE THE EFFECT_SET
    ############################################################################################

    #Are the effect sets self and other equivalent? Optional parameter mappings can give additional
    #constraints, i.e. saying that certain variables in self must be mapped to certain variables in other
    def equivalent(self, other, mappings, print_debug=False):
        return self.__effects_are_equivalent(other, mappings)

    def example_supports_effect_set(self, example, mappings):
        return self.__example_supports_effect_set(example, mappings)

    #Gets a list of all the effects in the effect set
    #The effects will be sorted, although ordering between effects with the same predicate is not defined
    def get_effects(self):
        if not self.__cached_return_value_for_get_effects:
            list_of_effects = []
            for s in self.__effects:
                for effect in s:
                    list_of_effects.append(effect)
            self.__cached_return_value_for_get_effects = list_of_effects
        return self.__cached_return_value_for_get_effects

    #Gets the index key for this effect set
    def get_index_key(self):
        if not self.__cached_index_key:
            property_names = []
            for effect in self.get_effects():
                property_names.append(effect.get_predicate())
            self.__cached_index_key = tuple(property_names)
        return self.__cached_index_key

    def size(self):
        return self.__size

    def get_predicate_list(self):
        if not self.__cached_predicate_list:
            predicate_names = []
            for effect in self.get_effects():
                predicate_names.append(effect.get_predicate())
            self.__cached_predicate_list = predicate_names
        return self.__cached_predicate_list

    ##Does not make any guarantee that the 2 effect sets will create n+1 effect sets when merged, but will
    ##do some initial checks that will cut back on a large number that won't
    #def effect_sets_might_merge(self, other):
        #assert self.size() == other.size() #This just should not be called if they are different
        #differences = sum((Counter(self.get_predicate_list()) - Counter(other.get_predicate_list())).values())
        #return differences == 1 or differences == 0


    def get_all_var_params(self):
        var_params = set()
        for effect in self.get_effects():
            var_params = var_params | effect.get_all_var_params()
        return var_params

    ############################################################################################
    ###CODE FOR CHECKING IF 2 EFFECT SETS ARE EQUIVALENT
    ############################################################################################

    #Returns whether or not the effects in the first effect set can be mapped onto the effects in the second
    #effect set. Mappings is any existing mappings that must be used (i.e. intention param)
    def __effects_are_equivalent(self, other, mappings):
        if self.size() != other.size(): #Make sure that the 2 effect sets have the same number of effects
            print("Lengths don't match; in a good implementation this shouldn't be triggered. Bug?")
            return None
        if self.get_index_key() != other.get_index_key(): #Make sure that the 2 effect sets have the same predicates
            print("Property names don't match; in a good implementation this shouldn't be triggered. Bug?")
            return None
        effects_in_other = other.get_effects()
        permutations = self.__generate_sorted_permutations_of_effects_in_effect_set()
        for permutation in permutations:
            bindings = self.__effect_set_effects_equal(permutation, effects_in_other, copy.deepcopy(mappings))
            if bindings is not None:
                return bindings
        return None #No permutation seems to have matched

    #Generates all the valid sorted orderings of the effects in the effect set
    def __generate_sorted_permutations_of_effects_in_effect_set(self):
        if not self.__cached_sorted_permutations:
            permuted_sets = []
            for s in self.__effects: #Remember how the effects are all nicely stored, ready for this kind of processing?
                current_set_permutations = list(itertools.permutations(s)) #What are all the ways of permuting this set?
                permuted_sets.append(current_set_permutations)
            cartesian_product = itertools.product(*permuted_sets) #And what is the cartesion product of all the set permutations?
            #Strip out all the inner lists, sets, etc.
            self.__cached_sorted_permutations = self.__strip_out_inner_lists(cartesian_product)
        return self.__cached_sorted_permutations

    #Assumes that the data is 2 layers deep, like what the permutation methods will return
    #Note: This is also used for the examples permutation method just below
    #This should return a list of lists of effects
    def __strip_out_inner_lists(self, permutations):
        stripped_out_permutations = []
        for perm in permutations:
            effects_for_perm = []
            for inner_set in perm:
                for effect in inner_set:
                    effects_for_perm.append(effect)
            stripped_out_permutations.append(effects_for_perm)
        return stripped_out_permutations

    #Checks whether or not effects1 and effects2 (ordered lists) can be simply mapped onto each other in their current orderings
    #Note that as well as being used to check whether or not effect sets
    def __effect_set_effects_equal(self, effects1, effects2, mappings):
        equivalent_variables = mappings
        map_values_mapped = set(mappings.values()) #As it should be 2 way.
        for i in range(len(effects1)): #For each effect
            effect1 = effects1[i]
            effect2 = effects2[i]
            for j in range (len(effect1.get_parameters())): #For each parameter
                param1 = effect1.get_parameters()[j]
                param2 = effect2.get_parameters()[j]
                #Are the parameters the same?
                if param1.is_var(): #The parameters are variables
                    if param1 in equivalent_variables and param2 in map_values_mapped:
                        if equivalent_variables[param1] != param2:
                            return None #If both have already been mapped, then for equality they must be mapped to each other
                    elif (not (param1 in equivalent_variables)) and (not (param2 in map_values_mapped)): #Neither is mapped
                        if param1.param_type() == param2.param_type():
                            equivalent_variables[param1] = param2
                            map_values_mapped.add(param2)
                        else:
                            return None #They are of different types, this is not a match
                    else: #Only one of them is mapped. In this case, it is impossible for them to be mapped to each other
                        return None
                else: #This is a value
                    if not param1.identifier() == param2.identifier():
                        return None
        assert len(map_values_mapped) == len(set(equivalent_variables.values()))
        return map_values_mapped
    #self.__latest_bindings = equivalent_variables #Because more than one algorithm uses this code. Changing the return type would be problematic

    ############################################################################################
    ###CODE FOR FINDING PERMUTATIONS OF EFFECTS TO MAP ONTO GOALS
    ############################################################################################

    #Returns a tuple with the bindings used, and the goals that have been bound
    #Could make this more efficient, i.e. start by sorting the list from what would be the best match if it worked, to the worst, so that
    #as soon as we find a match we know we won't find a better one
    def best_way_to_bind_goals_to_effects(self, agent_goal):
        all_permutations = self.find_possible_effect_permutations_for_goals(agent_goal.get_goals_sorted_by_predicate())
        best_match = None
        for permutation in all_permutations:
            binding_information = self.bind_permutation_to_goals(permutation, agent_goal.get_flat_list())
            if binding_information:
                bindings, bound_goals = binding_information #unpack
                if not best_match or len(best_match[1]) < len(bound_goals):
                    best_match = binding_information
        return best_match

    def find_possible_effect_permutations_for_goals(self, goals):
        effects_from_effect_set_to_consider = []
        for current_predicate_tuple_in_goals in goals:
            predicate_name = list(current_predicate_tuple_in_goals)[0].get_predicate()
            effects_with_predicate_name = self.__get_effects_with_predicate_name(predicate_name)
            effects_with_predicate_name += [None for x in range(len(current_predicate_tuple_in_goals))] #Add in the None's
            effects_from_effect_set_to_consider.append(effects_with_predicate_name)
        permutations_for_each_predicate = []
        for i in range(len(effects_from_effect_set_to_consider)):
            current_goals_tuple = goals[i]
            current_effects_tuple = effects_from_effect_set_to_consider[i]
            number_of_effects_needed = len(current_goals_tuple)
            permutations_for_predicate = list(set(itertools.permutations(current_effects_tuple, number_of_effects_needed)))
            permutations_for_each_predicate.append(permutations_for_predicate)
        cartesian_product = itertools.product(*permutations_for_each_predicate)
        return self.__strip_out_inner_lists(cartesian_product)

    def __get_effects_with_predicate_name(self, name):
        for inner_tuple in self.__effects:
            if list(inner_tuple)[0].get_predicate() == name:
                return list(inner_tuple)
        return []

    #If successful, returns a tuple with the bindings, and then the goals.
    #Otherwise, None is returned
    def bind_permutation_to_goals(self, permutation, goals_list):
        equivalent_variables = {}
        map_values_mapped = set() #As it should be two way
        goals_bound = []
        for i in range(len(permutation)):
            effect1 = permutation[i]
            effect2 = goals_list[i]
            if effect1 is not None:
                goals_bound.append(effect2) #If it ends up not being bound, this won't be returned anyway
                #Check the parameters
                for j in range(len(effect1.get_parameters())):
                    param1 = effect1.get_parameters()[j]
                    param2 = effect2.get_parameters()[j]
                    #Are the parameters the same?
                    if param1.is_var(): #The parameters are variables
                        if param1 in equivalent_variables and param2 in map_values_mapped:
                            if equivalent_variables[param1] != param2:
                                return None #If both have already been mapped, then for equality they must be mapped to each other
                        elif (not (param1 in equivalent_variables)) and (not (param2 in map_values_mapped)): #Neither is mapped
                            if param1.param_type() == param2.param_type():
                                equivalent_variables[param1] = param2
                                map_values_mapped.add(param2)
                            else:
                                return None #They are of different types, this is not a match
                        else: #Only one of them is mapped. In this case, it is impossible for them to be mapped to each other
                            return None
                    else: #This is a value
                        if not param1.identifier() == param2.identifier():
                            return None
        return (equivalent_variables, goals_bound)


    ############################################################################################
    ###CODE FOR CHECKING IF AN EXAMPLE SUPPORTS AN EFFECT SET
    ############################################################################################

    def __example_supports_effect_set(self, example, mappings):
        possible_example_perms = self.__generate_possible_permutations_of_example(example)
        effects_in_this_effect_set = self.get_effects()
        for perm in possible_example_perms:
            bindings_to_match = self.__effect_set_and_example_effects_equal(effects_in_this_effect_set, perm, copy.deepcopy(mappings))
            if bindings_to_match is not None: #If the method returns a dictionary...
                return bindings_to_match
        return None

    #Returns an empty list if there are none
    #This code makes permutations of a subset of the effects in the example, that have the same predicate (and numbers of) as the
    #effect set that it will be checking support for...
    def __generate_possible_permutations_of_example(self, example):
        effects_from_example_to_consider = []
        for current_predicate_effect_set in self.__effects: #Work out which effects in the example we actually need to include in the permutations. A lot will be redundant.
            #Note: The following piece of code is a hack because you can't index into a set, so I couldn't check 0th element...
            #Was reluctant to use the convert to list trick, as I feared that might be O(n), whereas I know this is O(1)
            for effect in current_predicate_effect_set:
                predicate = effect.get_predicate()
                break
            #/END hack
            effects_from_example = example.get_effects_with_predicate(predicate)
            #Are there actually going to be enough?
            if len(effects_from_example) < len(current_predicate_effect_set): #There won't be enough for the mapping...
                return [] #There are no permutations as a result, so return an empty list
            effects_from_example_to_consider.append(effects_from_example)
        permutations_for_each_predicate = []
        for i in range(len(effects_from_example_to_consider)):
            number_effects_required = len(self.__effects[i]) #How many effects will be needed for the current predicate being checked?
            effects_to_permute = effects_from_example_to_consider[i]
            permutations_for_predicate = list(itertools.permutations(effects_to_permute, number_effects_required))
            permutations_for_each_predicate.append(permutations_for_predicate)
        cartesian_product = itertools.product(*permutations_for_each_predicate)
        return self.__strip_out_inner_lists(cartesian_product)

    #Very repetitive (this is nearly the same as another method), but just wanted to clean up the return value mess
    #effects
    #If the effect set can be mapped to the example, a dictionary of mappings saying how it was done is returned
    #This will be needed for the preconditions as they will want to be consistent with how the example was mapped
    #to the effects
    def __effect_set_and_example_effects_equal(self, effect_set_effects, example_effects, mappings):
        equivalent_variables = mappings
        map_values_mapped = set(mappings.values()) #As it should be 2 way.
        for i in range(len(effect_set_effects)): #For each effect
            effect_set_effect = effect_set_effects[i]
            example_effect = example_effects[i]
            for j in range (len(effect_set_effect.get_parameters())): #For each parameter
                param1 = effect_set_effect.get_parameters()[j]
                param2 = example_effect.get_parameters()[j]
                #Are the parameters the same?
                if param1.is_var(): #the parameter in the effect set is a variable
                    if param1 in equivalent_variables and param2 in map_values_mapped:
                        if equivalent_variables[param1] != param2:
                            return None #If both have already been mapped, then for equality they must be mapped to each other
                    elif (not (param1 in equivalent_variables)) and (not (param2 in map_values_mapped)): #Neither is mapped
                        if param1.param_type() == param2.param_type():
                            equivalent_variables[param1] = param2
                            map_values_mapped.add(param2)
                        else:
                            return None #They are of different types, this is not a match
                    else: #Only one of them is mapped. In this case, it is impossible for them to be mapped to each other
                        return None
                else: #This is a value
                    if not param1.identifier() == param2.identifier():
                        return None
        assert len(map_values_mapped) == len(set(equivalent_variables.values()))
        return equivalent_variables




######################################################################################################################################################
######################################################################################################################################################
## A precondition_table stores the preconditions of the action rule
## Preconditions have counts (using Statistics objects) that say how often a fact in the initial state occurred
## The precondition table uses a parameter defined in the SharedData class to determine whether or not a
## Facts that occurred very often are considered as preconditions when the agent attempts to plan with the rules
######################################################################################################################################################
######################################################################################################################################################

class Precondition_Table:

    def __init__(self):
        self.total_positive_examples = 0
        self.total_negative_examples = 0
        self.preconditions = {} #Just using a dictionary for now because only keeping counts of ungeneralised effects

    def get_reliable_preconditions(self):
        reliable_preconditions = []
        for precondition in self.preconditions:
            statistics_for_precondition = self.preconditions[precondition]
            if statistics_for_precondition.precondition_is_reliable():
                reliable_preconditions.append(precondition)
        return reliable_preconditions

    def get_precondition_strings(self):
        preconditions = []
        for precondition in self.preconditions:
            statistics_for_precondition = self.preconditions[precondition]
            preconditions.append(str(statistics_for_precondition.positives)+"/"+str(statistics_for_precondition.positives + statistics_for_precondition.negatives) + " " + str(precondition))
        return preconditionss

    def get_precondition_strings(self):
        minimum_frequency = 0 #Shared.MINIMUM_PRECONDITION_FREQUENCY
        precondition_strings = []
        for fact in self.preconditions:
            statistics = self.preconditions[fact]
            frequency = statistics.frequency()
            if frequency >= minimum_frequency:
                support = "<+" + str(statistics.positives) + ", -" + str(statistics.negatives) + ">"
                precondition_strings.append(support + fact.string_representation())
        return precondition_strings

    #Puts all the facts in the initial state of the given (positive) example into the precondition table
    #Example is the example that is being used to update the preconditions
    #bindings is a list of variable name -> object used when the example was bound to the effect set
    #bindings must be kept consistent in the preconditions
    #any fact containing an object that was not bound to a variable in the effect set should not be considered for a pre condition
    def update_table(self, example, bindings):
        Shared.reference_to_agent.knowledge().context().update_context(example.get_initial_facts()) #The first step in updating the table is to update the context
        self.total_positive_examples += 1 #How many positive example has the table seen?
        bound_objects = self.__reverse_dictionary(bindings) #It is possible this could be generated in the desired way in the first place
        partially_bound_facts = [] #What are the facts that will eventually need to be generalised using permutations?
        counted_facts = set()
        for initial_fact in example.get_initial_facts():
            fact = Fact("+" + str(initial_fact.get_predicate()),initial_fact.get_parameters())
            if not Shared.reference_to_agent.knowledge().context().fact_in_context(fact): #If the fact is not in the context (if it is, we want to ignore it!)
                if self.__fact_fully_bound(fact, bound_objects): #if any objects in the fact are bound
                    #This is the main case for adding preconditions into the table
                    generalised_fact = fact.get_generalised_copy_with_dictionary(bound_objects)
                    self.__add_positive_to_precondition(generalised_fact) #Adds the preconditon to the table
                    counted_facts.add(generalised_fact)
                elif self.__fact_partially_bound(fact, bound_objects): #if some of the objects in the fact are bound
                    partially_bound_facts.append(fact)
                    #Eventually permutations will be used to include these preconditions, although this version throws them away
                else:
                    "The fact is thrown away because it contains objects, none of which are bound by the effects of the example"
        #Now need to deal with the negative counts. Any fact in the table that is not in counted_facts should have a negative counted for it.
        for precondition in self.preconditions:
            if precondition not in counted_facts:
                self.__add_negative_to_precondition(precondition)

    #Turns values to keys and keys to values
    def __reverse_dictionary(self, dictionary):
        new_dictionary = {}
        for key, val in dictionary.items():
            assert val not in new_dictionary
            new_dictionary[val] = key
        return new_dictionary

    #Returns true if all parameters that are typed are in bindings
    def __fact_fully_bound(self, fact, bindings):
        for param in fact.get_parameters():
            if param.param_type(): #The param is typed, therefore can be generalised
                #If the param is not in the bindings and is not a place
                if param not in bindings and param.param_type() != "place":
                    return False
        return True

    #Returns true if there is at least one parameter that is in balls or walls that is in bindings, and at least one
    #that is in balls or walls but is not in bindings
    #Note: THIS DOES NOT HAVE ?PLACE SUPPORT!!!!
    def __fact_partially_bound(self, fact, bindings):
        at_least_one_bound = False
        at_least_one_not_bound = False
        for param in fact.get_parameters():
            if param.param_type():
                if param in bindings:
                    at_least_one_bound = True
                else:
                    at_least_one_not_bound = True
        return at_least_one_bound and at_least_one_not_bound

    def __add_positive_to_precondition(self, fact):
        if fact in self.preconditions:
            self.preconditions[fact].positives += 1
        else:
            self.preconditions[fact] = Statistics() #Create a new statistics object for the fact
            self.preconditions[fact].positives = 1 #And add the first positive onto it

    def __add_negative_to_precondition(self, fact):
        if fact in self.preconditions:
            self.preconditions[fact].negatives += 1


    def get_interesting_var_params(self):
        var_params = set()
        preconditions = self.get_reliable_preconditions()
        for precondition in preconditions:
            if precondition.get_predicate() != "hand_at" and precondition.get_predicate() != "+hand_at": #the places need to be tied to objects
                var_params = var_params | precondition.get_all_var_params()
        return var_params

#A statistics object represents the data for a given precondition
class Statistics:
    def __init__(self):
        self.positives = 0#How many times has the precondition occurred?
        self.negatives = 0#How many times has the precondition not occurred?

    def frequency(self):
        return self.positives / (self.negatives + self.positives)

    def __total_exs(self):
        return self.self.negatives + self.positives

    def precondition_is_reliable(self):
        return self.frequency() >= Shared.MINIMUM_PRECONDITION_FREQUENCY

#In an attempt to not have to put any more code in among the action rule class...
class Action_Rule_Connection_Rater():

    def __init__(self, action_rule):
        self.__action_rule = action_rule
        self.__effect_nodes = list()
        self.__construct_di_graph()
        self.__effect_nodes = set(self.__effect_nodes)

    def __construct_di_graph(self):

        #Identify all the nodes for the graph
        nodes = []
        intention = self.__action_rule.get_intention()
        effects = self.__action_rule.get_effects()
        preconditions = self.__action_rule.get_reliable_preconditions() + self.__action_rule.get_constraints()
        for fact in effects:
            node = self.__make_nodes_for_fact(fact, 3)
            nodes += node
            self.__effect_nodes += node
        for fact in preconditions:
            nodes += self.__make_nodes_for_fact(fact, 2)
        nodes += self.__make_nodes_for_fact(intention, 1)

        #Construct a digraph and add all the nodes for it
        digraph = Digraph()
        for node in nodes:
            digraph.add_node(node)

        #Now finally apply the edge heuristics
        for node1 in digraph:
            for node2 in digraph:
                if node1 != node2: #We don't want edges connecting a node to itself
                    if node1.get_level() >= node2.get_level() and node1.get_param() == node2.get_param():
                        digraph.add_edge(node1, node2)
                    elif node1.get_level() == 2 and node2.get_level() == 2 and node1.get_fact() == node2.get_fact():
                        digraph.add_edge(node1, node2)
        self.__digraph = digraph

    def __make_nodes_for_fact(self, fact, level):
        param_list = fact.get_parameters()
        return [Action_Rule_Connection_Rater.__Node(level, param, fact) for param in param_list]

    #Gives a connection rating that is anywhere from 0% to 100% as a float between 0 and 1.
    def get_connection_rating(self):
        scores_to_values = {}
        scores_to_values[1] = 1
        scores_to_values[2] = 0.5
        scores_to_values[3] = 0
        scores = []
        if not self.__effect_nodes:
            return 1
        for node in self.__effect_nodes:
            score = self.__score_node(node)
            scores.append(score)
        #At this point we have a list of scores.
        #1 means the node connected to the intention
        #2 means the node connected to the preconditions
        #3 means the node didn't connect at all

        #I am going to try weighing the scores by making the worst ones in the rating worth the most
        #and the later ones worth less and less.
        weights = [0.5**i for i in range(1, len(scores)+1)]
        max_sum = sum(weights)
        scores.sort(reverse=True)
        #Now calculate the dot product
        weighted_sum = sum([scores_to_values[x]*y for (x,y) in zip(scores, weights)])
        proportion = weighted_sum/max_sum
        return proportion
        #And scale it so that it is between 0 and 1, and based on the max_sum

    #What is the lowest level this node is connected to?
    #Low is better!
    def __score_node(self, node, visit_table=None):
        #Initialiser here to compact code
        if visit_table is None:
            visit_table = self.__initialise_visit_table()

        #Base case 1
        if visit_table[node] == True: #We've already been to this node!
            return node.get_level() #I think this is the best thing to do to prevent void being returned?
        visit_table[node] = True #At this point, we should mark it as visited
        #Base case 2
        if node.get_level() == 1:
            return 1
        #Base case 3
        if not self.__digraph.get_edges(node): #No edges
            return node.get_level() #Return its own score

        #Recursive case, return the minimum score of the edges
        edge_scores = []
        for edge in self.__digraph.get_edges(node):
            score = self.__score_node(edge, visit_table)
            edge_scores.append(score)
        return min(edge_scores)

    def __initialise_visit_table(self):
        visit_table = {}
        for node in self.__digraph:
            visit_table[node] = False
        return visit_table




    class __Node():

        def __init__(self, level, param, fact):
            self.__level = level
            self.__param = param
            self.__fact = fact

        def get_level(self):
            return self.__level

        def get_param(self):
            return self.__param

        def get_fact(self):
            return self.__fact
