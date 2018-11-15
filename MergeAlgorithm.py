#This file just contains the code for the merging algorithm.
#I am putting it in a seperate file for testing before integrating it

from Fact import Fact
from copy import deepcopy
from collections import Counter
from collections import OrderedDict
import itertools

#This code is just for setting up the data and getting it into the program form
effect_strings_1 = ['-hand_at(?p45)']
effect_strings_2 = ['-hand_at(?p46)']
es1 = [Fact.make_fact_from_string(string) for string in effect_strings_1]
es2 = [Fact.make_fact_from_string(string) for string in effect_strings_2]
intent1 = Fact.make_fact_from_string("Hit(?p460825)")
intent2 = Fact.make_fact_from_string("Hit(?p11084)")



#This is the actual algorithm. It uses es1, es2, intent1, and intent2 as the data.
#The integrated algorithm will extract the data from the action rules, which is similar

def get_all_merged_action_rules():
    #Firstly, check whether or not it is even possible to get valid mergings
    es1_predicates = count_of_predicates_in_facts(es1)
    es2_predicates = count_of_predicates_in_facts(es2)
    left_overs_in_es1 = sum((es1_predicates - es2_predicates).values())
    if left_overs_in_es1 != 0 and left_overs_in_es1 != 1:
        return []
    #Now that we know there is a possibility they will merge, find different possible ways
    implicit_tree = make_implicit_tree_dictionary(es1, es2)
    es1_index = [None] + list(implicit_tree.keys())
    #Unused var, but keeping incase of side effects.
    merged_ars = generate_merged_ars(implicit_tree, es1_index)

def make_predicate_dictionary(effects):
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
def make_implicit_tree_dictionary(es1, es2):
    d = OrderedDict()
    predicate_dictionary_for_es2 = make_predicate_dictionary(es2)
    for effect in es1:
        predicate = effect.get_predicate()
        if predicate in predicate_dictionary_for_es2:
            d[effect] = predicate_dictionary_for_es2[predicate]
        else:
            d[effect] = set()
        d[effect].add(None)
    return d


def generate_merged_ars(implicit_tree, es1_index):
    remaining_for_es2 = es2 + [None]
    merged_action_rules = []
    recursively_find_merged_ars(es1_index, implicit_tree, merged_action_rules, None, None, [], None, 0, {}, remaining_for_es2)


#The variables starting with g are the data that could be global, and the variables starting with p are proper parameters
#Everything is passed as it is easier to avoid the globals
#g_implicit_tree: The ordered dict that says what nodes are in the implicit tree
#g_merged_action_rules: What are all the action rules we've found?
#p_effect1: The first effect to merge (from es1)
#p_effect2: The second effect to merge (from es2)
#p_level: Where are we in the tree?
#p_bindings: What bindings do we have so far?
#p_remaining_for_es2: Which es2 facts have not yet been combined with es1 facts?
def recursively_find_merged_ars(es1_index, implicit_tree, merged_action_rules, e1, e2, merged_effects, p_mergeless_effect_in_es1, level, bindings, remaining_for_es2):

    #Process what should happen in this call
    if level != 0: #This means we have just started the program
        if e2 == None: #We are wanting to match p_effect1 onto nothing
            #As long as we haven't already got a p_effect1 unmerged, we can do this
            if p_mergeless_effect_in_es1 == None:
                p_mergeless_effect_in_es1 = e1
            else:
                print("Base case 1 triggered from trying to assign a second non merged fact")
                return
        else:
            #Note that the p_bindings an p_merged_effects are going to be updated by the merge_effects() method
            if not merge_effects(e1, e2, bindings, merged_effects):
                print("Base case 2 triggered from bindings contradiction")
                return #Don't do anything else on this call

    #Now figure out what should be done next
    if level == len(implicit_tree): #If we are at the lowest level
        print("Base case 3 triggered from a complete merged_effects")
        assert len(remaining_for_es2) == 1
        if p_mergeless_effect_in_es1 != None:
            merge_less_effect_in_es2 = list(remaining_for_es2)[0]
            new_action_rules = action_rules_for_merged_effects(merged_effects, bindings, p_mergeless_effect_in_es1, merge_less_effect_in_es2)
            #This method might have more than one merged action rule, because restrictions on the unmerged facts are a bit looser
            #Is the contents of updated_merged_effects a valid
            for action_rule in new_action_rules:
                merged_action_rules.append(action_rule)
    else: #Recursive case
        #What are all the possibilities at the next level?
        next_es1_fact = es1_index[level + 1]
        for es2_fact in implicit_tree[next_es1_fact]: #What are all the facts from es2 that could map onto the es1 fact?
            if es2_fact in remaining_for_es2: #It hasn't already been mapped elsewhere
                copy_of_merged_effects = deepcopy(merged_effects)
                copy_of_bindings = deepcopy(bindings)
                copy_of_remaining_for_es2 = deepcopy(remaining_for_es2)
                copy_of_remaining_for_es2.remove(es2_fact)
                recursively_find_merged_ars(es1_index, implicit_tree, merged_action_rules, next_es1_fact, es2_fact, copy_of_merged_effects, p_mergeless_effect_in_es1, level+1, copy_of_bindings, copy_of_remaining_for_es2)


