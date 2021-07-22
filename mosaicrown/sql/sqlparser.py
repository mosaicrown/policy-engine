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

import sqlparse
import sqlparse.sql as S
import sqlparse.tokens as T


DEBUG = False


class Node:
    """A node of the tree, it holds information on a (sub)query.

    :state: Represents the (sub)query targets.
    :childs: The list of references to the child nodes.
    """

    class State:
        """Represents the (sub)query targets and tokens.

        :aliases: The list of aliases the (sub)query declares in its
            projection.
        :cols: The list of columns identifier the (sub)query uses as
            projection and selection.
        :tables: The list of tables the (sub)query uses.
        :tokens: The list of tokens representing the (sub)query.
        """

        def __init__(self):
            self.aliases = set()
            self.cols = []
            self.tables = []
            self.tokens = None

        def __str__(self):

            def flatten(tokens):
                """Yield the leaf tokens forming the query."""
                for token in tokens:
                    if isinstance(token, Node.State) or token.is_group:
                        for subtoken in flatten(token.tokens):
                            yield subtoken
                    else:
                        yield token

            return u''.join(token.value for token in flatten(self.tokens))

    def __init__(self):
        self.state = Node.State()
        self.childs = []

    def __str__(self):
        return self.state.__str__()


def parse(statements):
    """Parse the SQL statemens and produces a list of trees.

    :statements: The SQL statements to parse.
    :return: A list of the trees storing the tables and columns identifiers
        the statements use.
    """
    stmts = sqlparse.parse(statements)

    forest = []
    for stmt in stmts:
        if not stmt.tokens:
            raise Exception("Empty SQL statement provided")
        forest.append(statement(stmt.tokens))

    return forest


def _first(tokens):
    """Search for the first token not being a whitespace or comment.

    :tokens: The list of tokens to search.
    :return: The index of the first token not being a whitespace or comment.
        -1 if no such token exists.
    """
    i = 0
    while i < len(tokens) and (tokens[i].is_whitespace or isinstance(
            tokens[i], S.Comment) or tokens[i].ttype is T.Comment.Single):
        i += 1

    if i == len(tokens):
        return -1
    return i


def _token_first(tokens):
    """Search for the first token not being a whitespace or comment.

    :tokens: The list of tokens to search.
    :return: The first token not being a whitespace or comment. `None` if
        no such token exists.
    """
    idx = _first(tokens)
    return tokens[idx] if idx != -1 else None


def statement(tokens):
    """Identify the statement and calls the proper handlers.

    :tokens: The sqlparse statement representation.
    :return: A tree storing the tables and columns identifiers the statement
        uses.
    """
    first = _token_first(tokens)
    if first and first.match(T.Keyword.DML, ["INSERT", "UPDATE", "DELETE"]):
        raise Exception(f"'{first.normalized}' is not supported yet.")
    if first and first.match(T.Keyword.DML, "SELECT"):
        return select(tokens)
    return None


# TODO: improve the parsing respecting the order
def select(tokens):
    """Visits the SELECT statement and creates its tree representation.

    The SELECT statements comply to the following syntax:

        SELECT [DISTINCT|ALL] expression+
        FROM tableExpression+
        [WHERE expression]
        [GROUP BY expression+ [HAVING expression]]
        [ORDER BY (expression [ASC|DESC] [NULLS [FIRST|LAST]])+]

    Whenever the SELECT statement involves a subquery, a new child node is
    created to hold information on the targets the subquery uses.

    :tokens: The sqlparse SELECT statement representation.
    :return: A tree storing the tables and columns identifiers the statement
        uses.
    """
    current = Node()
    current.state.tokens = tokens

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if DEBUG:
            print(type(tok).__name__, tok.ttype, tok)

        # SELECT [DISTINCT|ALL] expression+
        if tok.match(T.Keyword.DML, ["SELECT"]):
            length = _comma_separated_list(
                current,
                tokens[i + 1:],
                skip=_skip_modifier,
                item_resolver=_parameter_resolver,
                limiter=lambda tok: tok.match(T.Keyword, "FROM"))
            i += length

        # FROM tableExpression+
        elif tok.match(T.Keyword, "FROM"):
            length = _comma_separated_list(
                current,
                tokens[i + 1:],
                item_resolver=_table_resolver,
                limiter=lambda tok: isinstance(tok, S.Where) or tok.match(
                    T.Keyword, ["GROUP BY", "ORDER BY"]))
            i += length

        # [WHERE expression]
        elif isinstance(tok, S.Where):
            if DEBUG:
                print("WHERE")
            _expression(current, tok.tokens[1:])

        # [GROUP BY expression+ [HAVING expression]]
        elif tok.match(T.Keyword, "GROUP BY"):
            length = _comma_separated_list(
                current,
                tokens[i + 1:],
                item_resolver=_parameter_resolver,
                limiter=lambda tok: tok.match(T.Keyword,
                                              ["HAVING", "ORDER BY"]))
            i += length
        elif tok.match(T.Keyword, "HAVING"):
            length = _expression(current, tokens[i + 1:])
            i += length

        # [ORDER BY (expression [ASC|DESC] [NULLS [FIRST|LAST]])+]
        elif tok.match(T.Keyword, "ORDER BY"):
            length = _comma_separated_list(current,
                                           tokens[i + 1:],
                                           item_resolver=_parameter_resolver)
            i += length

        elif tok.is_keyword:
            raise Exception(
                f"""Unexpected keyword '{tok.normalized}'. This may be an invalid or
                    unsupported keyword.
                    To use a keyword as a plain string, use backticks:
                    `{tok.normalized}`
                """)

        i += 1

    return current


