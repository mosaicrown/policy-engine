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

from abc import ABC
from abc import abstractmethod


class Constraints(ABC):
    """Constraints intereface."""

    @abstractmethod
    def __init__(self, permissions, prohibitions):
        """Create a constraints class.

        :param permissions: A dictionary grouping permission constraints on a
            table-bases.
        :type permissions: dict
        :param prohibitions: A dictionary grouping prohibition constraints on a
            table-bases.
        :type prohibitions: dict
        """
        pass


class Constraint(ABC):
    """Constraint intereface."""

    @abstractmethod
    def __init__(self, left, op, right):
        """Create a constraint.

        :type permission: bool
        :param left: The left operand of the constraint.
        :type left: str
        :param op: The operator of the constraint.
        :type op: str
        :param right: The right operand of the constraint.
        :type right: str
        """
        pass

    @abstractmethod
    def __str__(self):
        """Return a string representation of the constraint."""
        pass
