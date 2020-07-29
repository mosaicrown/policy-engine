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


class Query(ABC):
    """Query intereface."""

    @abstractmethod
    def __init__(self, query):
        """Parse the given query and produce an internal representation.

        :query: The query to parse and operate on.
        """
        pass

    @abstractmethod
    def __str__(self):
        """Render the query."""
        pass

    @abstractmethod
    def get_subqueries(self):
        """Return an enumeration of targets, each representing a (sub)query targets.

        :return: An enumeration of (sub)queries targets.
        """
        pass

    @abstractmethod
    def get_targets(self):
        """Return a disctionary representing the access request of the query.

        The items of the dictionary use as key the table identifier and as
        value the column identifiers.

        :return: A dictionary representing the access request of the query.
        """
        pass

    def render(self):
        """Render the query."""
        return self.__str__()
