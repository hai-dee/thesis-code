from collections import Counter
from random import choice
from math import *
from SharedData import * #Just easier than having to modify the code very much

#A collection of functions that allow the agent to carry out simple visual tasks in the world

######################################################################################################
######################################################################################################
### PUBLIC INTERFACE
######################################################################################################
######################################################################################################


#Is the given fact satisfied in quant state?
def constraint_satisfied(constraint, quant_state):
    #Do some initial processing
    predicate = constraint.get_predicate()
    parameters = constraint.get_parameters()
    if len(parameters) > 1:
        second_type = parameters[1].param_type()
    if len(parameters) > 2:
        third_type = parameters[2].param_type()
    #Now, check what test we need to use and carry out the test
    if predicate == "hand_at" or predicate == "+hand_at":
        (actual_x, actual_y) = (quant_state.x, quant_state.y)
        (expected_x, expected_y) = constraint.get_parameters()[0].value()
        return abs(actual_x - expected_x) <= 2 and abs(actual_y - expected_y) <= 2
    elif predicate == "place_touching" or predicate == "+place_touching":
        parameters = constraint.get_parameters()
        if second_type == "o":
            return place_touching_obj(parameters[0].identifier(), quant_state.objects[parameters[1].identifier()])
        elif second_type == "s" or second_type == "w":
            return place_touching_wall(parameters[0].identifier(), parameters[1].identifier())
    elif predicate == "place_near" or predicate == "+place_near":
        parameters = constraint.get_parameters()
        if second_type == "o":
            return place_near_obj(parameters[0].identifier(), quant_state.objects[parameters[1].identifier()])
        elif second_type == "s" or second_type == "w":
            return place_near_wall(parameters[0].identifier(), parameters[1].identifier())
    elif predicate == "place_behind" or predicate == "+place_behind":
        if second_type == "o" and third_type == "o":
            return "Not Implemented"
        elif second_type == "o" and (third_type == "w" or third_type == "s"):
            return place_obj_wall_aligned(parameters[0].identifier(), quant_state.objects[parameters[1].identifier()], parameters[2].identifier())
    elif predicate == "clear_path" or predicate == "+clear_path":
        return True
        #if bound_place: #If there isn't an unbound place then there's actually no reason to care whether or not the constraint is satisfied as the information is never used
    else:
        return True
    print(str(constraint) + "has an unrecognised predicate so could not be evaluated with the current hand place")

def get_random_touching_wall(quant_state):
    points = set()
    for wall in walls: #walls is defined in SharedData
        points.update(get_wall_touch_solutions((wall,)))
    points = [point for point in points if is_reachable(quant_state, point)]
    return choice(list(points))

def get_random_place_touching_object(quant_state):
    #Pick a random object that is on the table
    random_obj = choice([obj for obj in quant_state.objects.values() if obj.on_table])
    points = [point for point in get_obj_touch_solutions((random_obj,)) if is_reachable(quant_state, point)]
    if points:
        return choice(points) #Pick one
    else:
        return None

def get_random_place(quant_state):
    while True:
        x = choice(range(round(LEFT_WALL), round(RIGHT_WALL)))
        y = choice(range(round(NEAR_WALL), round(FAR_WALL)))
        if is_reachable(quant_state, (x, y)):
            return (x,y)

def get_point_for_constraints(constraints, updated_bindings, quant_state):
    #Need to go through every constraint, and call the appropriate methods
    integer_solutions = Counter()
    for constraint in constraints:
        print("Dealing with constraint", constraint)
        constraint = constraint.get_specific_copy_with_dictionary(updated_bindings)
        predicate = constraint.get_predicate()
        parameters = constraint.get_parameters()
        second_type = parameters[1].param_type()
        if len(parameters) > 2:
            third_type = parameters[2].param_type()
        #And also, convert the parameters into a tuple of parameters for the constraint solution finders
        constraint_params = []
        for param in parameters[1:]:
            if param.param_type() == "o":
                name = param.identifier()
                obj = quant_state.objects[name]
                constraint_params.append(obj)
            else:
                constraint_params.append(param.identifier())
        constraint_params = tuple(constraint_params)
        if predicate == "place_touching" or predicate == "+place_touching":
            #What are the parameter types?
            parameters = constraint.get_parameters()
            if second_type == "o":
                integer_solutions.update(get_obj_touch_solutions(constraint_params))
            elif second_type == "s" or second_type == "w":
                ints = get_wall_touch_solutions(constraint_params)
                integer_solutions.update(ints)
        elif predicate == "place_behind" or predicate == "+place_behind":
            if second_type == "o" and third_type == "o":
                integer_solutions.update(get_obj_obj_align_solutions(constraint_params))
            elif second_type == "o" and (third_type == "w" or third_type == "s"):
                integer_solutions.update(get_obj_wall_align_solutions(constraint_params))
        elif predicate == "clear_path" or predicate == "+clear_path":
            val = None
            if parameters[0].is_var() and parameters[1].is_value():
                val = parameters[1]
                other = parameters[0]
            elif parameters[0].is_value() and parameters[1].is_var():
                val = parameters[0]
                other = parameters[1]
            else:
                print("infinite solutions, not bothering...")
                continue
            #val = tuple([x.strip() for x in val.value()[1:-1].split(",")])
            integer_solutions.update(get_clear_path_solutions(val.value(), quant_state))
        elif predicate == "behind_drop" or predicate == "+behind_drop":
            "NEED TO REIMPLEMENT"
            #constraint_params = tuple(list(constraint_params).append("right_wall"))
            #integer_solutions.update(get_obj_wall_align_solutions(constraint_params))
    #Remove any points that are unreachable
    for place in integer_solutions:
        if not is_reachable(quant_state, place): #Is the place covered in the given state?
            integer_solutions[place] = 0 #safer than deleting
    #Now that we have the counts, we need to pick a random point that is good and return it
    if integer_solutions == Counter():
        print("No solutions exist?")
        return None
    [(_, max_count)] = integer_solutions.most_common(1)
    print("The max constraints I can satisfy is " + str(max_count))
    if max_count > 0:
        best_places = [place for place in integer_solutions if integer_solutions[place] == max_count]
        chosen = choice(best_places)
        return chosen
    else:
        return None

