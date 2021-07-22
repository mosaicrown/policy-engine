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


import logging
import pathlib
import posixpath
import pprint
import urllib.parse
from collections import namedtuple

import colorama
import rdflib
import rdflib.plugins.sparql as sparql
from rdflib import URIRef

if __package__:
    from .namespaces import ODRL
    from .namespaces import MOSAICROWN
else:
    from mosaicrown.namespaces import ODRL
    from mosaicrown.namespaces import MOSAICROWN


colorama.init(autoreset=True)


def get_objects(graph, predicate, subject=None):
    """Return a set of all the objects that match a predicate (and subject).

    :graph: The policy graph.
    :predicate: The predicate of the rules to match.
    :subject: The subject of the rules to match (defaults to any).
    :return: A set of all the objects that match the parameters in the graph.
    """
    triples = graph.triples((subject, predicate, None))
    return set(obj for (subj, pred, obj) in triples)


def get_subjects(graph, predicate, object=None):
    """Return a set of all the subjects that match a predicate (and object).

    :graph: The policy graph.
    :predicate: The predicate of the rules to match.
    :object: The object of the rules to match (defaults to any).
    :return: A set of all the subjects that match the parameters in the graph.
    """
    triples = graph.triples((None, predicate, object))
    return set(subj for (subj, pred, obj) in triples)


def get_targets(graph):
    """Return a set of all the odrl:target in the policy.

    :graph: The policy graph.
    :return: A set of all the odrl:target in the policy.
    """
    return get_objects(graph, ODRL.target)


def get_assignee(graph):
    """Return a set of all the odrl:assignee in the policy.

    :graph: The policy graph.
    :return: A set of all the odrl:assignee in the policy.
    """
    return get_objects(graph, ODRL.assignee)


def generate_subpaths(iri):
    """Generate all subpaths from an IRI string.

    :iri: An IRI string.
    :yield: A list of subpaths from the parent to the children.
    """
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(iri)
    parent = urllib.parse.urlunsplit((scheme, netloc, "/", None, None))
    path = pathlib.PurePosixPath(path)

    # Iterate over the path parts (separated by "/").
    for part in path.parts:
        # Yields a path without the trailing "/".
        parent = urllib.parse.urljoin(parent, part)
        yield parent
        # Adds the trailing "/" for subsequent iterations.
        parent = urllib.parse.urljoin(parent, part + "/")


def add_iri_hierarchy_to_graph(graph, iri, predicate, reverse=False):
    """Parse an IRI string and adds a dependency predicate to its parts.

    For instance, using the IRI "http://example.com/A/B" the following
    triples are added to the graph:

      ("http://example.com/",  predicate, "http://example.com/A"  )
      ("http://example.com/A", predicate, "http://example.com/A/B")

    :graph: The policy graph.
    :iri: An IRI string.
    :predicate: The predicate that will be used to generate the triples.
    :reverse: If reverse is True, the triples subject and object are swapped.
    """
    paths = [rdflib.URIRef(path) for path in generate_subpaths(iri)]
    for parent, child in zip(paths, paths[1:]):
        subj, obj = (child, parent) if reverse else (parent, child)
        logging.debug(f"Adding ({subj}, {predicate}, {obj})")
        graph.add((subj, predicate, obj))


def get_target_constraints(graph, target):
    """Recover constraints of rules having the specified URI as target.

        :graph: The policy graph.
        :target: The IRI string of the target.
        :return: The list of constraints on the given target.
        """
    operand_types = [URIRef("http://www.w3.org/ns/odrl/2/and"), URIRef("http://www.w3.org/ns/odrl/2/or")]
    operand_type = ", ".join(("<{}>".format(o_type) for o_type in operand_types))

    regex = f"http://((.)+/)?{target}"
    # SPARQL query to recover the constraints inside a rule
    # To not use the REGEX remove FILTER REGEX(STR(?target),"{regex}", "i")
    query_string = f"""
                   SELECT DISTINCT ?leftOperand ?operator ?rightOperand ?type ?operand ?logcon
                      WHERE {{
                        {{
                        ?rule odrl:target ?target.
                        FILTER REGEX(STR(?target),"{regex}", "i")
                        ?policy ?type ?rule.
                        ?rule odrl:constraint ?con.
                        ?con odrl:leftOperand ?leftOperand.
                        ?con odrl:operator ?operator.
                        ?con odrl:rightOperand ?rightOperand
                        }} UNION
                        {{
                        ?rule odrl:target ?target.
                        FILTER REGEX(STR(?target),"{regex}", "i")
                        ?policy ?type ?rule.
                        ?rule odrl:constraint ?logcon.
                        ?logcon ?operand ?con.
                        ?con odrl:leftOperand ?leftOperand.
                        ?con odrl:operator ?operator.
                        ?con odrl:rightOperand ?rightOperand
                        FILTER (?operand IN ({operand_type}))
                        }}
                      }}
                """
    # Recover only the constraint of the rules having the correct target
    bindings = {
        "target": rdflib.URIRef(target)
    }
    # Setup namespaces of the policy
    namespaces = {"odrl": ODRL, "mosaicrown": MOSAICROWN}

    query = sparql.prepareQuery(query_string, initNs=namespaces)
    # To use bindings instead of REGEX graph.query(query, initBindings=bindings)
    return graph.query(query)


