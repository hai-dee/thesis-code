class Graph:

    def __init__(self):
        self._adjacency_list = {} #Use a dictionary

    def __iter__(self):
        for key in self._adjacency_list:
            yield key

    def __contains__(self, item):
        return item in self._adjacency_list

    def add_node(self, item):
        if item not in self:
            self._adjacency_list[item] = set()
            return True
        else:
            return False

    def add_edge(self, item1, item2):
        if not item1 in self or not item2 in self:
            raise KeyError("The items must be in the graph")
        else:
            self.__adjacency_list[item1].add(item2)
            self._adjacency_list[item2].add(item1)
            return True

    def get_edges(self, item):
        if not item in self:
            raise KeyError("The items must be in the graph")
        else:
            return self._adjacency_list[item]

class Digraph(Graph):
    def add_edge(self, item1, item2):
        if not item1 in self or not item2 in self:
            raise KeyError("The items must be in the graph")
        else:
            self._adjacency_list[item1].add(item2)
            return True
