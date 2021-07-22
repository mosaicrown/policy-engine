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

from pathlib import Path

import pytest
import rdflib
from pytest import raises
from rdflib import Literal
from rdflib import plugin
from rdflib import query as q
from rdflib import URIRef
from rdflib import Variable
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.evaluate import evalQuery

from mosaicrown import vocabularies, utils
from mosaicrown.namespaces import ODRL, MOSAICROWN
from mosaicrown.sparql.sparqlparser import add_filter
from mosaicrown.sparql.sparqlparser import add_triple
from mosaicrown.sparql.sparqlparser import extract_subject
from mosaicrown.sparql.sparqlparser import extract_object
from mosaicrown.sparql.sparqlparser import extract_predicates
from mosaicrown.sparql.sparqlparser import parse_SPARQL_query
from mosaicrown.sql.sqlconstraint import SQLConstraint
from mosaicrown.sql.sqlconstraint import SQLConstraints
from mosaicrown.sql.sqlquery import SQLQuery
from mosaicrown.utils import get_target_constraints


@pytest.fixture
def load_graph(request):
    file = request.param
    test_dir = Path(__file__).parent

    # create empty RDF graph
    graph = rdflib.Graph()

    # parse ODRL vocabolary
    graph.parse(vocabularies.JSON_LD["ODRL"], format="json-ld")

    # parse MOSAICROWN vocabulary
    # only the namespace is downloaded at runtime by RDFLib, NOT the vocabulary
    graph.parse(f"{test_dir}/files/ns/mosaicrown/vocabulary.json", format="json-ld")

    # parse policy
    graph.parse(f"{test_dir}/files/policies/{file}", format="json-ld")

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

    return graph


@pytest.fixture()
def query_targets(request):
    queries = {
        "student": "SELECT student.sex FROM student",
        "professor": "SELECT professor.age FROM professor",
        "secretary": "SELECT secretary.age FROM secretary"
    }
    expectations = {
        "student": ["SELECT student.sex FROM (SELECT * FROM student WHERE (sex = female AND age >= 18)) AS student",
                    "SELECT student.sex FROM (SELECT * FROM student WHERE (age >= 18 AND sex = female)) AS student"],
        "professor": ["SELECT professor.age FROM (SELECT * FROM professor WHERE (sex = male)) AS professor"],
        "secretary": ["SELECT secretary.age FROM (SELECT * FROM secretary WHERE ((sex != female OR age <= 30))) "
                      "AS secretary", "SELECT secretary.age FROM (SELECT * FROM secretary "
                                      "WHERE ((age <= 30 OR sex != female))) AS secretary"]
    }
    return queries[request.param], expectations[request.param]


def strip(string):
    print(" ".join(string.split()))
    return " ".join(string.split())


def eq(str1, str2):
    return strip(str1) == strip(str2)


def test_no_constraints():
    query = "SELECT A.a FROM A"
    constraints = None
    expectation = query

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


def test_only_permissions():
    query = "SELECT A.a FROM A"
    constraints = SQLConstraints(
        permissions={"A": [[SQLConstraint("b", "=", "true")]]},
        prohibitions={}
    )
    expectation = "SELECT A.a FROM (SELECT * FROM A WHERE (b = true)) AS A"

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


def test_only_prohibitions():
    query = "SELECT A.a FROM A"
    constraints = SQLConstraints(
        permissions={},
        prohibitions={"A": [SQLConstraint("b", "=", "true")]}
    )
    expectation = """
        SELECT A.a FROM (SELECT * FROM A WHERE NOT (b = true)) AS A
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


def test_multiple_or_d_permissions():
    query = "SELECT A.a FROM A"
    constraints = SQLConstraints(
        permissions={
            "A": [
                [
                    SQLConstraint("b", "=", "true"),
                    SQLConstraint("c", "=", "true")
                ],
                [
                    SQLConstraint("d", "=", "true"),
                    SQLConstraint("e", "=", "true")
                ]
            ]
        },
        prohibitions={}
    )
    expectation = """
        SELECT A.a
        FROM (SELECT *
              FROM A
              WHERE ((b = true OR c = true) AND
                    (d = true OR e = true))) AS A
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


def test_multiple_permissions_and_prohibitions():
    query = "SELECT A.a FROM A"
    constraints = SQLConstraints(
        permissions={
            "A": [
                [SQLConstraint("b", "=", "true")],
                [SQLConstraint("c", "=", "true")],
            ]
        },
        prohibitions={
            "A": [
                SQLConstraint("d", "=", "true"),
                SQLConstraint("e", "=", "true"),
            ]
        }
    )
    expectation = """
        SELECT A.a
        FROM (SELECT *
              FROM A
              WHERE (b = true AND c = true) AND
                    NOT (d = true OR e = true)) AS A
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


def test_constraint_with_multiple_identifiers():
    query = "SELECT A.a FROM A"
    constraints = SQLConstraints(
        permissions={"A": [[SQLConstraint("b", "=", "c")]]},
        prohibitions={}
    )
    expectation = """
        SELECT A.a
        FROM (SELECT *
              FROM A
              WHERE (b = c)) AS A
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


