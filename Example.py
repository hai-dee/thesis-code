from copy import deepcopy
from Fact import Fact
from math import hypot
import SharedData as Shared
import File_Writer
from collections import Counter
from Qualitative_State import Qualitative_State
import Simulated_Vision

example_to_action_rule_counts = Counter()

#Renamed to Qualitative Example, as that is essentially what it is
#Other classes will need to be modified to cope with the name change
class Qualitative_Example:

    __next_example_id = 1

    def __init__(self, action, target, quantitative_states):
        self.__id_num = Qualitative_Example.__next_example_id
        Qualitative_Example.__next_example_id += 1
        #What was the agent trying to do?

        #This mess all refers to the intention. Best to not modify it in any way to be safe
        self.__action_name = action #I.e. move, hit, grasp, or ungrasp
        if target:
            self.__raw_intent_param = target
            self.__qual_intent_param = "Intent"
            self.__qual_init_param = "Init"
        else:
            self.__qual_init_param = "Init"
            self.__raw_intent_param = None
            self.__qual_intent_param = None


        self.__intention = Fact(action, [self.__qual_init_param, self.__qual_intent_param])

        self.__quant_states = quantitative_states #Might not want to save this, as it is unnecessary, although useful for debugging

        self.__initialise_qualitative_data() #Generate the qualitative representation of this example
        #Currently it is only going to initialise the effects that it can identify by only looking at the first and last states.

    def __str__(self):
        intention_string = str(self.get_intention_fact())
        constraint_strings = [str(x) for x in self.get_constraints()]
        initial_strings = [str(x) for x in self.get_initial_facts()]
        effect_strings = [str(x) for x in self.get_effect_facts()]
        return str(self.get_example_id()) + " " + intention_string + "\n" + "Constraints: " + str(constraint_strings) + "\n" + "Preconditions: " + str(initial_strings) + "\n" + "Effects: " + str(effect_strings) + "\n\n"


    def sorted_effect_strings(self):
        effect_strings = [str(x) for x in self.get_effect_facts()]
        return sorted(effect_strings)

    def sorted_initial_strings(self):
        initial_strings = [str(x) for x in self.get_initial_facts()]
        return sorted(initial_strings)

    def intention_param_string(self):
        return str(self.get_intention_fact())

    #Returns the fact that corresponds to the agent's intention
    def get_intention_fact(self):
        return self.__intention

    def get_intention_params(self):
        return self.__intention.get_parameters()

    def get_initial_facts(self):
        return self.__extract_facts(self.__initial_state_dict)

    def get_effect_facts(self):
        return self.__extract_facts(self.__effects_dict)

    def get_constraints(self):
        return self.__extract_facts(self.__constraints_dict)

    #Get a list of the constraints in this example that only contain the given params
    def constraints_with_params(self, params):
        to_return = []
        for constraint in self.get_constraints():
            if constraint.contains_only_specified_params(params):
                to_return.append(constraint)
        return to_return


    def get_example_id(self):
        return self.__id_num

    #What was the agent trying to accomplish?
    def get_action(self):
        return self.__action_name

    #Returns a set of all effects that have the given predicate
    #Return an empty set if the predicate can't be found
    def get_effects_with_predicate(self, predicate):
        if predicate in self.__effects_dict:
            return self.__effects_dict[predicate]
        else:
            return set()

    #This method extracts facts out of the dictionary form so that the public methods can return a linear
    #list of the facts
    def __extract_facts(self, dict_of_facts):
        all_facts = []
        for dict_key in dict_of_facts:
            set_of_facts = dict_of_facts[dict_key]
            for fact in set_of_facts:
                all_facts.append(fact)
        return all_facts

