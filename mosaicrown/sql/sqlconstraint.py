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
from collections import namedtuple

from rdflib import URIRef

if __package__:
    from ..constraint import Constraint
    from ..constraint import Constraints
    from ..namespaces import ODRL
else:
    from mosaicrown.constraint import Constraint
    from mosaicrown.constraint import Constraints
    from mosaicrown.namespaces import ODRL


"""Map to convert ODRL operators to SQL operators"""
_operator_map = {
        "eq": "=",
        "gt": ">",
        "gteq": ">=",
        "lt": "<",
        "lteq": "<=",
        "neq": "!="
}


def _convert_operator(odrl_operator):
    """Given an ODRL operator returns the corresponding SQL operator.

    :odrl_operator: IRI of the ODRL operator.
    """
    to_check = pathlib.PurePosixPath(odrl_operator).parts[-1]
    return _operator_map[to_check] if to_check in _operator_map else None


class SQLConstraints(Constraints):
    """SQLConstraints class."""

    def __init__(self, permissions, prohibitions):
        """Create a constraints class.

        :param permissions: A dictionary grouping permission constraints on a
            table-bases.
        :type permissions: dict
        :param prohibitions: A dictionary grouping prohibition constraints on a
            table-bases.
        :type prohibitions: dict
        """
        self.permissions = permissions
        self.prohibitions = prohibitions

    @staticmethod
    def create_constraints(constraints, target):
        """Create a SQLConstraints class given a list of constraints.
        
        Factory method to create a SQLConstraints class given a list of
        constraints.

        The list of constraints DOES NOT contain SQLConstraint, but instead it
        contains the result of the SPARQL query run by the
        mosaicrown.utils.get_target_constraints function.

        Expected format:
            <br><b>(leftOperand, operator, rightOperand, type)</b>

        :param constraints: List of constraints result of a SPARQL query.
        :param target: Name of the target table
        """

        permissions = {}
        prohibitions = {}
        logical_map = {}
        ConstraintResult = namedtuple("ConstraintResult", "leftOperand operator rightOperand type operand logical")

        for row in constraints:
            constraint_result = ConstraintResult(*row)
            op = _convert_operator(constraint_result.operator)

            constraint = SQLConstraint(pathlib.PurePosixPath(constraint_result.leftOperand).parts[-1], op,
                                       pathlib.PurePosixPath(constraint_result.rightOperand).parts[-1])

            if constraint_result.operand is not None and constraint_result.logical is not None \
                    and constraint_result.operand == URIRef("http://www.w3.org/ns/odrl/2/or"):

                logical_URI = constraint_result.logical.n3()
                if logical_URI not in logical_map:
                    logical_map[logical_URI] = []

                logical_map[logical_URI].append(constraint)
            else:
                if constraint_result.type == ODRL.permission:
                    if target not in permissions:
                        permissions[target] = []
                    permissions[target].append([constraint])
                else:
                    if target not in prohibitions:
                        prohibitions[target] = []
                    prohibitions[target].append(constraint)

        for to_or in logical_map.values():
            if target not in permissions:
                permissions[target] = []
            permissions[target].append(to_or)

        return SQLConstraints(permissions, prohibitions)


class SQLConstraint(Constraint):
    """SQLConstraint class."""

    def __init__(self, left, op, right):
        """Create a constraint.

        Left and right operands are either column identiers or literals.

        :param permission: The constraint origin. True, when the constraints
            origins from a permission, False otherwise.
        :type permission: bool
        :param left: The left operand of the constraint.
        :type left: str
        :param op: The operator of the constraint.
        :type op: str
        :param right: The right operand of the constraint.
        :type right: str
        """
        self.left = left
        self.op = op
        self.right = right

    def __str__(self):
        """Return a string representation of the constraint."""
        return " ".join([self.left, self.op, self.right])