#are the given place, obj, wall aligned?
#This code can be used for
# - Checking place-obj-wall alignment
# - Checking hand-obj-wall alignment
def place_obj_wall_aligned(place, obj, wall):
    if wall == "left_wall":
        if obj.x > place[0]: #The centre of the object is further to the right of the center of the hand
            return False
        else:
            m, c = line_formula(place[0], place[1], obj.x, obj.y)
            x = LEFT_WALL
            y = m*x+c
            return ((y >= NEAR_WALL + OBJ_RAD) and (y <= FAR_WALL - OBJ_RAD))
    elif wall == "right_wall":
        if obj.x < place[0]:
            return False
        else:
            m, c = line_formula(place[0], place[1], obj.x, obj.y)
            x = RIGHT_WALL
            y = m*x+c
            return ((y >= NEAR_WALL + OBJ_RAD) and (y <= FAR_WALL - OBJ_RAD))
    elif wall == "near_wall":
        if obj.y > place[1]:
            return False
        else:
            if obj.x == place[0]:#Cause checking the vertical case will kill it
                return True
            else:
                m, c = line_formula(place[0], place[1], obj.x, obj.y)
                y = NEAR_WALL
                x = (y-c)/m
                return x-OBJ_RAD >= LEFT_WALL and x + OBJ_RAD <= RIGHT_WALL
    elif wall == "far_wall":
        if obj.y < place[1]:
            return False
        else:
            if obj.x == place[0]:#Cause checking the vertical case will kill it
                return True
            else:
                m, c = line_formula(place[0], place[1], obj.x, obj.y)
                y = FAR_WALL
                x = (y-c)/m
                return x-OBJ_RAD >= LEFT_WALL and x + OBJ_RAD <= RIGHT_WALL

##are the given place, obj1, and obj2 aligned?
#def place_obj_obj_aligned(place, obj1, obj2):
    ##Firstly, is obj1 in between place and obj2 in both dimensions?
    #if not (sorted(place[0], obj1.x, obj2.x) and sorted(place[1], obj1.y, obj2.y)):
        #return False
    ##Now, are they on the same line?
    #if round(place[0]) == round(obj1.x) == round(ob2.x): #more or less vertically aligned

    #elif round(place[0]) == round(obj1.x) == round(ob2.x): #more or less horizontally aligned

    #else:



#For this, I have taken an approach where I see whether or not any of the circle circumference is inside the rounding box
#of the grid point. This box goes from x+/-0.5 and y+/-0.5. An easy way of determining this is checking if the circle
#intersects with any of the sides of the box.
#Circles always have up to 2 solutions for any given x/y (a positive and a negative solution)
#------------------
#This code can be used for
# - Checking whether a place touches an object
# - Checking whether the hand touches an object
def place_touching_obj(place, obj):
    max_r = OBJ_RAD + HAND_RAD +1 #Radius of the circle
    min_r = OBJ_RAD + HAND_RAD -1
    (px,py) = place #x and y coordinates for the point we are checking
    dist = hypot(px-obj.x, py-obj.y)

    return dist <= max_r and dist >= min_r

#This code is very much like the above, except it has a larger tolerance
def place_near_obj(place, obj):
    max_r = OBJ_RAD + HAND_RAD +3 #Radius of the circle
    min_r = OBJ_RAD + HAND_RAD -3
    (px,py) = place #x and y coordinates for the point we are checking
    dist = hypot(px-obj.x, py-obj.y)

    return dist <= max_r and dist >= min_r