def get_all_policy_rules_by_type(graph, rule_types=None):

    if not rule_types or len(rule_types) == 0:
        return None

    types = ", ".join(("<{}>".format(type) for type in rule_types))

    # SPARQL query to recover all the rules inside the policy graph
    queryString = """
           SELECT DISTINCT ?rule ?target ?assignee ?action ?purpose
              WHERE {{
                  ?policy ?predicate ?rule.
                  ?rule odrl:target ?target.
                  ?rule odrl:assignee ?assignee.
                  ?rule odrl:action ?action.
                  ?rule mosaicrown:purpose ?purpose
                  FILTER (?predicate IN ({type}))
              }}
        """.format(type=types)

    namespaces = {"odrl": ODRL, "mosaicrown": MOSAICROWN}
    query = sparql.prepareQuery(queryString, initNs=namespaces)
    result = graph.query(query)
    Rule = namedtuple('Rule', 'URI target assignee action purpose')
    ruleDict = {}

    for row in result:
        if row[0] in ruleDict:
            ruleDict[row[0]].append(Rule(*row))
        else:
            ruleDict[row[0]] = [Rule(*row)]
    ruleSet = set()
    for rows in ruleDict.values():
        targets = tuple(row.target for row in rows)
        ruleSet.add(Rule(rows[0].URI, targets, rows[0].assignee, rows[0].action, rows[0].purpose))

    return ruleSet


def get_rules(graph, targets, assignee, action, purpose, pred, ns=None,
              expand_graph=True):
    """Get the rules that assign the predicate `pred` to the assignee over
    the dictionary of targets (a map between table IRIs and accessed columns).

    :graph: The policy graph.
    :targets: A dictionary that maps table IRIs to accessed columns.
    :assignee: The user who is requesting the access.
    :action: The action that the user wants to perform.
    :purpose: The purpose for the access.
    :pred: The predicate that defines the rules that we are interested in.
    :ns: The dictionary of namespaces to add to the default ODRL one.
    :expand_graph: If True, introduces new hierarchical predicates on the
        IRI received as parameters (defaults to True).
    :return: A dictionary that maps table IRIs to the rules that involve the
        requested columns (as specified in the `targets` dictionary).
    """

    if expand_graph:
        add_iri_hierarchy_to_graph(graph, assignee, ODRL.belongsTo, True)
        add_iri_hierarchy_to_graph(graph, purpose, ODRL.partOf, True)

    # TODO: move namespaces updates to the reasoners when available.
    # Generate the namespaces to be used in the query.
    namespaces = {"odrl": ODRL, "mosaicrown": MOSAICROWN}
    if ns:
        namespaces.update(ns)

    # Create the query.
    queryString = """
       SELECT DISTINCT ?rule
          WHERE {
              ?policy ?predicate ?rule .
              ?rule odrl:assignee ?assigneeRec .
              ?assignee mosaicrown:belongsTo* ?assigneeRec .
              ?rule odrl:action ?actionRec .
              ?action odrl:includedIn* ?actionRec .
              ?rule odrl:target ?targetRec .
              ?target odrl:partOf* ?targetRec .
              ?rule mosaicrown:purpose ?purposeRec .
              ?purpose mosaicrown:declinationOf* ?purposeRec .
          }
    """
    query = sparql.prepareQuery(queryString, initNs=namespaces)

    # Prepare the result dictionary.
    rules = {}

    # Iterate over the tables and find a rule that has predicate on the
    # columns.
    for table_IRI in targets:
        column_rules = {}

        for column_name in targets[table_IRI]:
            column_IRI = rdflib.URIRef(posixpath.join(table_IRI, column_name))

            if expand_graph:
                add_iri_hierarchy_to_graph(graph, column_IRI,
                                           ODRL.partOf, True)

            bindings = {
                "predicate": pred,
                "action": action,
                "target": column_IRI,
                "assignee": assignee,
                "purpose": purpose
            }

            # Extract the rule uids that has predicate on the column.
            result = graph.query(query, initBindings=bindings)

            column_rules[column_IRI] = set(row[0] for row in result)

        # Add the column rules to the dictionary of table rules.
        rules[table_IRI] = column_rules

    return rules


