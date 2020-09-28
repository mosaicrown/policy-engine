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

import rdflib                           # noqa

import mosaicrown                       # noqa
from mosaicrown import namespaces       # noqa
from mosaicrown import utils            # noqa
from mosaicrown import visualization    # noqa
from mosaicrown import vocabularies

graph = rdflib.Graph()
graph.parse("examples/scripts/policies/assets.jsonld", format="json-ld")
graph.parse(vocabularies.JSON_LD["ODRL"], format="json-ld")

generic = rdflib.URIRef("http://unibg.it/user")
parabosc = rdflib.URIRef("http://unibg.it/user/parabosc")

targets = {"http://unibg.it/table/students/": ["Sex", "CF", "Birthdate"]}

# Example of usage
# utils.check_permission(graph, targets, assignee=generic,
#                        action=namespaces.ODRL.read, purpose=None))
