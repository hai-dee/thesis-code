import SharedData as Shared
from Fact import Fact
from math import hypot
from math import ceil
from math import floor
from collections import Counter
from random import choice
import Simulated_Vision #A collection of functions useful for determining visual properties of the agent's world

#This class represents the qualitative state of the world at a certain time.
#Most of the "vision system" code is here too.
class Qualitative_State:

    def __init__(self, quant_state):
        self.__qualitative_state_facts = self.__make_list_of_qual_facts(quant_state)
        self.__quantitative_state = quant_state
        #There is code in the example class that could be used for making a dictionary out of it if necessary...

    def get_quantitative_state(self):
        return self.__quantitative_state


    def get_qualitative_facts(self):
        return self.__qualitative_state_facts

    def hand_quant_x(self):
        return self.__quantitative_state.x

    def hand_quant_y(self):
        return self.__quantitative_state.y

    #Takes a generalised goal as a parameter, and returns the facts that can be mapped onto it.
    def get_candidates_for_goal(self, goal):
        facts_with_same_predicate = self.__facts_with_predicate(goal.get_predicate())
        candidates = []
        for fact in facts_with_same_predicate:
            if self.__fact_matches_goal(goal, fact):
                candidates.append(fact)
        return candidates


    def __facts_with_predicate(self, predicate):
        if predicate[0] == "+": #If this is a positive predicate
            predicate_without_plus = predicate[1:]
        else:
            predicate_without_plus = predicate
        return [fact for fact in self.get_qualitative_facts() if fact.get_predicate() == predicate_without_plus]


    def __fact_matches_goal(self, goal, fact):
        for i in range(len(goal.get_parameters())):
            param_in_goal = goal.get_parameters()[i]
            param_in_fact = fact.get_parameters()[i]
            if param_in_goal.is_var():
                if param_in_goal.param_type() != param_in_fact.param_type():
                    return False
            else: #It is a value
                if param_in_goal.identifier() != param_in_fact.identifier():
                    return False
        return True

    def contains_fact(self, fact):
        if fact.positive_predicate(): #This is for something that SHOULD exist
            plain_copy = fact.get_plain_copy_of_fact()
            return plain_copy in set(self.get_qualitative_facts())
        elif fact.negative_predicate():
            plain_copy = fact.get_plain_copy_of_fact()
            return plain_copy not in set(self.get_qualitative_facts())
        else:
            return fact in set(self.get_qualitative_facts())

    def place_fact_true(self, fact):
        result = Simulated_Vision.constraint_satisfied(fact, self.get_quantitative_state())
        return result


    #Return a dictionary of all the objects currently in the world, by type
    def objects_dictionary(self):
        objs = {}
        objs["w"] = ["left_wall", "near_wall", "far_wall"]
        objs["s"] = ["right_wall"]
        objs["o"] = set(self.__quantitative_state.objects.keys())
        return objs


    #Copied from example class for now. Will collapse the code down once I know it actually works
    def __make_list_of_qual_facts(self, quant_state):
        qual_list = [] #Will add them all into dict at the end
        ########################################################################################
        ## FACTS RELATED TO THE TOUCH SENSOR VARIABLES
        if quant_state.grip: #Is the hand currently grasping?
            qual_list.append(Fact("grasp_sensor", None))
        if quant_state.touch: #Is the hand currently touching something?
            qual_list.append(Fact("touch_sensor", None))
        #if quant_state.sound: #Is the sound sensor currently activated? (Not entirely sure if this effect is actually sensible) - it isn't.
        #   qual_list.append(Fact("sound_sensor", None))
        #Facts related to hand/ finger position/ movement
        #if quant_state.vx != 0 or quant_state.vy != 0: #Is the hand currently moving?
        #    qual_list.append(Fact("+hand_moving", None))
        #########################################################################################


        #########################################################################################
        ## FACTS RELATED TO THE FINGERS
        if quant_state.finger_vel != 0: #Are the fingers currently moving?
            qual_list.append(Fact("fingers_moving", None)) #Semi redundant
        if quant_state.finger_vel < 0:
            qual_list.append(Fact("fingers_opening",None))
        if quant_state.finger_vel > 0:
            qual_list.append(Fact("fingers_closing", None))
        if quant_state.finger_pos == -1:
            qual_list.append(Fact("fingers_flat", None))
        if quant_state.finger_pos == 1:
            qual_list.append(Fact("fingers_closed", None))
        #########################################################################################

        #########################################################################################
        ### FACTS RELATED TO RELATIONSHIPS BETWEEN OBJECTS
        #Note: Some of these probably need to be refactored.
        #Facts related to relationships between the hand, objects, and walls
        #The relationships between the walls are always the same for this world, hardcode this in for now (this could be calculated if necessary)

        hand_place = (quant_state.x, quant_state.y)

        for i in range(len(Shared.walls_wrap_around)):
            wall = Shared.walls_wrap_around[i]
            #What are the propeties of the wall that are always true?
            wall2 = Shared.walls_wrap_around[i-1] #-1 rather than +1 cause it gets the wrap around correct
            qual_list.append(Fact("touching", [wall, wall2]))
            qual_list.append(Fact("touching", [wall2, wall]))
            qual_list.append(Fact("on_table", [wall]))
            #Is the hand touching the wall?
            if Simulated_Vision.place_touching_wall(hand_place, wall):
                qual_list.append(Fact("hand_touching", [wall]))
        for obj_name in quant_state.objects:
            obj = quant_state.objects[obj_name]
            if obj.on_table: #We only want to learn facts about objects that are on the table
                qual_list.append(Fact("on_table", [obj.name]))
                if obj.grasped: #Check if object is grasped by hand
                    qual_list.append(Fact("hand_grasping", [obj.name]))
                if Simulated_Vision.place_touching_obj(hand_place, obj): #Is the hand plae touching this object?
                    qual_list.append(Fact("hand_touching", [obj.name]))
                for wall in Shared.walls_wrap_around:
                    if Simulated_Vision.obj_touching_wall(obj, wall): #Check if the object is touching any of the walls
                        qual_list.append(Fact("touching", [wall, obj.name]))
                        qual_list.append(Fact("touching", [obj.name, wall]))
                    if Simulated_Vision.place_obj_wall_aligned(hand_place, obj, wall): #And check if the hand is aligned with this object and wall
                        qual_list.append(Fact("hand_behind", [obj.name, wall]))
                for obj_name_2 in quant_state.objects: #check if this object is touching any other objects
                    obj2 = quant_state.objects[obj_name_2]
                    if obj != obj2 and Simulated_Vision.obj_touching_obj(obj, obj2):
                        qual_list.append(Fact("touching", [obj.name, obj2.name]))
        return qual_list


    #What are all the facts that are associated with place in the given quant state?
    #quant_state is a single quant state object
    #place is a tuple that contains firstly the place coordinates (which might or might not be the hand place) and then the name to use for the place in the facts
    def facts_for_place(self, place):
        quant_state = self.__quantitative_state
        set_of_facts = set()
        ((place_x, place_y), place_name) = place #Unpack the place data
        #Is the hand at the place? i.e. is the x and y both within +/- 0.5 of the place?
        if quant_state.x >= place_x - 0.5 and quant_state.x <= place_x + 0.5 and quant_state.y >= place_y - 0.5 and quant_state.y <= place_y + 0.5:
            set_of_facts.add(Fact("hand_at", [place_name]))
        for obj_name in quant_state.objects:
            obj = obj = quant_state.objects[obj_name]
            if obj.on_table:
                if Simulated_Vision.place_touching_obj((place_x, place_y), obj):
                    set_of_facts.add(Fact("place_touching", [place_name, obj_name]))
                if Simulated_Vision.place_near_obj((place_x, place_y), obj):
                    set_of_facts.add(Fact("place_near", [place_name, obj_name]))
                #TODO: ADD THE OBJ OBJ ALIGNMENT CHECK HERE
        for wall in Shared.walls_wrap_around:
            if Simulated_Vision.place_touching_wall((place_x, place_y), wall):
                set_of_facts.add(Fact("place_touching", [place_name, wall]))
            for obj_name in quant_state.objects:
                obj = quant_state.objects[obj_name]
                if obj.on_table:
                    if Simulated_Vision.place_obj_wall_aligned((place_x, place_y), obj, wall):
                        set_of_facts.add(Fact("place_behind", [place_name, obj_name, wall]))
                        if wall == "right_wall":
                            set_of_facts.add(Fact("behind_drop", [place_name, obj_name])) #hack!
        return list(set_of_facts)


    def facts_for_places(self, places):
        all_facts = []
        #Get facts for each individual place
        for place in places:
            facts_for_cur_place = self.facts_for_place(place)
            all_facts += facts_for_cur_place
        #Get facts that involve both places
        if len(places) == 2:
            quant_state = self.__quantitative_state
            ((place_x1, place_y1), _) = places[0]
            ((place_x2, place_y2), _) = places[1]
            if Simulated_Vision.clear_path_exists((place_x1, place_y1), (place_x2, place_y2), quant_state):
                "clear path commented out"
		#all_facts.append(Fact("clear_path", [place_name1, place_name2]))
            else:
                print("NOT CLEAR")
        elif len(places) != 1:
            print("SOMETHING HAS GONE WRONG IN QUAL STATE CODE")
        return all_facts
