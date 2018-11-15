from tkinter import *
from tkinter.filedialog import * #Import the stuff for nice file saving

from threading import Thread
from queue import Queue
from time import sleep
from State import State
from math import hypot
from Fact import Fact

from TheAgent import The_Agent
import SharedData as Shared
import File_Writer
import logging


####################################################################################################
### GUI CONSTANTS
####################################################################################################

BUTTON_WIDTH = 20
MAGNIFICATION_FACTOR  = 2
HAND_COLOR = "yellow" #What colour should the hand be drawn in?

#These should probably not be changed.
MIN_TIME_DELAY = 20 # ?
MAX_TIME_DELAY = 500
TIME_DELAY_CHANGE = 10

####################################################################################################
### GUI DATA
####################################################################################################
time_delay = 30 #How much delay should there be between attempts to draw the next state? (in milliseconds)
#Need to see what the implications are once the learning is very slow
#This is to try and speedup/slow down the visualisation.

canvas = None
window = None
data_box = None

####################################################################################################
### GUI INITIALISATION
####################################################################################################

#Initialises the main window, sets up the frames inside it, and calls initialisation for the controls in the controls frame
#the visualisation in the visualisations frame and the listeners that need to be added to the mainloop
def initialise_window():
    global window

    window = Tk()
    #Initialise the main frames
    controls_frame = Frame(window)

    right_frame = Frame(window)

    visualisation_frame = Frame(right_frame)
    text_frame = Frame(right_frame)

    #Position the frames in the main window
    controls_frame.grid(column=0, row=0, sticky=NW)
    right_frame.grid(column=1, row=0, sticky=NW)
    visualisation_frame.grid(column=0,row=0, sticky=NW)
    text_frame.grid(column=0, row=1, sticky=NW)

    #Initialise the frames
    initialise_control_frame(controls_frame)
    initialise_visualisation_frame(visualisation_frame)
    initialise_text_frame(text_frame)

    initialise_mainloop_listeners(window)
    window.mainloop()


def initialise_control_frame(controls_frame):
    #Label - "Learning"
    w = Label(controls_frame, text="Learning Controls", fg="red").grid(row=0, column=0)
    #Resume/Pause button (does not preserve the thread on pause, as that is pointless)
    resume_learning_button = Button(controls_frame, text="Resume Learning", command=lambda: resume_learning(resume_learning_button), width=BUTTON_WIDTH)
    resume_learning_button.grid(row=10, column=0)
    do_planning_button = Button(controls_frame, text="Resume Random Planning", command=lambda: resume_planning(do_planning_button), width=BUTTON_WIDTH)
    do_planning_button.grid(row=11, column=0)
    reset_sim_button = Button(controls_frame, text="Reset Sim", command=lambda: sim_reset(), width=BUTTON_WIDTH)
    reset_sim_button.grid(row=12, column=0)
    show_example_button = Button(controls_frame, text="Show Example", command=show_next_example, width=BUTTON_WIDTH)
    show_example_button.grid(row=13, column=0)
    hack_button = Button(controls_frame, text="do hand at plan!", command=hand_at_plan, width=BUTTON_WIDTH)
    hack_button.grid(row=14, column=0)


    Frame(controls_frame,  height=15).grid(row=15, column=0) #Hack to add space

    #Label - "Planning"
    Label(controls_frame, text="Planning Controls", fg="red").grid(row=20, column=0)
    #Textbox for entering goals
    text_box = Text(controls_frame, width=BUTTON_WIDTH, height=4)
    text_box.grid(row=25, column=0)
    #Button for carrying out plan
    plan_button = Button(controls_frame, text="Get Plan", command=lambda: make_plan(text_box), width=BUTTON_WIDTH)
    plan_button.grid(row=30, column=0)
    constraint_test_button = Button(controls_frame, text="Get Place", command=lambda: test_constraints(text_box), width=BUTTON_WIDTH)
    constraint_test_button.grid(row=32, column=0)
    Frame(controls_frame,  height=15).grid(row=35, column=0) #Hack to add space

    #Label - "Visualisation apperance"
    Label(controls_frame, text="Visualisation Controls", fg="red").grid(row=40, column=0)
    #Text output ON/OFF (Will not have this feature in the first version
    #Speed up
    Button(controls_frame, text="Speed up", command=speed_up, width=BUTTON_WIDTH).grid(row=50, column=0)
    #Slow down
    Button(controls_frame, text="Slow down", command=slow_down, width=BUTTON_WIDTH).grid(row=60, column=0)
    vis_button = Button(controls_frame, text="Disable Vis",  command=lambda: disable_vis(vis_button), width=BUTTON_WIDTH)
    vis_button.grid(row=70, column=0)
    Frame(controls_frame,  height=20).grid(row=75, column=0) #Hack to add space

    #Label - "Manual Actuators"
    Label(controls_frame, text="Manual Actuators", fg="red").grid(row=80, column=0)
    grasp_button = Button(controls_frame, text="Grasp", command=manual_grasp, width=BUTTON_WIDTH)
    grasp_button.grid(row=90, column=0)
    ungrasp_button = Button(controls_frame, text="Ungrasp", command=manual_ungrasp, width=BUTTON_WIDTH)
    ungrasp_button.grid(row=100, column=0)
    hit_button = Button(controls_frame, text="Hit Random", command=manual_hit_random, width=BUTTON_WIDTH)
    hit_button.grid(row=110, column=0)
    move_button = Button(controls_frame, text="MoveTo Random", command=manual_move_random, width=BUTTON_WIDTH)
    move_button.grid(row=120, column=0)
    target_entry_box = Entry(controls_frame)

    hit_target_button = Button(controls_frame, text="Hit Target", command=lambda: manual_hit_target(target_entry_box.get()), width=BUTTON_WIDTH)
    hit_target_button.grid(row=130, column=0)
    move_target_button = Button(controls_frame, text="MoveTo Target", command=lambda: manual_move_target(target_entry_box.get()), width=BUTTON_WIDTH)
    move_target_button.grid(row=140, column=0)
    move_place_button = Button(controls_frame, text="MoveTo Place", command=lambda: manual_move_place(target_entry_box.get()), width=BUTTON_WIDTH)
    move_place_button.grid(row=145, column=0)
    target_entry_box.grid(row=150, column=0)

    object_names_button = Button(controls_frame, text="Print Object Names", command=print_object_names, width=BUTTON_WIDTH)
    object_names_button.grid(row=160, column=0)


    knowledge_button = Button(controls_frame, text="Knowledge Summary", command=knowledge_file, width=BUTTON_WIDTH)
    knowledge_button.grid(row=190, column=0)

    print_state_button = Button(controls_frame, text="Print State", command=print_state, width=BUTTON_WIDTH)
    print_state_button.grid(row=200, column=0)


