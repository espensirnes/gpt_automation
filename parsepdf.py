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
	sections = exctract_pdf_text(path, fname, True)
	print("... done")
	return sections


def exctract_pdf_text(pdf_path, fname, force):
	
	#Check for stored data:

	sections = read_sections(fname, force)
	if not sections is None:
		return sections
	
	# Open the PDF file
	document = fitz.open(pdf_path)

	pages, fonts, headings = analyze_pdf(document)

	html = blocks_to_text(pages, fonts, headings, fname)
	sections = get_sections(html)


	with open(f'{fname}{'.dmp'}', 'wb') as f:
			pickle.dump(sections, f)

	document.close()
	
	return sections



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
		if '</h2>' in sec:
			sec = '<h2>' +  sec
		subsections = sec.split('<h2>')
		for subsec in subsections:
			if '</h2>' in subsec:
				subsec = '<h2>' +  subsec
			a.append(subsec)
	
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
	headings = {}
	
	for page in p:
		s = ''
		blocks = []
		for block in page:
			if not undesiredfont(block) in undesired_blocks:
				#s+=getline(block)
				blocks.append(block)
				add_fonts(block, fonts, headings)
		pages.append(blocks)

	#with open('test.txt', 'w', encoding='utf-8') as f:
	#	f.write(s)

	return pages, fonts, headings

def getline(block):
	s = ''
	for line in block['lines']:
		for span in line['spans']:
			s+=f' {span['text']} '
			print(span['text'])
			print(span['bbox'])
		s += '\n'
	return s


def add_undersired_contents(block, undesired_blocks):
	n = len(block["lines"]) 
	#Undesired content
	if n>= 1 and  n <= 5:
		add_to_dict(undesired_blocks, 
			undesiredfont(block)
			)
		
def add_fonts(block, fonts, headings):
	for line in block["lines"]:
		for span in line["spans"]:
			add_to_dict(fonts, fontstring(span))
			add_to_dict(headings, fontstring(span, False))
					
def blocks_to_text(pages, fonts, headings, fname):

	html = ''
	plain = ''
	rows = []
	numbers = []
	spans = []
	pages_spans = []
	plain_font = sorted(fonts, key=fonts.get, reverse=True)[0]
	headings = get_headings(headings, plain_font)
	tables = []
	for pnum, blocks in enumerate(pages):
		spans = []
		for block in blocks:
			h, p, r, s = analyze_block(block, plain_font, headings)
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




def add_to_dict(d, key):
	if len(key.strip()) == 0:
		return
	if key in d:
		d[key] += 1
	else:
		d[key] = 1



def get_headings(headings, plain_font):
	plain_font_size = float(plain_font.split(':')[1])
	plain_font_color = float(plain_font.split(':')[2])
	htmp={k:headings[k] for k in headings}
	heads = []
	for b, z in [(False, 1.1), (True, 1.1), (False, 1.0), (True, 1.0)]:
		headings_filtered = {}
		for k in htmp:
			hsize = float(k.split(':')[1])
			hcolor = float(k.split(':')[2])
			if hsize>z*plain_font_size and ((hcolor!=plain_font_color) or b):
				headings_filtered[k] = htmp[k]
		h = sorted(headings_filtered, key=headings_filtered.get, reverse=True)
		if len(h)>1:
			if htmp[h[0]]>5:
				heads.append(h[0])
				htmp.pop(h[0])
	if len(heads)==0:
		heads = sorted(headings_filtered, key=headings_filtered.get, reverse=True)

	
	
	#heading frequency should increase
	#if it does not increase, subsequent items are probably not headings
	h = []
	nmin = headings[heads[0]]
	for k in heads:
		if headings[k]<nmin:
			break
		h.append(k)

	return h

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
	

def analyze_block(block, plain_font, headings):
	html = '\n'
	plain = '\n'
	row = []
	spans = []
	was_plain = False
	for line in block["lines"]:
		h, p, is_plain = analyze_line(line, headings, plain_font, spans)
		if (not was_plain) and is_plain:
			html += '<p>' + h
			was_plain = True
		elif was_plain and (not is_plain):
			html += '</p>' + h
			was_plain = False
		else:
			html += h
		
		plain += p
		row.append(p)
	
	if ('<p>' in html) and not ('</p>' in html):
		html += '</p>'


	return html, plain, row, spans

def analyze_line(line, headings, plain_font,spans):
	plain = ''
	html = ''
	is_plain = True
	head = 'NA'
	for span in line["spans"]:
		text = span["text"]
		font = span["font"]
		print(f"{font}:{span["size"]}:{text}")
		spans.append(span)

		plain += f" {text} "

		fnt = fontstring(span)
		heading = fontstring(span, False)

		if not fnt == plain_font:
			is_plain == False

		if heading in headings:
			head = heading

		text = "<b>" + text + "</b>" if "Bold" in font else text
			
		text = "<i>" + text + "</i>" if "Italic" in font else text
		
		html += f" {text} "

	if head in headings:
		level = list(headings).index(head) + 1
		html = f'<h{level}>' + plain + f'</h{level}>\n'

	return html, plain, is_plain



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

