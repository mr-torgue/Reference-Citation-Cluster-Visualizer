'''
We use the semanticscholar API for references and citations.
We use caching to prevent sending too many requests

Input papers as a biblatex/bibtex file
For each paper we need a DOI:
1) either available
2) or use api to find it


TODO:
1. Add API keys
'''

import requests
import requests_cache
import networkx as nx
import matplotlib.pyplot as plt
import sys
import json
import crossref_commons.retrieval


from pybtex.database import parse_file
from contextlib import suppress

API_URL_BASE_SS = "https://api.semanticscholar.org/graph/v1/"


def main():
	if len(sys.argv) >= 2 and len(sys.argv) <= 4:
		crossref = "semanticscholar"
		using_all = False
		# cache expires after a week
		requests_cache.install_cache(cache_name='semanticscholar_cache', backend='sqlite', expire_after=604800)
		print("You specified file %s" % sys.argv[1])
		if len(sys.argv) >= 3 and sys.argv[2] == "CrossRef":
			print("Using CrossRef")
			crossref = "crossref"
		else:
			print("Using SemanticScholar")
		if len(sys.argv) >= 4 and sys.argv[3] == "ALL":
			print("Visualizing every reference")
			using_all = True
		else:
			print("Only visualizing given references")
		papers = parse_papers(sys.argv[1], source=crossref)
		visualize(papers, plot_everything=using_all)
	else:
		print("Usage: python3 RCCV.py [filename] [CrossRef/SemanticScholar] [ALL]")


'''
get metadata for given doi from semanticscholar
we use the semanticscholar id as the main identifier
* paperId,
* title,
* venue,
* year,
* referenceCount,
* citationCount,
* references,
* citations,
* citations.paperId,
* references.paperId,
* citations.title,
* references.title,
* citations.externalIds,
* references.externalIds'
'''
def get_metadata_semanticscholar(doi):
	result = {}
	try:
		# get results
		response = requests.get(API_URL_BASE_SS + "paper/" + doi, params={'fields': 'paperId,title,venue,year,referenceCount,citationCount,citations,references,citations.paperId,references.paperId,citations.title,references.title,citations.externalIds,references.externalIds'})
		print("Did we get it from cache: %s" % response.from_cache)
		paper = response.json()

		# only id is required, suppress the other keyerrors
		result['id'] = paper['paperId']
		# very ugly with all those suppresses, need to rewrite this
		with suppress(KeyError): 
			result['title'] = paper['title']
		with suppress(KeyError): 
			result['venue'] = paper['venue']
		with suppress(KeyError): 
			result['year'] = paper['year']
		with suppress(KeyError): 
			result['ref_count'] = paper['referenceCount']
		result['references'] = []
		for reference in paper['references']:
			new_reference = {}
			with suppress(KeyError): 
				new_reference["id"] = reference['paperId']
				new_reference["title"] = reference['title']
			if new_reference != {}:
				result['references'].append(new_reference)
		with suppress(KeyError): 
			result['cite_count'] = paper['citationCount']
		result['citations'] = []
		for citation in paper['citations']:
			new_citation = {}
			with suppress(KeyError): 
				new_citation["id"] = citation['paperId']
				new_citation["title"] = citation['title']
			if new_citation != {}:
				result['citations'].append(new_citation)
		return result
	except KeyError as e:
		print("Key %s not available" % e)
	except Exception as e:
		print(e)
	return None


def get_metadata_crossref(doi):
	result = {}
	try:
		response = crossref_commons.retrieval.get_publication_as_json(doi)

		# only id is required, suppress the other keyerrors
		result['id'] = response['DOI']
		with suppress(KeyError): 
			result['title'] = response['title']
		with suppress(KeyError): 
			result['venue'] = response['container-title']
		with suppress(KeyError): 
			result['year'] = response['published']['date-parts'][0][0]
		with suppress(KeyError): 
			result['ref_count'] = response['references-count']
		result['references'] = []
		for reference in response['reference']:
			new_reference = {}
			with suppress(KeyError): 
				new_reference["id"] = reference['DOI']
				new_reference["title"] = reference['article-title']
			if new_reference != {}:
				result['references'].append(new_reference)
		with suppress(KeyError): 
			result['cite_count'] = response['is-referenced-by-count']
		return result
	except KeyError as e:
		print("Key %s not available" % e)
	except Exception as e:
		print(e)
	return None




