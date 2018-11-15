import SharedData as Shared
from copy import deepcopy

class Fact():

    #Predicate is a string with the predicate name, e.g. "touching"
    #Parameters can either be Param objects or strings for values.
    #This method just assumes that if they aren't strings, they must be params. It does no other checking, it just assumes params
    def __init__(self, predicate, parameters):
        self.__predicate = predicate
        if parameters:
            #Are the parameters string or params?
            self.__parameters = []
            for val in parameters:
                if type(val) is str:
                    if val[0] == "?": #It is a variable
                        param_obj = Param(val[2:], True, val[1])
                        self.__parameters.append(param_obj)
                    else:
                        param_obj = Param(val, False, None)
                        self.__parameters.append(param_obj)
                elif type(val) is Param:
                    self.__parameters.append(val)
                elif type(val) is tuple:
                    param_obj = Param(val, False, "p")
                    self.__parameters.append(param_obj)
        else:
            self.__parameters = []
        self.__string = None

    def contains_only_specified_params(self, params):
        for param in self.get_parameters():
            if param not in params:
                return False
        return True

    @staticmethod
    def make_fact_from_string(string):
        predicate = string[0 : string.index("(")]
        param_string = string[string.index("(") + 1: len(string) -1]
        #Need to remember how to do this properly
        params = [param.strip() for param in param_string.split(",")]
        if params[0] == '':
            params = []
        return Fact(predicate, params)

    def contains_variables(self):
        for param in self.__parameters:
            if param.is_var():
                return True
        return False

    def contains_concrete_places(self):
        for param in self.__parameters:
            if param.is_value() and param.param_type() == "p":
                return True
        return False

    def contains_place_variables(self):
        for param in self.__parameters:
            if param.is_var() and param.param_type() == "p":
                return True
        return False

    def contains_negation_and_vars(self):
        return self.negative_predicate() and self.contains_variables()

    def __str__(self):
        return self.string_representation()

    def get_predicate(self):
        return self.__predicate

    #Does this fact contain a + on the start of the predicate?
    def positive_predicate(self):
        return self.get_predicate()[0] == "+"

    #does this fact contain a - on the start of the predicate?
    def negative_predicate(self):
        return self.get_predicate()[0] == "-"

    def get_parameters(self):
        return self.__parameters

    def get_all_var_params(self):
        var_params = set()
        for parameter in self.__parameters:
            if parameter.is_var():
                var_params.add(parameter)
        return var_params

    def string_representation(self):
        if not self.__string:
            string_rep = self.__predicate + "("
            is_first = True #To know whether or not we need to put a comma and space first
            for parameter in self.__parameters:
                if is_first:
                    is_first = False
                else:
                    string_rep += ", "
                string_rep += parameter.to_string()
            string_rep += ")"
            self.__string = string_rep
        return self.__string

    #Note: A lot of methods will need to switch to using this code.
    #Fact needs to be immutable
    def __get_copy_with_new_parameters(self, new_params):
        return Fact(self.__predicate, new_params)

    def __get_copy_of_fact(self):
        params_copy = deepcopy(self.get_parameters())
        return Fact(self.get_predicate(), params_copy)

    #Get a copy of the fact that does not contain the + or -
    def get_plain_copy_of_fact(self):
        if self.positive_predicate() or self.negative_predicate():
            params_copy = deepcopy(self.get_parameters())
            return Fact(self.get_predicate()[1:], params_copy)
        else:
            return self.__get_copy_of_fact() #Nothing to do but we'd be safe to copy it anyway

    def get_generalised_copy_with_dictionary(self, dictionary):
        params = []
        for param in self.get_parameters():
            if param.param_type() and param.param_type() != "place":
                params.append(dictionary[param])
            else:
                params.append(param)
        return Fact(self.get_predicate(), params)

    def get_specific_copy_with_dictionary(self, dictionary):
        params = []
        for param in self.get_parameters():
            if param.is_var() and param in dictionary:
                params.append(dictionary[param])
            else:
                params.append(param)
        return Fact(self.get_predicate(), params)

    def __eq__(self, other):
        if other is None:
            return False
        return (self.__predicate, tuple(self.__parameters)) == (other.__predicate, tuple(other.__parameters))

    def __hash__(self):
        return hash((self.__predicate, tuple(self.__parameters)))

    #Takes the facts in a list of lists. All facts that are passed in will be generalised together, but duplicate removal will
    #only be done within lists.
    #This allows intention, preconditions (currently not used in this) and effects to be kept seperate.
    @staticmethod
    def generalise_list_of_facts(facts):
        new_outer_list = []
        new_names = {}
        for inner_list in facts:
            new_inner_list = []
            for fact in inner_list:
                new_param_list = []
                for param in fact.get_parameters():
                    if not param.param_type(): #Assume that we can generalise anything with a type
                        new_param_list.append(param)
                    elif param in new_names:
                        new_param_list.append(new_names[param])
                    else:
                        new_param = Param.new_variable_param(param.param_type())
                        new_names[param] = new_param
                        new_param_list.append(new_param)
                new_fact = fact.__get_copy_with_new_parameters(new_param_list)
                new_inner_list.append(new_fact)
            new_outer_list.append(new_inner_list)
        return new_outer_list

    @staticmethod
    def assign_fresh_variables_to_list_of_facts(facts):
        new_outer_list = []
        new_param_names = {}
        for inner_list in facts:
            new_inner_list = []
            for fact in inner_list:
                new_param_list = []
                for param in fact.get_parameters():
                    if param.is_value():
                        new_param_list.append(param)
                    elif param.is_var():
                        if not (param in new_param_names): #Have we already given a new name to this param?
                            new_param_names[param] = Param.new_variable_param(param.param_type())
                        new_param_list.append(new_param_names[param])
                new_fact = fact.__get_copy_with_new_parameters(new_param_list)
                new_inner_list.append(new_fact)
            new_outer_list.append(new_inner_list)
        return new_outer_list


