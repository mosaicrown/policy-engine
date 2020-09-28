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
import rdflib.plugins.sparql as sparql

from mosaicrown.namespaces import ODRL
from mosaicrown.vocabularies import JSON_LD
from mosaicrown.visualization import triples_table
from mosaicrown.visualization import results_table


# Initialize colorama.
colorama.init(autoreset=True)

# Initialize namespace
EXAMPLE = rdflib.Namespace("http://example.com/")


def execute_sparql(graph, query, description=None):
    if description:
        print(f"\n{colorama.Fore.CYAN}[*] {description}\n")

    results = graph.query(query)
    print(results_table(query, results))


def main():
    # create empty RDF graph.
    graph = rdflib.Graph()
    # parse movies policy and add to graph.
    graph.parse("examples/scripts/policies/movies.jsonld", format="json-ld")

    # Print the triples in the policy.
    print('\n[*] The policy\n')
    print(triples_table(graph))

    execute_sparql(
        graph,
        """
            PREFIX odrl:  <http://www.w3.org/ns/odrl/2/>
            SELECT DISTINCT ?policy ?action ?target
            WHERE {
                ?policy odrl:permission ?rule .
                ?rule odrl:action ?action .
                ?rule odrl:target ?target .
            }
        """,
        description="Get all the actions over targets.")

    execute_sparql(
        graph,
        """
            PREFIX odrl:  <http://www.w3.org/ns/odrl/2/>
            SELECT DISTINCT ?policy ?target
            WHERE {
                ?policy odrl:permission ?node .
                ?node odrl:action odrl:transfer .
                ?node odrl:target ?target .
            }
        """,
        description="Get all the targets with action transfer.")

    execute_sparql(
        graph,
        """
            PREFIX odrl:  <http://www.w3.org/ns/odrl/2/>
            SELECT DISTINCT ?policy ?target
            WHERE {
                ?policy odrl:permission ?node .
                ?node odrl:action odrl:sell .
                ?node odrl:target ?target .
            }
        """,
        description="Get all the targets with action sell.")

    # import odrl vocabulary to know action hierarchy.
    print(colorama.Fore.CYAN + "\n[*] Importing ODRL ... ", end="")
    graph.parse(location=JSON_LD['ODRL'], format='json-ld')
    print(colorama.Fore.GREEN + "Done")

    execute_sparql(
        graph,
        """
            PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
            SELECT DISTINCT ?policy ?action ?target
            WHERE {
                ?policy odrl:permission ?node .
                ?node odrl:action ?action .
                odrl:sell odrl:includedIn* ?action .
                ?node odrl:target ?target .
            }
        """,
        description="Get all the targets with action sell (or parents).")

    print(colorama.Fore.CYAN +
          "\n[*] Prepare statement for assignees who can do action on target.")
    queryString = """
        SELECT DISTINCT ?policy ?assignee
        WHERE {
            ?policy odrl:permission ?node .
            ?node odrl:assignee ?assignee .
            ?node odrl:action ?actionRec .
            ?action odrl:includedIn* ?actionRec .
            ?node odrl:target ?target .
        }
    """
    query = sparql.prepareQuery(queryString, initNs={'odrl': ODRL})

    print(colorama.Fore.CYAN +
          "\n[*] Use prepared statement with sell asset:9898.\n")
    results = graph.query(query,
                          initBindings={
                            'action': ODRL['sell'],
                            'target': EXAMPLE['asset:9898.movie'],
                          })
    print(results_table(queryString, results))


if __name__ == "__main__":
    main()
