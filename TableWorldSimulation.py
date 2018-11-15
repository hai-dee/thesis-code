from Example import Qualitative_Example

from State import State
import SharedData as Shared
from SharedData import * #Cause it is too much of a pain to make work properly otherwise
import Simulated_Vision

from copy import deepcopy
from random import random
from random import shuffle
from random import gauss
from math import hypot
from math import atan2
from math import sqrt
from math import pi as PI
from time import sleep

from utils.vect import Vect

#For various stupid reasons, this isn't in the python libraries
def signum(n):
    if n == 0:
        return 0
    elif n > 0:
        return 1.0
    else:
        return -1.0

#Constants for the physics
MAX_FORCE = 50
HAND_MASS = 5.0
HAND_DECCEL = 2 #Deceleration under friction
HAND_FRICTION = HAND_DECCEL * HAND_MASS
HAND_COLOR = "yellow"
GRASP_SPEED = 0.4
OBJ_MASS = 0.5 #Was originally 0.5
OBJ_DECCEL = 0.3 #Was originally 0.3
OBJ_FRICTION = OBJ_DECCEL * OBJ_MASS
BOUNCE_FACTOR = 0 #Was originally 0.7
TIME_STEP_LENGTH = 0.1
MOVE_INCREMENTS = 10
HAND_RAD = 8
OBJ_RAD =  5
COLLISION_DIST = HAND_RAD + OBJ_RAD
GRASP_DISTANCE = 2
EPSILON = 0.1
NUM_OBJECTS = 3

#Proabilities/ constants to use when deciding on a random action for the agent to carry out
PROB_OF_START_ACTION = 0.05
PROB_GRASPING_WHEN_NEAR = 0.5
PROB_RANDOM_GRASPING = 0.01
PROB_UNGRASPING = 0.01
PROB_REVERSING_FROM_WALL = 0.2
PROB_SPEEDUP = 0.03
MIN_TIME_BETWEEN_GRASPING = 300
PROB_UNGRASPING_WHEN_GRASPING = 0.4

PROB_UNGRASP_HOLDING = 0.1
PROB_GRASP_NEAR = 0.75

PROB_OF_MOVE = 0.35 #normally 0.35
PROB_OF_HIT = PROB_OF_MOVE + 0.35 #normally 0.35
PROB_OF_GRASP_NOT_NEAR = PROB_OF_HIT + 0.15 #normally 0.15

#Probabilities for differet
PROB_TARGET_WALL = 0.4
PROB_TARGET_OBJ = 1 - PROB_TARGET_WALL

#Used for selecting a place
PROB_PLACE_TOUCHING_WALL = 0.3 #normally 0.3
PROB_PLACE_TOUCHING_OBJ = PROB_PLACE_TOUCHING_WALL + 0.3 #normally 0.3
PROB_PLACE_SPECIAL_ALIGN = PROB_PLACE_TOUCHING_OBJ + 0.1
PROB_PLACE_RANDOM = PROB_PLACE_SPECIAL_ALIGN + 0.3


