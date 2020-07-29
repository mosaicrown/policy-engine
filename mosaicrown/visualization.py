# Copyright 2020 Unibg Seclab (https://seclab.unibg.it)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import matplotlib.pyplot as plt
import networkx as nx
import rdflib.plugins.sparql as sparql
import rdflib
import tabulate

import pathlib

if __package__:
    from .namespaces import ODRL
    from .vocabularies import JSON_LD
    from . import utils
else:
    from namespaces import ODRL
    from vocabularies import JSON_LD
    import utils


def remove_ns(ns, path):
    try:
        return pathlib.PurePosixPath(path).relative_to(ns).as_posix()
    except ValueError:
        return path


def draw_graph(graph, pred, subj=None, obj=None, reverse=False, **kwargs):
    G = nx.DiGraph()

    labels = {}
    for (s, _, o) in graph.triples((subj, pred, obj)):
        s, o = [x.toPython() for x in (s, o)]
        G.add_nodes_from((s, o))
        G.add_edge(s, o, predicate=pred)
        labels[s] = remove_ns(o, s)
        labels[o] = labels.get(o, o)

    G = G.reverse() if reverse else G
    kwargs.update({"node_size": 1000, "node_color": "white", "node_shape": "s"})
    pos = nx.drawing.nx_agraph.graphviz_layout(G, prog="dot")
    nx.draw_networkx_edges(G, pos, **kwargs)
    nx.draw_networkx_nodes(G, pos, **kwargs)
    nx.draw_networkx_labels(G, pos, labels, **kwargs)
    return G


def triples_table(graph, **kwargs):
    return tabulate.tabulate(graph.triples((None, None, None)),
                             headers=("Subject", "Predicate", "Object"),
                             tablefmt="fancy_grid",
                             **kwargs)


def results_table(query, results, **kwargs):
    headers = None
    try:
        globs, parsed = sparql.parser.parseQuery(query)
        headers = [var["var"].toPython().lstrip("?").title()
                   for var in parsed["projection"]]
    except Exception:
        pass

    return tabulate.tabulate(list(results), headers=headers,
                             tablefmt="fancy_grid", **kwargs)


def main():
    graph = rdflib.Graph()
    graph.parse(source="policies/assets.json", format="json-ld")

    for target in utils.get_targets(graph):
        utils.add_iri_hierarchy_to_graph(graph, target,
                                         predicate=ODRL.partOf, reverse=True)

    draw_graph(graph, ODRL.partOf, reverse=True)
    plt.show()

    graph = rdflib.Graph()
    graph.parse(location=JSON_LD["ODRL"], format="json-ld")

    draw_graph(graph, ODRL.includedIn, reverse=True)
    plt.show()


if __name__ == "__main__":
    main()
