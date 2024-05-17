import re
import tabula
import numpy as np
import prompts
import fitz  # PyMuPDF
import pickle
import os
import get_tables


FORCE_PARSING = True


def open_pdf(path, year, isin, intcode, sid, fname, name):

	if sid is None:
		sid = intcode
	

	print(f"Analyzing pdf text for {name} ({year}) - {isin}")
	sections = exctract_pdf_text(path, fname, False)
	print("... done")
	return sections


def exctract_pdf_text(pdf_path, fname, force):
	
	#Check for stored data:

	sections = read_sections(fname, force)
	if not sections is None:
		return sections
	
	# Open the PDF file

	document = open_and_split_pages(pdf_path)

	pages, fonts = analyze_pdf(document)

	

	html = blocks_to_text(pages, fonts, fname)
	sections = get_sections(html)


	with open(f'{fname}{'.dmp'}', 'wb') as f:
			pickle.dump(sections, f)

	document.close()
	
	return sections



import fitz  # Import the library

def open_and_split_pages(pdf_path):
	document = fitz.open(pdf_path)
	edit_doc = fitz.open(pdf_path)
	for i in range(len(document)-1, -1, -1):
		split_page(document, i, edit_doc)
	document.close()
	return edit_doc

def split_page(doc, pnum, edit_doc):
	page = doc[pnum]
	rect = page.rect  # Get the dimensions of the page
	width = rect.width
	height = rect.height
	
	if width < height:  # Check if the page is landscape
		return
	
	blocks = page.get_text("dict")["blocks"]
	for block in blocks:
		if blocking_block(block,width/2):
			return
	
	# Define the rectangles for the left and right halves
	left_half = fitz.Rect(0, 0, width / 2, height)
	right_half = fitz.Rect(width / 2, 0, width, height)

	page_number = page.number

	# Insert two new pages in place of the current page

	edit_doc.delete_page(pnum)
	for half in [right_half, left_half]:
		n = edit_doc.insert_page(pnum, width=width / 2, height=height)  # Insert at current index
		edit_doc[pnum].show_pdf_page(edit_doc[pnum].rect, doc, pnum, clip=half)  # Offset due to insertion
	


def blocking_block(block, midpoint):
	if 'bbox' in block and 'lines' in block:
		x0, y0, x1, y1 = block['bbox']
		if x0 < midpoint < x1:
			for line in block['lines']:
				x0, y0, x1, y1 = line['bbox']
				if x0 < midpoint < x1:
					for span in line['spans']:
						x0, y0, x1, y1 = span['bbox']
						if x0 < midpoint < x1:
							return True
	return False


def read_sections(fname, force):

	path = f'{fname}{'.dmp'}'
	if os.path.exists(path) and (not force):
		with open(path, 'rb') as f:
			sections = pickle.load(f)
		return sections
	else:
		return None

def get_sections(html):

	a = []
	sections = html.split('<h1>')
	for sec in sections:
		if '</h1>' in sec:
			sec = '<h1>' +  sec

		a.append(sec)

	
	return a




def analyze_pdf(document):

	p = []
	undesired_blocks = {}
	for page in document:
		blocks = page.get_text("dict")["blocks"]
		b = []
		for block in blocks:
			if 'lines' in block:
				b.append(block)
				add_undersired_contents(block, undesired_blocks)
		p.append(b)
	
	undesired_blocks =  {key: value for key, value in undesired_blocks.items() if value > 10}

	
	pages = []
	fonts = {}
	s = ''
	for page in p:
		blocks = []
		for block in page:
			if not undesiredfont(block) in undesired_blocks:
				s+=getline(block)
				blocks.append(block)
				add_fonts(block, fonts, s)
		pages.append(blocks)
	
	if len(s) == 0:
		return 'no content', None
	if is_unreadable(s):
		return 'unreadable', None

	#with open('test.txt', 'w', encoding='utf-8') as f:
	#	f.write(s)

	return pages, fonts