def initialise_visualisation_frame(visualisation_frame):
    global canvas
    canvas = Canvas(visualisation_frame, height=275, width=600, bg="white")
    canvas.grid(column=1, row=0)
    #Draw the table outline onto the canvas
    canvas.create_line(X(Shared.LEFT_WALL), Y(Shared.FAR_WALL), X(Shared.RIGHT_WALL), Y(Shared.FAR_WALL))
    canvas.create_line(X(Shared.LEFT_WALL), Y(Shared.NEAR_WALL), X(Shared.RIGHT_WALL), Y(Shared.NEAR_WALL))
    canvas.create_line(X(Shared.LEFT_WALL), Y(Shared.FAR_WALL), X(Shared.LEFT_WALL), Y(Shared.NEAR_WALL))
    canvas.create_line(X(Shared.RIGHT_WALL), Y(Shared.FAR_WALL), X(Shared.RIGHT_WALL), Y(Shared.NEAR_WALL))

def initialise_text_frame(text_frame):
    global data_box
    text_box = Text(text_frame, width=120, height=23)
    text_box.grid(column=0, row=0)
    data_box = text_box

#Initialises the extra listners in the mainloop. This is what controls the visualisation.
def initialise_mainloop_listeners(window):
    window.after(500, check_for_state_to_draw)
    window.after(500, check_for_example_to_display) #This may do weird things with the threads, it may get behind. It is only intended for the single examples mode
    #window.after(2000, __check_for_knowledge_file_generation_status) #This doesn't need to be very frequent
    window.protocol('WM_DELETE_WINDOW', exit_window) #Override default window exit behaviour


####################################################################################################
### CALLBACKS FOR CONTROLS
####################################################################################################

#This method starts/ pauses the learning. The learn() method on the agent is called, which then does its work in a seperate thread.
#Each learning iteration, it checks the status of the current_learning variable. If currently_learning is set to false, it will
#exit out the learning. The thread is not saved, as a new one is created if/ when learning continues.
#Need to add some more controls to prevent this from creating more than one thread.
def resume_learning(resume_learning_button):
    if Shared.currently_learning and not Shared.pause_learning:
        #Currently learning and have not tried to pause. Assume the learning should be paused.
        resume_learning_button["text"] = "Resume Learning"
        Shared.pause_learning = True
    elif not Shared.currently_learning and not Shared.currently_planning:
        Shared.currently_learning = True
        #Currently not learning. Assume learning should resume.
        resume_learning_button["text"] = "Pause Learning"
        The_Agent().learn()