def test_constraint_with_unknown_table():
    query = "SELECT A.a FROM A"
    constraints = SQLConstraints(
        permissions={"B": [[SQLConstraint("b", "=", "c")]]},
        prohibitions={}
    )
    sqlquery = SQLQuery(query)
    with raises(Exception,
                match="invalid constaint: unknown table"):
        sqlquery.add_constraints(constraints)


EXAM_PERMISSIONS = {
    "exam": [[SQLConstraint("CourseId", "=", "DB")]]
}

EXAM_PROHIBITIONS = {
    "exam": [SQLConstraint("Date", "=", "19/02/2020")]
}

STUDENT_PERMISSIONS = {
    "student": [
        [SQLConstraint("1000", "<", "Income")],
        [SQLConstraint("Income", "<", "2000")],
    ]
}

STUDENT_PROHIBITIONS = {
    "student": [SQLConstraint("Ethnicity", "IN", "('Asian', 'Hispanic')")]
}


# SELECT
def test_select():
    query = """
        SELECT student.Id, student.Sex
        FROM student
    """
    constraints = SQLConstraints(
        permissions=STUDENT_PERMISSIONS,
        prohibitions=STUDENT_PROHIBITIONS
    )
    expectation = """
        SELECT student.Id, student.Sex
        FROM (SELECT *
              FROM student
              WHERE (1000 < Income AND Income < 2000) AND
                    NOT (Ethnicity IN ('Asian', 'Hispanic'))) AS student
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


def test_select_with_subquery():
    query = """
        SELECT student.Id, (SELECT MAX(exam.Grade)
                            FROM exam
                            WHERE exam.StudentId = student.Id)
        FROM student
    """
    constraints = SQLConstraints(
        permissions={**STUDENT_PERMISSIONS, **EXAM_PERMISSIONS},
        prohibitions={**STUDENT_PROHIBITIONS, **EXAM_PROHIBITIONS}
    )
    expectation = """
        SELECT student.Id, (SELECT MAX(exam.Grade)
                            FROM (SELECT *
                                  FROM exam
                                  WHERE (CourseId = DB) AND
                                        NOT (Date = 19/02/2020)) AS exam
                            WHERE exam.StudentId = student.Id)
        FROM (SELECT *
              FROM student
              WHERE (1000 < Income AND Income < 2000) AND
                    NOT (Ethnicity IN ('Asian', 'Hispanic'))) AS student
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


# FROM
def test_inner_join():
    query = """
        SELECT student.Sex, exam.Grade
        FROM student INNER JOIN exam
        ON student.Id = exam.StudentId
    """
    constraints = SQLConstraints(
        permissions={**STUDENT_PERMISSIONS, **EXAM_PERMISSIONS},
        prohibitions={**STUDENT_PROHIBITIONS, **EXAM_PROHIBITIONS}
    )
    expectation = """
        SELECT student.Sex, exam.Grade
        FROM (SELECT *
              FROM student
              WHERE (1000 < Income AND Income < 2000) AND
                    NOT (Ethnicity IN ('Asian', 'Hispanic')))
             AS student
             INNER JOIN
             (SELECT *
              FROM exam
              WHERE (CourseId = DB) AND NOT (Date = 19/02/2020))
             AS exam
             ON student.Id = exam.StudentId
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


def test_inner_join_with_subquery():
    query = """
        SELECT student.Id, exam.Grade
        FROM (SELECT student.Id
              FROM student
              WHERE student.Sex = "Female") INNER JOIN exam
        ON student.Id = exam.StudentId
    """
    constraints = SQLConstraints(
        permissions={**STUDENT_PERMISSIONS, **EXAM_PERMISSIONS},
        prohibitions={**STUDENT_PROHIBITIONS, **EXAM_PROHIBITIONS}
    )
    expectation = """
        SELECT student.Id, exam.Grade
        FROM (SELECT student.Id
              FROM (SELECT *
                    FROM student
                    WHERE (1000 < Income AND Income < 2000) AND
                          NOT (Ethnicity IN ('Asian', 'Hispanic')))
                   AS student
              WHERE student.Sex = "Female")
        INNER JOIN
        (SELECT *
         FROM exam
         WHERE (CourseId = DB) AND
               NOT (Date = 19/02/2020)) AS exam
        ON student.Id = exam.StudentId
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