#This code can be used for:
# - Checking whether a place touches a wall
# - Checking whtether the hand touches a wall
def place_touching_wall(place, wall):
    if wall == "left_wall":
        return place[0] - HAND_RAD <= LEFT_WALL + TOUCH_ERROR
    elif wall == "right_wall":
        return place[0] + HAND_RAD >= RIGHT_WALL - TOUCH_ERROR
    elif wall == "near_wall":
        return place[1] - HAND_RAD <= NEAR_WALL + TOUCH_ERROR
    elif wall == "far_wall":
        return place[1] + HAND_RAD >= FAR_WALL - TOUCH_ERROR

def place_near_wall(place, wall):
    if wall == "left_wall":
        return place[0] - HAND_RAD <= LEFT_WALL + 2
    elif wall == "right_wall":
        return place[0] + HAND_RAD >= RIGHT_WALL - 2
    elif wall == "near_wall":
        return place[1] - HAND_RAD <= NEAR_WALL + 2
    elif wall == "far_wall":
        return place[1] + HAND_RAD >= FAR_WALL - 2


def obj_touching_wall(obj, wall):
    if wall == "left_wall":
        return obj.x - OBJ_RAD <= LEFT_WALL + TOUCH_ERROR
    elif wall == "right_wall":
        return obj.x + OBJ_RAD >= RIGHT_WALL - TOUCH_ERROR
    elif wall == "near_wall":
        return obj.y - OBJ_RAD <= NEAR_WALL + TOUCH_ERROR
    elif wall == "far_wall":
        return obj.y + OBJ_RAD >= FAR_WALL - TOUCH_ERROR

def obj_touching_obj(obj, obj2):
    dist = hypot(obj.x - obj2.x, obj.y - obj2.y)
    touch_dist = OBJ_RAD * 2
    return dist > touch_dist - TOUCH_ERROR and dist < touch_dist + TOUCH_ERROR

######################################################################################################
### FINDING SOLUTIONS FOR THE GIVEN CONSTRAINT
######################################################################################################

def get_clear_path_solutions(given_point, quant_state):
    unrounded_places = set()
    for row in range(int(LEFT_WALL), int(RIGHT_WALL)):
        for col in range(int(NEAR_WALL), int(FAR_WALL)):
            if is_reachable(quant_state, (row, col)) and clear_path_exists(given_point, (row, col), quant_state):
                unrounded_places.add((row, col))
    integer_solutions = list(set([(round(x), round(y)) for (x, y) in unrounded_places]))
    return integer_solutions


def get_obj_obj_align_solutions(constraint):
    (obj1, obj2) = constraint
    x1 = obj1.x
    y1 = obj1.y
    x2 = obj2.x
    y2 = obj2.y
    if x1 == x2: #This must be a vertical line
        if y1 < y2: #The first object is below the second one
            max_y = y1 - (OBJ_RAD + HAND_RAD)
            min_y = NEAR_WALL + HAND_RAD
        else: #The first object is above the second
            max_y = FAR_WALL - HAND_RAD
            min_y = y1 + OBJ_RAD + HAND_RAD
        y_points = [min_y] + [y for y in range(ceil(min_y), floor(max_y) + 1)] + [max_y]
        unrounded_places =  set([(x1, y) for y in y_points])
    elif y1 == y2: #This must be a horizontal line
        if x1 < x2: #The first object is to the left of the second object
            max_x = x1-(OBJ_RAD+HAND_RAD)
            min_x = LEFT_WALL+HAND_RAD
        else: #The first object is to the right of the second object
            max_x = RIGHT_WALL-HAND_RAD
            min_x = x1 +(OBJ_RAD+HAND_RAD)
        x_points = [min_x] + [x for x in range(ceil(min_x), floor(max_x) + 1)] + [max_x]
        unrounded_places = set([(x, y1) for x in x_points])
    else: #Now the more standard case where we use the line formula
        (m, c) = line_formula(x1, y1, x2, y2)
        dx = abs((HAND_RAD+OBJ_RAD)/sqrt(1 + m**2))
        dy = abs(m*dx)
        #Need to work out min_x, max_x, min_y, and max_y
        if x1 < x2: #first object is left of second object
            x_starting_point = x1 - dx
            x_increment = -1 #We need to go down in the x direction
        else:
            x_starting_point = x1 + dx
            x_increment = +1#We need to go up in the x direction
        if y1 < y2: #first object is below the second object
            y_starting_point = y1 - dy
            y_increment = -1
        else:
            y_starting_point = y1 + dy
            y_increment = +1

        unrounded_places = set()

        #Find all the valid integer points using x
        unrounded_places.add((x_starting_point, m*x_starting_point+c))#Deal with the border case
        if x_increment == 1: #if the increment is 1, the starting point should be ceiled
            x = ceil(x_starting_point)
        else:
            x = floor(x_starting_point)
        while x >= LEFT_WALL + HAND_RAD and x <= RIGHT_WALL - HAND_RAD:
            y = m*x+c
            if y >= NEAR_WALL + HAND_RAD and y <= FAR_WALL - HAND_RAD: #If y is within the constraints
                unrounded_places.add((x, y))
                x += x_increment
            else:
                break
        unrounded_places.add(((y_starting_point-c)/m, y_starting_point))
        if y_increment == 1: #if the increment is 1, the starting point should be ceiled
            y = ceil(y_starting_point)
        else:
            y = floor(y_starting_point)
        #Find all the valid integer points using y
        while y >= NEAR_WALL + HAND_RAD and y <= FAR_WALL - HAND_RAD:
            x = (y-c)/m
            if x >= LEFT_WALL + HAND_RAD and x <= RIGHT_WALL - HAND_RAD:
                unrounded_places.add((x,y))
                y += y_increment
            else:
                break
    integer_solutions = list(set([(round(x), round(y)) for (x, y) in unrounded_places]))
    return integer_solutions