def resume_planning(do_planning_button):
    if Shared.currently_planning:
        do_planning_button["text"] = "Resume Random Planning"
        Shared.currently_planning = False
    elif not Shared.currently_learning and not Shared.currently_planning:
        Shared.currently_planning = True
        do_planning_button["text"] = "Pause Random Planning"
        The_Agent().plan()

def fix():
    "todo"

#Clears the data the agent has learnt.
def clear_data():
    "todo"

def print_state():
    print("=======CURRENT STATE OF WORLD=======")
    qual_state = The_Agent().controller().get_current_state()
    for fact in qual_state.get_qualitative_facts() + qual_state.facts_for_place(((qual_state.hand_quant_x(), qual_state.hand_quant_y()), "Current")):
        print(fact)
    print("====================================")

#Saves the data the agent has learnt
def save():
    if not Shared.currently_planning and not Shared.currently_learning:
        save_file = asksaveasfile()
        File_Writer.FileWriter().save_learnt_data(save_file.name)

def load():
    if not Shared.currently_planning and not Shared.currently_learning:
        load_file = askopenfile()
        File_Writer.FileWriter().load_learnt_data(load_file.name)

def sim_reset():
    if not Shared.currently_planning and not Shared.currently_learning:
        The_Agent().controller().reset()
        reset_vis()

def knowledge_file():
    if not Shared.currently_planning and not Shared.currently_learning:
        The_Agent().make_knowledge_file()

#Decreate the frequency that the states are redrawn (probably not very accurate)
def slow_down():
    time_delay += TIME_DELAY_CHANGE
    if time_delay > MAX_TIME_DELAY:
        time_delay = MAX_TIME_DELAY

#Increase the frequency that the states are redrawn (probably not very accurate)
def speed_up():
    time_delay -= TIME_DELAY_CHANGE
    if time_delay < MIN_TIME_DELAY:
        time_delay = MIN_TIME_DELAY

#Disables/ enables the visualisation. Data collection may be significantly faster with this feature disabled
def disable_vis(vis_button):
    global canvas
    if Shared.visualisation_enabled:
        Shared.visualisation_enabled = False
        vis_button["text"] = "Enable Vis"
        Shared.examples_to_display = Queue() #Clear the backlog
    else:
        Shared.visualisation_enabled = True
        reset_vis()
        vis_button["text"] = "Disable Vis"

def reset_vis():
    canvas.delete(ALL)
    canvas.create_line(X(Shared.LEFT_WALL), Y(Shared.FAR_WALL), X(Shared.RIGHT_WALL), Y(Shared.FAR_WALL))
    canvas.create_line(X(Shared.LEFT_WALL), Y(Shared.NEAR_WALL), X(Shared.RIGHT_WALL), Y(Shared.NEAR_WALL))
    canvas.create_line(X(Shared.LEFT_WALL), Y(Shared.FAR_WALL), X(Shared.LEFT_WALL), Y(Shared.NEAR_WALL))
    canvas.create_line(X(Shared.RIGHT_WALL), Y(Shared.FAR_WALL), X(Shared.RIGHT_WALL), Y(Shared.NEAR_WALL))
    cur_state = The_Agent().controller().get_current_state().get_quantitative_state()
    Shared.currently_drawing.acquire()
    Shared.drawing_queue.put(cur_state)
    Shared.currently_drawing.release()

#Unfortunately this isn't going to stop it from doing the learning if it is still doing that.
#Might just want to kill the thread instead.
def exit_window():
    Shared.playing = False
    Shared.visualisation_enabled = False
    Shared.currently_drawing.acquire()
    Shared.currently_drawing.notify()
    Shared.currently_drawing.release()
    File_Writer.FileWriter().close_all_log_files()
    window.destroy()

#We only want to plan if we are not currently learning, otherwise the data structure could become corrupted.
def make_plan(text_widget):
    if not Shared.currently_planning and not Shared.currently_learning  and not Shared.showing_example:
        #Shared.currently_planning = True
        text = text_widget.get(1.0, END) #What should the parameters be?
        goals = extract_effects(text)
        The_Agent().plan_for_goals(goals)

def hand_at_plan():
    goal = Fact("+hand_at", [(74, 65)])
    The_Agent().plan_for_goals([goal])

def test_constraints(text_widget):
    if not Shared.currently_planning and not Shared.currently_learning and not Shared.showing_example:
        #Shared.currently_planning = True
        text = text_widget.get(1.0, END) #What should the parameters be?
        constraints = extract_effects(text)
        The_Agent().find_place(constraints)

