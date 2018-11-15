from Context import Context
import File_Writer
import Example
import SharedData
from PrimitiveAction import Primitive_Action
from threading import Thread
from TableWorldSimulation import TableWorldSimulation
from Qualitative_State import Qualitative_State
from PlanningLog import Planning_Log
#from Action_Rule import ActionRuleToGoalsMapping
import Fact
import Current_Goal
from copy import copy
import Simulated_Vision
from random import choice
from time import sleep
from collections import OrderedDict

import pickle

from copy import deepcopy

#The agent needs to have a learn() method and a plan() method.
class The_Agent:

    #As this is a singleton, need to keep a static reference to the agent that will be initialised in the first access.
    the_agent = None

    def __new__(self, *args, **kwargs):
        if not The_Agent.the_agent:
            The_Agent.the_agent = super(The_Agent, self).__new__(self, *args, **kwargs)
            The_Agent.the_agent.__initialise_agent()
            SharedData.reference_to_agent = The_Agent.the_agent
        return The_Agent.the_agent

    #Initialises each of the agent's components.
    def __initialise_agent(self):
        self.__motor_control = AgentMotorControl()
        self.__knowledge = AgentKnowledge()
        self.__learner = AgentLearner()
        self.__planner = AgentPlanner()

    #Return the agent's knowledge.
    def knowledge(self):
        return self.__knowledge

    def set_new_knowledge_base(self, new):
        self.__knowledge = new

    def set_world_state(self, state):
        self.__motor_control.set_simulation(state)

    #Return the agent's learner
    def learner(self):
        return self.__learner

    #Return the agent's planner
    def planner(self):
        return self.__planner

    def controller(self):
        return self.__motor_control

    #This method tells the agent to start using its learner to learn.
    def learn(self):
        self.learner().learn()

    #Refine action rules with planner!
    def plan(self):
        self.learner().plan()

    def show_next_example(self):
        random_action_thread = Thread(target=self.controller().do_random_action)
        random_action_thread.start()

    def print_possible_ars_for_goals(self, goals):
        self.__planner.print_possible_ars_for_goals(goals)

    def plan_for_goals(self, goals):
        planning_thread = Thread(target=lambda: self.__planner.plan_for_goals(goals))
        planning_thread.start()


    def find_place(self, constraints):
        print("I am going to find out which of these facts is satisfied in the current state")
        for constraint in constraints:
            print(constraint)
        print("----------------")
        self.__planner.test_current_state_check(constraints)
        #self.__motor_control.find_place(constraints)


    def make_knowledge_file(self):
        File_Writer.FileWriter().write_all_knowledge_to_file(self.__knowledge)
    ################################################################################################
    ### METHODS FOR LEARNING
    ################################################################################################