####################################################################################################
### CODE FOR BUILDING THE QUALITATIVE REPRESENTATION
####################################################################################################


    #Qualitative data includes a list of preconditions and a list of effects for the action
    #Preconditions and effects are stored in a form that allows for fast processing
    def __initialise_qualitative_data(self):
        self.__qualitative_places = self.__define_qualitative_places()
        self.__constraints_dict = self.__constraints_dict()
        self.__initial_state_dict = self.__initial_state_dict()
        self.__effects_dict = self.__effects_dict()

    def __define_qualitative_places(self):
        #Init, Intent, Final
        places = {}
        quant_intent = self.__raw_intent_param
        quant_init = (round(self.__quant_states[0].x), round(self.__quant_states[0].y))
        quant_final = (round(self.__quant_states[-1].x), round(self.__quant_states[-1].y))
        #Firstly set up quant
        if quant_intent != None:
            places["Intent"] = (quant_intent, "Intent")
        #Now set up init
        if quant_init == quant_intent:
            places["Init"] = (quant_init, "Intent")
        else:
            places["Init"] = (quant_init, "Init")
        #Finally set up final
        if quant_final == quant_intent:
            places["Final"] = (quant_final, "Intent")
        elif quant_final == quant_init:
            places["Final"] = (quant_final, "Init")
        else:
            places["Final"] = (quant_final, "Final")
        place_log = open("places.txt", "a")
        place_log.write(str(places)+"\n")

        place_log.close()
        return places

    def __constraints_dict(self):
        quant_state = self.__quant_states[0]
        qual_state = Qualitative_State(quant_state)
        place_list = []
        if "Intent" in self.__qualitative_places:
            place_list.append(self.__qualitative_places["Intent"])
        place_list.append(self.__qualitative_places["Init"])
        place_facts = qual_state.facts_for_places(place_list)
        return self.__make_dictionary_for_qual_facts(place_facts)


    #What was true at the start of this example?
    def __initial_state_dict(self):
        quant_state = self.__quant_states[0]
        qual_state = Qualitative_State(quant_state)
        standard_facts =  qual_state.get_qualitative_facts()
        return self.__make_dictionary_for_qual_facts(standard_facts)



    #What did this example result in?
    def __effects_dict(self):
        #Get the initial state facts [again to speed up code writing time, will optimise this if the memory usage is too painful]
        init_qual_state = Qualitative_State(self.__quant_states[0])
        hand_at_fact_init = Fact("hand_at", ["Init"])
        init_state_facts = init_qual_state.get_qualitative_facts() + [hand_at_fact_init]
        initial_dict = self.__make_dictionary_for_qual_facts(init_state_facts)

        #Need to make a combined constraints-initial dict
        #Now build up the effects dict
        qual_state = Qualitative_State(self.__quant_states[-1])
        final_state_facts = qual_state.get_qualitative_facts()
        hand_at_fact_final = None
        #Probably very bug prone...
        hand_at_fact_final = Fact("hand_at", [self.__qualitative_places["Final"][1]])
        final_dict = self.__make_dictionary_for_qual_facts(final_state_facts + [hand_at_fact_final])
        return self.__generate_state_difference_dictionary(initial_dict, final_dict)

    #Seperating this out, because I think it will make the code easier to read
    def __make_dictionary_for_qual_facts(self, qual_facts):
        fact_dictionary = {}
        for fact in qual_facts:
            self.__add_fact_into_dictionary(fact_dictionary, fact)
        return fact_dictionary

    #Because other parts of the code need to be able to add in just one fact at a time
    def __add_fact_into_dictionary(self, dictionary, fact):
        predicate = fact.get_predicate()
        if predicate in dictionary:
            dictionary[predicate].add(fact)
        else:
            dictionary[predicate] = set()
            dictionary[predicate].add(fact)

    #This is needed to find the effects for this example
    def __generate_state_difference_dictionary(self, start_dictionary, end_dictionary):
        different_facts = {}
        for predicate in start_dictionary:
            for fact in start_dictionary[predicate]: #There may be more than one fact in the set for this property name
                #Is the same fact also in the end_dictionary? (We only care if it isn't)
                #One possible way this could break is problems in the hash function/ equality function of the fact class
                if  (predicate not in end_dictionary) or (fact not in end_dictionary[predicate]): #This fact must have gone false, therefore it is a negative effect
                    new_effect = Fact("-" + predicate, deepcopy(fact.get_parameters()))
                    self.__add_fact_into_dictionary(different_facts, new_effect)
        for predicate in end_dictionary:
            for fact in end_dictionary[predicate]:
                if (predicate not in start_dictionary) or (fact not in start_dictionary[predicate]):
                    new_effect = Fact("+" + predicate, deepcopy(fact.get_parameters()))
                    self.__add_fact_into_dictionary(different_facts, new_effect)
        return different_facts
