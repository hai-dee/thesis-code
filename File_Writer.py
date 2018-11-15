#This singleton class handles all the file writing
from datetime import datetime
import SharedData as Shared
import pickle #Module for saving objects
import TheAgent


LOG_FILE_PATH = "logs/"


class FileWriter():

    __the_file_writer = None

    def __new__(self, *args, **kwargs):
        if not FileWriter.__the_file_writer:
            FileWriter.__the_file_writer = super(FileWriter, self).__new__(self, *args, **kwargs)
            #initialise the time_string
            self.__files = {} #Store all the files in a collection (i.e. dictionary)
            self.general_log = None
        return FileWriter.__the_file_writer


    ################################################################################################
    ###Saving data files that can be reloaded at a later date
    ################################################################################################

    def write_to_general_log(self, string_to_write):
        if not "general" in self.__files:
            self.__files["general"] = open(LOG_FILE_PATH + "general/general_log", 'a')
            self.__files["general"].write("--------------------------------------------------------\n")
        self.__files["general"].write(str(string_to_write))
        self.__files["general"].flush()

    def write_to_plan_log(self, string_to_write):
        if not "plan_log" in self.__files:
            self.__files["plan_log"] = open(LOG_FILE_PATH + "plan/plan_log", 'a')
            self.__files["plan_log"].write("--------------------------------------------------------\n")
        self.__files["plan_log"].write(str(string_to_write))
        self.__files["plan_log"].flush()



    def save_learnt_data(self, file_name):
        file = open(file_name, "wb")
        agent_knowledge = TheAgent.The_Agent().knowledge()
        simulation_state = TheAgent.The_Agent().world_state()
        pickle.dump((agent_knowledge, simulation_state), file)
        file.close()

    def load_learnt_data(self, file_name):
        file = open(file_name, "rb")
        (agent_knowledge, simulation_state) =  pickle.load(file)
        TheAgent.The_Agent().set_new_knowledge_base(agent_knowledge)
        TheAgent.The_Agent().set_world_state(simulation_state)
        file.close()

    ################################################################################################
    ################################################################################################


    def update_count_file(self, agent_knowledge_base):
        if not "count" in self.__files:
            time_string = str(datetime.now())
            time_string = time_string.replace(":", "-") #Otherwise it will crash on windows
            self.__files["count"] =  open(LOG_FILE_PATH + "counts/counts" + time_string + ".txt", "w")
        for prim_action_name in agent_knowledge_base._prim_actions():
            prim_action = agent_knowledge_base._prim_actions()[prim_action_name]
            self.__files["count"].write(prim_action_name + " ")
            counts = prim_action.counts_of_rules()
            for i in range(1, Shared.MAX_EFFECT_SET_SIZE+1):
                self.__files["count"].write(str(counts[i]) + " ")
            self.__files["count"].write("\n")
        self.__files["count"].write("\n")

    def write_example_to_file(self, example):
        if not "example" in self.__files:
            time_string = str(datetime.now())
            time_string = time_string.replace(":", "-") #Otherwise it will crash on windows
            self.__files["example"] = open(LOG_FILE_PATH + "example/example_log" + time_string + ".txt", "w")
            self.__files["example"].write("Examples\n\n")
        self.__files["example"].write(str(example))

    def log_example_added_to_action_rule_attempt(self, added, action_rule, example):
        if not "example_added_log" in self.__files:
            time_string = str(datetime.now())
            time_string = time_string.replace(":", "-") #Otherwise it will crash on windows
            self.__files["example_added_log"] = open(LOG_FILE_PATH + "example-added/example_added_log" + time_string + ".txt", "w")
            self.previous_example = None
        #Only want to add the example if it is different to the previous one.
        #so the file output will be an example, and then all the action rules that it was added to
        if example != self.previous_example:
            self.__files["example_added_log"].write("==================EXAMPLE===========================\n")
            self.__files["example_added_log"].write(str(example))
            self.__files["example_added_log"].write("==================ACTION RULES======================\n")
        else:
            self.previous_example = example
        self.__files["example_added_log"].write("---\n")
        self.__files["example_added_log"].write(action_rule.summary())
        self.__files["example_added_log"].write("\n")


    #Each time a new example is added, want to know how many of each kind of action rule there are
    def update_action_rule_count(self, agent_knowledge_base):
        if not "counts" in self.__files:
            print("making new file for counts")
            time_string = str(datetime.now())
            time_string = time_string.replace(":", "-") #Otherwise it will crash on windows
            self.__files["counts"] = open(LOG_FILE_PATH + "ar-counts/counts" + time_string + ".txt", "w")
        self.__files["counts"].write("===========\n")
        for prim_action in agent_knowledge_base._prim_actions():
            count_dict = dict(agent_knowledge_base._prim_actions()[prim_action].counts_of_rules())
            self.__files["counts"].write(prim_action + str(count_dict) + "\n")
        self.__files["counts"].write("\n")


    #This file gives an overview of all the action rules that are in the system, and the nodes that they link to
    def generate_links_file(self, agent_knowledge_base):
        "todo"



    def write_all_knowledge_to_file(self, agent_knowledge_base):
        time_string = str(datetime.now())
        time_string = time_string.replace(":", "-") #Otherwise it will crash on windows
        knowledge_file = open(LOG_FILE_PATH + "knowledge/knowledge" + time_string + ".txt", "w")
        #Write the context to the file
        knowledge_file.write("###############################################\n")
        knowledge_file.write("###THE CONTEXT\n")
        knowledge_file.write("###############################################\n")
        for fact in agent_knowledge_base.context().all_facts_in_context():
            knowledge_file.write(str(fact) + "\n")
        knowledge_file.write("\n\n")

        knowledge_file.write("###############################################\n")
        knowledge_file.write("### THE ACTION RULES\n")
        knowledge_file.write("###############################################\n\n")
        primitive_actions = agent_knowledge_base._prim_actions()
        for prim_action in primitive_actions:
            knowledge_file.write("============Action Rules for " + prim_action + " ===============\n\n")
            for size in primitive_actions[prim_action]._get_indexes():
                knowledge_file.write("------------Of size " + str(size) + " ----------\n")
                effect_set_nodes = primitive_actions[prim_action].effect_set_nodes_of_size(size)
                effect_set_nodes = sorted(filter(lambda x: x.get_support() >= 5, effect_set_nodes), key=lambda node : node.get_support(), reverse=True)
                for node in effect_set_nodes:
                    knowledge_file.write("##################################################\n")
                    effect_strings = [str(x) for x in node.get_effect_set().get_effects()]
                    knowledge_file.write("Intention: " + str(node.get_intention()) + "\n")
                    knowledge_file.write("Effect Set " + str(node.get_effect_set().get_id()) + "("+ str(node.get_support()) + " support, " + str(len(node.get_action_rules())) + " action rules)\n")
                    knowledge_file.write("Effects: " + str(effect_strings) + "\n")
                    supersets = [x.get_effect_set().get_id() for x in node.get_superset_links()]
                    subsets = [x.get_effect_set().get_id() for x in node.get_subset_links()]
                    knowledge_file.write("Subsets: " + str(subsets) + "\n")
                    knowledge_file.write("Supersets: " + str(supersets) + "\n")
                    knowledge_file.write("\n")
                    #Now print all the action rules for the node
                    for ar in node.get_action_rules():
                        knowledge_file.write(ar.summary())
                        knowledge_file.write("\n")

                    knowledge_file.write("\n")
                    knowledge_file.write("\n")


                #action_rules =  primitive_actions[prim_action].action_rules_of_size(size)
                #action_rules_nodes_of_size = sorted(action_rules, key=lambda rule : rule.support(), reverse=True)
                #for action_rule in action_rules_nodes_of_size:
                    #if True: ##action_rule.support() >= 0: #If the action rule might actually be plausible
                        #knowledge_file.write(str(action_rule.get_id()) + "(Support: "+ str(action_rule.unique_support())+ "(" + str(action_rule.support()) + ")) "+ str(action_rule.get_intention()) + " " + str(action_rule.effect_set().get_id()) + "\n")
                        #if action_rule.above_support_threshold(): #otherwise it all becomes too slow
                            #knowledge_file.write("Quality ranking: " + str(action_rule.score_for_bindings()) + "\n")
                        #knowledge_file.write("Preconditions:  " + str(action_rule.get_precondition_strings()) + "\n")
                        #knowledge_file.write("Constraints:  " + str(action_rule.get_constraint_strings()) + "\n")
                        #knowledge_file.write("Effects:        " + str(action_rule.get_effect_strings()) + "\n")
                        #knowledge_file.write("\n")
                        #knowledge_file.write("\n")

    def close_all_log_files(self):
        for file in self.__files.values():
            file.close()