class AgentLearner:

    #Putting imports here to prevent circular reference problems
    import File_Writer
    import SharedData

    def __init__(self):
        self.__examples_learnt_from = 0
        self.__planning_log = Planning_Log() #The agent will learn about its rules using the planning log

    #This method creates a new thread, and learns on the new thread until the control variable says to stop learning, at which point
    #the method and thread exit
    def learn(self):
        SharedData.currently_learning = True #We are now currently learning
        SharedData.pause_learning = False #The program cannot be paused
        learning_thread = Thread(target=self.learning_mainloop)
        learning_thread.start() #And now processing on the GUI thread should have stopped.

    def plan(self):
        SharedData.currently_planning = True
        plan_thread = Thread(target=self.planning_mainloop)
        plan_thread.start()

    def planning_mainloop(self):
        while SharedData.currently_planning == True:
            sleep(1) #Just to try and sync it
            print("CHOOSING PLAN")
            choosen_goal_set = self.__planning_log.choose_goal_set()
            The_Agent().controller().reset()
            if SharedData.visualisation_enabled:
                SharedData.examples_to_display.put(choosen_goal_set)
            try:
                positive_result = The_Agent().planner().plan_for_goals(choosen_goal_set)
                print(positive_result)
                if positive_result:
                    self.__planning_log.update_goal_set(choosen_goal_set, "Success")
                else:
                    self.__planning_log.update_goal_set(choosen_goal_set, "Failure")
            except:
                #If this happens, we know that the goal set caused the planner to crash. Want to handle it gracefully.
                self.__planning_log.update_goal_set(choosen_goal_set, "Crash")

    #The learning mainloop will learn from 5000 learning examples (500 in the laptop version)
    #and then start trying to plan with its rules, refining the rules as it goes
    def learning_mainloop(self):
        #The learning example phase
        should_stop = 0
        while not self.learning_should_pause() and self.__examples_learnt_from <= 80000:
            next_example = The_Agent().controller().do_random_action()
            print(next_example)
            The_Agent().knowledge().add_example(next_example)
            File_Writer.FileWriter().write_example_to_file(next_example)
            ##Do we need to do file writing?
            if next_example.get_example_id() %500 == 0:
                File_Writer.FileWriter().write_all_knowledge_to_file(The_Agent().knowledge())
            self.__examples_learnt_from += 1
            should_stop += 1
            if should_stop == 4000:
                break
        while not self.learning_should_pause() and self.__examples_learnt_from > 80000:
            sleep(1) #Just to try and sync it
            print("CHOOSING PLAN")
            choosen_goal_set = self.__planning_log.choose_goal_set()
            if SharedData.visualisation_enabled:
                SharedData.examples_to_display.put(choosen_goal_set)
            try:
                positive_result = The_Agent().planner().plan_for_goals(choosen_goal_set)
                print(positive_result)
                if positive_result:
                    self.__planning_log.update_goal_set(choosen_goal_set, "Success")
                else:
                    self.__planning_log.update_goal_set(choosen_goal_set, "Failure")
            except:
                #If this happens, we know that the goal set caused the planner to crash. Want to handle it gracefully.
                self.__planning_log.update_goal_set(choosen_goal_set, "Crash")
            self.__examples_learnt_from += 1
        self.__planning_log.print_table()
        self.pause_learning() #And the thread will exit, and learning will end. The data will still be in the agent, as it is global

    #Should the learning thread exit now?
    #Note that the GUI might have paused the learning.
    def learning_should_pause(self):
        return SharedData.pause_learning

    #Set variables to pause the learning
    def pause_learning(self):
        SharedData.currently_learning = False
        SharedData.pause_learning = True


#The agent's knowledge.
#The knowledge is represented as an index of primitive action objects, and a context object that stores the context of the world.
class AgentKnowledge:

    def __init__(self):
        self.__context = Context()
        self.__primitive_actions = {}

    def power_set_nodes_for_goal(self, goal_set):
        nodes = []
        for name in self.__primitive_actions:
            prim_action = self.__primitive_actions[name]
            power_set_nodes = prim_action.get_power_set_for_goal_set(goal_set)
            for node in power_set_nodes:
                nodes.append(node)
        return nodes

    def add_example(self, example):
        action_type = example.get_action()
        if action_type in self.__primitive_actions:
            self.__primitive_actions[action_type].learn_from_example(example)
        else:
            self.__primitive_actions[action_type] = Primitive_Action(action_type)
            self.__primitive_actions[action_type].learn_from_example(example)

    def context(self):
        return self.__context

    def _prim_actions(self):
        return self.__primitive_actions


class AgentPlanner:

####################################################################################################
### MAIN RECURSIVE PLANNING ALGORITHM
####################################################################################################

    #This needs to be changed so that expected goals are put on the stack.
    def plan_for_goals(self, goals):

        actions_used = []

        print("STARTING PLAN")
        if self.__goals_negated_with_variables(goals):
            print("These goals contain negated variables, and thus make no sense to me!")
            print("FINISHING PLAN")
            return False
        planning_stack = []
        planning_stack.append(Current_Goal.Current_Goal(goals, "Full"))
        number_of_actions = 0 #How many actions have been carried out in total?
        current_action_depth = 0 #How many actions are currently on the stack?
        loop_kill_counter = 0
        KILL_AT = 200
        while planning_stack != [] and number_of_actions < SharedData.MAXIMUM_ACTIONS_ATTEMPTED_IN_PLAN:
            loop_kill_counter += 1
            if loop_kill_counter >= KILL_AT:
                return
            print("Number of actions so far completed: ", number_of_actions)
            self.print_stack_state(planning_stack)
            item_on_top_of_stack = planning_stack[-1] #We don't want to remove it yet
            if item_on_top_of_stack.stack_data_type() == "Goal": #If goals are on top of stack
                goals_on_top_of_stack = item_on_top_of_stack #To try and make the code more readable
                #What type of goals are on the top of the stack?
                if goals_on_top_of_stack.type_is_full() or goals_on_top_of_stack.type_is_unsatisfied():
                    unsatisfied_goals, mapping = self.map_goals_onto_current_state(goals_on_top_of_stack.goals(), The_Agent().controller().get_current_state())
                    print("Mapping goals onto the current state with mapping")
                    for key in mapping:
                        print(key, mapping[key])
                    for goal in unsatisfied_goals:
                        print(goal)
                    if not unsatisfied_goals: #Case 1 for full goals: All goals are satisfied, so this goal should be removed from stack
                        planning_stack.pop()
                        for item in reversed(planning_stack): #Need to apply the bindings to the first action rule below this goal item
                            if item.stack_data_type() == "Action":
                                item.update_bindings(mapping)
                                break
                    elif len(unsatisfied_goals) < goals_on_top_of_stack.number_of_goals():#Case 2 for full goals: Some of the goals are satisfied, so a new goal should be made for the unsatisfied ones
                        bound_unsatisfied_goals = [goal.get_specific_copy_with_dictionary(mapping) for goal in unsatisfied_goals]
                        print("Bound them for unsatisfied goals")
                        for goal in bound_unsatisfied_goals:
                            print(goal)
                        for item in reversed(planning_stack): #Need to apply the bindings to the first action rule below this goal item
                            if item.stack_data_type() == "Action":
                                item.update_bindings(mapping)
                                break
                        planning_stack.append(Current_Goal.Current_Goal(bound_unsatisfied_goals, "Unsatisfied", goals_on_top_of_stack.get_black_list()))
                    else: #We want to put an action rule onto the stack
                        best_ar = self.new_choose_best_rule(goals_on_top_of_stack)
                        if best_ar == None:
                            while len(planning_stack) > 0 and planning_stack[-1].stack_data_type() != "Action":
                                planning_stack.pop()
                            if len(planning_stack) == 0:
                                print("I am stuck, giving up")
                                break
                            else:
                                #Does this code actually work?
                                print("Trying the top action")
                                continue
                        else:
                            number_of_actions += 1 #We have added an action to the stack
                            current_action_depth += 1
                            planning_stack.append(best_ar.goals_expected_to_accomplish())
                            planning_stack.append(best_ar)
                            #We only want to put the preconditions onto the stack if there is not already the maximum number of actions on it (as if we can't add anymore actions, we don't want to do further planning!)
                            if current_action_depth < SharedData.MAXIMUM_NUMBER_ACTIONS_ON_STACK:
                                planning_stack.append(best_ar.goals_for_preconditions())
                elif goals_on_top_of_stack.type_is_expected():
                    print("Error: This code should not have been hit")
                    print("This goal should have been processed immediately after the action rule")
                else:
                    print("Unrecognised goal type " + goals_on_top_of_stack.goal_type())
            else: #There must be an action on the top of the stack
                current_action_depth -= 1
                action_on_top_of_stack = item_on_top_of_stack
                planning_stack.pop() #Need to tidy up this code a bit
                #Shouldn't the action itself just do this?
                if action_on_top_of_stack.action_parameter_unbound():
                    print("the action parameter is unbound")
                    action_on_top_of_stack.bind_random_object_to_intention()
                else:
                    print("The action parameter is bound")

                #Check whether or not the action's preconditions are all satisfied
                print("Checking whether the action's preconditions are fully satisfied in the current state")
                success_expected = False
                precon_goals = action_on_top_of_stack.goals_for_preconditions().goals()
                print("Checking whether or not the precon goals are satisfied")
                for pre in precon_goals:
                    print(str(pre))
                unsatisfied_precons, _ = self.map_goals_onto_current_state(precon_goals, The_Agent().controller().get_current_state())
                if unsatisfied_precons:
                    print("not all the precons were satisfied, i.e.")
                    for precon in unsatisfied_precons:
                        print(precon)
                else:
                    success_expected = True
                    print("all the precons were satisfied")

                #carry out the action
                print("Carrying out action: " + str(action_on_top_of_stack.action_type()))
                The_Agent().controller().carry_out_bound_action(action_on_top_of_stack)
                print("Carried out bound action")
                actions_used.append(action_on_top_of_stack)
                goals_expected_to_be_satisfied = planning_stack.pop() #Pop the expected frame off

                actions_removed = False
