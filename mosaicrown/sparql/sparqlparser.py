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

from rdflib.plugins.sparql.operators import AdditiveExpression
from rdflib.plugins.sparql.operators import ConditionalOrExpression
from rdflib.plugins.sparql.operators import MultiplicativeExpression
from rdflib.plugins.sparql.operators import RelationalExpression
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.parserutils import Expr
from rdflib.term import Literal
from rdflib.term import URIRef
from rdflib.term import Variable


# TODO: this method only supports filters of the type FILTER (?variable <comparison> <Literal>)
def add_filter(where_part, left_operand, operator, right_operand):
    """
        Directly add a filter statement to the where part of the SPARQL query passed as input.

        :where_part: where part of the parseResult in which the filter is inserted
        :left_operand: variable used as left operand
        :operator: operator used in the filter
        :right_operand: element used as right operand
    """
    # Outer: ConditionalOrExpression_ ConditionalOrExpression_ RelationalExpression_
    # Left and Right: AdditiveExpression_ MultiplicativeExpression_
    left_expr = Expr(name="AdditiveExpression", evalfn=AdditiveExpression,
                     expr=Expr(name="MultiplicativeExpression", evalfn=MultiplicativeExpression,
                               expr=Variable(left_operand)))
    right_expr = Expr(name="AdditiveExpression", evalfn=AdditiveExpression,
                      expr=Expr(name="MultiplicativeExpression", evalfn=MultiplicativeExpression,
                                expr=Literal(right_operand)))
    outer_expr = Expr(name="ConditionalOrExpression_", evalfn=ConditionalOrExpression,
                      expr=Expr(name="ConditionalOrExpression", evalfn=ConditionalOrExpression,
                                expr=Expr(name="RelationalExpression", evalfn=RelationalExpression,
                                          expr=left_expr, op=operator, other=right_expr)))
    sparql_filter = Expr(name="Filter", expr=outer_expr)
    where_part.append(sparql_filter)


def handle_triples(block, prefix_dict):
    """
    Given a block containing SPARQL triples, recover every triple
    :block: parseResult block inside the where statement containing the triples
    :prefix_dict: dictionary to translate prefixes inside the predicates
    """
    for triple in block.get("triples"):
        print("==================")
        subject = extract_subject(triple)
        predicates = extract_predicates(triple, prefix_dict)
        triple_object = extract_object(triple, prefix_dict)
        print("Subject", subject)  # subject
        print("Predicate path", predicates)  # predicate
        print("Object", triple_object)  # object


def handle_filters(block):
    print("==================")
    variable = block.expr.expr.expr.expr.expr.expr  # Interested variable
    print("Filter variable", variable)
    op = block.expr.expr.expr.op # Operator
    print("Filter operator", op)
    right_operand = block.expr.expr.expr.other  # Right operand of the filter
    if not right_operand.expr and len(right_operand) > 0:
        # Group case
        operands = [operand.expr.expr.expr.expr.expr for operand in right_operand]
        r_operand = ", ".join(operands)
        print("Filter right operand", r_operand)
    else:
        # Single case
        r_operand = str(right_operand.expr.expr)
        print("Filter right operand", r_operand)
    return (variable, op, r_operand)

def extract_subject(triple):
    return triple[0]


def extract_predicates(triple, prefix_dict):
    predicate = triple[1].part
    predicates = []
    for path in predicate:
        total_path = []
        for section in path.part:
            if hasattr(section.part, "prefix"):
                total_path.append(f"{prefix_dict[section.part.prefix]}{section.part.localname}")
            else:
                total_path.append(path.part[0].part)
        predicate = ", ".join(total_path)
        predicates.append(predicate)
    predicates = " OR ".join(predicates)
    return predicates


def extract_object(triple, prefix_dict):
    if hasattr(triple[2], "prefix"):
        # object
        prefix = ""
        value = ""
        localname = ""
        if triple[2].prefix:
            # Object with prefix used
            prefix = prefix_dict[triple[2].prefix]
        if triple[2].string:
            value = triple[2].string
        if triple[2].localname:
            localname = triple[2].localname
        triple_object = f"{prefix}{localname}{value}"
    else:
        triple_object = triple[2]

    return triple_object


# TODO: this method only works for triple of type ?var1 SinglePath ?var2
def add_triple(triples, subject, predicate, object):
    """
    Add a triple to the triples list in input.
    Format: PathAlternative = {part: [PathSequence = {part: PathElt}]}
    The created triple is directly added to triples list

    :triples: list containing every triple of the SPARQL where statement
    :subject: triple subject
    :predicate: triple predicate
    :object: triple predicate
    """
    predicate_tokens = CompValue("PathAlternative",
                                 part=[CompValue("PathSequence",
                                                 part=[CompValue("PathElt", part=URIRef(predicate))])])
    new_triple = [Variable(subject), predicate_tokens, Variable(object)]
    triples.append(new_triple)


def extract_projection_variable(tree_part):
    """
    If the tree_part passed has a 'projection' section, a list containing every variable is returned. If there
    is no 'projection' section an empty list is returned instead.

    :tree_part: parseResult checked
    :returns: a list containing every retrieved variable in the checked tree_part
    """

    if "projection" in tree_part:
        # Projection variable extraction
        return [variable.var for variable in tree_part.projection]
    return []


def parse_SPARQL_query(query, is_tree=False):
    """
    Parse the given SPARQL query and extracts SELECT variables, WHERE triples and filters
    :query: string representing the query to parse or a tree in parseResult format
    :is_tree: this flag has to be enabled in order to use the parseResult format
    """

    if not is_tree:
        tree = parseQuery(query)  # parseResult
    else:
        tree = query

    prefixes = tree[0]  # prefixes are contained in a list in the first element of the tree

    prefix_dict = {}  # {prefix_name: prefix_value}
    variables = []  # variable used for result projection

    for part in prefixes:
        # Check the Prefix section
        if hasattr(part, "prefix"):
            prefix_dict[part.prefix] = part.iri

    where_part = None  # where statement
    triples = None  # triples in the triple block of the where statement

    for part in tree:

        # Recover variables in SELECT part
        variables += extract_projection_variable(part)
        filters = []
        if part.where:
            where_part = part.where.part
            for triple_block in part.where.part:
                if "triples" in triple_block:
                    # ordinary triple expression
                    triples = triple_block.triples
                    handle_triples(triple_block, prefix_dict)
                else:
                    # filter expression
                    filters.append(handle_filters(triple_block))
                print("==================")

    return where_part, triples, tree, filters, prefix_dict