def get_obj_wall_align_solutions(constraint):
    obj, wall_name = constraint
    if wall_name == "left_wall":
        polygon = polygon_for_left_wall(obj)
    elif wall_name == "right_wall":
        polygon = polygon_for_right_wall(obj)
    elif wall_name == "near_wall":
        polygon = polygon_for_near_wall(obj)
    elif wall_name == "far_wall":
        polygon = polygon_for_far_wall(obj)
    if len(polygon) <= 2:
        integer_solutions = get_points_on_line(polygon)
    else:
        integer_solutions = get_points_inside_polygon(polygon)
    return integer_solutions


def get_obj_touch_solutions(constraint):
    (obj,) = constraint #unpack it
    xc = obj.x
    yc = obj.y
    r = OBJ_RAD + HAND_RAD #The circle we are calculating has a combined radius
    integer_solutions = set()
    #The default range can't do what we want, i.e. get the edge cases + measurements at roughly every 1 unit in between them.
    min_x = xc - r
    max_x = xc + r
    min_y = yc - r
    max_y = yc + r
    x_values_to_check = set([min_x] + [x for x in range(ceil(min_x), floor(max_x)+1)] + [max_x])
    y_values_to_check = set([min_y] + [y for y in range(ceil(min_y), floor(max_y)+1)] + [max_y])
    for x in x_values_to_check:
        unsigned_height = sqrt(max(0, (r**2 - (xc -x)**2)))
        pos_y = yc+unsigned_height
        neg_y = yc-unsigned_height
        integer_solutions.add((round(x), round(pos_y)))
        integer_solutions.add((round(x), round(neg_y)))
    for y in y_values_to_check:
        unsigned_height = sqrt(max(0, (r**2 - (yc -y)**2))) #hack!
        pos_x = xc+unsigned_height
        neg_x = xc-unsigned_height
        integer_solutions.add((round(pos_x), round(y)))
        integer_solutions.add((round(neg_x), round(y)))
    return integer_solutions
    #for y in y_values_to_check

#I decided it was not worth trying to collapse this piece of code down as it is hardcoding 4 walls either way. Yay for copy paste
#I suspect that it could be written as a single line in python, as nesting the x and y loops would work, and conditionals mixed in....
def get_wall_touch_solutions(wall_name):
    (wall_name,) = wall_name #unpack
    if wall_name == "left_wall":
        x = round(LEFT_WALL + HAND_RAD)
        min_y = round(NEAR_WALL + HAND_RAD)
        max_y = round(FAR_WALL - HAND_RAD)
        return set([(x, y) for y in range(min_y, max_y+1)])
    elif wall_name == "right_wall":
        x = round(RIGHT_WALL - HAND_RAD)
        min_y = round(NEAR_WALL + HAND_RAD)
        max_y = round(FAR_WALL - HAND_RAD)
        return set([(x, y) for y in range(min_y, max_y+1)])
    elif wall_name == "near_wall":
        y = round(NEAR_WALL + HAND_RAD)
        min_x = round(LEFT_WALL + HAND_RAD)
        max_x = round(RIGHT_WALL - HAND_RAD)
        return set([(x, y) for x in range(min_x, max_x+1)])
    elif wall_name == "far_wall":
        y = round(FAR_WALL - HAND_RAD)
        min_x = round(LEFT_WALL + HAND_RAD)
        max_x = round(RIGHT_WALL - HAND_RAD)
        return set([(x, y) for x in range(min_x, max_x+1)])