# WHERE
def test_where_with_subquery():
    query = """
        SELECT exam.CourseId, student.Id
        FROM student JOIN exam as outer_exam
        ON student.Id = exam.StudentId
        WHERE exam.Grade = (SELECT MAX(exam.Grade)
                            FROM exam
                            WHERE exam.CourseId = outer_exam.CourseId)
    """
    constraints = SQLConstraints(
        permissions={**STUDENT_PERMISSIONS, **EXAM_PERMISSIONS},
        prohibitions={**STUDENT_PROHIBITIONS, **EXAM_PROHIBITIONS}
    )
    expectation = """
        SELECT exam.CourseId, student.Id
        FROM (SELECT *
              FROM student
              WHERE (1000 < Income AND Income < 2000) AND
                    NOT (Ethnicity IN ('Asian', 'Hispanic')))
             AS student
             JOIN
             (SELECT *
              FROM exam
              WHERE (CourseId = DB) AND
                    NOT (Date = 19/02/2020)) AS outer_exam
             ON student.Id = exam.StudentId
             WHERE exam.Grade = (SELECT MAX(exam.Grade)
                                 FROM (SELECT *
                                       FROM exam
                                       WHERE (CourseId = DB) AND
                                             NOT (Date = 19/02/2020))
                                       AS exam
                                 WHERE exam.CourseId = outer_exam.CourseId)
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


# ALIAS
def test_table_alias():
    query = """
        SELECT S.Id, E.Date, E.CourseId, E.StudentId
        FROM student S, exam E
    """
    constraints = SQLConstraints(
        permissions={**STUDENT_PERMISSIONS, **EXAM_PERMISSIONS},
        prohibitions={**STUDENT_PROHIBITIONS, **EXAM_PROHIBITIONS}
    )
    expectation = """
        SELECT S.Id, E.Date, E.CourseId, E.StudentId
        FROM (SELECT *
              FROM student
              WHERE (1000 < Income AND Income < 2000) AND
              NOT (Ethnicity IN ('Asian', 'Hispanic'))) AS S,
             (SELECT *
              FROM exam
              WHERE (CourseId = DB) AND
                    NOT (Date = 19/02/2020)) AS E
    """

    sqlquery = SQLQuery(query)
    sqlquery.add_constraints(constraints)
    rewritten = sqlquery.render()
    assert eq(rewritten, expectation)


# WITH CONSTRAINTS EXTRACTED FROM THE POLICY
@pytest.mark.parametrize('load_graph, query_targets', [("policy.jsonld", "student"), ("policy.jsonld", "professor"),
                                                       ("policy.jsonld", "secretary")],
                         indirect=['load_graph', 'query_targets'])
def test_recover_simple(load_graph, query_targets):
    graph = load_graph
    query, expectations = query_targets
    sqlquery = SQLQuery(query)
    for target in sqlquery.get_targets():
        result = get_target_constraints(graph, target)
        constraints = SQLConstraints.create_constraints(result, target)
        sqlquery.add_constraints(constraints)

    rewritten = sqlquery.render()
    print("==============")
    print(f"{rewritten}\n{expectations[0]}")
    print("==============\n")
    assert rewritten in expectations


# REWRITE SPARQL QUERY
def test_simple_SPARQL_rewrite():

    # Parse RDF graph
    g = rdflib.Graph()
    test_dir = Path(__file__).parent
    g.parse(f"{test_dir}/files/rdf/test_data.rdf")

    query = """SELECT ?name
    WHERE {
    ?p a <http://www.w3.org/2006/vcard/ns#Individual>.
    ?p <http://www.w3.org/2006/vcard/ns#Name> ?name
    }"""

    # Result containing every name of every Individual in test_data.rdf
    normal_result = [row[0] for row in g.query(query)]

    # Assert normal results size and contents
    assert len(normal_result) == 2
    assert all(person in normal_result for person in [Literal('Corks'), Literal('John')])

    # Parse the querystring
    where, triples, tree, filters, prefix_dict = parse_SPARQL_query(query)

    # Recover data from the recovered triples
    for triple in triples:
        if extract_predicates(triple, prefix_dict) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" and \
                extract_object(triple, prefix_dict) == URIRef("http://www.w3.org/2006/vcard/ns#Individual"):
            variable = extract_subject(triple)

    # Assert the correct source variable is recovered
    assert variable == Variable("p")

    # Add triple and filter relative to constraint to the parse tree
    add_triple(triples, str(variable), "http://www.w3.org/2006/vcard/ns#country-name", "x")  #?p vcard:country ?x
    add_filter(where, "x", "=", "Italy")  # FILTER (?x = "Italy)

    # Let rdflib do its magic
    result_converter = plugin.get("sparql", q.Result)
    rewritten_result = [row[0] for row in result_converter(evalQuery(g, translateQuery(tree), initBindings={}))]

    # Assert rewritten query result size and contents
    assert len(rewritten_result) == 1
    assert all(person in rewritten_result for person in [Literal('John')])