##                #And now do checking for serendipidy
                for i in range(len(planning_stack)):
                    item = planning_stack[i]
                    if item.stack_data_type() == "Goal":
                        ug,  _ = self.map_goals_onto_current_state(item.goals(), The_Agent().controller().get_current_state())
                        if not ug:
                            actions_removed = True
                            planning_stack = planning_stack[:i]
                            print(planning_stack)
                        break

                #Now, evaluate the action that was just carried out. Did it do as it was expected to do?

                cur_state_check = The_Agent().controller().get_current_state()
                print(goals_expected_to_be_satisfied)
                print(goals_expected_to_be_satisfied.goals)
                expected_check = goals_expected_to_be_satisfied.goals()
                unsatisfied_goals, mapping = self.map_goals_onto_current_state(expected_check, cur_state_check)

                if actions_removed:
                    action_on_top_of_stack.get_action_rule().add_expected_success()
                    print("stuff was removed, action is a success")
                    print(planning_stack)
                    continue
                elif unsatisfied_goals:
                    print("Not all goals were satisfied")
                    for goal in unsatisfied_goals:
                        print(goal)
                    cur_state = The_Agent().controller().get_current_state()
                    (x, y) = (cur_state.hand_quant_x(), cur_state.hand_quant_y())
                    print(x, y)
                    planning_stack[-1].add_ar_id_to_black_list(action_on_top_of_stack.id_of_action_rule())
                    if success_expected:
                        "currently not using this - addin failure either way!"
                    action_on_top_of_stack.get_action_rule().add_unexpected_failure()
                else:
                    action_on_top_of_stack.get_action_rule().add_expected_success()
                if planning_stack[-1].type_is_unsatisfied():
                    planning_stack.pop() #We want to reassess what needs to be done

        #Check if there are any actions on the stack. If there are, just carry them out and throw away any goals
        #This is the case where the maximum plan size was exceeded. So it is still worth emptying the stack.
        if planning_stack !=[]:
            while planning_stack != []:
                next_item = planning_stack.pop()
                if next_item.stack_data_type() == "Action":
                    if next_item.action_parameter_unbound():
                        print("the action parameter is unbound")
                        next_item.bind_random_object_to_intention()
                    The_Agent().controller().carry_out_bound_action(next_item)
                    actions_used.append(next_item)

        #Do a final check to see if this has actually worked or not.
        unsatisfied_goals, mapping = self.map_goals_onto_current_state(goals, The_Agent().controller().get_current_state())
        print("FINISHING PLAN")
        print("The action sequence was\n\n")
        print("\\begin{enumerate*}")
        for action in actions_used:
            con_string = " with constraints: \\{"
            constraints = [c.get_specific_copy_with_dictionary(action.bindings) for c in action.get_action_rule().get_constraint_set().get_constraints()]
            for con in constraints:
                con_string += str(con) + ", "
            con_string = con_string[:-2] + "\\}" #Trim the extra ", " and add the ending
            intention = action.get_action_rule().get_intention().get_specific_copy_with_dictionary(action.bindings)
            line = "\\item " + str(intention) + con_string
            line = line.replace("MoveTo", "Move_To")
            line = line.replace("_", "\\_")
            line = line.replace("+", "")
            print(line)
        print("\\end{enumerate*}")
        return not unsatisfied_goals

    def print_stack_state(self, stack):
        print("========================THE PLANNING STACK TRACE=============================")
        for item in stack:
            item.print_summary()
            print("----------------------------------")
        print("=============================================================================")


    def __goals_negated_with_variables(self, goals):
        for goal in goals:
            if goal.contains_negation_and_vars():
                return True
        return False

    def test_current_state_check(self, goals):
        current_state = The_Agent().controller().get_current_state()
        unsatisfied, bindings = self.map_goals_onto_current_state(goals, current_state)
        print("The unsatisfied facts are:")
        for goal in unsatisfied:
            print(goal)
        for key in bindings:
            print(str(key) + "->" + str(bindings[key]))
        print("-------------")
        print("And now I will create a Current Goal object")
        bound_goals = [goal.get_specific_copy_with_dictionary(bindings) for goal in unsatisfied]
        current = Current_Goal.Current_Goal(bound_goals, "Unsatisfied")
        for goal in current.goals():
            print(goal)

    #Takes a list of goals that the agent needs to map onto the current state
    #This method does not take a list of bindings.
    #Any known bindings should have been put into the goals by making new fact objects, by the caller.
    def map_goals_onto_current_state(self, goals, current_state):
        (contain_place_vars, contain_normal_vars, contain_no_vars, contains_concrete_places) = self.categorize_goals(goals)
        #Firstly, check those without vars against the current state. This is straightforward.
        unachieved_var_less = [fact for fact in contain_no_vars if not current_state.contains_fact(fact)]
        unachieved_concrete_places = [fact for fact in contains_concrete_places if not current_state.place_fact_true(fact)]

        used_objects = self.object_names_in_facts(contain_no_vars)

        best_bindings, unachieved_normal_vars = self.map_non_place_var_facts(contain_normal_vars, current_state, used_objects)

        #Now, we need to deal with place vars.
        print("checking place vars")
        best_bindings_2, unachieved_place_vars = self.map_place_var_facts(contain_place_vars, best_bindings, current_state, used_objects)

        unsatisfied_goals = unachieved_var_less + unachieved_concrete_places + unachieved_normal_vars + unachieved_place_vars
        return unsatisfied_goals, best_bindings_2

    def object_names_in_facts(self, facts):
        names = set()
        for fact in facts:
            for param in fact.get_parameters():
                if param.is_obj():
                    names.add(param.identifier())
        return names


    #Depending on the characteristics of a goal, it might need to be handled in different ways
    #So we seperate them into 3 categories
    # - Straightforward goals without variables
    # - Goals with normal variables
    # - Goals with (?place) variables that will need to be handled by the visual system
    def categorize_goals(self, goals):
        no_vars = []
        normal_vars = []
        place_vars = []
        concrete_places = []
        for goal in goals:
            if goal.contains_place_variables():
                place_vars.append(goal)
            elif goal.contains_concrete_places():
                concrete_places.append(goal)
            elif goal.contains_variables():
                normal_vars.append(goal)
            else:
                no_vars.append(goal) #This could actually include facts that contain objects
        return (place_vars, normal_vars, no_vars, concrete_places)

    #Map the facts that contain vars but no place vars onto the current state and generate bindings
    def map_non_place_var_facts(self, contain_normal_vars_facts, current_state, used_objs):
        goals_to_include_in_tree = [None] + contain_normal_vars_facts
        implicit_tree = self.generate_implicit_tree_list(goals_to_include_in_tree, current_state)
        best_bindings, score = self.find_best_bindings_for_current_state(None, 0, {}, implicit_tree, goals_to_include_in_tree)
        #Decided to do this in a seperate step
        unsatisfied_goals = self.__unsatisfied_goals_with_bindings(contain_normal_vars_facts, best_bindings, current_state)
        return best_bindings, unsatisfied_goals

    def __unsatisfied_goals_with_bindings(self,goals,bindings, current_state):
        unsatisfied_goals = []
        for goal in goals:
            bound_goal = goal.get_specific_copy_with_dictionary(bindings)
            if bound_goal.contains_variables() and not bound_goal.contains_place_variables():
                unsatisfied_goals.append(bound_goal)
            else:
                if not current_state.contains_fact(bound_goal):
                    unsatisfied_goals.append(bound_goal)
        return unsatisfied_goals

    def generate_implicit_tree_list(self, var_goals, current_state):
        implicit_tree_list = [None] #The first is always None, as it is at level 0 (the root node of the implicit tree is empty)
        for goal in var_goals[1:]: #We don't want to look at the None at the start
            list_for_goal = current_state.get_candidates_for_goal(goal)
            list_for_goal.append(None) #Append a None to the end
            implicit_tree_list.append(list_for_goal)
        return implicit_tree_list

    def find_best_bindings_for_current_state(self, current_node_fact, current_level, current_bindings, implicit_tree_data, goal_data):
        result = self.bind_goal_to_fact(current_node_fact, goal_data[current_level], current_bindings)
        if result  == "Invalid": #This is one of the base cases. Binding failed, so we don't want to do anything else with this implicit subtree.
            return "Invalid" #The caller will know the result of this branch does not matter
        else:
            (updated_bindings, score) = result #We know there is something to unpack, so unpack it
            if current_level == len(goal_data) - 1: #We know there are no more layers after this, i.e. this is an implicit leaf node. This is the other base case
                return (updated_bindings, score)
            else: #Else we want to carry out the recursive case
                #For the recursive case, we want to determine which subtree of the current node is the best
                #For this, we need to calculate the bindings and score for each subtree, and then put them all into a method that determines the best one
                #This best one should then be returned
                list_of_bindings_and_scores = []
                for fact in implicit_tree_data[current_level + 1]: #for each implicit subtree of the current node
                    recursive_result = self.find_best_bindings_for_current_state(fact, current_level+1, updated_bindings, implicit_tree_data, goal_data)
                    if recursive_result != "Invalid":
                        list_of_bindings_and_scores.append(recursive_result)
                best_bindings, best_score = self.choose_best_score_and_bindings(list_of_bindings_and_scores) #And return the best one that was found
                #Note that in a correct implementation, the recursive case will never return "Invalid" because a None node will always be valid, with a score of 0
                return (best_bindings, best_score + score) #Must add the current nodes score

    #Try and bind the goal to the fact.
    #ASSUMPTIONS
    # - The predicates are the same
    # - The types of the variables are the same
    # - The values are all the same
    #Therefore, we only need to check bindings, and very little more than that!
    def bind_goal_to_fact(self, world_fact, goal, bindings):
        if world_fact == None:
            return bindings, 0 #No changes needed to be made
        bindings_copy = copy(bindings) #Because we don't want to modify original (and aren't using links)
        for i in range(len(world_fact.get_parameters())): #We want to iterate through all the parameters
            param_in_fact = world_fact.get_parameters()[i] #ith parameter in fact
            param_in_goal = goal.get_parameters()[i] #ith parameter in goal
            if param_in_goal.is_var():
                if param_in_goal in bindings: #Is this already in the existing bindings?
                    existing_binding = bindings[param_in_goal]#This is the parameter that has been previously bound
                    if existing_binding != param_in_fact: #Contradiction!
                        return "Invalid"
                else: #Because it isn't yet bound, we can bind it
                    if param_in_fact in bindings.values():
                        return "Invalid"
                    else:
                        bindings_copy[param_in_goal] = param_in_fact
        #Because we got this far, it must have all been valid
        #And because it was not a None, it gets a score of 1
        return bindings_copy, 1

    def choose_best_score_and_bindings(self, possible_bindings_with_scores):
        best_score = None
        best_bindings = None
        for bindings, score in possible_bindings_with_scores:
            if best_score == None or score > best_score:
                best_score = score
                best_bindings = bindings
            elif score == best_score:
                if len(bindings) < len(best_bindings):
                    best_score = score
                    best_bindings = bindings
        return (best_bindings, best_score)

    ###############################################################
    #########   HANDLE THE PLACE VAR FACTS
    ###############################################################

    def map_place_var_facts(self, place_facts, bindings, current_state, used_objects):
        #Firstly, need to select bindings for any place facts that don't already have them
        updated_bindings = self.__bind_unbound_normal_vars(place_facts, bindings, current_state)

        #SHOULD THAT HAVE BEEN DONE USING PERMUTATIONS?
        unsatisfied_facts = set()
        categorized_place_facts = self.__categorize_place_facts(place_facts, updated_bindings)
        print("Print out state of catego")
        for (place_param, facts_for_place) in categorized_place_facts:
            print(place_param)
            for fact in facts_for_place:
                print(fact)
        print("Done!")
        print(str(categorized_place_facts))
        for (place_param, facts_for_place) in categorized_place_facts:
            facts_for_place = [goal.get_specific_copy_with_dictionary(updated_bindings) for goal in facts_for_place]
            print("Processing " + str(place_param))
            for fact in facts_for_place:
                print(fact)
            hand_at_fact = self.__contains_hand_at_fact(facts_for_place)
            #If there is a hand_at fact, it needs to be removed from the general list and we need to check whether it is optimal
            if hand_at_fact is not None:
                facts_for_place.remove(hand_at_fact)
                if self.__current_hand_place_optimal(hand_at_fact, facts_for_place, updated_bindings, current_state):
                    print("Current place is optimal")
                    updated_bindings[hand_at_fact.get_parameters()[0]] = Fact.Param((int(current_state.hand_quant_x()), int(current_state.hand_quant_y())), False, "p")
                    continue
                else:
                    unsatisfied_facts.add(hand_at_fact)
            #If we got this far, it couldn't have been satisfied
            #And we need to find the best point for the place
            point = Simulated_Vision.get_point_for_constraints(facts_for_place, updated_bindings, current_state.get_quantitative_state())
            print("The chosen point is " + str(point))
            if point:
                updated_bindings[place_param] = Fact.Param(point, False, "p")
        return updated_bindings, list(unsatisfied_facts)

    #Note: This needs to fail correctly when there are not enough bindings
    #This also needs to not bind already bound objects that were bound in the goals
    def __bind_unbound_normal_vars(self, place_facts, bindings, current_state):
        updated_bindings = copy(bindings) #Just to make debugging easier
        unbound_vars = self.__unbound_vars(place_facts, bindings)
        types_dictionary_for_current_state = current_state.objects_dictionary()
        for bound_obj in updated_bindings.values():
            type_of_obj = bound_obj.param_type()
            types_dictionary_for_current_state[type_of_obj].remove(bound_obj.identifier())
            #Need to ensure this is actually doing the right thing
        #This means the types dictionary should now only contain variables that are not already used
        for unbound_var in unbound_vars:
            type_of_var = unbound_var.param_type()
            chosen_binding = choice(list(types_dictionary_for_current_state[type_of_var]))
            updated_bindings[unbound_var] = Fact.Param(chosen_binding, False, type_of_var)
            types_dictionary_for_current_state[type_of_var].remove(chosen_binding)
        return updated_bindings


    def __unbound_vars(self, place_facts, bindings):
        unbound_vars = set()
        for fact in place_facts:
            for param in fact.get_parameters():
                if param.param_type() != "p" and param.is_var() and param not in bindings:
                    unbound_vars.add(param)
        return list(unbound_vars)


    def __categorize_place_facts(self, place_facts,updated_bindings):
        if place_facts == []:
            return []
        place_facts_categories = {}
        facts_with_multi_places = set()
        for fact in place_facts:
            unique_places = set()
            for param in fact.get_parameters():
                if param.param_type() == "p" and param.is_var():
                    unique_places.add(param)
            if len(unique_places) == 1:
                param = list(unique_places)[0]
                if param not in place_facts_categories:
                    place_facts_categories[param] = set()
                place_facts_categories[param].add(fact)
            else:
                facts_with_multi_places.add(fact)
        flat_list = []
        for place in place_facts_categories:
            facts = place_facts_categories[place]
            flat_list.append((place, list(facts)))
        flat_list.sort(key=lambda p : len(p[1]), reverse=True)
        for special in facts_with_multi_places:
            flat_list[-1][1].append(special)
        return flat_list


    def __contains_hand_at_fact(self, facts):
        for fact in facts:
            if fact.get_predicate() == "+hand_at" or fact.get_predicate() == "hand_at":
                return fact
        return None

    #If the hand at fact is optimal, this means that all the other facts can be made true with the current hand place
    def __current_hand_place_optimal(self, hand_at_fact, facts_for_place, bindings, current_state):
        current_hand_position = (current_state.hand_quant_x(), current_state.hand_quant_y())
        updated_bindings = copy(bindings) #We must only shallow copy here!
        updated_bindings[hand_at_fact.get_parameters()[0]] = current_hand_position
        for fact in facts_for_place:
            bound_fact = fact.get_specific_copy_with_dictionary(updated_bindings)
            #We need to check each fact to see if the place is made equal to the hand position whether or not it is satisfied
            #Currently, this must make ALL of them true, so it is the simple if all pattern
            if not Simulated_Vision.constraint_satisfied(bound_fact, current_state.get_quantitative_state()):
                return False
        return True

    def new_choose_best_rule(self, current_goal):
        nodes = The_Agent().knowledge().power_set_nodes_for_goal(current_goal)
        #Firstly, pick an effect set [Node]
        power_set_nodes_to_process = sorted(list(nodes), key=lambda n: (n.get_effect_set().size(), n.best_action_rule_score()))
        chosen_effect_set_node = None
        while power_set_nodes_to_process != []: #While there are nodes remaining
            root_node = power_set_nodes_to_process.pop() #Does this get the first one? No! It gets the last one.
            print("&&&&&&&&")
            print(root_node.get_effect_set())
            best_node = self.find_best_node_in_sub_lattice(root_node)
            if best_node != None:
                chosen_effect_set_node = best_node
                break #As we don't need to search any further
        if chosen_effect_set_node != None:
            #Want to choose the best action rule from the effect set for the goals
            best_action_rule = chosen_effect_set_node.best_action_rule()
            bound_rules = best_action_rule.get_possible_bound_action_rules(current_goal)
            best = bound_rules[0] #Initialise it to the first one
            for bound_rule in bound_rules:
                if bound_rule.number_of_goals_expected_to_accomplish() > best.number_of_goals_expected_to_accomplish():
                    best = bound_rule
            return best

    def find_best_node_in_sub_lattice(self, root_node):
        best_neighbour = None
        best_score = 0 #root_node.best_action_rule_score()
        for neighbour in root_node.get_superset_links():
            neighbour_score = neighbour.best_action_rule_score()
            if neighbour_score > best_score and neighbour.var_count() == root_node.var_count() and neighbour.get_action_rules() != []:
                s = neighbour_score
                best_neighbour = neighbour
        if best_score >= root_node.best_action_rule_score() and best_neighbour is not None:# or root_node.is_subsumed():
            return self.find_best_node_in_sub_lattice(best_neighbour)
        else:
            return root_node



