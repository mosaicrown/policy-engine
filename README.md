# Policy engine

The policy engine is the tool responsible for parsing the
MOSAICrOWN policy and checking whether a subject request is
permitted or denied.

## Policy language

Policies are expressed in ODRL [1], a W3C specification that provides
an information model, a vocabulary, and encoding mechanisms for
representing statements about the usage of content.

Rules consists of four components:

- **assignee**: the *subject* that makes the request;
- **target**: the *dataset* on which the *subject* wants to perform operation;
- **action**: the category the *operation* requested falls in;
- **purpose**: the reason for which the *dataset* is being requested (a different definition with respect to ODRL vocabolary, see [MOSAICrOWN vocabolary](mosaicrown/namespaces)).

A MOSAICrOWN policy example containing a single  permission rule follows:

```json
{
    "@context": [
        "http://www.w3.org/ns/odrl.jsonld",
        "https://www.mosaicrown.eu/ns/mosaicrown.jsonld"
    ],
    "uid": "http://example.com/policy/1",
    "permission": [{
        "uid": "http://example.com/policy/1/1",
        "assignee": "http://example.com/user/Alice",
        "target": "http://example.com/table/CardHolder/Email",
        "action": "read",
        "purpose": "marketing"
    }]
}
```

### Hierarchies

Rules can be declared at different granularity levels.
For example someone may state a rule on an entire organization, a role, or a specific individual.
Based on the concept of hierarchies, the policy engine is able to accept or deny specific access requests
taking into account rules specified at different hierachy levels.

Hierarchies are supported on any of the four rule components.

### Joint visibility

If two or more attributes of the same object can be accessed
together, they must appear together in a policy rule.

In the following example we show two relational table and the permission rules on them.

<p align="center">
    <img src="https://user-images.githubusercontent.com/15113769/88814928-00c19e80-d1bb-11ea-97f4-4c4ab9be7fc9.jpg"
         alt="Color-coded representation of visibility" width="75%">
</p>

An access request like:
```SQL
SELECT P.CustomerID, P.Amount, P.Merchant
FROM Payment as P
```
even thought it accesses columns part of permissions, it is denied by the policy engine as no permissions rule allows the *joint visibility* of those columns.

## Implementation

The policy engine is divided into two main components:

- the **front end** that parses the access request extracting the targets it requires to execute
- the **core** that retrives the policy, builds an in memory representation and evaluates the access request based on the policy

### Front end

The front end understands the access request and extracts the targets from it.

Multiple front ends can suit the policy engine pipeline.
Currently, an implementation of a SQL front end has been implemented.

#### SQL front end

The SQL front end is implemented on top of *sqlparse* [2].
It supports a rich SQL query syntax.
The following partial grammar description shows the supported syntax for SELECT statements.
```SQL
SELECT [DISTINCT|ALL] expression+
FROM tableExpression+
[WHERE expression]
[GROUP BY expression+ [HAVING expression]]
[ORDER BY (expression [ASC|DESC] [NULLS [FIRST|LAST]])+]
```

An acces request like:
```SQL
SELECT CardHolder.Name FROM CardHolder
```
is parsed using *sqlparse* to produce the parse tree representation:

<p align="center">
    <img src="https://user-images.githubusercontent.com/15113769/88815168-4ed6a200-d1bb-11ea-8def-d61f43585d97.jpg"
         alt="Parse tree example">
</p>

The tree is then enriched, to identify and isolate the targets of the query:

    {"CardHolder": {"Name"}}

Finally, the targets are converted to an intermediary language-agnostic representation that is the input of the policy engine core using *metadata*.

    {"http://bank.eu/finance/CardHolder": {"Name"}}

### Core

The policy engine core reads all the available policies (either from a
repository or from sticky metadata), and creates an in-memory policy
graph (using RDFLib [3]).
A SPARQL query is then used to traverse the graph during evaluation.

The SPARQL query used to traverse the policy graph is:

```SPARQL
PREFIX odrl: <https://www.w3.org/ns/odrl/2/>
PREFIX mosaicrown: <https://www.mosaicrown.eu/ns/mosaicrown/1/>
SELECT DISTINCT ?rule
WHERE {
    ?policy ?predicate ?rule .
    ?rule odrl:assignee ?assigneeRec .
    ?assignee mosaicrown:belongsTo* ?assigneeRec .
    ?rule odrl:action ?actionRec .
    ?action odrl:includedIn* ?actionRec .
    ?rule odrl:target ?targetRec .
    ?target odrl:partOf* ?targetRec .
    ?rule mosaicrown:purpose ?purposeRec .
    ?purpose mosaicrown:declinationOf* ?purposeRec .
}
```

## Examples

### Demo

To run the demo of the policy engine:

    make demo

### Unibg

To run an example on a complex policy structure that uses both permissions and prohibitions:

    make unibg

### Shell

To run set up an interactive IPython shell with:
- MOSAICrOWN namespace available through a local webserver at http://localhost:8000/
- an in-memory representation of the sample policy available accessing the *graph* variable

```bash
make shell
```

### Scripts

To run some example script excercizing RDFLib and the policy engine capabilities:

    make run


## For more information

[1] [ODRL information model 2.2](https://www.w3.org/TR/odrl-model) - a standard description model and format to express rules statements to be associated to content in general

[2] [sqlparse](https://github.com/andialbrecht/sqlparse) - a non-validating SQL parser for Python providing support for parsing, splitting and formatting SQL statements

[3] [RDFLib](https://github.com/RDFLib/rdflib) - a pure Python package for working with RDF