class TableWorldSimulation:

    def __init__(self):
        self.__hand_force_y = 0
        self.__hand_force_x = 0
        self.__hand_pos_x = 0
        self.__hand_pos_y = 15 + HAND_RAD
        self.__hand_vel_x = 0
        self.__hand_vel_y = 0
        self.__hand_accel_x = 0
        self.__hand_accel_y = 0
        self.__hand_touching_obj = False
        self.__hand_touching_wall = False
        self.__finger_force = 0
        self.__finger_pos = 0
        self.__finger_vel = 0
        self.__gripping = False
        self.__sound_occurred = False
        self.__grasped_obj = None
        self.__last_collision = None
        self.__objects = []
        self.__current_action = None
        self.__current_action_string = None
        self.__final_x = None
        self.__final_y = None
        self.__time_since_grasp = 0 # How long ago was the last grasp?
        self.__target_x = None #Target x of the current move or hit action
        self.__target_y = None #Target y of the current move or hit action
        self.__target_dir = None #Direction of target when started
        self.__target_name = None
        self.__target_obj = None #The object that is the target, if any
        self.__target_speed = None #Desired speed for moving to the target
        self.__end_radius = None #Distance from the target to slow down at
        self.__count_stopped = 0
        self.__low_velocity_limit = 1.5
        self.__hit_action_past_target = False
        self.__start_of_action_x = None
        self.__start_of_action_y = None

    def reset(self):
        self.__hand_force_y = 0
        self.__hand_force_x = 0
        self.__hand_pos_x = 0
        self.__hand_pos_y = 15 + HAND_RAD
        self.__hand_vel_x = 0
        self.__hand_vel_y = 0
        self.__hand_accel_x = 0
        self.__hand_accel_y = 0
        self.__hand_touching_obj = False
        self.__hand_touching_wall = False
        self.__finger_force = 0
        self.__finger_pos = 0
        self.__finger_vel = 0
        self.__gripping = False
        self.__sound_occurred = False
        self.__grasped_obj = None
        self.__last_collision = None
        self.__objects = []
        self.__reset_objects()
        self.__current_action = None
        self.__current_action_string = None
        self.__final_x = None
        self.__final_y = None
        self.__time_since_grasp = 0 # How long ago was the last grasp?
        self.__target_x = None #Target x of the current move or hit action
        self.__target_y = None #Target y of the current move or hit action
        self.__target_dir = None #Direction of target when started
        self.__target_name = None
        self.__target_obj = None #The object that is the target, if any
        self.__target_speed = None #Desired speed for moving to the target
        self.__end_radius = None #Distance from the target to slow down at
        self.__count_stopped = 0
        self.__low_velocity_limit = 1.5
        self.__hit_action_past_target = False
        self.__start_of_action_x = None
        self.__start_of_action_y = None


    def get_next_example(self):
        states_in_example = [] #List of State objects in this example
        action_name = None
        action_param = None
        previous_state = None
        currently_recording_action = False
        while(True):
            self.__set_actuators()
            self.__compute_new_state()
            cur_state = self.__make_state_object()
            if Shared.visualisation_enabled:
                #Need to make it so that it waits for the state to be drawn before continuing
                Shared.currently_drawing.acquire()
                Shared.drawing_queue.put(cur_state)
                Shared.currently_drawing.wait()
                Shared.currently_drawing.release()
                #Finish of waiting
            if self.__current_action and not currently_recording_action: #This must be the start of the action
                action_name = self.__current_action
                action_param = self.__target_name
                currently_recording_action = True
                if previous_state:
                    states_in_example.append(previous_state)
                states_in_example.append(cur_state)
            elif self.__current_action: #There is an action currently, and this isn't the first state
                states_in_example.append(cur_state)
            elif (not self.__current_action) and states_in_example:
                #There must have been an action, but it has just finished now.
                #Attach the current state on, as it must be the last one in the action
                self.__final_x = self.__hand_pos_x
                self.__final_y = self.__hand_pos_y
                cur_state = self.__make_state_object()
                Shared.currently_drawing.acquire()
                Shared.drawing_queue.put(cur_state)
                Shared.currently_drawing.wait()
                Shared.currently_drawing.release()
                self.__reset_place_variables()
                states_in_example.append(cur_state) #Do we definitely want to do this? Is this actually the last state, or was the previous state the last state?
                if action_name == "Grasp" or action_name == "Ungrasp" or action_name == "UnGrasp":
                    action_param = None
                example = Qualitative_Example(action_name, action_param, states_in_example)
                if Shared.visualisation_enabled:
                    Shared.examples_to_display.put(example) #This is for debug purposes
                Shared.all_examples.append(example)
                return example
            if len(states_in_example) > 500: #It's probably stuck
                self.__reset_action_state()
                self.__reset_place_variables()
                states_in_example = [] #List of State objects in this example
                action_name = None
                action_param = None
                previous_state = None
                currently_recording_action = False
            previous_state = cur_state #Because when the action starts, we will need this

    def __reset_place_variables(self):
        self.__final_x = None
        self.__final_y = None
        self.__target_x = None
        self.__target_y = None
        self.__start_of_action_x = None
        self.__start_of_action_y = None

    def get_current_state(self):
        return self.__make_state_object()

    def do_grasp_action(self):
        self.__choose_grasp_action() #Set the actuators for a grasp action
        while self.__current_action == "Grasp":
            self.__set_actuators_action()
            self.__compute_new_state()
            if Shared.visualisation_enabled:
                cur_state = self.__make_state_object()
                Shared.currently_drawing.acquire()
                Shared.drawing_queue.put(cur_state)
                Shared.currently_drawing.wait()
                Shared.currently_drawing.release()

    def do_ungrasp_action(self):
        self.__choose_ungrasp_action() #Set the actuators for a grasp action
        while self.__current_action == "Ungrasp":
            self.__set_actuators_action()
            self.__compute_new_state()
            if Shared.visualisation_enabled:
                cur_state = self.__make_state_object()
                Shared.currently_drawing.acquire()
                Shared.drawing_queue.put(cur_state)
                Shared.currently_drawing.wait()
                Shared.currently_drawing.release()

    def do_move_action_on_random(self):
        self.__choose_move_action() #Set the actuators for a move action
        while self.__current_action == "MoveTo":
            self.__set_actuators_action()
            self.__compute_new_state()
            if Shared.visualisation_enabled:
                cur_state = self.__make_state_object()
                Shared.currently_drawing.acquire()
                Shared.drawing_queue.put(cur_state)
                Shared.currently_drawing.wait()
                Shared.currently_drawing.release()

    def do_hit_action_on_random(self):
        self.__choose_hit_action() #Set the actuators for a hit action
        while self.__current_action == "Hit":
            self.__set_actuators_action()
            self.__compute_new_state()
            if Shared.visualisation_enabled:
                cur_state = self.__make_state_object()
                Shared.currently_drawing.acquire()
                Shared.drawing_queue.put(cur_state)
                Shared.currently_drawing.wait()
                Shared.currently_drawing.release()

    def do_hit_action(self, target):
        if self.__set_action_target(target): #This will be false if the target does not exist, or if for any other reason it can't be set
            self.__choose_hit_action_with_set_target()
            while self.__current_action == "Hit":
                self.__set_actuators_action()
                self.__compute_new_state()
                if Shared.visualisation_enabled:
                    cur_state = self.__make_state_object()
                    Shared.currently_drawing.acquire()
                    Shared.drawing_queue.put(cur_state)
                    Shared.currently_drawing.wait()
                    Shared.currently_drawing.release()

    def do_move_action(self, target):
        if self.__set_action_target(target): #This will be false if the target does not exist, or if for any other reason it can't be set
            self.__choose_move_action_with_set_target()
            while self.__current_action == "MoveTo":
                self.__set_actuators_action()
                self.__compute_new_state()
                if Shared.visualisation_enabled:
                    cur_state = self.__make_state_object()
                    Shared.currently_drawing.acquire()
                    Shared.drawing_queue.put(cur_state)
                    Shared.currently_drawing.wait()
                    Shared.currently_drawing.release()

    def do_move_to_place(self, place):
        self.__set_move_place(place)
        self.__choose_move_action_with_set_target()
        while self.__current_action == "MoveTo":
            self.__set_actuators_action()
            self.__compute_new_state()
            if Shared.visualisation_enabled:
                cur_state = self.__make_state_object()
                Shared.currently_drawing.acquire()
                Shared.drawing_queue.put(cur_state)
                Shared.currently_drawing.wait()
                Shared.currently_drawing.release()

    def do_hit_to_place(self, place):
        self.__set_move_place(place)
        self.__choose_hit_action_with_set_target()
        while self.__current_action == "Hit":
            self.__set_actuators_action()
            self.__compute_new_state()
            if Shared.visualisation_enabled:
                cur_state = self.__make_state_object()
                Shared.currently_drawing.acquire()
                Shared.drawing_queue.put(cur_state)
                Shared.currently_drawing.wait()
                Shared.currently_drawing.release()

    def objects_currently_in_world(self):
        return self.__objects

    def __make_state_object(self):
        state = State()
        (state.add_hand_data(self.__hand_pos_x, self.__hand_pos_y, self.__hand_vel_x, self.__hand_vel_y, self.__hand_accel_x, self.__hand_accel_y, self.__hand_force_x, self.__hand_force_y,
                            self.__hand_touching_obj or self.__hand_touching_wall, self.__gripping, self.__sound_occurred, self.__finger_pos, self.__finger_vel, self.__finger_force, self.__current_action,
                            self.__target_obj, self.__target_x, self.__target_y, self.__start_of_action_x, self.__start_of_action_y, self.__final_x, self.__final_y))
        for obj in self.__objects:
            state.add_object_data(obj)
        return state

    def __compute_new_state(self):
        self.__sound_occurred = False
        if not self.__any_objects_on_table():
            self.__reset_objects()
        self.__do_hand_grasping()
        self.__compute_force_accel_veloc()
        self.__move_and_check_collisions()
        self.__compute_touch_sensors()

    def __do_hand_grasping(self):
        if self.__finger_force > 0:
            if self.__grasped_obj: #If currently holding something
                self.__gripping = True
                self.__finger_vel = 0
            elif self.__finger_pos >= 1.0: #If fingers are already in a first
                self.__gripping = False
                self.__finger_vel = 0
            else:
                old = self.__finger_pos
                self.__finger_pos = min(1.0, self.__finger_pos + GRASP_SPEED * self.__finger_force)
                if self.__finger_pos >= 0:
                    for obj in self.__objects:
                        if self.__near_object(obj):
                            self.__grasp_object(obj)
                            self.__gripping = True
                            self.__finger_pos = 0
                            break
                self.__finger_vel = self.__finger_pos - old
        elif self.__finger_force < 0:
            self.__gripping = False
            old = self.__finger_pos
            self.__finger_pos = max(-1.0, self.__finger_pos + GRASP_SPEED * self.__finger_force)
            self.__finger_vel = self.__finger_pos - old
            if self.__grasped_obj:
                self.__grasped_obj.is_grasped = False
                self.__grasped_obj = None
        else:
            self.__gripping = False
            self.__finger_vel = 0

    def __grasp_object(self, obj):
        dist = hypot(obj.x - self.__hand_pos_x, obj.y - self.__hand_pos_y)
        minimum = HAND_RAD + OBJ_RAD
        if dist > minimum: #Doesn't yet touch, so move object all the way to hand so it touches
            sc = minimum / dist
            obj.x = self.__hand_pos_x + sc * (obj.x - self.__hand_pos_x)
            obj.y = self.__hand_pos_y + sc * (obj.y - self.__hand_pos_y)
        self.__grasped_obj = obj
        obj.is_grasped = True
        obj.vx = self.__hand_vel_x
        obj.vy = self.__hand_vel_y


    #This method calcuates the force, acceleration, and velocities for the hand for this time step.
    def __compute_force_accel_veloc(self):
        ###Start by computing the forces... ###
        mass = HAND_MASS
        friction = HAND_FRICTION
        if self.__grasped_obj: # An object is currently grasped, need to take into account its mass and friction as well
            mass += OBJ_MASS #Need to double check variable name for this...
            friction += OBJ_FRICTION
        dvfr = friction * TIME_STEP_LENGTH / mass
        dvfx = self.__hand_force_x * TIME_STEP_LENGTH / mass
        dvfy = self.__hand_force_y * TIME_STEP_LENGTH / mass
        #If we are touching a wall, need to set the force in the appropriate direction to 0 (resulting in the hand sliding along the wall...)
        if dvfx > 0 and self.__contact_right_wall(): #Original version was evalulating the second part even if the first part was fault. This however SEEMS to be unnecessary...
            dvfx = 0
        elif dvfx < 0 and self.__contact_left_wall():
            dvfx = 0
        elif dvfy > 0 and self.__contact_far_wall():
            dvfy = 0
        elif dvfy < 0 and self.__contact_near_wall():
            dvfy = 0
        dvf = hypot(dvfx, dvfy) #Need to ensure this does get imported...
        ### Calculate the accerlation ###
        if abs(self.__hand_vel_x) > 0 or abs(self.__hand_vel_y) > 0: #The hand is currently moving
            total_vel = hypot(self.__hand_vel_x, self.__hand_vel_y)
            self.__hand_accel_x = dvfx - dvfr * self.__hand_vel_x / total_vel
            self.__hand_accel_y = dvfy - dvfr * self.__hand_vel_y / total_vel
        elif dvf > 0 and dvf > dvfr: #Not moving, and applied force is greater than friction
            self.__hand_accel_x = dvfx - dvfr * dvfx / dvf
            self.__hand_accel_y = dvfy - dvfr * dvfy / dvf
        else:
            self.__hand_accel_x = 0
            self.__hand_accel_y = 0
        ### Calculate the velocity ###
        new_vel_x = self.__hand_vel_x + self.__hand_accel_x
        new_vel_y = self.__hand_vel_y + self.__hand_accel_y
        if dvf < dvfr:
            if self.__hand_vel_x == 0 and self.__hand_vel_y == 0:
                self.__hand_accel_x = 0
                self.__hand_accel_y = 0
                new_vel_x = self.__hand_vel_x
                new_vel_y = self.__hand_vel_y
            else:
                if signum(self.__hand_vel_x) == -signum(new_vel_x): #Need to import signum (ended up defining it myself at top of file)
                    self.__hand_accel_x = -self.__hand_vel_x
                    new_vel_x = 0
                if signum(self.__hand_vel_y) == -signum(new_vel_y): #Need to import signum
                    self.__hand_accel_y = -self.__hand_vel_y
                    new_vel_y = 0
        self.__hand_vel_x = new_vel_x
        self.__hand_vel_y = new_vel_y
        ### Now need to work out the new velocities of the tw_objects ###
        deccel = OBJ_FRICTION/OBJ_MASS
        for obj in self.__objects:
            if obj.is_grasped:
                obj.vx = self.__hand_vel_x
                obj.vy = self.__hand_vel_y
            else:
                #Set the object velocity in the x direction...
                if obj.vx > 0:
                    obj.vx -= deccel
                    if obj.vx < 0:
                        obj.vx = 0
                else:
                    obj.vx += deccel
                    if obj.vx > 0:
                        obj.vx = 0
                #Set the object velocity in the y direction...
                if obj.vy > 0:
                    obj.vy -= deccel
                    if obj.vy < 0:
                        obj.vy = 0
                else:
                    obj.vy += deccel
                    if obj.vy > 0:
                        obj.vy = 0

    #Now, actually make the hand move based on the calculations in the previous method and check for collisions...
    def __move_and_check_collisions(self):
        self.__last_collision = None
        step = TIME_STEP_LENGTH / MOVE_INCREMENTS
        for t in range(MOVE_INCREMENTS): #Move in small increments...

            #Move the hand by one small step...
            prev_hand_x = self.__hand_pos_x
            prev_hand_y = self.__hand_pos_y
            self.__hand_pos_x += self.__hand_vel_x * step
            self.__hand_pos_y += self.__hand_vel_y * step

            #Move each object by one small step...
            for obj in self.__objects:
                obj.previous_x = obj.x
                obj.previous_y = obj.y
                obj.x += obj.vx * step
                obj.y += obj.vy * step

            #Now check for collisions with walls...
            if self.__hand_pos_x <= LEFT_WALL + HAND_RAD: #Check for collision with left wall
                #Check if a sound would have occurred...
                if prev_hand_x > LEFT_WALL + HAND_RAD:
                    self.__sound_occurred = True
                    self.__last_collision = "leftwall"
                self.__hit_wall_x(LEFT_WALL + HAND_RAD)
            elif self.__hand_pos_x >= RIGHT_WALL - HAND_RAD: #Check for collision with right wall
                if prev_hand_x < RIGHT_WALL - HAND_RAD:
                    self.__sound_occurred = True
                    self.__last_collision = "rightwall"
                self.__hand_pos_x = RIGHT_WALL - HAND_RAD #Why is there no method call here?
                self.__hand_vel_x = 0
            if self.__hand_pos_y <= NEAR_WALL + HAND_RAD: #Check for collision with near wall
                if prev_hand_y > NEAR_WALL + HAND_RAD:
                    self.__sound_occurred = True
                    self.__last_collision = "nearwall"
                self.__hit_wall_y(NEAR_WALL + HAND_RAD)
            elif self.__hand_pos_y >= FAR_WALL - HAND_RAD:
                if prev_hand_y < FAR_WALL - HAND_RAD:
                    self.__sound_occurred = True
                    self.__last_collision = "farwall"
                self.__hit_wall_y(FAR_WALL - HAND_RAD)
            #Now check if each object has collided with a wall...
            for obj in self.__objects:
                #Going over the right wall causes the object to fall on the floor
                if obj.x > RIGHT_WALL and not obj.is_grasped and obj.x < RIGHT_WALL + 20:
                    obj.x = FLOOR_X
                    obj.y = FLOOR_Y
                    obj.vx = 0
                    obj.vy = 0
                #Otherwise... has it collided with any other wall?
                if self.__on_table(obj):
                    if obj.x <= LEFT_WALL + OBJ_RAD:
                        if obj.previous_x > LEFT_WALL + OBJ_RAD:
                            self.__sound_occurred = True
                        self.__obj_bounce_wall_x(obj, LEFT_WALL + OBJ_RAD)
                    if obj.y <= NEAR_WALL + OBJ_RAD:
                        if obj.previous_y > NEAR_WALL + OBJ_RAD:
                            self.__sound_occurred = True
                        self.__obj_bounce_wall_y(obj, NEAR_WALL + OBJ_RAD)
                    if obj.y >= FAR_WALL - OBJ_RAD:
                        if obj.previous_y < FAR_WALL - OBJ_RAD:
                            self.__sound_occurred = True
                        self.__obj_bounce_wall_y(obj, FAR_WALL - OBJ_RAD)

            #Now check for collisions between hand and tw_objects
            for obj in self.__objects:
                if self.__on_table(obj) and obj != self.__grasped_obj:
                    self.__collide_hand(obj)

            #Now check for collisions between tw_objects
            for i in range(len(self.__objects) - 1):
                obj1 = self.__objects[i]
                if not self.__on_table(obj1):
                    continue
                for j in range(i + 1, len(self.__objects)):
                    obj2 = self.__objects[j]
                    if not self.__on_table(obj2):
                        continue
                    if obj1.is_grasped:
                        self.__collide_grasped(obj1, obj2)
                    elif obj2.is_grasped:
                        self.__collide_grasped(obj2, obj1)
                    else:
                        self.__collide_objects(obj1, obj2)

    def __compute_touch_sensors(self):
        self.__hand_touching_wall = (self.__hand_pos_x + HAND_RAD >= RIGHT_WALL - EPSILON
        or self.__hand_pos_x - HAND_RAD <= LEFT_WALL + EPSILON
        or self.__hand_pos_y + HAND_RAD >= FAR_WALL - EPSILON
        or self.__hand_pos_y - HAND_RAD <= NEAR_WALL + EPSILON)
        self.__hand_touching_obj = False
        for obj in self.__objects:
            if self.__near_object(obj):
                self.__hand_touching_obj = True
                break

    #Is this object on the table?
    def __on_table(self, obj):
        return obj.x <= RIGHT_WALL + OBJ_RAD

    def __near_object(self, obj):
        return self.__closer(obj.x - self.__hand_pos_x, obj.y - self.__hand_pos_y, COLLISION_DIST + GRASP_DISTANCE)

    def __closer(self, dx, dy, dist):
        return abs(dx) <= dist and abs(dy) <= dist and (dx**2 + dy**2) <= dist**2

    #Is the hand near enough to this object to grasp it?
    def __near_any_object(self):
        for obj in self.__objects:
            if self.__near_object(obj):
                return True
        return False

    #Is the hand touching the left wall?
    def __contact_left_wall(self):
        return (self.__hand_pos_x <= LEFT_WALL + HAND_RAD) or (self.__grasped_obj and self.__grasped_obj.x <= LEFT_WALL + OBJ_RAD)

    #Is the hand touching the right wall?
    def __contact_near_wall(self):
        return (self.__hand_pos_y <= NEAR_WALL + HAND_RAD) or (self.__grasped_obj and self.__grasped_obj.y <= NEAR_WALL + OBJ_RAD)

    #Is the hand touching the far wall?
    def __contact_far_wall(self):
        return (self.__hand_pos_y >= FAR_WALL - HAND_RAD) or (self.__grasped_obj and self.__grasped_obj.y >= FAR_WALL - OBJ_RAD)

    #Is the hand touching the right wall?
    def __contact_right_wall(self):
        return self.__hand_pos_x >= RIGHT_WALL - HAND_RAD #No need to check tw_objects cause of the hole in wall

    def __any_objects_on_table(self):
        for obj in self.__objects:
            if self.__on_table(obj):
                return True
        return False

    def __reset_objects(self):
        self.__objects = []
        shuffle(color_list)
        for i in range(NUM_OBJECTS):
            obj = self.__new_random_obj(color_list[i])
            self.__objects.append(obj)


    def __new_random_obj(self, color):
        x = LEFT_WALL + OBJ_RAD + random() * (RIGHT_WALL - LEFT_WALL - 2 * OBJ_RAD)
        y = FAR_WALL - OBJ_RAD - random() * (FAR_WALL - NEAR_WALL - 2 * OBJ_RAD)
        return Obj(x, y, color, color)

