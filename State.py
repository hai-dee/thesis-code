from copy import deepcopy

# Contains all the data the agent requires to draw on the GUI the info about a state (including the data box)

class State:

   def __init__(self):
      self.x = None
      self.y = None
      self.vx = None
      self.vy = None
      self.ax = None
      self.ay = None
      self.fx = None
      self.fy = None
      self.touch = None
      self.grip = None
      self.sound = None
      self.finger_pos = None
      self.finger_vel = None
      self.finger_force = None
      self.cur_action = None
      self.cur_target = None
      self.cur_target_x = None
      self.cur_target_y = None

   #Adds data about the hand, just puts it directly into the State_To_Draw object
   def add_hand_data(self, x, y, vx, vy, ax, ay, fx, fy, touch, grip, sound, finger_pos, finger_vel, finger_force, cur_action, cur_target, cur_target_x, cur_target_y, start_x, start_y, final_x, final_y):
      self.x = x
      self.y = y
      self.vx = vx
      self.vy = vy
      self.ax = ax
      self.ay = ay
      self.fx = fx
      self.fy = fy
      self.touch = touch
      self.grip = grip
      self.sound = sound
      self.finger_pos = finger_pos
      self.finger_vel = finger_vel
      self.finger_force = finger_force
      self.cur_action = cur_action
      self.cur_target =cur_target
      self.cur_target_x = cur_target_x
      self.cur_target_y = cur_target_y
      self.objects = {}
      self.start_x = start_x
      self.start_y = start_y
      self.final_x = final_x
      self.final_y = final_y

   def add_object_data(self, obj):
      obj_state = Obj_State(obj.name, obj.colour, obj.x, obj.y, obj.vx, obj.vy, obj.is_grasped, obj.on_table())
      self.objects[obj_state.name] = obj_state


class Obj_State:

   def __init__(self, name, colour, x, y, vx, vy, grasped, on_table):
      self.name = name
      self.colour = colour
      self.x = x
      self.y = y
      self.vx = vx
      self.vy = vy
      self.grasped = grasped
      self.on_table = on_table
