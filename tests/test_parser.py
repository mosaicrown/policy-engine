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

from pytest import raises
from rdflib import Variable

from mosaicrown.sparql.sparqlparser import extract_object
from mosaicrown.sparql.sparqlparser import extract_predicates
from mosaicrown.sparql.sparqlparser import extract_subject
from mosaicrown.sparql.sparqlparser import parse_SPARQL_query
from mosaicrown.sql.sqlquery import SQLQuery


# SELECT
def test_select():
    query = """
        SELECT student.Id, student.Sex
        FROM student
    """
    assert SQLQuery(query).get_targets() == {"student": {"Id", "Sex"}}


def test_select_modifier():
    query = """
        SELECT DISTINCT student.Ethnicity
        FROM student
    """
    assert SQLQuery(query).get_targets() == {"student": {"Ethnicity"}}


def test_select_with_subquery():
    query = """
        SELECT student.Id, (SELECT MAX(exam.Grade)
                            FROM exam
                            WHERE exam.StudentId = student.Id)
        FROM student
    """
    expectation = {"student": {"Id"}, "exam": {"StudentId", "Grade"}}
    assert SQLQuery(query).get_targets() == expectation


# FROM
def test_cross_join():
    query = """
        SELECT student.Id, exam.Date, exam.CourseId, exam.StudentId
        FROM student, exam
    """
    expectation = {
        "student": {"Id"},
        "exam": {"Date", "CourseId", "StudentId"}
    }
    assert SQLQuery(query).get_targets() == expectation


def test_cross_join_with_subquery():
    query = """
        select K.a,K.b
        from (
            select H.b
            from (
                select G.c
                from (
                    select F.d
                    from (
                        select E.e
                        from A, B, C, D, E
                    ), F
                ), G
            ), H
        ), I, J, K
    """
    expectation = {
        "K": {"a", "b"},
        "H": {"b"},
        "G": {"c"},
        "F": {"d"},
        "E": {"e"}
    }
    assert SQLQuery(query).get_targets() == expectation


def test_inner_join():
    query = """
        SELECT student.Sex, exam.Grade
        FROM student INNER JOIN exam
        ON student.Id = exam.StudentId
    """
    expectation = {"student": {"Sex", "Id"}, "exam": {"StudentId", "Grade"}}
    assert SQLQuery(query).get_targets() == expectation


def test_multiple_inner_join():
    query = """
        select A.a
        from ((A join B on A.id = B.id) join C on A.id = C.id)
            join (D join (E join F on E.id = F.id) on D.id = E.id)
                on A.id = F.id
            join G on A.id = G.id
    """
    expectation = {
        "A": {"id", "a"},
        "B": {"id"},
        "C": {"id"},
        "D": {"id"},
        "E": {"id"},
        "F": {"id"},
        "G": {"id"}
    }
    assert SQLQuery(query).get_targets() == expectation


def test_inner_join_with_subquery():
    query = """
        select A.a
        from (select A.a from A)
            join B on A.a = B.a
            join (select C.c from C) on B.c = C.c
    """
    expectation = {"A": {"a"}, "B": {"a", "c"}, "C": {"c"}}
    assert SQLQuery(query).get_targets() == expectation


def test_useless_table():
    query = """
        SELECT student.Id
        FROM student, exam
    """
    assert SQLQuery(query).get_targets() == {"student": {"Id"}}


# WHERE
def test_where():
    query = """
        SELECT student.Id, exam.CourseId
        FROM student JOIN exam
        ON student.Id = exam.StudentId
        WHERE exam.Grade > 27
    """
    expectation = {
        "student": {"Id"},
        "exam": {"StudentId", "CourseId", "Grade"}
    }
    assert SQLQuery(query).get_targets() == expectation


def test_where_with_subquery():
    query = """
        SELECT exam.CourseId, student.Id
        FROM student JOIN exam as outer_exam
        ON student.Id = exam.StudentId
        WHERE exam.Grade = (SELECT MAX(exam.Grade)
                            FROM exam
                            WHERE exam.CourseId = outer_exam.CourseId)
    """
    expectation = {
        "student": {"Id"},
        "exam": {"StudentId", "CourseId", "Grade"}
    }
    assert SQLQuery(query).get_targets() == expectation


# GROUP BY ... HAVING ...
def test_group_by():
    query = """
        SELECT AVG(exam.Grade)
        FROM exam
        GROUP BY exam.CourseId, exam.Date
    """
    expectation = {"exam": {"CourseId", "Date", "Grade"}}
    assert SQLQuery(query).get_targets() == expectation


def test_group_by_having():
    query = """
        SELECT AVG(exam.Grade)
        FROM exam
        GROUP BY exam.CourseId, exam.Date
        HAVING COUNT(exam.StudentId) > 100
    """
    expectation = {"exam": {"StudentId", "CourseId", "Date", "Grade"}}
    assert SQLQuery(query).get_targets() == expectation


