# Reference-Citation-Cluster-Visualizer
Visualizes the citations between a list of references in a graph.

Sometimes, you want to know if there are some patterns in the list of references you have collected for your research.
The Reference Citation Cluster Visualizer(RCCV) takes your reference list and checks which works cite each other.
The output will be a graph.
Questions you can answer:
* are there distinct clusters? (clusters of papers that never cite from the other cluster)
* are there important papers?

# Installation and Usage
Requirement: python3 needs to be installed.
Run 'pip3 requirements.txt' to install dependencies.
Usage: 'usage: RCCV.py [-h] [-s src] [-v] [-f] [-a] [-m max_nr] [-t thr_nr] filename'
Currently only supports items with a DOI.

## CrossRef
When using CrossRef please be polite and give some contact details!
1. cp crapi_key.tmp .crapi_key
Fill in the user agent and mailto.
Remove API token if you don't have one.

# Issues
RCCV supports both CrossRef (based on DOI) and SemanticScholar (based on their identifier).
SemanticScholar seems to offer the most complete coverage because DOI's are not always available.
1. All bibtex items need a DOI

# Roadmap
1. Search by title
2. Better graph representation
3. More advanced coloring and visualization (for example group same venues together)
4. Add API support for SemanticScholar