################################################################################################
### HANDLE ANY COLLISIONS THAT OCCUR
################################################################################################

    def __hit_wall_x(self, wall):
        self.__hand_vel_x = 0
        error = wall - self.__hand_pos_x
        self.__hand_pos_x += error
        if self.__grasped_obj:
            self.__grasped_obj.vx = 0
            self.__grasped_obj.x += error

    def __hit_wall_y(self, wall):
        self.__hand_vel_y = 0
        error = wall - self.__hand_pos_y
        self.__hand_pos_y += error
        if self.__grasped_obj:
            self.__grasped_obj.vy = 0
            self.__grasped_obj.y += error

    def __obj_bounce_wall_x(self, obj, wall):
        obj.vx *= -BOUNCE_FACTOR
        error = wall - obj.x
        obj.x += error
        if obj.is_grasped:
            self.__hand_vel_x *= -BOUNCE_FACTOR
            self.__hand_pos_x += error
            self.__last_collision = "leftwallWithObject"

    def __obj_bounce_wall_y(self, obj, wall):
        obj.vy *= -BOUNCE_FACTOR
        error = wall - obj.y
        obj.y += error
        if obj.is_grasped:
            self.__hand_vel_y *= -BOUNCE_FACTOR
            self.__hand_pos_y += error
            self.__last_collision = "YwallWithObject" #Need to make it so that it says the correct wall. The java code has a bug in this line.

    #Check if hand colliding with obj. If so, make them bounce with reduced bounce factor
    def __collide_hand(self, obj):
        disp = Vect(obj.x - self.__hand_pos_x, obj.y -self.__hand_pos_y)
        offset = self.__collide_overlap(disp, OBJ_RAD + HAND_RAD)
        if not offset:
            return
        self.__sound_occurred = True #As a collision has occurred...
        self.__last_collision = obj
        obj.x += 2 * offset.x
        obj.y += 2 * offset.y
        hand_vel = Vect(self.__hand_vel_x, self.__hand_vel_y)
        obj_vel = Vect(obj.vx, obj.vy)
        new_v = self.__bounce(hand_vel, HAND_MASS, obj_vel, OBJ_MASS, disp, BOUNCE_FACTOR/2)
        if new_v:
            self.__hand_vel_x = new_v["vx1"]
            self.__hand_vel_y = new_v["vy1"]
            obj.vx = new_v["vx2"]
            obj.vy = new_v["vy2"]

    def __collide_grasped(self, obj1, obj2):
        disp = Vect(obj2.x - obj1.x, obj2.y - obj1.y)
        offset = self.__collide_overlap(disp, OBJ_RAD * 2)
        if not offset:
            return
        self.__sound_occurred = True
        self.__last_collision = "graspedObjectWithObject"
        obj2.x += 2 * offset.x
        obj2.y += 2 * offset.y
        hand_obj1_vel = Vect(obj1.vx, obj1.vy)
        obj2_vel = Vect(obj2.vx, obj2.vy)
        new_v = self.__bounce(hand_obj1_vel, OBJ_MASS + HAND_MASS, obj2_vel, OBJ_MASS, disp, BOUNCE_FACTOR)
        if new_v:
            obj1.vx = new_v["vx1"]
            obj1.vy = new_v["vy1"]
            self.__hand_vel_x = new_v["vx1"]
            self.__hand_vel_y = new_v["vy1"]
            obj2.vx = new_v["vx2"]
            obj2.vy = new_v["vy2"]

    def __collide_objects(self, obj1, obj2):
        disp = Vect(obj2.x - obj1.x, obj2.y - obj1.y)
        offset = self.__collide_overlap(disp, OBJ_RAD * 2)
        if not offset:
            return
        self.__sound_occurred = True
        obj1.x -= offset.x
        obj1.y -= offset.y
        obj2.x += offset.x
        obj2.y += offset.y
        disp = Vect(obj2.x - obj1.x, obj2.y - obj1.y)
        obj1_vel = Vect(obj1.vx, obj1.vy)
        obj2_vel = Vect(obj2.vx, obj2.vy)
        new_v = self.__bounce(obj1_vel, OBJ_MASS, obj2_vel, OBJ_MASS, disp, BOUNCE_FACTOR)
        if new_v:
            obj1.vx = new_v["vx1"]
            obj1.vy = new_v["vy1"]
            obj2.vx = new_v["vx2"]
            obj2.vy = new_v["vy2"]

    def __collide_overlap(self, disp, target):
        square_distance = disp.x ** 2 + disp.y ** 2
        if square_distance > target ** 2: #Not in collision
            return None
        if square_distance == 0: #Exactly on top of each other
            return Vect(target / 2, 0)
        dist = sqrt(square_distance)
        overlap = (target / dist - 1) / 2
        return Vect(disp.x * overlap, disp.y * overlap)

    #A method that I don't understand ANY of!!!
    def __bounce(self, v1, mass1, v2, mass2, disp, R):
        speed_n1 = v1.x * disp.x + v1.y * disp.y
        speed_n2 = v2.y * disp.x + v2.y * disp.y
        vcm = (speed_n1 * mass1 + speed_n2 * mass2) / (mass1 + mass2)
        vn1 = speed_n1 - vcm
        vn2 = speed_n2 - vcm
        if vn2 > 0:
            return None #The 2 things are not moving towards each other - ?
        vn1 = vcm - vn1 * R
        vn2 = vcm - vn2 * R
        speed_t1 = v1.y * disp.x - v1.x * disp.y
        speed_t2 = v2.y * disp.x - v2.x * disp.y
        vtx1 = speed_t1 * (-disp.y)
        vty1 = speed_t1 * disp.x
        vtx2 = speed_t2 * (-disp.y)
        vty2 = speed_t2 * disp.x
        sqhypot = disp.x ** 2 + disp.y ** 2
        values = {}
        values["vx1"] =  (vtx1 + vn1 * disp.x) / sqhypot
        values["vy1"] =  (vty1 + vn1 * disp.y) / sqhypot
        values["vx2"] =  (vtx2 + vn2 * disp.x) / sqhypot
        values["vy2"] =  (vty2 + vn2 * disp.y) / sqhypot
        return values