'''
parse papers from (bibtex)file
returns a set of papers with the fields:
* id (required)
* title (required)
* year
* ...
'''
def parse_papers(file, source="semanticscholar"):
	papers = []
	try:
		bib_data = parse_file(file)
		for entry_key in bib_data.entries:
			entry = bib_data.entries[entry_key]
			try:
				if source == "crossref":
					papers.append(get_metadata_crossref(entry.fields["doi"]))
				else:
					papers.append(get_metadata_semanticscholar(entry.fields["doi"]))
			except KeyError:
				try:
					print("Could not find DOI for %s. Going to try to get DOI from title" % entry.fields["title"])
					# TODO
				except KeyError:
					print("Ignored %s because we could not find a title" % entry)
	except Exception as e: 
		print("Make sure to specify a correct bibtex file!\nException %s" % e)
	return papers



'''
if plot_everything is enabled we also plot the papers referenced but not in our list that are at least cited threshold times
'''
def visualize(papers, plot_everything=False, threshold=3):
	G = nx.DiGraph()
	# all papers in our list
	papers_ind = [paper['id'] for paper in papers]
	# all papers referenced but not in our list
	nonlist_papers_ind = []

	# add edges
	for paper in papers:
		# add the node
		G.add_node(paper['id'], title=paper['title'], year=paper['year'], refcount=paper['ref_count'], citecount=paper['cite_count'], venue=paper['venue'])
		for reference in paper["references"]:
			# if reference is not in our list and also not in our nonlist list yet
			if plot_everything and reference["id"] not in papers_ind and reference["id"] not in nonlist_papers_ind:
				nonlist_papers_ind.append(reference['id'])
				title = "no title"
				if 'title' in reference:
					title = reference['title']
				G.add_node(reference['id'], title=title)
			if plot_everything or reference["id"] in papers_ind:
				G.add_edge(paper["id"], reference["id"])
	


	idx_to_node_dict = {}
	for idx, node in enumerate(papers_ind):
		idx_to_node_dict[idx] = node
	print(papers_ind)
	print(G.nodes())

	options = {"edgecolors": "tab:gray", "node_size": 100, "alpha": 0.9}
	fig, ax = plt.subplots()
	pos = nx.spring_layout(G)
	mynodes = nx.draw_networkx_nodes(G, pos=pos, ax=ax, nodelist=papers_ind, node_color="tab:red", label="string", **options)
	allnodes = [mynodes]
	if plot_everything:
		nonlist_nodes = nx.draw_networkx_nodes(G, pos=pos, ax=ax, nodelist=nonlist_papers_ind, node_color="tab:blue", label="string", **options)
		allnodes.append(nonlist_nodes)

	nx.draw_networkx_edges(G, pos=pos, ax=ax)
	
	annot = ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
						bbox=dict(boxstyle="round", fc="w"),
						arrowprops=dict(arrowstyle="->"))
	annot.set_visible(False)

	def update_annot(ind):
		node_idx = ind["ind"][0]
		node = idx_to_node_dict[node_idx]
		xy = pos[node]
		annot.xy = xy
		node_attr = {'node': node}
		node_attr.update(G.nodes[node])
		text = '\n'.join(f'{k}: {v}' for k, v in node_attr.items())
		annot.set_text(text)

	def hover(event):
		vis = annot.get_visible()
		if event.inaxes == ax:
			for nodess in allnodes:
				cont, ind = nodess.contains(event)
				if cont:
					update_annot(ind)
					annot.set_visible(True)
					fig.canvas.draw_idle()
				else:
					if vis:
						annot.set_visible(False)
						fig.canvas.draw_idle()



	fig.canvas.mpl_connect("motion_notify_event", hover)
	plt.show() 

main()