def get_points_on_line(line):
    if len(line) == 0:
        return set()
    elif len(line) == 1:
        integer_solutions = set()
        [p1] = line
        integer_solutions.add((round(p1[0]), round(p1[0])))
        return integer_solutions
    elif len(line) == 2 and line[0][0] == line[1][0]: #Vertical line
        [p1, p2] = line
        x = round(p1[0])
        max_y = round(max(p1[1], p2[1]))
        min_y = round(min(p1[1], p2[1]))
        return set([(x, y) for y in range(min_y, max_y+1)])
    elif len(line) == 2 and line[0][1] == line[1][1]: #Horizontal line
        [p1, p2] = line
        y = round(p1[1])
        max_x = round(max(p1[0], p2[0]))
        min_x = round(min(p1[0], p2[0]))
        return set([(x, y) for x in range(min_x, max_x+1)])
    else:
        raise ValueError

####################################################################################################
## CODE FOR DETERMINING WHETHER OR NOT IT IS POSSIBLE FOR THE HAND TO BE ON A POINT
####################################################################################################

def polygon_for_right_wall(obj):
    obj_x = obj.x
    obj_y = obj.y
    polygon_points = [] #Clear the polygon points
    if obj.y-NEAR_WALL < HAND_RAD or FAR_WALL-obj.y < HAND_RAD:
        max_x = obj.x - (HAND_RAD+OBJ_RAD)
        min_x = LEFT_WALL - HAND_RAD
        if obj.y-NEAR_WALL < HAND_RAD:
            y = NEAR_WALL+HAND_RAD
        elif FAR_WALL-obj.y < HAND_RAD:
            y = FAR_WALL-HAND_RAD
        if min_x <= max_x: #Empty list will be returned if this fails
            polygon_points.append((max_x, y))
            polygon_points.append((min_x, y))
    else:
        polygon_points.append((obj_x, obj_y)) #First point to include in polygon

        #What are the formulas for the 2 lines that define the alignment area?
        m1, c1 = line_formula(obj_x, obj_y, RIGHT_WALL, FAR_WALL - OBJ_RAD)
        m2, c2, = line_formula(obj_x, obj_y, RIGHT_WALL, NEAR_WALL + OBJ_RAD)

        #Where does the first line intersect with the walls?
        #First check if it intersects with the near wall
        near_y1 = NEAR_WALL + HAND_RAD
        near_x1 = (near_y1 - c1)/m1
        if near_x1 >= LEFT_WALL + HAND_RAD:
            polygon_points.append((near_x1, near_y1))
            polygon_points.append((LEFT_WALL + HAND_RAD, NEAR_WALL + HAND_RAD)) #The bottom left corner
        else: #It must intersect with the left wall
            left_x1 = LEFT_WALL + HAND_RAD
            left_y1 = m1*left_x1+c1
            if left_y1 >= NEAR_WALL + HAND_RAD: #Is this point within the near wall?
                polygon_points.append((LEFT_WALL + HAND_RAD, left_y1))
        #Where does the second line intersect with the walls?
        #First check if it intersects with the far wall
        far_y2 = FAR_WALL - HAND_RAD
        far_x2 = (far_y2 - c2)/m2
        if far_x2 >= LEFT_WALL:
            polygon_points.append((LEFT_WALL + HAND_RAD, FAR_WALL - HAND_RAD)) #Because going clockwise, this point is first
            polygon_points.append((far_x2, far_y2))
        else:
            left_x2 = LEFT_WALL + HAND_RAD
            left_y2 = m2*left_x2+c2
            if left_y2 <= FAR_WALL - HAND_RAD:
                polygon_points.append((LEFT_WALL + HAND_RAD, left_y2))
    return polygon_points