def _comma_separated_list(node,
                          tokens,
                          item_resolver,
                          skip=None,
                          limiter=None):
    """Resolve comma separate list of items.

    :node: The current tree node on which the function operates.
    :tokens: The list of tokens representing the comma separated list or part
        of it.
    :item_resolver: A function that takes care of resolving a single list
        element.
    :skip: A function that skips tokens at the beginning of tokens and return
        the number of tokens skipped.
    :limiter: A function that identifies tokens representing the end of the
        comma separated list.
    :return: The number of tokens part of the comma separated list.
    """
    skipped = 0
    if skip:
        skipped = skip(tokens)
        tokens = tokens[skipped:]

    # consider tokens till the limiter
    if limiter:
        limit = 0
        for tok in tokens:
            if limiter(tok):
                break
            limit += 1
        tokens = tokens[:limit]

    length = skipped + len(tokens)

    # expand the tokens wrapped in IdentifierList
    expansion = []
    for tok in tokens:
        if isinstance(tok, S.IdentifierList):
            # hoping sqlparse does not wrap IdentifierList in other
            # IdentifierList
            expansion.extend(tok.tokens)
        else:
            expansion.append(tok)
    tokens = expansion

    # separate the list of tokens based on commas
    params = []
    current = []
    for tok in tokens:

        if DEBUG:
            print(type(tok).__name__, tok.ttype, tok)

        if tok.match(T.Punctuation, ','):
            if not current:
                raise Exception("invalid syntax: comma")
            params.append(current)
            current = []
        else:
            current.append(tok)
    if not current:
        raise Exception("invalid syntax: comma")
    params.append(current)

    # resolve parameters
    for param in params:
        item_resolver(node, param)
    return length


def _skip_modifier(tokens):
    """Skip DISTINCT and ALL modifiers.

    :tokens: The list of tokens representing the comma separated list or part
        of it.
    :return: The number of tokens skipped.
    """
    idx = _first(tokens)

    if idx == -1:
        return 0

    modifier = tokens[idx].match(T.Keyword, ["DISTINCT", "ALL"])
    return idx + modifier


def _parameter_resolver(node, param):
    """Resolve a projection or function parameter.

    :node: The current tree node on which the function operates.
    :param: The list of tokens representing the parameter of a comma separated
        list.
    """
    def _is_wildcard(token):
        return token.match(T.Wildcard, '*') or \
            isinstance(token, S.Identifier) and token.is_wildcard()

    # manage wildcard
    if len(param) == 1 and _is_wildcard(param[0]):
        raise Exception(
            "wildcard resolution requires information on the schema")
    _expression(node, param)


