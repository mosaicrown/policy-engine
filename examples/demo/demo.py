import rdflib

from mosaicrown import utils, vocabularies
from mosaicrown.namespaces import MOSAICROWN, ODRL
from mosaicrown.visualization import triples_table


# users
administrative = rdflib.URIRef("http://bank.eu/user/administrative")
agent_a = rdflib.URIRef("http://bank.eu/user/administrative/agentA")
analyst = rdflib.URIRef("http://bank.eu/user/analyst")

# actions
use = MOSAICROWN.use
write = MOSAICROWN.write
read = MOSAICROWN.read
sell = MOSAICROWN.sell
sellreport = MOSAICROWN.sellreport

# purposes
statistical = MOSAICROWN.statistical
marketing = MOSAICROWN.marketing


separator = '\n--------------------------------------------------' + \
            '\n\tPress any key to continue\n' + \
            '--------------------------------------------------'
debug_info = False


def policy_loading():
    """Load the running example policy into the graph."""
    # create empty RDF graph
    print("[*] Create the RDF graph")
    graph = rdflib.Graph()

    # parse ODRL vocabolary
    print("\n[*] Load ODRL vocabolary")
    graph.parse(vocabularies.JSON_LD["ODRL"], format="json-ld")

    # parse MOSAICROWN vocabulary
    # only the namespace is downloaded at runtime by RDFLib, NOT the vocabulary
    print("\n[*] Load MOSAICROWN vocabolary")
    graph.parse(location=vocabularies.JSON_LD["MOSAICROWN"], format="json-ld")

    pnames = ["p1", "p2", "p3"]
    pbasepath = "http://localhost:8000/"
    pext = '.jsonld'

    # parse policy
    print('\n[*] Load running example policy')
    for p in pnames:
        pname = ''.join(map(str, p)) + pext
        ppath = pbasepath + pname
        print(f'\tLoading policy {ppath}')
        graph.parse(ppath, format="json-ld")

    return graph


def preliminary_policy_expansion(graph):
    """Expand the policy graph with the knowledge contained within the policy.

    :graph: The policy graph
    """
    # expanding hierarchy of targets
    for target in utils.get_targets(graph):
        utils.add_iri_hierarchy_to_graph(graph,
                                         target,
                                         predicate=ODRL.partOf,
                                         reverse=True)
    # expanding hierarchy of subjects
    for assignee in utils.get_assignee(graph):
        utils.add_iri_hierarchy_to_graph(graph,
                                         assignee,
                                         predicate=MOSAICROWN.belongsTo,
                                         reverse=True)


def main():
    """Configure and run the demo example."""
    # loading the policy into RDF graph
    graph = policy_loading()

    # expand the graph with hierarchy concept on targets and assignees
    print("\n[*] Expand the policy graph with the hierarchy concept")
    preliminary_policy_expansion(graph)

    # serializing the graph to ease testing
    if debug_info:
        print('\n[*] Policy graph serialization\n')
        print(triples_table(graph))
        print('\n[*] Namespace entities')
        print('\tAdministrative user:\t', administrative)
        print('\tWrite action:\t\t', write)
        print('\tStatistical purpose:\t', statistical)

    print(separator)
    input()

    # all tables stored in the database
    target_IRIs = {
        'CardHolder': 'http://bank.eu/finance/CardHolder',
        'Payment': 'http://bank.eu/finance/Payment'
    }

    # access request generated by SQL query
    query = "SELECT CardHolder.Name FROM CardHolder"
    print(f"\n[*] Access request:\n\t{query}")
    # extracting the targets
    targets = utils.get_targets_from_query(query, target_IRIs)
    # checking access
    utils.check_access(graph, targets, administrative, read, statistical)

    print(separator)
    input()

    query = """
        SELECT C.CustomerID, P.Year, P.Month
        FROM Payment as P JOIN CardHolder as C
        GROUP BY P.Year, P.Month
        ORDER BY C.DateOfBirth
    """
    print(f"\n[*] Access request:\n\t{query}")
    targets = utils.get_targets_from_query(query, target_IRIs)
    utils.check_access(graph, targets, administrative, read, statistical)

    print(separator)
    input()

    query = """
        SELECT C.CustomerID
        FROM CardHolder as C
        WHERE C.CustomerID in (SELECT P.CustomerID
                               FROM Payment as P
                               WHERE P.Year = '2020' and P.Month = '04')
    """
    print(f"\n[*] Access request:\n\t{query}")
    targets = utils.get_targets_from_query(query, target_IRIs)
    utils.check_access(graph, targets, administrative, read, statistical)

    print(separator)
    input()

    query = "SELECT P.CustomerID, P.Month, P.Year, P.Amount FROM Payment as P"
    print(f"\n[*] Access request:\n\t{query}")
    targets = utils.get_targets_from_query(query, target_IRIs)
    utils.check_access(graph, targets, administrative, read, statistical)

    print(separator)
    input()

    query = "SELECT P.CustomerID, P.Month, P.Year FROM Payment as P"
    print(f"\n[*] Access request:\n\t{query}")
    targets = utils.get_targets_from_query(query, target_IRIs)
    utils.check_access(graph, targets, administrative, read, statistical)

    print(separator)
    input()

    query = "SELECT P.CustomerID FROM Payment as P WHERE P.Year = '2020'"
    print(f"\n[*] Access request:\n\t{query}")
    targets = utils.get_targets_from_query(query, target_IRIs)
    utils.check_access(graph, targets, administrative, use, statistical)

    print(separator)
    print()

    query = "SELECT P.CustomerID FROM Payment as P WHERE P.Year = '2020'"
    print(f"\n[*] Access request:\n\t{query}")
    targets = utils.get_targets_from_query(query, target_IRIs)
    utils.check_access(graph, targets, administrative, read, statistical)

    print(separator)
    input()

    query = "SELECT P.CustomerID FROM Payment as P WHERE P.Year = '2020'"
    print(f"\n[*] Access request:\n\t{query}")
    utils.add_iri_hierarchy_to_graph(graph,
                                     agent_a,
                                     MOSAICROWN.belongsTo,
                                     reverse=True)
    targets = utils.get_targets_from_query(query, target_IRIs)
    utils.check_access(graph, targets, agent_a, read, statistical)


if __name__ == '__main__':
    main()