def polygon_for_left_wall(obj):
    obj_x = obj.x
    obj_y = obj.y
    polygon_points = []
    if obj.y-NEAR_WALL < HAND_RAD or FAR_WALL-obj.y < HAND_RAD:
        max_x = RIGHT_WALL - HAND_RAD
        min_x = obj.x + (OBJ_RAD+HAND_RAD)
        if obj.y-NEAR_WALL < HAND_RAD:
            y = NEAR_WALL+HAND_RAD
        elif FAR_WALL-obj.y < HAND_RAD:
            y = FAR_WALL-HAND_RAD
        if min_x <= max_x: #Empty list will be returned if this fails
            polygon_points.append((max_x, y))
            polygon_points.append((min_x, y))
    else:
        polygon_points.append((obj_x, obj_y)) #First point to include in polygon

        #What are the formulas for the 2 lines that define the alignment area?
        m1, c1 = line_formula(obj_x, obj_y, LEFT_WALL, FAR_WALL - OBJ_RAD)
        m2, c2, = line_formula(obj_x, obj_y, LEFT_WALL, NEAR_WALL + OBJ_RAD)

        #Where does the first line intersect with the walls?
        #First check if it intersects with the near wall
        near_y1 = NEAR_WALL + HAND_RAD
        near_x1 = (near_y1 - c1)/m1
        if near_x1 <= RIGHT_WALL - HAND_RAD:
            polygon_points.append((near_x1, near_y1))
            polygon_points.append((RIGHT_WALL - HAND_RAD, NEAR_WALL + HAND_RAD)) #The bottom right corner
        else: #It must intersect with the right wall
            right_x1 = RIGHT_WALL - HAND_RAD
            right_y1 = m1*right_x1+c1
            if right_y1 >= NEAR_WALL + HAND_RAD: #Is this point within the near wall? #POTENTIAL BUG HERE
                polygon_points.append((RIGHT_WALL-HAND_RAD, right_y1))
        #Where does the second line intersect with the walls?
        #First check if it intersects with the far wall
        far_y2 = FAR_WALL - HAND_RAD
        far_x2 = (far_y2 - c2)/m2
        if far_x2 <= RIGHT_WALL - HAND_RAD:
            polygon_points.append((RIGHT_WALL - HAND_RAD, FAR_WALL - HAND_RAD)) #Because going clockwise, this point is first
            polygon_points.append((far_x2, far_y2))
        else:
            right_x2 = RIGHT_WALL - HAND_RAD
            right_y2 = m2*right_x2+c2
            if right_y2 <= FAR_WALL - HAND_RAD:
                polygon_points.append((RIGHT_WALL - HAND_RAD, right_y2))
    return polygon_points

def polygon_for_far_wall(obj):
    polygon_points = []
    #TODO: THE VERTICAL CASEs
    if obj.x-LEFT_WALL < HAND_RAD or RIGHT_WALL-obj.x < HAND_RAD:
        max_y = obj.y - (HAND_RAD+OBJ_RAD)
        min_y = NEAR_WALL+ HAND_RAD
        if obj.x-LEFT_WALL < HAND_RAD:
            x = LEFT_WALL+HAND_RAD
        elif RIGHT_WALL-obj.x < HAND_RAD:
            x = RIGHT_WALL-HAND_RAD
        if min_y <= max_y: #Empty list will be returned if this fails
            polygon_points.append((x, max_y))
            polygon_points.append((x, min_y))
    else:
        polygon_points.append((obj.x, obj.y)) #First point of the polygon
        #Define the guidlines for the alignment polygon
        m1,c1 = line_formula(obj.x, obj.y, LEFT_WALL+OBJ_RAD, FAR_WALL)
        m2,c2 = line_formula(obj.x, obj.y, RIGHT_WALL-OBJ_RAD, FAR_WALL)

        #Where does the 1st line intersect with the walls?
        #Does it intersect with the left wall?
        right_x1 = RIGHT_WALL - HAND_RAD
        right_y1 = m1 * right_x1 + c1
        if right_y1 >= NEAR_WALL + HAND_RAD: #It must intersect with the right wall
            polygon_points.append((right_x1, right_y1)) #Point on the wall
            polygon_points.append((RIGHT_WALL-HAND_RAD, NEAR_WALL+HAND_RAD)) #Point in the corner
        else: #It must intersect with the near wall
            far_y1 = NEAR_WALL + HAND_RAD
            far_x1 = (far_y1 - c1)/m1
            if far_x1 <= RIGHT_WALL-HAND_RAD: #Extra check to make sure it is properly in the wall
                polygon_points.append((far_x1, far_y1))
        #Now, where does the second line intersect with the walls?
        #Does it intersect with the left wall?
        left_x2 = LEFT_WALL + HAND_RAD
        left_y2 = m2*left_x2 + c2
        if left_y2 >= NEAR_WALL + HAND_RAD: #It is above the near wall
            polygon_points.append((LEFT_WALL+HAND_RAD, NEAR_WALL+HAND_RAD))#Do the corner first as we are wrapping around
            polygon_points.append((left_x2, left_y2))
        else: #It must intersect with the near wall
            near_y2 = NEAR_WALL+HAND_RAD
            near_x2 = (near_y2 - c2)/m2
            if near_x2 >= LEFT_WALL+HAND_RAD:
                polygon_points.append((near_x2, near_y2))
    return polygon_points


