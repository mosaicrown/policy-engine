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

from setuptools import setup


with open("README.rst") as fp:
    readme = fp.read()
    long_description = readme[readme.index("Description"):]


setup(
    name="mosaicrown",
    version="0.1.0",
    description="MOSAICrOWN policy engine",
    long_description=long_description,
    install_requires=[
        # RDF
        "rdflib-jsonld",
        "rdflib",
        # rdflib missing dependency
        "requests",
        # IRI
        "rfc3987",
        # constraints evaluation
        "simpleeval",
        # visualization
        "networkx",
        "matplotlib",
        "pygraphviz",
        "tabulate",
        "colorama",
        # SQL
        "sqlparse",
    ],
    url="http://github.com/unibg-seclab/policy-engine",
    author="UniBG Seclab",
    author_email="seclab@unibg.it",
    license="Apache",
    packages=[
        "mosaicrown",
    ],
    keywords="policy engine odrl access control data",
)