def _table_resolver(node, param):
    """Resolve a table expression.

    :node: The current tree node on which the function operates.
    :param: The list of tokens representing the parameter of a comma separated
        list.
    """
    def _resolve_table_or_parenthesis(node, token):
        if isinstance(token, S.Identifier):
            if token.has_alias():
                first = token.token_first(skip_ws=True, skip_cm=True)
                if isinstance(first, S.Parenthesis):
                    # TODO: attach alias to select (when a select is there)
                    raise Exception(
                        "Alias of complex tables is not supported yet.")
            node.state.tables.append(token)
            return True
        if isinstance(token, S.Parenthesis):
            subtokens = token.tokens[1:-1]
            first = _token_first(subtokens)
            if first and first.match(T.Keyword.DML, "SELECT"):
                child = select(subtokens)
                token.tokens = [token.tokens[0], child.state, token.tokens[-1]]
                node.childs.append(child)
            else:
                _comma_separated_list(node,
                                      subtokens,
                                      item_resolver=_table_resolver)
            return True
        return False

    if len(param) == 1:
        tok = param[0]
        _resolve_table_or_parenthesis(node, tok)
    else:
        i = 0
        while i < len(param):
            tok = param[i]
            next_tok = None if i + 1 >= len(param) else param[i + 1]

            table_or_parenthesis = _resolve_table_or_parenthesis(node, tok)
            if not table_or_parenthesis and \
                    tok.match(T.Keyword, ["CROSS JOIN",
                                          "FULL OUTER JOIN",
                                          "LEFT OUTER JOIN",
                                          "RIGHT OUTER JOIN",
                                          "JOIN",
                                          "INNER JOIN"]):
                if next_tok:
                    _resolve_table_or_parenthesis(node, next_tok)
                    i += 1
                else:
                    raise Exception("Missing argument to join")
            elif not table_or_parenthesis and tok.match(T.Keyword, "ON"):
                if DEBUG:
                    print("ON")
                length = _expression(node, param[i + 1:])
                i += length

            i += 1


UNARY = [
    "NOT", "ALL", "ANY", "EXISTS", "SOME"   # logical
]

BINARY = [
    "AND", "IN", "LIKE", "OR",              # logical
    "=", ">", "<", ">=", "<=", "<>",        # comparison
    "+", "-", "*", "/", "%",                # arithmetic
    "||",                                   # string
    "&", "|", "^",                          # bitwise
    "IS"                                    # NULL values
]

TERNARY = [("BETWEEN", "AND")]

PRECEDENCE = {
    "+": 5, "-": 5, "*": 5, "/": 5, "%": 5, "&": 5, "|": 5, "^": 5, "||": 5,
    "ALL": 5, "ANY": 5, "EXISTS": 5, "IN": 5, "SOME": 5,
    "=": 4, ">": 4, "<": 4, ">=": 4, "<=": 4, "<>": 4,
    "BETWEEN": 3, "LIKE": 3,
    "NOT": 2,
    "AND": 1,
    "OR": 0,
    "IS": -1
}

OPERATORS = list(PRECEDENCE.keys())


# TODO: handle sqlparse issue #370 on '-' arithmetic operator
def _expression(node, tokens):
    """Resolve a SQL expression.

    :node: The current tree node on which the function operates.
    :tokens: The list of tokens containing the expression.
    :return: The number of tokens representing the expression.
    """
    # stacks for a shift-reduce parser
    args = []
    ops = []

    def _shift(val, args):
        args.append(val)

    def _reduce(args, ops):
        assert len(ops) >= 1
        op_name = ops.pop()

        # ternary operators
        if ops and (ops[-1], op_name) in TERNARY:
            assert len(args) >= 3
            ops.pop()
            args.pop()  # right
            args.pop()  # middle
            args.pop()  # left
        # binary operators
        elif op_name in BINARY:
            assert len(args) >= 2
            args.pop()  # right
            args.pop()  # left
        # unary operators
        elif op_name in UNARY:
            assert len(args) >= 1
            args.pop()  # arg
        else:
            print(f"Unexpected keyword '{op_name}'.")
        args.append("placeholder")

    count = 0
    for tok in tokens:
        if DEBUG:
            print(tok, args, ops)

        # sqlparse packages up parenthesis
        if isinstance(tok, S.Parenthesis):
            subtokens = tok.tokens[1:-1]
            first = _token_first(subtokens)
            if first and first.match(T.Keyword.DML, "SELECT"):
                child = select(subtokens)
                tok.tokens = [tok.tokens[0], child.state, tok.tokens[-1]]
                node.childs.append(child)
            else:
                _comma_separated_list(node,
                                      subtokens,
                                      item_resolver=_expression)
            _shift("parenthesis", args)

        # sqlparse packages up comparisons
        elif isinstance(tok, S.Comparison):
            _expression(node, tok.tokens)
            _shift("comparison", args)

        # sqlparse packages up arithmetic and bitwise operations
        elif isinstance(tok, S.Operation):
            _expression(node, tok.tokens)
            _shift("operation", args)

        # sqlparse packages up functions
        elif isinstance(tok, S.Function):
            _function(node, tok)
            _shift("function", args)

        # sqlparse packages up cases
        elif isinstance(tok, S.Case):
            _case(node, tok)
            _shift("case", args)

        # resolve operator
        elif tok.match(T.Keyword, [keyword for _, keyword in TERNARY]) and \
                ops and (ops[-1], tok.normalized) in TERNARY:
            _shift(tok.normalized, ops)
        elif tok.match(T.Keyword, OPERATORS) or \
                tok.match(T.Operator, OPERATORS) or \
                tok.match(T.Operator.Comparison, OPERATORS):
            while ops and PRECEDENCE[ops[-1]] >= PRECEDENCE[tok.normalized]:
                _reduce(args, ops)
            _shift(tok.normalized, ops)

        # name or something with an alias
        elif isinstance(tok, S.Identifier):
            # sqlparse treats anything with an alias as an identifier
            if tok.has_alias():
                first = tok.token_first(skip_ws=True, skip_cm=True)
                if first.match(T.Name, None):
                    node.state.cols.append(tok)
                else:
                    _expression(node, [first])
                node.state.aliases.add(tok.get_alias())
                _shift("alias", args)
            else:
                # sqlparse treats string literals as identifiers
                is_string_literal = tok.normalized.startswith('"') and \
                        tok.normalized.endswith('"')
                if not is_string_literal:
                    # remove ordering information
                    if tok.get_ordering():
                        tok = tok.tokens[0]
                    node.state.cols.append(tok)
                _shift(tok.normalized, args)

        # literal
        elif tok.match(T.Keyword, ["^NULL$", "^NOT\\s+NULL$"], regex=True) or \
                tok.ttype in [T.Literal,
                              T.Literal.Number,
                              T.Literal.String,
                              T.Literal.String.Single,
                              T.Number,
                              T.Number.Float,
                              T.Number.Integer,
                              T.String,
                              T.String.Symbol]:
            _shift(tok.normalized, args)

        # whitespaces and comments
        elif tok.is_whitespace or isinstance(tok, S.Comment) or \
                tok is T.Comment.Single:
            pass

        else:
            # don't count unconsumed tokens
            if count:
                count -= 1
            break

        count += 1

    while ops and len(args) >= 1:
        _reduce(args, ops)

    if len(args) != 1:
        raise Exception("invalid comparison clause: %s" % tokens)
    return count