# ORDER BY
def test_order_by():
    query = """
        SELECT student.Id
        FROM student
        ORDER BY student.BirthDate DESC NULLS LAST,
                 student.Income ASC NULLS FIRST
    """
    expectation = {"student": {"Id", "BirthDate", "Income"}}
    assert SQLQuery(query).get_targets() == expectation


def test_order_by_case():
    query = """
        SELECT student.Id
        FROM student
        ORDER BY (CASE
                      WHEN student.BirthDate IS NULL THEN student.Id
                      ELSE student.BirthDate
                  END) DESC NULLS LAST, student.Income ASC NULLS FIRST
    """
    expectation = {"student": {"Id", "BirthDate", "Income"}}
    assert SQLQuery(query).get_targets() == expectation


# OPERATIONS
def test_operations():
    query = """
        SELECT "CF:"||professor.Cf,
               1.5*(professor.Salary+100)-(3)*student.Income
        FROM student
        JOIN exam ON student.Id = exam.StudentId
        JOIN course ON exam.CourseId = course.Cid
        JOIN professor ON course.ProfCf = professor.Cf
        WHERE student.Id = "12345678"
    """
    expectation = {
        "student": {"Id", "Income"},
        "exam": {"StudentId", "CourseId"},
        "course": {"Cid", "ProfCf"},
        "professor": {"Cf", "Salary"}
    }
    assert SQLQuery(query).get_targets() == expectation


def test_is_operator():
    query = """
        SELECT student.Id
        FROM student
        WHERE student.Ethnicity IS NOT NULL
    """
    expectation = {"student": {"Id", "Ethnicity"}}
    assert SQLQuery(query).get_targets() == expectation


def test_in_operator():
    query = """
        SELECT student.Id
        FROM student
        WHERE student.Ethnicity IN ("Asian", "Hispanic")
    """
    expectation = {"student": {"Id", "Ethnicity"}}
    assert SQLQuery(query).get_targets() == expectation


# FUNCTIONS
def test_std_functions():
    query = """
        SELECT COUNT(exam.CourseId)
        FROM student JOIN exam
        ON student.Id = exam.StudentId
        WHERE student.Id = "12345678" AND DATEDIFF(NOW(), exam.Date) < 365
    """
    expectation = {
        "student": {"Id"},
        "exam": {"StudentId", "CourseId", "Date"}
    }
    assert SQLQuery(query).get_targets() == expectation


def test_std_functions_modifier():
    query = """
        SELECT COUNT(ALL exam.CourseId)
        FROM student JOIN exam
        ON student.Id = exam.StudentId
    """
    expectation = {"student": {"Id"}, "exam": {"StudentId", "CourseId"}}
    assert SQLQuery(query).get_targets() == expectation


def test_mosaicrown_functions():
    query = """
        SELECT TOKENIZE(student.Id),
               L_DIVERSITY(student.Sex, student.Ethnicity, exam.Grade)
        FROM student JOIN exam
        ON student.Id = exam.StudentId
        WHERE exam.CourseId = "DB" AND DATEDIFF(NOW(), exam.Date) < 365
    """
    expectation = {
        "student": {
            "Id",
            "Id/tokenize",
            "Sex/l_diversity",
            "Ethnicity/l_diversity"
        },
        "exam": {
            "StudentId",
            "CourseId",
            "Date",
            "Grade/l_diversity"
        }
    }
    assert SQLQuery(query).get_targets() == expectation


# CASE
def test_case():
    query = """
        SELECT student.Id,
        CASE student.Ethnicity
            WHEN 'Asian' THEN 'Asia'
            WHEN 'Hispanic' THEN 'Latin America'
            ELSE 'Somewhere'
        END
        FROM student
    """
    expectation = {"student": {"Id", "Ethnicity"}}
    assert SQLQuery(query).get_targets() == expectation


def test_case_when():
    query = """
        SELECT student.Id,
        CASE
            WHEN student.Income < 1000 THEN 'Nothing'
            WHEN student.Income < 1500 THEN 'Some'
            ELSE 'Maximum'
        END
        FROM student
    """
    expectation = {"student": {"Id", "Income"}}
    assert SQLQuery(query).get_targets() == expectation


# ALIAS
def test_select_with_alias():
    query = """
        SELECT student.Id BadgeNumber,
            12.546 AS F,
            "something" AS S,
            '' AS EMP, NULL AS N,
            student.Income / 12 AS Monthly,
            YEAR(student.BirthDate) AS YearOfBirth,
            CASE student.Sex
                WHEN 'M' THEN 'Male'
                WHEN 'F' < 1500 THEN 'Female'
                ELSE 'Other'
            END AS FullSex,
            (SELECT MAX(exam.Grade)
             FROM exam
             WHERE exam.StudentId = student.Id) AS MaxGrade
        FROM student
    """
    expectation = {
        "student": {"Id", "Income", "BirthDate", "Sex"},
        "exam": {"StudentId", "Grade"}
    }
    assert SQLQuery(query).get_targets() == expectation