def polygon_for_near_wall(obj):
    polygon_points = []
    #If it is going to result in a vertical line in one direction and one that does not add to the area in the other
    #This case is a bit weird in that there is actually no valid places, unless OBJ_RAD >= HAND_RAD.
    #But in practice, the physics would result in similar effects to alignment if the hand is against the wall too
    #Because objects very near the wall could also have no valid places, it is best to make this case cover all cases
    #where the distance from the left or right wall to the object centre is less than the hand radius.
    if obj.x-LEFT_WALL < HAND_RAD or RIGHT_WALL-obj.x < HAND_RAD: #object is very close to the side walls
        min_y = obj.y + (HAND_RAD+OBJ_RAD)
        max_y = FAR_WALL - HAND_RAD
        if obj.x-LEFT_WALL < HAND_RAD:
            x = LEFT_WALL+HAND_RAD
        elif RIGHT_WALL-obj.x < HAND_RAD:
            x = RIGHT_WALL-HAND_RAD
        if min_y <= max_y: #Empty list will be returned if this fails
            polygon_points.append((x, max_y))
            polygon_points.append((x, min_y))
    else: #The standard case
        polygon_points.append((obj.x, obj.y))
        m1,c1 = line_formula(obj.x, obj.y, LEFT_WALL+OBJ_RAD, NEAR_WALL)
        m2,c2 = line_formula(obj.x, obj.y, RIGHT_WALL-OBJ_RAD, NEAR_WALL)
        right_x1 = RIGHT_WALL-HAND_RAD
        right_y1 = m1 * right_x1 + c1
        if right_y1 <= FAR_WALL-HAND_RAD:
            polygon_points.append((right_x1, right_y1))
            polygon_points.append((RIGHT_WALL-HAND_RAD, FAR_WALL-HAND_RAD))
        else: #must intersect with the far wall
            far_y1 = FAR_WALL-HAND_RAD
            far_x1 = (far_y1 - c1)/m1
            if far_x1 <= RIGHT_WALL - HAND_RAD:
                polygon_points.append((far_x1, far_y1))
        left_x2 = LEFT_WALL +HAND_RAD
        left_y2 = m2*left_x2 + c2
        if left_y2 <= FAR_WALL-HAND_RAD:
            polygon_points.append((LEFT_WALL+HAND_RAD, FAR_WALL-HAND_RAD))
            polygon_points.append((left_x2, left_y2))
        else:
            far_y2 = FAR_WALL-HAND_RAD
            far_x2 = (far_y2 - c2)/m2
            if far_x2 >= LEFT_WALL+HAND_RAD:
                polygon_points.append((far_x2, far_y2))
    return polygon_points


def get_points_inside_polygon(polygon_points):
    triangles = triangulate_polygon(polygon_points)
    rounded_points = set()
    for triangle in triangles:
        points_inside = get_points_inside(triangle)
        rounded_points.update(points_inside)
    return rounded_points

#Because the polygons are always convex, I can safely use this simple approach
def triangulate_polygon(polygon_points):
    triangles = []
    first_point = polygon_points[0] #This point will be in every polygon
    for i in range (1, len(polygon_points) -1): #We want to skip the ends
        triangle = (first_point, polygon_points[i], polygon_points[i+1])
        triangles.append(triangle)
    return triangles

def get_points_inside(triangle):
    triangle = [(round(x), round(y)) for (x,y) in list(triangle)]
    points_in_triangle = []
    #Need to ensure this is not the special case
    if len(set([x for (x, y) in triangle])) == 3: #We know there are no vertical edges
        #Sort the points by x value
        triangle.sort(key=lambda p : p[0])
        (p1, p2, p3) = (triangle[0], triangle[1],triangle[2])
        em1, ec1 = line_formula(p1[0],p1[1],p3[0],p3[1]) #The longest side in the x dimension
        em2, ec2 = line_formula(p1[0],p1[1],p2[0],p2[1]) #The left edge
        em3, ec3 = line_formula(p2[0],p2[1],p3[0],p3[1]) #The right edge

        #Is p2 above or below (p1, p3)?
        y_at_p2x = em1*p2[0] + ec1 #What y at x=p2.x on (p1, p3)?
        if y_at_p2x < p2[1]: #Then p2 is above
            for x in range(p1[0], p3[0]+1): #For each 1 pixel wide vertical strip
                min_y = round(em1 * x + ec1) #The min for y is on (p1, p3)
                #max_y depend on whether it is to the left or right of p2
                if x < p2[0]: #it is to the left
                    max_y = round(em2 * x + ec2)
                else:#it is to the right
                    max_y = round(em3 * x + ec3)
                points_on_strip = [(x, y) for y in range(min_y, max_y+1)]
                points_in_triangle += points_on_strip
        else: #p2 is below the line of (p1, p3)
            for x in range(p1[0], p3[0]+1): #For each 1 pixel wide vertical strip
                max_y = round(em1 * x + ec1) #It is on (p1, p3)
                #min_y depends on whether it is to the left of the right of p2
                if x < p2[0]:
                    min_y = round(em2 * x + ec2)
                else:
                    min_y = round(em3 * x + ec3)
                points_on_strip = [(x, y) for y in range(min_y, max_y+1)]
                points_in_triangle += points_on_strip
    else: #This is the special case; there are vertical edges
        #We know that either P1.x == P2.x or P2.x == P3.x
        #Depending on which it is, it is easiest to handle them as seperate cases
        triangle.sort(key=lambda p : p[1])#We want them to be secondly sorted on y
        triangle.sort(key=lambda p : p[0])
        (p1, p2, p3) = (triangle[0], triangle[1],triangle[2])
        if p1[0] == p2[0]: #If p1.x == p2.x
            em1, ec1 = line_formula(p1[0],p1[1], p3[0], p3[1]) #The lower edge
            em2, ec2 = line_formula(p2[0], p2[1], p3[0], p3[1]) #The upper edge
            for x in range(p1[0], p3[0]+1): #For each 1 pixel wide vertical strip
                min_y = round(em1 * x + ec1)
                max_y = round(em2 * x + ec2)
                points_on_strip = [(x, y) for y in range(min_y, max_y+1)]
                points_in_triangle += points_on_strip
        elif p2[0] == p3[0]: #elif p2.x == p3.x
            em1, ec1 = line_formula(p1[0],p1[1], p2[0], p2[1]) #The lower edge
            em2, ec2 = line_formula(p1[0],p1[1], p3[0], p3[1]) #The upper edge
            for x in range(p1[0], p3[0]+1): #For each 1 pixel wide vertical strip
                min_y = round(em1 * x + ec1)
                max_y = round(em2 * x + ec2)
                points_on_strip = [(x, y) for y in range(min_y, max_y+1)]
                points_in_triangle += points_on_strip
    return points_in_triangle