class Param:

    __variable_symbol = "?"

    #param type is optional for a value. If it is not given, Param will attempt to resolve the type using the global list of types of values
    def __init__(self, param_identifier, is_var, param_type):
        self.__identifier = param_identifier #Should be a string (will usually be meaningful for a value, and a number for a variable)
        self.__is_var = is_var #Should be a boolean
        if param_type:
            self.__type = param_type #Should be a single character, e.g. o for object, w for wall, and s for slot wall
        else:
            if is_var == False:
                self.__type = Param.type_of_name(param_identifier) #Resolve the type
            else:
                #This should not happen!!!
                assert False
        self.__param_string = self.__make_param_string()

    def __str__(self):
        return self.__make_param_string()

    #Not sure if this will work...
    def value(self):
        return self.__identifier

    #Private constructor method that makes the string for the param
    def __make_param_string(self):
        string = ""
        if self.__is_var:
            string += Param.__variable_symbol + self.__type #Only append the type on if it is a variable. Could potentially put types in values too, although
            #probably not necessary
        string += str(self.__identifier)
        return string

    def identifier(self):
        return self.__identifier

    #What type is the param?
    def param_type(self):
        return self.__type

    def is_obj(self):
        return self.is_value() and self.__type != None

    #Is this a var?
    def is_var(self):
        return self.__is_var

    #Is this a value? (i.e. not a var)
    def is_value(self):
        return not self.__is_var

    #String for printing nice output of the param
    def to_string(self):
        return self.__param_string

    def __hash__(self):
        return hash((self.__identifier, self.__type, self.__is_var))

    def __eq__(self, other):
        return (self.__identifier, self.__type, self.__is_var) == (other.__identifier, other.__type, other.__is_var)

    #This is a static method that takes a value and determines what the type of it is, based on the dictionary of types that is the Shared
    @staticmethod
    def type_of_name(value_name):
        for param_type in Shared.types_dictionary:
            if value_name in Shared.types_dictionary[param_type]:
                return param_type
        return None

    __cur_number = 0 #What is the identifier that the next variable generated should have?
    #Makes a variable for the given type, including assigning an identifier to it
    #This perhaps should be a private static method, used by the below static method.
    @staticmethod
    def new_variable_param(var_type):
        Param.__cur_number += 1
        new_param = Param(Param.__cur_number, True, var_type)
        return new_param
