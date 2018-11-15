from datetime import datetime
import SharedData as Shared
import pickle
import TheAgent

LOG_FILE_PATH = "logs/"

class FileWriter():

    __the_file_writer = None

    def __new__(self, *args, **kwargs):
        if not FileWriter.__the_file_writer:
            FileWriter.__the_file_writer = super(FileWriter, self).__new__(self, *args, **kwargs)
            #initialise the time_string
            self.__files = {} #Store all the files in a collection (i.e. dictionary)
        return FileWriter.__the_file_writer

    def load_learnt_data(self, file_name):
        file = open(file_name, "rb")
        (agent_knowledge, simulation_state) =  pickle.load(file)
        TheAgent.The_Agent().set_new_knowledge_base(agent_knowledge)
        TheAgent.The_Agent().set_world_state(simulation_state)
        file.close()

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


    def close_all_log_files(self):
        for file in self.__files.values():
            file.close()
