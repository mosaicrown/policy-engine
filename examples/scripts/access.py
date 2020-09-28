#!/usr/bin/env python3

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


import colorama
import rdflib

from mosaicrown import utils
from mosaicrown.namespaces import MOSAICROWN, ODRL
from mosaicrown.visualization import results_table
from mosaicrown.visualization import triples_table


# Initialize colorama
colorama.init(autoreset=True)


def main():

    graph = rdflib.Graph()
    graph.parse(source="examples/scripts/policies/assets.jsonld",
                format="json-ld")

    print(colorama.Fore.CYAN + "[*] Add IRI-based hierarchy on targets")
    for target in utils.get_targets(graph):
        utils.add_iri_hierarchy_to_graph(graph, target,
                                         predicate=ODRL.partOf,
                                         reverse=True)

    print(colorama.Fore.CYAN + "[*] Add IRI-based hierarchy on assignees")
    for assignee in utils.get_assignee(graph):
        utils.add_iri_hierarchy_to_graph(graph, assignee,
                                         predicate=MOSAICROWN.belongsTo,
                                         reverse=True)

    print(colorama.Fore.CYAN + "\n[*] The policy\n")
    print(triples_table(graph))

    print(colorama.Fore.CYAN + "\n\n[*] Actions\n")
    query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        SELECT DISTINCT ?rule ?assignee ?action ?target
            WHERE {
                ?policy odrl:permission ?rule .
                ?rule odrl:assignee ?assignee .
                ?rule odrl:action ?action .
                ?rule odrl:target ?targetRec .
                ?target odrl:partOf* ?targetRec .
            }
    """
    results = graph.query(query)
    print(results_table(query, results))

    generic = rdflib.URIRef("http://unibg.it/user")
    parabosc = rdflib.URIRef("http://unibg.it/user/parabosc")
    action = ODRL.read
    purpose = MOSAICROWN.statistical
    IRIs = {'students': 'http://unibg.it/table/students'}

    # Generic user access request.

    query = "SELECT students.Ethnicity FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, generic, action, purpose)

    query = "SELECT students.Ethnicity, students.CF FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, generic, action, purpose)

    query = "SELECT students.Sex, students.CF, students.Birthdate FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, generic, action, purpose)

    query = "SELECT students.IBAN FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, generic, action, purpose)

    query = "SELECT students.NotPreviouslyDefined FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, generic, action, purpose)

    # Parabosc user access request.

    query = "SELECT students.Ethnicity FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, parabosc, action, purpose)

    query = "SELECT students.Ethnicity, students.CF FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, parabosc, action, purpose)

    query = "SELECT students.Sex, students.CF, students.Birthdate FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, parabosc, action, purpose)

    query = "SELECT students.IBAN FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, parabosc, action, purpose)

    query = "SELECT students.NotPreviouslyDefined FROM students"
    targets = utils.get_targets_from_query(query, IRIs)
    utils.check_access(graph, targets, parabosc, action, purpose)


if __name__ == "__main__":
    main()
