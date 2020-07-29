import rdflib                           # noqa

import mosaicrown                       # noqa
from mosaicrown import namespaces       # noqa
from mosaicrown import utils            # noqa
from mosaicrown import visualization    # noqa
from mosaicrown import vocabularies

graph = rdflib.Graph()
graph.parse("examples/scripts/policies/assets.json", format="json-ld")
graph.parse(vocabularies.JSON_LD["ODRL"], format="json-ld")

generic = rdflib.URIRef("http://unibg.it/user")
parabosc = rdflib.URIRef("http://unibg.it/user/parabosc")

targets = {"http://unibg.it/table/students/": ["Sex", "CF", "Birthdate"]}

# Example of usage
# utils.check_permission(graph, targets, assignee=generic,
#                        action=namespaces.ODRL.read, purpose=None))
