#############################################################################################
###THE DIGRAPH CLASS
#############################################################################################
class Graph:

    def __init__(self):
        "Constructs a new digraph"
        self._adjacency_list = {} #Use a dictionary
    def __iter__(self):
        for key in self._adjacency_list:
            yield key
    def __contains__(self, item):
        "Overides the in operator"
        return item in self._adjacency_list

    def add_node(self, item):
        "Adds an item to the graph if it doesn't already exist"
        "Returns True if the item is added"
        if item not in self:
            self._adjacency_list[item] = set()
            return True
        else:
            return False

    def add_edge(self, item1, item2):
        "Add an edge from item1 to item2 and vice versa"
        if not item1 in self or not item2 in self:
            raise KeyError("The items must be in the graph")
        else:
            self.__adjacency_list[item1].add(item2)
            self._adjacency_list[item2].add(item1)
            return True

    def get_edges(self, item):
        "Get edges for the given item"
        if not item in self:
            raise KeyError("The items must be in the graph")
        else:
            return self._adjacency_list[item]

class Digraph(Graph):

    def add_edge(self, item1, item2):
        "Add an edge from item1 to item2 and vice versa"
        if not item1 in self or not item2 in self:
            raise KeyError("The items must be in the graph")
        else:
            self._adjacency_list[item1].add(item2)
            return True