def check_permission(graph, targets, assignee, action, purpose, ns=None,
                     expand_graph=True):
    """Check if the requested access complies with the policy.

    :graph: The policy graph.
    :targets: A dictionary that maps table IRIs to accessed columns.
    :assignee: The user who is requesting the access.
    :action: The action that the user wants to perform.
    :purpose: The purpose for the access.
    :ns: The dictionary of namespaces to add to the default ODRL one.
    :expand_graph: If True, introduces new hierarchical predicates on the
        IRI received as parameters (defaults to True).
    :return: A dictionary that maps table IRIs to a set of policy uids that
        grant the access, or None if the access does not comply with the
        policy.
    """
    rules = get_rules(
        graph=graph,
        targets=targets,
        assignee=assignee,
        action=action,
        purpose=purpose,
        pred=ODRL.permission,
        ns=ns,
        expand_graph=expand_graph)

    # For each table, get the intersection of the permission rules, since for
    # each table we want to find a permission rule that grants the join
    # visibility over all the accessed columns.
    join_permission_rules = {
        table_IRI: set.intersection(*rules[table_IRI].values())
        for table_IRI in rules}

    # If all the accessed table have at least one join permission rule (the
    # intersection is not empty), then return them, otherwise return None,
    # to state that the access does not comply with the policy.
    if all(join_permission_rules.values()):
        return join_permission_rules
    return None


def check_prohibition(graph, targets, assignee, action, purpose, ns=None,
                      expand_graph=True):
    """Check if the requested access is forbidden explicitly by the policy.
    This check only verifies if there is a prohibition rule that explicitly
    denies the visibility of the requested targets to the assignee. Even
    if the policy does not explicitly denies the access, it does not mean
    that there is a permission rule that grants it, so it is important to
    always check for positive permissions also.

    :graph: The policy graph.
    :targets: A dictionary that maps table IRIs to accessed columns.
    :assignee: The user who is requesting the access.
    :action: The action that the user wants to perform.
    :purpose: The purpose for the access.
    :ns: The dictionary of namespaces to add to the default ODRL one.
    :expand_graph: If True, introduces new hierarchical predicates on the
        IRI received as parameters (defaults to True).
    :return: A dictionary that maps table IRIs to a set of policy uids that
        deny the access, or None if the access does is not explicitly denied.
    """
    rules = get_rules(
        graph=graph,
        targets=targets,
        assignee=assignee,
        action=action,
        purpose=purpose,
        pred=ODRL.prohibition,
        ns=ns,
        expand_graph=expand_graph)

    # For each table, get the intersection of the permission rules, since for
    # each table we want to find a permission rule that grants the join
    # visibility over all the accessed columns.
    prohibition_rules = {
        table_IRI: set.union(*rules[table_IRI].values())
        for table_IRI in rules}

    # If any of the accessed table have at least one prohibition rule on one
    # of the accessed columns, return the rules that deny the access, otherwise
    # return None, to state that the access is not explicitly denied.
    if any(prohibition_rules.values()):
        return prohibition_rules
    return None


def check_access(graph, targets, assignee, action, purpose, ns=None,
                 expand_graph=True):
    """Check if the requested access is both:

        * not explicitly denied by a prohibition rule.
        * explicitly granted by a permission rule.

    :graph: The policy graph.
    :targets: A dictionary that maps table IRIs to accessed columns.
    :assignee: The user who is requesting the access.
    :action: The action that the user wants to perform.
    :purpose: The purpose for the access.
    :ns: The dictionary of namespaces to add to the default ODRL one.
    :expand_graph: If True, introduces new hierarchical predicates on the
        IRI received as parameters (defaults to True).
    :return: True if granted, False if denied (or not granted).
    """

    print(colorama.Fore.CYAN + "\n[*] Testing access")
    print("\tAssignee:", assignee, sep="\t")
    print("\tAction:\t", action, sep="\t")
    print("\tTargets:", pprint.pformat(targets), sep="\t")
    print("\tPurpose:", purpose, sep="\t")

    prohibitions = check_prohibition(
        graph=graph,
        targets=targets,
        assignee=assignee,
        action=action,
        purpose=purpose,
        ns=ns,
        expand_graph=expand_graph)

    if prohibitions:
        print(
            colorama.Fore.RED +
            f"[*] Access prohibited by: {pprint.pformat(prohibitions)}")
        return False
    else:
        print(colorama.Fore.YELLOW + "Access not prohibited")

    permissions = check_permission(
        graph=graph,
        targets=targets,
        assignee=assignee,
        action=action,
        purpose=purpose,
        ns=ns,
        expand_graph=expand_graph)

    if permissions:
        print(colorama.Fore.GREEN + "Access permitted:")
        for k in permissions:
            print(colorama.Fore.GREEN + "\ttarget:\t\t" + k)
            print(colorama.Fore.GREEN +
                  "\tperm. rules:\t" +
                  pprint.pformat(permissions[k]))
        return True
    else:
        print(
            colorama.Fore.RED +
            f"Access not explicitly permitted -> denied.")
        return False