def is_unreadable(s):
	n = 0
	for char in s:
		if '\ue000' <= char <= '\uf8ff' or '\U000f0000' <= char <= '\U000ffffd' or '\U00100000' <= char <= '\U0010fffd':
			n += 1
	return n/len(s)>0.9
	
def getline(block):
	s = ''
	for line in block['lines']:
		for span in line['spans']:
			s+=f'{span['text']}'
		s += '\n'
	return s


def add_undersired_contents(block, undesired_blocks):
	n = len(block["lines"]) 
	#Undesired content
	if n>= 1 and  n <= 5:
		key = undesiredfont(block)
		undesired_blocks[key] = undesired_blocks.get(key, 0) + 1 

		
def add_fonts(block, fonts, s):

	for line in block["lines"]:
		identical = all(fontstring(sp) == fontstring(line["spans"][0]) for sp in line["spans"])
		s_ = ''
		for span in line["spans"]:
			key = fontstring(span)
			(a, t) = fonts.get(key, ([] , []))
			s_ += span['text']
			if not identical:
				a.append(len(s)+ len(s_))
				t.append(span['text'].strip())
				fonts[key] = (a, t)
		if identical:
			a.append(len(s))
			t.append(s_.strip())
			fonts[key] = (a, t)

			

					
def blocks_to_text(pages, fonts, fname):
	if pages == 'unreadable' or pages == 'no content':
		return pages
	html = ''
	plain = ''
	rows = []
	numbers = []
	spans = []
	pages_spans = []
	heading, plain_font = get_fonts(fonts)
	tables = []
	used_headings = {}
	for pnum, blocks in enumerate(pages):
		spans = []
		for block in blocks:
			h, p, r, s = analyze_block(block, plain_font, heading, used_headings, plain)
			html += h
			plain += p
			spans.append((len(rows),s))
			rows.append(r)
			add_number(r, numbers)
		pages_spans.append(spans)
		tbl, head, pos = get_tables.get(spans)
		if len(tbl):
			tables.append([tbl, head, pos])

	
	html = insert_tables(tables, html)
	html = clean_html(html)
	save_html(html, fname)

	return html

def add_number(r, numbers):
	numbers.append(0)
	for i in range(1, len(r)):
		c = r[i].replace(',','').replace(' ','')
		if is_number(c):
			numbers[-1] += 1




def is_number(x):
	try:
		a = float(x)
		return True
	except:
		return False


def save_html(html,fname):

	meta = f"\n<meta charset='utf-8'><title>{fname.split('\\')[-1]}</title>"
	html_head = f"<!DOCTYPE html>\n<html>\n<head>{meta}\n<style>\n{css}\n</style>\n</head>\n<body>\n"
	html_tail = "</html>\n</body>\n"
	htmldoc = html_head + html + html_tail

	with open(f'{fname}{'.html'}', 'w', encoding='utf-8') as f:
		f.write(htmldoc)

def insert_tables(tables, html):
	DIVSTR = '\n<div class="markdown-table">\n'
	lines = html.split('\n')
	for i, (t, h, p) in enumerate(tables):
		a, b = p
		heading = f'\n<b>Table {i}: {h}</b>\n\n'
		lines[a:b] = [''] * (b - a)
		lines[a] = heading + DIVSTR + t + '\n</div>\n'
		

	html = '\n'.join(lines)

	return html



def clean_html(html):
	for s, r in [("\r\n", "\n"), 
				("\n"*3, "\n"*2)]:
		while s in html:
			html = html.replace(s,r)
	
	return html





def get_fonts(fonts):
	fa = {}
	fn = {}
	srt = sorted(fonts, key=fonts.get, reverse=True)
	plain = srt[0]
	totlen = 0
	for k in fonts:
		totlen += sum([len(x) for x in fonts[k][1]])
	headings = {}
	for hspan in [0.8, 0.6, 0.4, 0.2]:
		d = {}
		for k in srt:
			a, t = fonts[k]
			h = [len(s) for s in t]
			n = sum(h)
			diff = 0
			if len(a)>5:
				diff = np.sort(np.diff(a))
				diff =diff[int(len(a)*0.5)]
			start = min(a)/totlen
			end = max(a)/totlen

			if False:
				print((n/totlen<0.05,diff,end-start,len(np.unique(t)),np.mean(h)))
				print(t)
				d[end-start] = t
			if (n/totlen<0.05 and end-start>hspan and 
				len(np.unique(t))>4 and  np.mean(h)>10 and np.mean(h)<500):
				headings[k] = len(np.unique(t))
		if len(headings):
			break
	h = sorted(headings, key=headings.get)
	return h[0], plain


