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

from collections import defaultdict

import sqlparse
import sqlparse.sql as S
import sqlparse.tokens as T

if __package__:
    from .sqlparser import _token_first
    from .sqlparser import Node
    from .sqlparser import parse
    from ..query import Query
else:
    from mosaicrown.sql.sqlparser import _token_first
    from mosaicrown.sql.sqlparser import Node
    from mosaicrown.sql.sqlparser import parse
    from mosaicrown.query import Query


class SQLQuery(Query):
    """A SQL query."""

    def __init__(self, query):
        """Parse the given SQL query and creates a tree representation."""
        forest = parse(query)
        if not forest or len(forest) > 1:
            raise Exception("None or too many statements in the given query.")
        self.root = forest[0]

        self._resolve_select_aliases()
        self._resolve_from_aliases()

    def __str__(self):
        """Render the query."""
        return self.root.__str__()

    def _resolve_select_aliases(self):
        """Resolve the projection aliases.

        Manages the alias scope, by inheriting aliases declared in the parent
        node to the child nodes, and removes columns identifiers that
        corresponds to aliases.
        """
        def __resolve_select_aliases(root):
            if not root or root.state.aliases is None:
                return

            root.state.cols = [
                col for col in root.state.cols
                if col.normalized not in root.state.aliases
            ]

            for child in root.childs:
                # inherit outer scope aliases
                child.state.aliases.union(root.state.aliases)
                __resolve_select_aliases(child)

            root.state.aliases = None

        __resolve_select_aliases(self.root)

    # TODO: might need to resolve tables and aliases globally
    def _resolve_from_aliases(self):
        """Resolve the table aliases.

        Manages the alias scope, by inheriting aliases declared in the parent
        node to the child nodes, and substitutes table aliases with the table
        they refer to.
        """
        def __resolve_from_aliases(root, tables, aliases):

            # to avoid side effects on the parent node
            tables = set(tables)
            aliases = dict(aliases)

            for table in root.state.tables:
                tables.add(table.normalized)
                if table.has_alias():
                    aliases[table.get_alias()] = table.normalized

            for col in root.state.cols:
                column = col.normalized
                # separate anonimization function from column
                column = column.partition('/')[0]
                column = column.replace("`", "").replace("`", "")
                if column.count('.') == 1:
                    table_name, column_name = column.split('.')
                    # tables have priority over aliases
                    if table_name not in tables and table_name in aliases:
                        col.normalized = aliases[table_name] + "." + column_name

            for child in root.childs:
                __resolve_from_aliases(child, tables, aliases)

        __resolve_from_aliases(self.root, set(), dict())

    def add_constraints(self, cons):
        """Add constraints to the SQL query.

        :cons: An iterable containing constraints.
        """
        if not cons or (not cons.permissions and not cons.prohibitions):
            return

        targets = self.get_targets()
        # consider iterating over the targets ignoring other entries
        tables = set(cons.permissions.keys()) | set(cons.prohibitions.keys())
        for table in tables:
            if table not in targets:
                raise ValueError(f"invalid constaint: unknown table {table}")

        # translate constraints to subqueries
        subqueries = dict()
        for table in tables:
            permissions, prohibitions = "", ""
            if table in cons.permissions:
                to_and = []
                for to_or in cons.permissions[table]:
                    if len(to_or) == 1:
                        to_and.append(str(to_or[0]))
                    elif len(to_or) > 1:
                        to_and.append(f"({' OR '.join(map(str, to_or))})")
                permissions = " AND ".join(to_and)
            if table in cons.prohibitions:
                prohibitions = " OR ".join(map(str, cons.prohibitions[table]))

            if permissions and prohibitions:
                subquery = f"""
                    (SELECT * FROM {table}
                    WHERE ({permissions}) AND NOT ({prohibitions}))
                """
            elif permissions:
                subquery = f"(SELECT * FROM {table} WHERE ({permissions}))"
            else:
                subquery = f"(SELECT * FROM {table} WHERE NOT ({prohibitions}))"

            subqueries[table] = _token_first(sqlparse.parse(subquery)[0].tokens)

        def _rewrite(root, subqueries):
            for idx, table in enumerate(root.state.tables):
                norm = table.normalized
                if norm in subqueries:
                    alias = norm if not table.has_alias() else table.get_alias()
                    root.state.tables[idx].tokens = [
                        subqueries[norm],
                        S.Token(T.Whitespace, " "),
                        S.Token(T.Keyword, "AS"),
                        S.Token(T.Whitespace, " "),
                        S.Identifier([S.Token(T.Name, alias)])
                    ]

            for child in root.childs:
                _rewrite(child, subqueries)

        # update the query
        _rewrite(self.root, subqueries)

    def get_subqueries(self):
        """Return an enumeration of targets, each representing a (sub)query targets.

        :return: An enumeration of dictionaries representing the targets each
            (sub)queries uses.
        """

        def _get_subqueries(root, known_tables):
            subqueries = []
            if not root:
                return subqueries

            # to avoid side effects on the parent node
            known_tables = set(known_tables)
            for table in root.state.tables:
                known_tables.add(table.normalized)

            subqueries.append(to_dict(root, known_tables))
            for child in root.childs:
                subqueries.extend(_get_subqueries(child, known_tables))
            return subqueries

        subqueries = _get_subqueries(self.root, set())
        # attach numerical identifier to subqueries
        return list(enumerate(subqueries))

    def get_targets(self):
        """Return a disctionary representing the access request of the query.

        :return: A dictionary of the table-column pairs the query accesses.
        """
        def _back_to_common_state(root, node):
            if not root:
                return node

            node.state.cols.extend(root.state.cols)
            node.state.tables.extend(root.state.tables)

            for child in root.childs:
                _back_to_common_state(child, node)

            return node

        node = _back_to_common_state(self.root, Node())

        known_tables = {table.normalized for table in node.state.tables}
        return to_dict(node, known_tables)


def to_dict(node, known_tables):
    """Convert the node to a dictionary representation.

    The dictionary represents the tables and columns identifiers used by the
    query.

    :node: The node on which the function operates.
    :known_tables: The set of tables the query has scope on.
    :return: The dictionary representing the targets the statement uses.
    """
    targets = defaultdict(set)
    for col in node.state.cols:
        table_name, column_name = split_table_from_column(col.normalized)
        if table_name not in known_tables:
            raise Exception(
                f"invalid syntax: unknown table {table_name}"
            )
        targets[table_name].add(column_name)
    return targets


def split_table_from_column(column):
    # separate anonimization function from column
    column, sep, fun = column.partition('/')
    column = column.replace("`", "").replace("`", "")
    if column.count('.') != 1:
        # columns resolution requires information on the schema
        raise Exception(
            f"invalid syntax: {column} has none or too many '.'"
        )
    table_name, column_name = column.split('.')
    # re-attach the anonimization function
    if fun:
        column_name = column_name + sep + fun
    return table_name, column_name


def get_targets_from_query(query, IRIs):
    """Convert targets representation to IRI.

    :query: The query that the user wants to perform in SQL format.
    :IRIs: A dictionary that maps the name of a database to an IRI.
    :return: A targets dictionary that uses IRI for tables.
    """
    targets = SQLQuery(query).get_targets()
    try:
        return {IRIs[table]: set(targets[table]) for table in targets}
    except KeyError as ke:
        raise Exception(f"No IRI known for table: {ke.args[0]}")
