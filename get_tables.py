import numpy as np


MIN_OBS = 5

def get(spanitems):
	all_spans = []
	for r, spans in spanitems:
		for span in spans:
			all_spans.append((r, span))
	table, rnums = bbox_to_table(all_spans)
	table, heading, pos = remove_text(table, rnums)
	if not is_nummerical(table):
		return [], None, None
	table = markdown_table(table)
	return table, heading, pos

def is_nummerical(table):
	if len(table) == 0:
		return False
	nmbr = []
	for r in table:
		for c in r[1:]:
			nmbr.append(is_number(c))

	return sum(nmbr)/len(nmbr)>0.2

def remove_text(table, rnums):
	a = content(table)
	b = len(table)- content(table[::-1])
	if a>=b:
		return [], None, None
	heading = ''
	if a>0:
		heading = table[a-1,0]
	rnums = rnums[a:b]
	rnums = rnums[rnums!=None]
	pos = min(rnums), max(rnums)
	return table[a:b], heading, pos

def content(table):
	i = 0
	for r in table:
		cntnt = False
		for c in r[1:]:
			if not c is None:
				cntnt = True
				break
		if cntnt:
			return i
		else:
			i += 1
	return i


def bbox_to_table(all_spans):
	nr = [None, None]
	a = []
	for i, (r, span) in enumerate(all_spans):
		a.append(span['bbox'])
		x0, y0, x1, y1 = span['bbox']
		if is_number(span):
			if nr[0] is None:
				nr[0] = i
			nr[1] = i
	if (nr[0] is None) or (nr[1] is None) or (nr[0]>nr[1]-2):
		return [], []
	a = np.array(a)
	start = max(1, nr[0]-6)
	end = min(nr[1]+5, len(all_spans))

	page = all_spans[start:end]
	a = a[start:end]
	x = split_spans(a, 0)
	y = split_spans(a, 1)

	ny = max([y[k] for k in y])
	nx = max([x[k] for k in x])

	table = np.full((ny+1, nx+1), None, dtype='object')
	rnums = np.full((ny+1, nx+1), None, dtype='object')
	for r, span in page:
		x0, y0, x1, y1 = span['bbox']
		table[y[y0], x[x0]] = span['text']
		rnums[y[y0], x[x0]] = r

	return table, rnums

def split_spans(arr, k):
	s = np.argsort(arr[:,k])
	arr = arr[s]
	a = arr[:,k:k+1]
	b = arr[:,2+k:3+k]
	intersect = (a <= a.T)&(a.T <= b)
	intersect[np.tril_indices(len(a), -1)] = False
	sections = np.sum(intersect,0)
	diff = np.insert(np.diff(sections), 1,0)

	#removing ordinary sentences at the beginning
	nz = np.nonzero(diff<0)[0]
	if len(nz):
		intersect[:nz[0],nz[0]:] = False

	sections = np.sum(intersect,0)
	diff = np.diff(sections, prepend=[0])
	groups = []
	g = []
	for i in range(len(diff)):
		if diff[i] <= 0:
			groups.append(g)
			g = [i]
		else:
			g.append(i)
	groups.append(g)
	
	d = {}
	for i, g in enumerate(groups):
		for j in g:
			d[a[j,0]] = i
	return d




def markdown_table(table):
	# Determine the maximum width of each column
	num_columns = len(table[0])  # Assume all rows have the same number of columns
	max_width = [0] * num_columns

	# Find maximum width for each column
	for row in table:
		for index, item in enumerate(row):
			if item is None:
				item = ''
			# Update the maximum width for each column
			max_width[index] = max(max_width[index], len(item))

	# Adjust widths to be at least the width of the longest item + 2 spaces
	max_width = [width + 2 for width in max_width]

	# Create the Markdown table string
	markdown_str = ""
	for row_index, row in enumerate(table):
		line = "|"
		for index, item in enumerate(row):
			if item is None:
				item = ''
			if index == 0:  # Left align for the first column
				line += f" {item.ljust(max_width[index] - 1)}|"
			else:  # Right align for all other columns
				line += f" {item.rjust(max_width[index] - 1)}|"
		line += "\n"
		
		# Add the line to the final Markdown string
		markdown_str += line
		
		# After the header row, add the alignment row
		if row_index == 0:
			line = "|"
			for i, width in enumerate(max_width):
				if i == 0:
					line += ' ' + '-' * (width - 2) + ' |'  # Left-aligned
				else:
					line += ' ' + '-' * (width - 2) + ' |'  # Right-aligned
			line += "\n"
			markdown_str += line

	return markdown_str


def is_number(x):
	if x is None:
		return False
	if not type(x) == str:
		x = x['text']
	for a in [(',',''), (' ',''), ('$',''), 
		   ('(',''), (')',''), ('%','')]:
		x = x.replace(*a)
	try:
		a = float(x)
		return True
	except:
		return False


