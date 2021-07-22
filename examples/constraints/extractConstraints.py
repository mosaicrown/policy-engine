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

import pathlib

import rdflib

from mosaicrown import utils
from mosaicrown import vocabularies
from mosaicrown.namespaces import MOSAICROWN
from mosaicrown.namespaces import ODRL
from mosaicrown.sql.sqlconstraint import SQLConstraints
from mosaicrown.sql.sqlquery import SQLQuery
from mosaicrown.utils import get_target_constraints


separator = '--------------------------------------------------'


def policy_loading():
    """Load the running example policy into the graph."""
    # create empty RDF graph
    print("[*] Create the RDF graph")
    graph = rdflib.Graph()

    # parse ODRL vocabolary
    print("\n[*] Load ODRL vocabolary")
    graph.parse(vocabularies.JSON_LD["ODRL"], format="json-ld")

    # parse MOSAICROWN vocabulary
    # only the namespace is downloaded at runtime by RDFLib, NOT the vocabulary
    print("\n[*] Load MOSAICROWN vocabolary")
    graph.parse(location=vocabularies.JSON_LD["MOSAICROWN"], format="json-ld")

    pbasepath = "http://localhost:8000/policy.jsonld"

    # parse policy
    print('\n[*] Load running example policy')
    print(f'\tLoading policy {pbasepath}')
    graph.parse(pbasepath, format="json-ld")

    return graph


def preliminary_policy_expansion(graph):
    """Expand the policy graph with the knowledge contained within the policy.

    :graph: The policy graph
    """
    # expanding hierarchy of targets
    for target in utils.get_targets(graph):
        utils.add_iri_hierarchy_to_graph(graph, target,
                                         predicate=ODRL.partOf,
                                         reverse=True)
    # expanding hierarchy of subjects
    for assignee in utils.get_assignee(graph):
        utils.add_iri_hierarchy_to_graph(graph, assignee,
                                         predicate=MOSAICROWN.belongsTo,
                                         reverse=True)


def main():
    # Create the 2 policies RDF graphs
    graph = policy_loading()

    # Expand the graph with hierarchy concept on targets and assignees
    print("\n[*] Expand the policy graph with the hierarchy concept")
    preliminary_policy_expansion(graph)

    print("\n[*] Constraint extraction")
    # SPARQL query to recover a constraint inside a policy rule
    target = "student"

    result = get_target_constraints(graph, target)

    target = pathlib.PurePosixPath(target).parts[-1]

    constraints = SQLConstraints.create_constraints(result, target)

    query = "SELECT student.sex FROM student"
    print(f"Origianl query:\n{query}\n")
    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)

    print(f"Rewritten query:\n{sqlquery.render()}")


if __name__ == '__main__':
    main()