def fontstring(span):
	font, size, color = span['font'], span['size'], span['color']
	return f"{font}:{size}:{color}"



def undesiredfont(block):
	"Creates keys to flag undesired repeated contents"
	keys = []
	for line in block["lines"]:
		for span in line["spans"]:
			s = span["text"].strip()
			if len(s) and not_int(s):#disregarding page numbers
				keys.append(f"{span['font']}{span['size']}:{span['text']}")
	key = ';'.join(keys)
	return key

def not_int(s):
	try:
		i = int(s)
	except:
		return True
	

def analyze_block(block, plain_font, heading, used_headings, fulltxt):
	html = '\n'
	plain = '\n'
	row = []
	spans = []
	was_plain = False

	h0 = ''
	for line in block["lines"]:
		h, p, is_plain = analyze_line(line, heading, plain_font, spans, used_headings, fulltxt)

		if (not was_plain) and is_plain:
			html += '<p>' + h
			was_plain = True
		elif was_plain and (not is_plain):
			html += '</p>' + h
			was_plain = False
		else:
			html += h
		
		plain += p
		h0 = h
		row.append(p)
	
	if ('<p>' in html) and not ('</p>' in html):
		html += '</p>'


	return html, plain, row, spans


def analyze_line(line, heading, plain_font,spans, used_headings, fulltxt):
	plain = ''
	html = ''
	is_plain = True
	
	for span in line["spans"]:
		text = span["text"]
		font = span["font"]

		spans.append(span)

		plain += f" {text} "

		fnt = fontstring(span)

		if not fnt == plain_font:
			is_plain == False


		text = "<b>" + text + "</b>" if "Bold" in font else text
			
		text = "<i>" + text + "</i>" if "Italic" in font else text
		
		html += f" {text} "

		html = add_heading(fnt, heading, text, used_headings, html, fulltxt)


	return html, plain, is_plain

def add_heading(fnt, heading, text, used_headings, html, fulltxt):
	if not fnt == heading:
		return html
	
	if len(used_headings):
		if len(fulltxt) - list(used_headings.values())[-1]<1000: #no text in heading range
			return html
		
	head_txt = text.lower().strip()
	for s in ['cont', 'continued', 'forts.', 'fortsettelse']:
		head_txt = head_txt.replace(f' {s}', '')

	if head_txt in used_headings:
		return html
	
	used_headings[head_txt] = len(fulltxt)

	html = f'<h1>' + text + f'</h1>\n'

	return html

css = """
body {
  counter-reset: h1;
}

h1 {
	color: #4CAF50; /* Green */
	font-weight: bold;
	margin-bottom: 0.5em;
	text-shadow: 1px 1px 2px #ccc;
	counter-reset: h2;
	counter-increment: h1;
	content: counter(h1) ". ";
}

h2 {
	color: #2196F3; /* Blue */
	font-weight: 500;
	margin-bottom: 0.4em;
	counter-reset: h3;
	counter-increment: h2;
	content: counter(h1) "." counter(h2) ". ";
}

h3 {
	color: #F44336; /* Red */
	font-weight: normal;
	margin-bottom: 0.3em;
	counter-reset: h4;
	counter-increment: h3;
	content: counter(h1) "." counter(h2) "." counter(h3) ". ";
}

/* Style to display the numbers before the headings */
h1:before, h2:before, h3:before {
  content: counter(h1) " ";
}

h2:before {
  content: counter(h1) "." counter(h2) " ";
}

h3:before {
  content: counter(h1) "." counter(h2) "." counter(h3) " ";
}
.markdown-table { white-space: pre; font-family: monospace; }
"""

