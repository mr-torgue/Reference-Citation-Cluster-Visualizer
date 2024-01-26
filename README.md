# Reference-Citation-Cluster-Visualizer
Visualizes the citations between a list of references in a graph.

Sometimes, you want to know if there are some patterns in the list of references you have collected for your research.
The Reference Citation Cluster Visualizer(RCCV) takes your reference list and checks which works cite each other.
The output will be a graph.
Questions you can answer:
* are there distinct clusters? (clusters of papers that never cite from the other cluster)
* are there important papers?

# Issues
RCCV supports both CrossRef (based on DOI) and SemanticScholar (based on their identifier).
SemanticScholar seems to offer the most complete coverage because DOI's are not always available.