def show_next_example():
    if not Shared.currently_planning and not Shared.currently_learning and not Shared.showing_example:
        The_Agent().show_next_example()

def manual_grasp():
    if not Shared.currently_planning and not Shared.currently_learning  and not Shared.showing_example:
        The_Agent().controller().do_grasp_action()

def manual_ungrasp():
    if not Shared.currently_planning and not Shared.currently_learning  and not Shared.showing_example:
        The_Agent().controller().do_ungrasp_action()

def manual_hit_random():
    if not Shared.currently_planning and not Shared.currently_learning  and not Shared.showing_example:
        The_Agent().controller().do_hit_action_on_random()

def manual_move_random():
    if not Shared.currently_planning and not Shared.currently_learning  and not Shared.showing_example:
        The_Agent().controller().do_move_action_on_random()

def manual_hit_target(target):
    if not Shared.currently_planning and not Shared.currently_learning  and not Shared.showing_example:
        The_Agent().controller().do_hit_action_on_target(target)

def manual_move_target(target):
    if not Shared.currently_planning and not Shared.currently_learning  and not Shared.showing_example:
        The_Agent().controller().do_move_action_on_target(target)

def manual_move_place(place):
    if not Shared.currently_planning and not Shared.currently_learning  and not Shared.showing_example:
        x, y = [int(num) for num in place.split(',')]
        The_Agent().controller().do_move_to_place((x, y))

def print_object_names():
    global data_box
    data_box.delete(1.0, END)
    objs = The_Agent().controller().objects_currently_in_world()
    data_box.insert(END, "***Objects in the world*** \n")
    for obj in objs:
        data_box.insert(END, obj + "\n")

####################################################################################################
### PLAN INFO READING
####################################################################################################
def extract_effects(text):
    list_of_effects = text.split('\n')
    effect_objects = []
    for effect in list_of_effects:
        if effect != "": #Not the best way of solving the bug, but a quick hack for now...
            effect_objects.append(Fact.make_fact_from_string(effect))
    return effect_objects
####################################################################################################
### VISUALISATION EVENTS
####################################################################################################
#Is there currently a state to be drawn?
#States are put in SharedData.drawing_queue by the learner, and polled by the GUI when they are drawn.
def check_for_state_to_draw():
    if not Shared.drawing_queue.empty():
        state = Shared.drawing_queue.get()
        display_next_state(state)
        #Tell the simulation to stop waiting now.
        #The way this has been done may be able to cause a deadlock, need to double check it
        Shared.currently_drawing.acquire()
        Shared.currently_drawing.notify()
        Shared.currently_drawing.release()
    window.after(time_delay, check_for_state_to_draw) #Reregister with mainloop

def check_for_example_to_display():
    if not Shared.examples_to_display.empty():
        example = Shared.examples_to_display.get()
        print_example_to_box(example)
    window.after(500, check_for_example_to_display)

####################################################################################################
### DISPLAYING THE CURRENT STATE
####################################################################################################

def print_example_to_box(example):
    global data_box
    data_box.delete(1.0, END)
    if isinstance(example, list):
        data_box.insert(END, " ".join([str(x) for x in example]))
        return
    data_box.insert(END, example.intention_param_string() + "\n\n")
    for i in range(0, len(example.sorted_initial_strings()), 2):
        string_1 = example.sorted_initial_strings()[i]
        if i + 1 < len(example.sorted_initial_strings()):
            string_2 = example.sorted_initial_strings()[i+1]
        else:
            string_2 = ""
        data_box.insert(END, "%-50s %s\n" % (string_1, string_2))
    data_box.insert(END, "\n")
    for i in range(0, len(example.sorted_effect_strings()), 2):
        string_1 = example.sorted_effect_strings()[i]
        if i + 1 < len(example.sorted_effect_strings()):
            string_2 = example.sorted_effect_strings()[i+1]
        else:
            string_2 = ""
        data_box.insert(END, "%-50s %s\n" % (string_1, string_2))

#Draws the state specified by state_snap_shot
def display_next_state(state_snap_shot):
    #data_box.delete(1.0, END)
    #__display_quantitative_in_box(state_snap_shot)
    update_hand_sprite(state_snap_shot)
    for obj_name in state_snap_shot.objects:
        update_object_sprite(state_snap_shot.objects[obj_name])
    display_target_position(state_snap_shot)
    canvas.update()
    #update_data_box(state_snap_shot)