################################################################################################
### SETTING THE ACTUATORS; RANDOM, HIT, MOVE, GRASP, UNGRASP
################################################################################################

    ### INTERNAL SETTING OF THE ACTUATORS ###

    #Todo: Investigate why there appears to be dead code in this method
    def __set_actuators(self):

        ####These lines of code seem to be redundant #####
        old_fx = self.__hand_force_x
        old_fy = self.__hand_force_y
        old_ff = self.__finger_force
        ##################################################

        ##this is where the new code goes

        #This is where the stuff for setting the mouse forces went, but because this feature has been disabled, not bothering with that code
        if not self.__current_action and random() < PROB_OF_START_ACTION: #Start a new action...
            self.__choose_new_action()
        if not self.__current_action:
            self.__time_since_grasp = 0 #Where is this variable defined?
            self.__set_actuators_random() #Just do some random behaviour
        else:
            self.__set_actuators_action() #Continue the current action

    def __set_actuators_action(self):
        if self.__current_action == "MoveTo":
            self.__set_actuators_move_action()
        elif self.__current_action == "Hit":
            self.__set_actuators_hit_action()
        elif self.__current_action == "Grasp":
            self.__set_actuators_grasp_action()
        elif self.__current_action == "Ungrasp":
            self.__set_actuators_ungrasp_action()

    ### SET THE ACTUATORS RANDOMLY (i.e. no deliberate action is currently being carried out) ###

    def __set_actuators_random(self):
        old_fx = self.__hand_force_x
        old_fy = self.__hand_force_y
        old_ff = self.__finger_force
        #If touching the wall, reverse direction with the given probability
        if self.__hand_touching_wall and random() < PROB_REVERSING_FROM_WALL:
            if self.__hand_vel_y == 0 and abs(old_fy) > 0.1:
                self.__hand_force_y = -old_fy
            if self.__hand_vel_x == 0 and abs(old_fx) > 0.1:
                self.__hand_force_x = -old_fx
        #Speed up with the specified probability
        if random() < PROB_SPEEDUP:
            if abs(self.__hand_vel_x) > 4 or abs(self.__hand_vel_y) > 4: #if going fast
                self.__hand_force_x = self.__bound(self.__hand_force_x * 3, -MAX_FORCE, MAX_FORCE)
                self.__hand_force_y = self.__bound(self.__hand_force_y * 3, -MAX_FORCE, MAX_FORCE)
            else: #If going slow
                self.__hand_force_x = self.__bound(gauss(0,MAX_FORCE / 2), -MAX_FORCE, MAX_FORCE)
                self.__hand_force_y = self.__bound(gauss(0,MAX_FORCE / 2), -MAX_FORCE, MAX_FORCE)
        #Else we aren't speeding up.
        else:
            self.__hand_force_x = self.__bound(self.__hand_force_x *gauss(0.95,0.05), -MAX_FORCE, MAX_FORCE)
            self.__hand_force_y = self.__bound(self.__hand_force_y *gauss(0.95,0.05), -MAX_FORCE, MAX_FORCE)
            if abs(self.__hand_force_x) < 0.5 and abs(self.__hand_force_y) < 0.5:
                #Very low force, so just set to 0
                self.__hand_force_x = 0
                self.__hand_force_y = 0
            if abs(self.__hand_vel_x) < 0.5 and abs(self.__hand_vel_y) < 0.5:
                #Very low velocity so just set to a random force
                self.__hand_force_x = self.__bound(gauss(0,MAX_FORCE / 2), -MAX_FORCE, MAX_FORCE)
                self.__hand_force_y = self.__bound(gauss(0,MAX_FORCE / 2), -MAX_FORCE, MAX_FORCE)
        #Do random grasp actions based on probabilities
        self.__time_since_grasp += 1
        ready_to_grasp = self.__time_since_grasp > MIN_TIME_BETWEEN_GRASPING #Trying to shorten some of the conditions slightly
        if ready_to_grasp and not self.__grasped_obj and self.__finger_force == 0 and self.__finger_pos < 0 and random() < PROB_GRASPING_WHEN_NEAR and self.__near_any_object():
            self.__finger_force = 1 #Maximum grasping force
            self.__time_since_grasp = 0
        elif not self.__grasped_obj and self.__finger_force >= 0 and self.__finger_pos > 0 and random() < PROB_UNGRASPING_WHEN_GRASPING:
            self.__finger_force = -1 #Maximum ungrasping force
        elif self.__grasped_obj and ready_to_grasp and random() < PROB_UNGRASPING and self.__finger_force > 0:
            self.__finger_force = -1 #Maximum ungrasping force
            self.__time_since_grasp = 0
        elif self.__finger_force == 0 and self.__finger_pos < 0 and random() < PROB_RANDOM_GRASPING:
            self.__finger_force = 1.0 #Maximum grasping force
            self.__time_since_grasp = 0
        elif self.__finger_force == 0 and self.__finger_pos > -1 and random() < PROB_UNGRASPING: #This is apparently potentially an impossible condition...
            self.__finger_force = -1
            self.__time_since_grasp = 0
        elif self.__finger_pos == -1 and self.__finger_force < 0: #Hand is fully open and trying to open more
            self.__finger_force = 0 #So stop trying...

    def __bound(self, val, minimum, maximum):
        if val < minimum:
            return minimum
        elif val > maximum:
            return maximum
        else:
            return val


    def __reset_action_state(self):
        self.__current_action = None
        self.__target_name = None
        self.__current_action_string = None