class AgentMotorControl:


    def __init__(self):
        self.__simulation = TableWorldSimulation()

    def reset(self):
        self.__simulation.reset()

    def carry_out_bound_action(self, action):
        action_type = action.action_type()
        if action_type == "Grasp":
            self.__simulation.do_grasp_action() #Do on the same thread
        elif action_type == "Ungrasp":
            self.__simulation.do_ungrasp_action()
        elif action_type == "MoveTo":
            action_parameter = action.action_parameter().identifier()
            print("Move: the action parameter is " + str(action_parameter))
            self.__simulation.do_move_to_place(action_parameter)
        elif action_type == "Hit":
            action_parameter = action.action_parameter().identifier()
            print("Hit: the action parameter is " + str(action_parameter))
            self.__simulation.do_hit_to_place(action_parameter)
        else:
            print("action type was" + str(action_type))

    def set_simulation(self, new):
        self.__simulation = new

    def do_random_action(self):
        return self.__simulation.get_next_example()

    def get_current_state(self):
        return Qualitative_State(self.__simulation.get_current_state())

    def do_grasp_action(self):
        grasp_thread = Thread(target=self.__simulation.do_grasp_action)
        grasp_thread.start()

    def do_ungrasp_action(self):
        ungrasp_thread = Thread(target=self.__simulation.do_ungrasp_action)
        ungrasp_thread.start()

    def do_hit_action_on_random(self):
        hit_action_thread = Thread(target=self.__simulation.do_hit_action_on_random)
        hit_action_thread.start()

    def do_move_action_on_random(self):
        move_action_thread = Thread(target=self.__simulation.do_move_action_on_random)
        move_action_thread.start()

    def do_move_to_place(self, place):
        move_action_thread = Thread(target=lambda: self.__simulation.do_move_to_place(place))
        move_action_thread.start()

    def do_move_action_on_target(self, target):
        move_action_thread = Thread(target=lambda: self.__simulation.do_move_action(target))
        move_action_thread.start()

    def do_hit_action_on_target(self, target):
        hit_action_thread = Thread(target=lambda: self.__simulation.do_hit_action(target))
        hit_action_thread.start()

    def objects_currently_in_world(self):
        objects = self.__simulation.objects_currently_in_world()
        return list(["left_wall", "near_wall", "right_wall", "far_wall"] + [x.get_name() for x in objects if x.on_table()])

    def find_place(self, constraints):
        current_state = self.get_current_state()
        point = Simulated_Vision.get_point_for_constraints(constraints, current_state.get_quantitative_state())
        print(point)
        self.do_move_to_place(point)