####################################################################################################
## CODE FOR DETERMINING WHETHER OR NOT IT IS POSSIBLE FOR THE HAND TO BE ON A POINT
####################################################################################################

def is_reachable(quant_state, point):
    x, y = point
    if x < LEFT_WALL + HAND_RAD or x > RIGHT_WALL - HAND_RAD or y < NEAR_WALL + HAND_RAD or y > FAR_WALL - HAND_RAD:
        return False
    if in_object_radius(point, quant_state.objects):
        return False
    return True

def in_object_radius(point, objects_in_world):
    x, y = point
    r = HAND_RAD + OBJ_RAD
    for obj_name in objects_in_world:
        obj = objects_in_world[obj_name]
        square_distance = (obj.x - x)**2 + (obj.y - y)**2
        if square_distance < (r-0.5) ** 2:
            return True
    return False
####################################################################################################
### DETERMINING WHETHER A CLEAR PATH EXISTS BETWEEN TWO POINTS
####################################################################################################


def clear_path_exists(p1, p2, quant_state):
    for obj_name in quant_state.objects:
        obj = quant_state.objects[obj_name]
        obj_x = obj.x
        obj_y = obj.y
        if object_blocks_path(p1, p2, (obj_x, obj_y)):
            return False
    return True

def object_blocks_path(p1, p2, obj):
    #Make it easier to do the calculations
    x0 = obj[0]
    x1 = p1[0]
    x2 = p2[0]
    y0 = obj[1]
    y1 = p1[1]
    y2 = p2[1]

    Dx = x2 - x1 #Change in X
    Dy = y2 - y1 #Change in Y

    #Ensure this isn't an undefined gradient case
    if Dx == 0:
        if x0 > (x1 - (HAND_RAD + OBJ_RAD)) and x0 < (x1 + HAND_RAD + OBJ_RAD):
            y_list = [y0, y1, y2]
            if sorted(y_list)[1] == y0:
                return True
        return False
    elif Dy == 0:
        if y0 > (y1 - (HAND_RAD + OBJ_RAD)) and y0 < (y1 + HAND_RAD + OBJ_RAD):
            x_list = [x0, x1, x2]
            if sorted(x_list)[1] == x0:
                return True
        return False
    #How far is it from the line?
    top = abs((Dy*x0)-(Dx*y0)-(x1*y2) + (x2*y1))
    bottom = sqrt(Dx**2+Dy**2)
    distance_from_line = top/bottom

    #Check whether or not we need to do anymore tests
    if distance_from_line >= OBJ_RAD + HAND_RAD: #It is sufficently far away
        return False

    #If it is near, we need to make sure it is near the actual segment

    #1) What are the line slope constants for the line?
    m1 = (y2 - y1) /(x2 - x1)
    c1 = y2 - m1*x2

    #2)And what about the perpendicular line?
    m2 = -1/m1
    c2 = y0 - m2*x0

    #And now, we need to solve for x
    xc = (c2 - c1)/(m1 - m2)
    yc = m1*xc + c1

    x_list = [x1, x2, xc]
    y_list = [y1, y2, yc]
    between_x = sorted(x_list)[1] == xc #Is the intercepting point in between?
    between_y = sorted(y_list)[1] == yc

    return between_x and between_y

####################################################################################################
### SUPPORT FUNCTIONS
####################################################################################################

def line_formula(x1, y1, x2, y2):
    m = (y2-y1)/(x2-x1)
    c = y1 - m*x1
    return (m,c)