### SET THE ACUTATORS FOR A MOVE ACTION ###

    def __set_actuators_move_action(self):
        dx = self.__target_x - self.__hand_pos_x
        dy = self.__target_y - self.__hand_pos_y
        dist = hypot(dx, dy)
        if self.__move_action_finished(dx, dy, dist): #Are we already at the destination?
            self.__reset_action_state()
        else: #Still need to move...
            t_speed = self.__target_speed
            if dist <= self.__end_radius:
                t_speed = t_speed * dist/ self.__end_radius
            t_vel_x = t_speed * dx/dist
            t_vel_y = t_speed * dy/dist
            same_direction_x = signum(self.__hand_vel_x) == signum(t_vel_x)
            same_direction_y = signum(self.__hand_vel_y) == signum(t_vel_y)
            if same_direction_x and abs(self.__hand_vel_x) > abs(t_vel_x):
                #Too fast - slow down at max
                self.__hand_force_x =- MAX_FORCE * signum(t_vel_x)
            elif not same_direction_x or abs(self.__hand_vel_x) < abs(t_vel_x):
                #Too slow or opposite direction
                self.__hand_force_x = MAX_FORCE * signum(t_vel_x)
            if same_direction_y and abs(self.__hand_vel_y) > abs(t_vel_y):
                #Too fast - slow down at max
                self.__hand_force_y =- MAX_FORCE * signum(t_vel_y)
            elif not same_direction_x or abs(self.__hand_vel_y) < abs(t_vel_y)/2:
                #Too slow or opposite direction
                self.__hand_force_y = MAX_FORCE * signum(t_vel_y)
            self.__finger_force = 0 #Don't need finger force in a move action...

    def __move_action_finished(self, dx, dy, dist):
        if (self.__hand_force_x != 0 or self.__hand_force_y != 0) and (dist < 1 or (abs(self.__hand_vel_x) <= self.__low_velocity_limit and abs(self.__hand_vel_y) <= self.__low_velocity_limit)):
            self.__count_stopped += 1
        else:
            self.__count_stopped = 0
        if self.__count_stopped > 5:
            self.__count_stopped = 0
            return True

        #if velocity is low and it is near the target
        if abs(self.__hand_vel_y) < self.__low_velocity_limit and abs(self.__hand_vel_x) < self.__low_velocity_limit and dist <= GRASP_DISTANCE:
        #If it is near the target object, stop the action, set force to 0, move rest of way to target
            if (self.__target_obj and self.__near_object(self.__target_obj)) or not self.__target_obj: #If object and near it, or if a wall...
                self.__count_stopped = 0
                self.__hand_pos_x = self.__target_x
                self.__hand_pos_y = self.__target_y
                self.__hand_vel_x = 0
                self.__hand_vel_y = 0
                self.__hand_force_x = 0
                self.__hand_force_y = 0
                return True
        #If it has gone past the target, stop action, and set force to 0
        dir_diff = 2 * abs(atan2(dy, dx) - self.__target_dir)
        if dir_diff > PI and dir_diff < 3 * PI:
            self.__hand_force_x = 0
            self.__hand_force_y = 0
            return True
        return False #Move action isn't finished, so keep going

    ### SET THE ACUTATORS FOR A HIT ACTION ###
    def __set_actuators_hit_action(self):
        dx = self.__target_x - self.__hand_pos_x
        dy = self.__target_y - self.__hand_pos_y
        dist = hypot(dx, dy)
        if (self.__hand_past_target(dx, dy, dist) and self.__hand_vel_x == 0 and self.__hand_vel_y == 0) or self.__hand_stuck(dist):
            self.__reset_action_state()
        else:
            t_speed = 0
            if not self.__hit_action_past_target:
                t_speed  = self.__target_speed
            t_vel_x = t_speed * dx/ dist
            t_vel_y = t_speed * dy/ dist
            same_direction_x = signum(self.__hand_vel_x) == signum(t_vel_x)
            same_direction_y = signum(self.__hand_vel_y) == signum(t_vel_y)
            if same_direction_x and abs(self.__hand_vel_x) > abs(t_vel_x):
            #Going too fast, slow down at max
                self.__hand_force_x = -MAX_FORCE * signum(t_vel_x)
            elif (not same_direction_x) or abs(self.__hand_vel_x) < abs(t_vel_x):
            #Too slow or opposite direction, speed up at max
                self.__hand_force_x = MAX_FORCE * signum(t_vel_x)

            if same_direction_y and abs(self.__hand_vel_y) > abs(t_vel_y):
            #Going too fast, slow down at max
                self.__hand_force_y = -MAX_FORCE * signum(t_vel_y)
            elif (not same_direction_y) or abs(self.__hand_vel_y) < abs(t_vel_y)/2:
            #Too slow or opposite direction, speed up at max
                self.__hand_force_y = MAX_FORCE * signum(t_vel_y)
        self.__finger_force = 0 #Don't want the fingers to be moving for a hit action

    #This was originally called check past target
    def __hand_past_target(self, dx, dy, dist):
        if self.__hit_action_past_target:
            return True
        if self.__target_obj and self.__last_collision == self.__target_obj:
            self.__hit_action_past_target = True
            return True
        dir_diff = 2 * abs(atan2(dy, dx) - self.__target_dir)
        if dist == 0 or (dir_diff > PI and dir_diff < 3 * PI):
            self.__hit_action_past_target = True
            return True
        return False

    def __hand_stuck(self, dist):
        if (self.__hand_force_x != 0 or self.__hand_force_y != 0) and (dist < 1 or (abs(self.__hand_vel_x) < self.__low_velocity_limit and abs(self.__hand_vel_y) < self.__low_velocity_limit )):
            self.__count_stopped += 1
        else:
            self.__count_stopped = 0
        if self.__count_stopped > 5:
            self.__count_stopped = 0
            return True
        return False