def update_hand_sprite(state):
    finger_rad = Shared.HAND_RAD * (3-state.finger_pos)/4
    (hand_tlx, hand_tly, hand_brx, hand_bry) = circle_coordinates((state.x, state.y), Shared.HAND_RAD)
    (finger_tlx, finger_tly, finger_brx, finger_bry) = circle_coordinates((state.x, state.y), finger_rad)
    if not canvas.coords("hand"): #The hand has not been drawn before
        canvas.create_oval(hand_tlx, hand_tly, hand_brx, hand_bry, tags="hand")
        canvas.create_oval(finger_tlx, finger_tly, finger_brx, finger_bry, fill=HAND_COLOR,tags="fingers")
    else: #Need to update the current hand position
        (previous_hand_tlx, previous_hand_tly, _, _) = canvas.coords("hand")
        canvas.move("hand", hand_tlx - previous_hand_tlx, hand_tly - previous_hand_tly)
        canvas.delete("fingers") # Can't resize an existing object. Will refactor this if too slow
        canvas.create_oval(finger_tlx, finger_tly, finger_brx, finger_bry, fill=HAND_COLOR,tags="fingers")

#As long as the object is actually on the table, update its sprite
def update_object_sprite(obj_state):
    if not obj_state.on_table:
        if canvas.coords(obj_state.name): #If it is drawn still..
            canvas.delete(obj_state.name)#We want to remove it from the graphics pane
    else:
        (obj_tlx, obj_tly, obj_brx, obj_bry) = circle_coordinates((obj_state.x, obj_state.y), Shared.OBJ_RAD)
        name_of_obj = obj_state.name
        if not canvas.coords(name_of_obj): #This object is not currently drawn
            canvas.create_oval(obj_tlx, obj_tly, obj_brx, obj_bry, tags=name_of_obj, fill=obj_state.colour)
        else: #Move the existing sprite
            (previous_obj_tlx, previous_obj_tly, _, _) = canvas.coords(name_of_obj)
            canvas.move(name_of_obj, obj_tlx - previous_obj_tlx, obj_tly - previous_obj_tly)


def display_target_position(state):
    #Best to just redraw it each time
    if canvas.coords("intent"):
        canvas.delete("intent")
    if state.cur_target_x and state.cur_target_y:
        (tlx, tly, brx, bry) = circle_coordinates((state.cur_target_x, state.cur_target_y), 1)
        canvas.create_oval(tlx, tly, brx, bry, fill="red", tags="intent")
    if canvas.coords("init"):
        canvas.delete("init")
    if state.start_x and state.start_y:
        (tlx, tly, brx, bry) = circle_coordinates((state.start_x, state.start_y), 1)
        canvas.create_oval(tlx, tly, brx, bry, fill="blue", tags="init")
    if canvas.coords("final"):
        canvas.delete("final")
    if state.final_x and state.final_y:
        (tlx, tly, brx, bry) = circle_coordinates((state.final_x, state.final_y), 1)
        canvas.create_oval(tlx, tly, brx, bry, fill="green", tags="final")

####################################################################################################
### CONVERSION FUNCTIONS
####################################################################################################

#Convert the given internal x value into the correspon/ding graphical x value/
def X(x):
    return (x - Shared.LEFT_WALL) * MAGNIFICATION_FACTOR

#Convert the given internal y value into the corresponding graphical y value
def Y(y):
    return (Shared.FAR_WALL - y) * MAGNIFICATION_FACTOR

#Get the coordinates for drawing a circle that has been specified by its centre and radius
def circle_coordinates(centre, radius):
    (centre_x, centre_y) = centre
    tlx = get_graphics_circle_top_left_x(centre_x, radius)
    tly = get_graphics_circle_top_left_y(centre_y, radius)
    brx = get_graphics_circle_bottom_right_x(centre_x, radius)
    bry = get_graphics_circle_bottom_right_y(centre_y, radius)
    return (tlx, tly, brx, bry)

def get_graphics_circle_top_left_x(centre_x, radius):
    actual_centre_x = centre_x - Shared.LEFT_WALL
    return (actual_centre_x - radius) * MAGNIFICATION_FACTOR

def get_graphics_circle_top_left_y(centre_y, radius):
    actual_centre_y = Shared.FAR_WALL - centre_y
    return (actual_centre_y - radius) * MAGNIFICATION_FACTOR

def get_graphics_circle_bottom_right_x(centre_x, radius):
    actual_centre_x = centre_x - Shared.LEFT_WALL
    return (actual_centre_x + radius)* MAGNIFICATION_FACTOR

def get_graphics_circle_bottom_right_y(centre_y, radius):
    actual_centre_y = Shared.FAR_WALL - centre_y
    return (actual_centre_y + radius)*MAGNIFICATION_FACTOR
