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
import argparse
import os.path
import logging
import itertools 

from pybtex.database import parse_file
from contextlib import suppress


logger = logging.getLogger("RCCV_logger")
API_URL_BASE_SS = "https://api.semanticscholar.org/graph/v1/"

'''
The main function handles the user inputs.
Format RCCV.py [-h] [-s src] filename

'''
def main():
	# initialize handler
	logger.addHandler(logging.StreamHandler())
	# CLI
	parser = argparse.ArgumentParser(description="models references")
	parser.add_argument("filename", help="BibTex file to be used")
	parser.add_argument("-s", "--source", type = str, metavar = "src", default = "ss", help = "use \"ss\" for SemanticScholar or \"cr\" for CrossRef")
	parser.add_argument("-v", "--verbose", action="store_true", help = "show INFO logging")
	parser.add_argument("-f", "--force", action="store_true", help = "don't get results from cache")
	parser.add_argument("-a", "--all", action="store_true", help = "also shows referenced works not in the bibtex file")
	parser.add_argument("-m", "--max", type = int, metavar = "max_nr", default=10, help = "maximum nodes not in bibtex file(default 10)")
	parser.add_argument("-t", "--threshold", type = int, metavar = "thr_nr", default=3, help = "only include node not in bibtex file if at least thr_nr references")
	args = parser.parse_args()

	# check if file exists
	if not os.path.exists(args.filename):
		logger.error("please specify an existing file!")
		raise SystemExit(1)

	# check if SemanticScholar or CrossRef is specified
	if args.source != "ss" and args.source != "cr":
		logger.error("please specify a valid source: ss(SemanticScholar) or cr(CrossRef)")
		raise SystemExit(1)

	# check if numbers are within the ranges
	if args.max < 0 or args.max > 64 or args.threshold < 1 or args.threshold > 256:
		logger.error("please specify a max and threshold within the thresholds 0-64 and 1-256")
		raise SystemExit(1)

	# set verbose logging
	if args.verbose:
		logger.setLevel(logging.INFO)
		logger.info("setting logging level to INFO")
	else:
		logger.setLevel(logging.WARNING)

	# set cache if force is not active
	if not args.force:
		# cache expires after a week
		requests_cache.install_cache(cache_name='RCCV_cache', backend='sqlite', expire_after=604800)
		logger.info("enabling cache")

	# log settings to info
	logger.info("""\nusing the following settings:
	filename: %s
	source: %s
	verbose: %s 
	no cache: %s
	show all results: %s
	maximum non-list nodes: %d
	threshold non-list nodes: %d""" % (args.filename, "SemanticScholar" if args.source == "ss" else "CrossRef", args.verbose, args.force, args.all, args.max, args.threshold))

	papers = parse_papers(args.filename, source=args.source)
	visualize(papers, plot_everything=args.all, threshold=args.threshold, maximum=args.max)

	'''
	if len(sys.argv) >= 2 and len(sys.argv) <= 4:
		crossref = "semanticscholar"
		using_all = False
		# cache expires after a week
		requests_cache.install_cache(cache_name='RCCV_cache', backend='sqlite', expire_after=604800)
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
def parse_papers(file, source="ss"):
	papers = []
	try:
		bib_data = parse_file(file)
		for entry_key in bib_data.entries:
			entry = bib_data.entries[entry_key]
			try:
				if source == "cr":
					logger.info("Using CrossRef")
					papers.append(get_metadata_crossref(entry.fields["doi"]))
				else:
					logger.info("Using SemanticScholar")
					papers.append(get_metadata_semanticscholar(entry.fields["doi"]))
			except KeyError:
				try:
					logger.error("Could not find DOI for %s. Going to try to get DOI from title" % entry.fields["title"])
					# TODO
				except KeyError:
					logger.error("Ignored %s because we could not find a title" % entry)
	except Exception as e: 
		logger.error("Make sure to specify a correct bibtex file!\nException %s" % e)
	return papers



'''
if plot_everything is enabled we also plot the papers referenced but not in our list that are at least cited threshold times
'''
def visualize(papers, plot_everything=False, threshold=3, maximum=10):
	G = nx.DiGraph()
	# all papers in our list
	papers_ind = [paper['id'] for paper in papers]
	# all papers referenced but not in our list
	nonlist_papers_ind = []

	# get all unique papers cited by our list and store the counts as well (only when plot_everything=True)
	nonlist_papers = {}
	if plot_everything:
		for paper in papers:
			for reference in paper["references"]:
				# should not be in our list of papers
				if reference["id"] not in papers_ind:
					# does not yet exist
					if reference["id"] not in nonlist_papers:
						nonlist_papers[reference["id"]] = reference
						# make sure this field does not already exist!
						nonlist_papers[reference["id"]]["mycount"] = 1
					else:
						nonlist_papers[reference["id"]]["mycount"] += 1
		# we need at most maximum nr entries and all should have >= threshold
		try:
			nonlist_papers = {x: nonlist_papers[x] for x in nonlist_papers if nonlist_papers[x]['mycount'] >= threshold}
			nonlist_papers = dict(sorted(nonlist_papers.items(), key=lambda item: item[1]['mycount'])[:maximum])
			#nonlist_papers = dict(itertools.islice(nonlist_papers.items(), maximum)) 
		except Exception as e:
			print("Error %s" % e)
			pass 
		assert len(nonlist_papers) <= maximum
		# create nodes for the top 10
		for nonlist_paper in nonlist_papers:
			entry = nonlist_papers[nonlist_paper]
			title = "no title"
			if 'title' in entry:
				title = entry['title']
			G.add_node(nonlist_paper, title=title)
		nonlist_papers_ind = list(nonlist_papers.keys())

	# second pass, not the most efficient but the easiest to understand
	for paper in papers:
		G.add_node(paper['id'], title=paper['title'], year=paper['year'], refcount=paper['ref_count'], citecount=paper['cite_count'], venue=paper['venue'])
		for reference in paper["references"]:
			if reference["id"] in papers_ind or reference["id"] in nonlist_papers:
				G.add_edge(paper["id"], reference["id"])
	
	# make a mapping
	idx_to_node_dict = {}
	for idx, node in enumerate(G.nodes()):
		idx_to_node_dict[idx] = node


	# create a color map
	color_map = []
	for node in G:
		if node in nonlist_papers:
			color_map.append('green')
		else:
			color_map.append('blue')

	options = {"edgecolors": "tab:gray", "node_size": 100, "alpha": 0.9}
	fig, ax = plt.subplots()
	pos = nx.spring_layout(G)
	mynodes = nx.draw_networkx_nodes(G, pos=pos, ax=ax, node_color=color_map, label="string", **options)
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
			cont, ind = mynodes.contains(event)
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