### SET THE ACTUATORS FOR A GRASP OR UNGRASP ACTION ###

    def __set_actuators_grasp_action(self):
        if self.__gripping or self.__finger_pos >= 1 or self.__fingers_stuck():
            self.__reset_action_state()
        else: #Still need to grasp... set finger force to max grasp force
            self.__finger_force = 1

    def __set_actuators_ungrasp_action(self):
        if self.__finger_pos <= -1 or self.__fingers_stuck():
            self.__reset_action_state()
        else: #Still need to ungrasp... set finger force to max ungrasp force
            self.__finger_force = -1

    #If fingers haven't moved for 5 steps, then they are stuck
    def __fingers_stuck(self):
        if self.__finger_force != 0 and abs(self.__finger_vel) < 0.01: #Finger force isn't 0, but the fingers are hardly moving...
            self.__count_stopped += 1
        else:
            self.__count_stopped = 0
        if self.__count_stopped > 5:
            self.__count_stopped = 0
            return True
        return False

####################################################################################################
### CHOOSING A NEW ACTION AND TARGET ###############################################################
####################################################################################################

    #Choose a new action and set the actuator variables
    def __choose_new_action(self):
        choice = random()
        if self.__grasped_obj and choice < PROB_UNGRASP_HOLDING:
            self.__choose_ungrasp_action()
        elif self.__near_any_object() and choice < PROB_GRASP_NEAR:
            self.__choose_grasp_action()
        if choice < PROB_OF_MOVE:
            self.__choose_move_action()
        elif choice < PROB_OF_HIT:
            self.__choose_hit_action()
        elif choice < PROB_OF_GRASP_NOT_NEAR:
            self.__choose_grasp_action()
        else:
            self.__choose_ungrasp_action()
        self.__start_of_action_x = self.__hand_pos_x
        self.__start_of_action_y = self.__hand_pos_y

    def __choose_move_action(self):
        if self.__choose_place_target():
            self.__current_action = "MoveTo"
            self.__current_action_string = "MoveTo("+str(self.__target_name)+")"
            self.__end_radius = 30
            self.__target_speed = 30

    def __choose_move_action_with_set_target(self):
        self.__current_action = "MoveTo"
        self.__current_action_string = "MoveTo("+str(self.__target_name)+")"
        self.__end_radius = 30
        self.__target_speed = 30


    def __choose_hit_action(self):
        if self.__choose_place_target():
            self.__current_action = "Hit"
            self.__current_action_string = "Hit("+str(self.__target_name)+")"
            self.__hit_action_past_target = False
            self.__target_speed = 60

    def __choose_hit_action_with_set_target(self):
        self.__current_action = "Hit"
        self.__current_action_string = "Hit("+str(self.__target_name)+")"
        self.__hit_action_past_target = False
        self.__target_speed = 60

    def __choose_grasp_action(self):
        self.__target_obj = None
        self.__current_action = "Grasp"
        self.__current_action_string = "Grasp"

    def __choose_ungrasp_action(self):
        self.__target_obj = None
        self.__current_action = "Ungrasp"
        self.__current_action_string = "Ungrasp"


    #Currently a prototype version, it just keeps searching (using a recursive loop)
    def __choose_place_target(self):
        current_state = self.__make_state_object()
        self.__place = None
        choice = random()
        if choice < PROB_PLACE_TOUCHING_WALL:
            (x, y) = Simulated_Vision.get_random_touching_wall(current_state)
            self.__target_x = x
            self.__target_y = y
            self.__target_name = (x,y)
            self.__target_dir = atan2(self.__target_y - self.__hand_pos_y, self.__target_x - self.__hand_pos_x)
            return True
        elif choice < PROB_PLACE_TOUCHING_OBJ:
            result = Simulated_Vision.get_random_place_touching_object(current_state)
            if result != None:
                (x, y) = result
                self.__target_x = x
                self.__target_y = y
                self.__target_name = (x,y)
                self.__target_dir = atan2(self.__target_y - self.__hand_pos_y, self.__target_x - self.__hand_pos_x)
                return True
        elif choice <PROB_PLACE_SPECIAL_ALIGN:
            print("Special align is not yet implemented")
        elif choice <PROB_PLACE_RANDOM:
            (x, y) = Simulated_Vision.get_random_place(current_state)
            self.__target_x = x
            self.__target_y = y
            self.__target_name = (x,y)
            self.__target_dir = atan2(self.__target_y - self.__hand_pos_y, self.__target_x - self.__hand_pos_x)
            return True
        self.__choose_place_target() #If a place wasn't chosen, better try again

    #Returns True if the target exists and setting was successful
    #This method is used for moving to a given target
    def __set_action_target(self, target):
        if target == "near_wall":
            self.__target_x = (LEFT_WALL + RIGHT_WALL)/2
            self.__target_y = NEAR_WALL + HAND_RAD
        elif target == "far_wall":
            self.__target_x = (LEFT_WALL + RIGHT_WALL)/2
            self.__target_y = FAR_WALL - HAND_RAD
        elif target == "left_wall":
            self.__target_x = LEFT_WALL + HAND_RAD
            self.__target_y = (FAR_WALL + NEAR_WALL) / 2
        elif target == "right_wall":
            self.__target_x = RIGHT_WALL - HAND_RAD
            self.__target_y = (FAR_WALL + NEAR_WALL)/2
        elif target in [x.get_name() for x in self.__objects if x.on_table()]:
            target_obj = next(x for x in self.__objects if x.get_name() == target) #I hope this works correctly...
            dist_x = target_obj.x - self.__hand_pos_x
            dist_y = target_obj.y - self.__hand_pos_y
            dist = hypot(dist_x, dist_y)
            self.__target_x = target_obj.x - (OBJ_RAD + HAND_RAD) * dist_x / dist
            self.__target_y = target_obj.y - (OBJ_RAD + HAND_RAD) * dist_y / dist
            self.__target_obj = target_obj
        else:
            return False
        self.__target_dir = atan2(self.__target_y - self.__hand_pos_y, self.__target_x - self.__hand_pos_x)
        self.__target_name = target
        return True

    def __set_move_place(self, place):
        place_x, place_y = place
        self.__target_x = place_x
        self.__target_y = place_y
        self.__target_dir = atan2(self.__target_y - self.__hand_pos_y, self.__target_x - self.__hand_pos_x)
        self.__target_name = place
        self.__target_obj = None


class Obj:

    def __init__(self, x, y, name, colour):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.name = colour.replace(" ", "")
        self.colour = colour
        self.is_grasped = False

    def __closer(self, dx, dy, dist):
        return abs(dx) <= dist and abs(dy) <= dist and (dx**2 + dy**2) <= dist**2

    def get_name(self):
        return self.name

    def on_table(self):
            return self.x <= RIGHT_WALL + OBJ_RAD