def _function(node, token):
    """Resolve a SQL function.

    :node: The current tree node on which the function operates.
    :token: The token representing the function.
    """
    funs = ["DP", "K_ANONIMITY", "L_DIVERSITY", "T_CLOSENESS", "TOKENIZE"]

    def _resolve_function_parameters(node, token):
        subtokens = token.tokens[1:-1]
        first = _token_first(subtokens)
        # extract columns from function parameters when present
        if first:
            if first.match(T.Keyword.DML, "SELECT"):
                child = select(subtokens)
                token.tokens = [token.tokens[0], child.state, token.tokens[-1]]
                node.childs.append(child)
            else:
                _comma_separated_list(node,
                                      subtokens,
                                      skip=_skip_modifier,
                                      item_resolver=_parameter_resolver)

    identifier = token.tokens[0]
    parenthesis = token.tokens[1]

    # sqlparse mistakes operators for functions when a space doesn't separates
    # the operator and the paretheses
    if identifier.normalized.upper() in OPERATORS:
        # convert identifier into keyword
        identifier = S.Token(T.Keyword, identifier.normalized)
        _expression(node, [identifier, parenthesis])
    # anonimization function
    elif identifier.normalized in funs:
        # keep anonimization function as we consider it part of the schema
        prev_count = len(node.state.cols)
        _resolve_function_parameters(node, parenthesis)
        next_count = len(node.state.cols)
        cols = node.state.cols[prev_count:next_count]
        node.state.cols = node.state.cols[:prev_count]  # restore state
        for col in cols:
            node.state.cols.append(
                S.Token(T.Literal,
                        col.normalized + '/' + identifier.normalized.lower()))
    # other function
    else:
        _resolve_function_parameters(node, parenthesis)


def _case(node, token):
    """Resolve a SQL case.

    :node: The current tree node on which the function operates.
    :token: The token representing the case.
    """
    cases = token.get_cases(skip_ws=True)

    # case <cond>
    cond, value = cases[0]
    if not value:
        _expression(node, cond)
        cases.pop(0)

    # when <cond> then <value>
    for cond, value in cases:
        if cond:
            if cond[0].match(T.Keyword, "WHEN") and \
                    value[0].match(T.Keyword, "THEN"):
                _expression(node, cond[1:])
                _expression(node, value[1:])
            else:
                missing = "WHEN" if cond[0].match(T.Keyword, "WHEN") \
                    else "THEN"
                raise Exception(f"invalid syntax: missing keyword {missing}")

    # else <value>
    cond, value = cases[-1]
    if not cond:
        if value[0].match(T.Keyword, "ELSE"):
            _expression(node, value[1:])
        else:
            raise Exception(f"invalid syntax: missing keyword ELSE")