def test_table_alias():
    query = """
        SELECT S.Id, E.Date, E.CourseId, E.StudentId
        FROM student S, exam E
    """
    expectation = {
        "student": {"Id"},
        "exam": {"Date", "CourseId", "StudentId"}
    }
    assert SQLQuery(query).get_targets() == expectation


# requires knowledge of the schema
def test_cross_join_alias():
    query = """
        SELECT SE.Id, SE.Date, SE.CourseId, SE.StudentId
        FROM (student, exam) SE
    """
    with raises(Exception,
                match="Alias of complex tables is not supported yet."):
        SQLQuery(query)

    # expectation = {
    #     "student": {"Id"},
    #     "exam": {"Date", "CourseId", "StudentId"}
    # }
    # assert SQLQuery(query).get_targets() == expectation


# requires knowledge of the schema
def test_inner_join_alias():
    query = """
        SELECT SE.Sex, SE.Grade
        FROM (student INNER JOIN exam
        ON student.Id = exam.StudentId) SE
    """
    with raises(Exception,
                match="Alias of complex tables is not supported yet."):
        SQLQuery(query)

    # expectation = {"student": {"Id", "Sex"}, "exam": {"StudentId", "Grade"}}
    # assert SQLQuery(query).get_targets() == expectation


def test_inner_join_with_subquery_alias():
    query = """
        select AB.b from (select A.a, B.b from A, B) AS AB join C on AB.a = C.a
    """
    with raises(Exception,
                match="Alias of complex tables is not supported yet."):
        SQLQuery(query)

    # expectation = {"A": {"a"}, "B": {"b"}, "C": {"a"}}
    # assert SQLQuery(query).get_targets() == expectation


def test_where_with_alias():
    query = """
        SELECT student.Id BadgeNumber,
            student.Income / 12 AS Monthly,
            YEAR(student.BirthDate) AS YearOfBirth,
            CASE student.Sex
                WHEN 'M' THEN 'Male'
                WHEN 'F' < 1500 THEN 'Female'
                ELSE 'Other'
            END AS FullSex,
            (SELECT MAX(exam.Grade)
             FROM exam
             WHERE exam.StudentId = student.Id) AS MaxGrade
        FROM student
        WHERE BadgeNumber > "12345678" AND Monthly > 1000 AND
            YearOfBirth < 20 AND FullSex IN ('Female', 'Other') AND
            MaxGrade = 30
    """
    expectation = {
        "student": {"Id", "Income", "BirthDate", "Sex"},
        "exam": {"StudentId", "Grade"}
    }
    assert SQLQuery(query).get_targets() == expectation


def test_aliases_everywhere():
    query = """
        select C.c AS CC
        from (select A_T.a AS AA, B_T.b AS BB from A AS A_T, B AS B_T)
            join C on A.a = C.c
        where EXISTS(select D_T.d AS DD, E_T.e AS BB from D AS D_T, E AS E_T)
    """
    expectation = {"A": {"a"}, "B": {"b"}, "C": {"c"}, "D": {"d"}, "E": {"e"}}
    assert SQLQuery(query).get_targets() == expectation


# EXTRACT TARGETS FROM SPARQL QUERY
def test_simple_SPARQL_parsing():

    example = '''
            PREFIX dbpedia-owl: <http://dbpedia.org/ontology/>
            SELECT ?p ?h ?c WHERE {
            ?p a dbpedia-owl:Artist.
            ?h dbpedia-owl:birthPlace | dbpedia-owl:district ?c.
            ?c <http://xmlns.com/foaf/0.1/name> "York"@en.
            FILTER (?p IN (<http://example.org/JohnDoe>, <http://example.org/Jack>)).
            FILTER (?p < 0.35)
            }
            '''
    # Extraction procedure and parse tree creation
    where, triples, tree, filters, prefix_dict = parse_SPARQL_query(example)

    # General control on dimension
    assert len(where) == 3  # 1 triple section + 2 filters
    assert len(triples) == 3  # 3 triples

    # Expected values
    subjects = [Variable("p"), Variable("h"), Variable("c")]
    predicates = ["http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                  "http://dbpedia.org/ontology/birthPlace OR http://dbpedia.org/ontology/district",
                  "http://xmlns.com/foaf/0.1/name"]
    objects = ["http://dbpedia.org/ontology/Artist", Variable("c"), "York"]

    # Expected filters
    f_sub = [Variable("p"), Variable("p")]
    operators  = ["IN", "<"]
    f_obj = ['http://example.org/JohnDoe, http://example.org/Jack', "0.35"]

    # Triples controls
    for triple in triples:
        assert extract_subject(triple) == subjects.pop(0)
        assert extract_predicates(triple, prefix_dict) == predicates.pop(0)
        assert extract_object(triple, prefix_dict) == objects.pop(0)

    # Filters controls
    for filter in filters:
        assert filter[0] == f_sub.pop(0)
        assert filter[1] == operators.pop(0)
        assert filter[2] == f_obj.pop(0)