def merge_effects(e1, e2, existing_bindings, existing_merged_effects):
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


#This method is incomplete: Currently it only applies bindings to unmerged_in_es2 and ensures that it and the es1 fact are not identical
def action_rules_for_merged_effects(merged_effects, bindings, un_merged_in_es1, un_merged_in_es2):
    #This method's main role is to handle the fact that there might be more than one way of dealing with
    #any bindings that haven't yet been processed

    possible_ars = []
    invalid_binding = None #Is there anyway of merging that would cause only n facts?

    if un_merged_in_es1.get_predicate() == un_merged_in_es2.get_predicate():
        bindings_copy = deepcopy(bindings)
        if merge_effects(un_merged_in_es1, un_merged_in_es2, bindings_copy, []) == True:
            invalid_binding = bindings_copy

    #What are all the unbound variables in es1?
    remaining_1 = [var for var in un_merged_in_es1.get_parameters() if var not in bindings.keys()]
    remaining_2 = [var for var in un_merged_in_es2.get_parameters() if var not in bindings.keys()]

    #And what are all the binding permutations for these unbound variables?
    if remaining_1 != [] and remaining_2 != []:
        extended_bindings = get_extended_bindings(remaining_1, remaining_2, bindings)
        if extended_bindings:
            for extended_binding in extended_bindings:
                if extended_binding != invalid_binding:
                    copy_merged_effects = deepcopy(merged_effects)
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
    print(len(possible_ars))
    return possible_ars

def get_extended_bindings(vars1, vars2, existing_bindings):
    possible_bindings_dictionary = {}
    type_dict_for_2 = make_type_dictionary(vars2)
    for var in vars1:
        typ = var.param_type()
        if typ in type_dict_for_2:
            possible_bindings_dictionary[var] = type_dict_for_2[typ]
            possible_bindings_dictionary[var].add(None)
    if possible_bindings_dictionary != {}:
        vars_in_keys = [None] + list(possible_bindings_dictionary.keys())
        extended_bindings = []
        recursively_generate_bindings(vars_in_keys, possible_bindings_dictionary, 0, None, None, existing_bindings, extended_bindings)
        return extended_bindings
    else:
        return None


def make_type_dictionary(variables):
    d = dict()
    for variable in variables:
        var_type = variable.param_type()
        if var_type not in d:
            d[var_type] = set()
        d[var_type].add(variable)
    return d

def recursively_generate_bindings(keys, implicit_tree, level, param1, param2, current_binding, all_bindings):
    updated_binding = current_binding
    if level != 0:
        #Process the current state
        if param2 is not None:
            updated_binding = deepcopy(current_binding) #Only copy when we need to
            updated_binding[param1] = param2
    #The base case
    if level == len(implicit_tree):
        all_bindings.append(updated_binding)
    #Else the recursive case
    else:
        new_param1 = keys[level+1]
        for new_param2 in implicit_tree[new_param1]:
            if new_param2 is None or (new_param2 not in current_binding.values()):
                recursively_generate_bindings(keys, implicit_tree, level+1, new_param1, new_param2, updated_binding, all_bindings)

def count_of_predicates_in_facts(list_of_facts):
    return Counter([fact.get_predicate() for fact in list_of_facts])

get_all_merged_action_rules()
