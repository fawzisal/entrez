"""Simple interface to the amazing NCBI databases (Entrez).

equery(tool[, ...]) - Yield the response of a query with the given tool.
eapply(db, term, tool[, db2, retmax, ...]) - Yield the response of applying
                                        a tool over the results of a query.

Examples of use:

* Fetch information for SNP with id 3000, as in the example of
  http://www.ncbi.nlm.nih.gov/projects/SNP/SNPeutils.htm

  for line in equery(tool='fetch', db='snp', id='3000'):
      print(line)

* Get a summary of nucleotides related to accession numbers
  NC_010611.1 and EU477409.1

  for line in eapply(db='nucleotide',
                     term='NC_010611.1[accs] OR EU477409.1[accs]',
                     tool='summary'):
      print(line)

"""

#
# Useful references (at http://www.ncbi.nlm.nih.gov/books):
# * Converting accession numbers:
#     /NBK25498/#chapter3.Application_2_Converting_access
# * Retrieving large datasets:
#     /NBK25498/#chapter3.Application_3_Retrieving_large
# * E-Utilities:
#     /NBK25497/#chapter2.The_Nine_Eutilities_in_Brief
#

from re import search
try:
    from urllib import urlencode
    from urllib2 import urlopen
except ImportError:  # Python 3
    from urllib.parse import urlencode
    from urllib.request import urlopen


_valid_tools = 'info search post summary fetch link gquery citmatch'.split()
_valid_params = ('db term id usehistory query_key WebEnv '
                 'rettype retmode retstart retmax').split()


def equery(tool='search', **params):
    """Return http response for the requested E-utility query."""
    # First make some basic checks.
    assert tool in _valid_tools, 'Invalid web tool: %s' % tool
    for k in params:
        assert k in _valid_params, 'Unknown parameter: %s' % k
    # TODO: we could really check better than this...

    # Make a POST request and return the http response object.
    url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/e%s.fcgi' % tool
    for line_bytes in urlopen(url, urlencode(params).encode('ascii')):
        yield line_bytes.decode('ascii').rstrip()


def eapply(db, term, tool, db2=None, retmax=500, **params):
    """Yield the results of querying db with term, and using tool over them.

    Select (search) the elements in database db that satisfy the query
    in term, and yield the output of applying the given tool on them.

    Args:
      db: Database where the query is done.
      term: Query term that selects elements to process later.
      tool: E-Utilitiy that is used on the selected elements.
      db2: Database where tool is applied. If None, it's the same as db.
      retmax: Chunk size of the reading from the NCBI servers.
      params: Extra parameters to use with the E-Utility.
    """
    # Use the search tool with usehistory='y' to select the elements,
    # and keep the values of WebEnv, QueryKey and Count in the fields dict.
    fields = {}
    for line in equery(tool='search', usehistory='y', db=db, term=term):
        for k in ['WebEnv', 'QueryKey', 'Count']:
            if k not in fields and '<%s>' % k in line:
                fields[k] = search('<%s>(\S+)</%s>' % (k, k), line).groups()[0]
    # Now we can use the values of WebEnv and QueryKey to reference
    # the results of the search.

    # Ask for the results of using tool over the selected elements, in
    # batches of retmax each.
    for retstart in range(0, int(fields.get('Count', '1')), retmax):
        for line in equery(tool=tool, db=(db2 or db),
                           WebEnv=fields['WebEnv'],
                           query_key=fields['QueryKey'],
                           retstart=retstart, retmax=retmax, **params):
            yield line
