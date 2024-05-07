import re
import tabula
import numpy as np
import prompts
import fitz  # PyMuPDF
import pickle

ANALYZED_SAVE_DIR = r"Z:\OSE\accountingdata\annual_reports_extract" + '\\'
FORCE_PARSING = True


def open_pdf(path, year, isin, intcode, sid, client):

	if sid is None:
		sid = intcode
	fname = ANALYZED_SAVE_DIR + f"{year}_{isin}_{sid}"

	print(f"Analyzing pdf text for {isin}")
	sections, txt = exctract_pdf_text(path, fname)
	print(f"Analyzing pdf tables for {isin}")
	tables = extract_pdf_tables(path, txt, fname, client)
	print("... done")
	return tables, sections



def extract_pdf_tables(path, txt, fname, client):
	tables = tabula.read_pdf(path, pages='all', multiple_tables=True, guess=True, stream=False)
	d = {}
	for t in tables:
		caption, fixed = get_table(a, t, txt, client)
		d[caption] = fixed

	with open(f"{fname}.tbl", 'wb') as f:
		pickle.dump(d, f)

	return d

def get_table(a, tbl, txt, client):
	tbl = tbl.to_csv(sep='|', index=False)
	tablecont = gpt_identify_text_heavy(tbl, client)
	if  tablecont !='NUMERIC':
		return
	prev_lines = get_previoius_lines(tbl, txt)
	if prev_lines is None:
		fixed = gpt_fix_table(tbl, client, True)
		return f"Table {len(a)+1}: \n\n{fixed}"
	fixed = gpt_fix_table(f"Possible header row: {prev_lines[1]} \n\n" + tbl, client)
	caption = decide_table_caption(prev_lines, client)
	return caption, fixed
	
	
def get_previoius_lines(tbl, txt):
	"Unfortunately tabula tends to miss the first row, so adding the previous line in case it contains the headers"
	N_PREV_LINES = 5
	lines = tbl.split('\n')
	if len(lines)<2:
		return None
	items = []
	for i in range(1,min(len(lines), 4)):
		items.append(re.escape(lines[i].split('|')[0]))
	p = r'.*?'
	pattern = f'^{p}({p.join(items)}){p}$'
	m = re.match(pattern, txt, re.DOTALL)
	if m is None:
		return None
	n = m.start(1)
	prev_lines = txt[:n].split('\n')[-N_PREV_LINES:-2]
	return prev_lines

def gpt_fix_table(tablestr, client, simple = False):
	# Call the model and print the response
	if simple:
		promptstr = prompts.fix_table_simple
	else:
		promptstr = prompts.fix_table_header

	completion = client.chat.completions.create(
		model="gpt-3.5",
		messages=[
			{"role": "system", "content": prompts.fix_table_header},
			{"role": "user", "content": f"Here is the table: \n {tablestr}"}
		], 
		temperature = 0
		)

	return completion.choices[0].message.content

def gpt_identify_text_heavy(tablestr, client):
	# Call the model and print the response
	
	completion = client.chat.completions.create(
		model="gpt-3.5-turbo",
		messages=[
			{"role": "system", "content": prompts.is_mainly_text},
			{"role": "user", "content": f"Here is the table: \n {tablestr}"}
		], 
		temperature = 0
		)

	return completion.choices[0].message.content


def decide_table_caption(captions, tablestr, client):
	# Call the model and print the response
	
	completion = client.chat.completions.create(
		model="gpt-3.5-turbo",
		messages=[
			{"role": "system", "content": prompts.decide_table_caption},
			{"role": "user", "content": f"Here are the captions: \n {str(captions)}"},
			{"role": "user", "content": f"Here is the table: \n {tablestr}"}
		], 
		temperature = 0
		)

	return completion.choices[0].message.content



def exctract_pdf_text(path, fname):
	# Open the PDF file
	document = fitz.open(path)

	plain_count, heading_candidates, block_count, b = analyze_pdf(document)

	html, plain = get_pdf_contents(plain_count, block_count, heading_candidates, b)


	for s, r in [("\r\n", "\n"), 
				 ("\n\n", "\n"),
				 ("  ", " "),]:
		while s in html:
			html = html.replace(s,r)

	sections = get_sections(html)

	document.close()
	html_head = "<!DOCTYPE html>\n<html>\n<body>\n"
	html_tail = "</html>\n</body>\n"
	htmldoc = html_head + html + html_tail

	for contents, extension in  [(htmldoc, '.html'), (plain,   '.txt')]:
		with open(f'{fname}{extension}', 'w', encoding='utf-8') as f:
			f.write(contents)
	
	with open(f"{fname}.sec", 'wb') as f:
		pickle.dump(sections, f)
	
	return sections, plain

def analyze_pdf(document):
	plain_count = {} #For detecting plain text
	heading_candidates = {} #For detecting headings
	block_count = {} #For detecting repeated page contents (footer, header etc.)
	

	for page in document:
		blocks = page.get_text("dict")["blocks"]
		identify_undesired(blocks)


	return plain_count, heading_candidates, block_count, b

def identify_undesired(blocks):
	b = []
	for block in blocks:
		if 'lines' in block:
			b.append(block)
			#Undesired content
			if len(block["lines"]) >= 1 and len(block["lines"]) <= 5:
				add_to_dict(block_count, 
					undesiredfont(block)
					)
					
def get_pdf_contents(plain_count, block_count, heading_candidates, blocks):

	html = ''
	plain = ''
	plain_srt = sorted(plain_count, key=plain_count.get, reverse=True)

	undesired_blocks =  {key: value for key, value in block_count.items() if value > 10}
	blocks_desired = []
	for font, block in blocks:
		if not block in undesiredfont(block):
			blocks_desired.append((font, block))

	headings = get_headings(heading_candidates, plain_srt, undesired_blocks, b)

	for font, block in blocks_desired:
		block_text, plain_text = analyze_block(block, font==plain_srt[0], headings, undesired_blocks)
		html += block_text
		plain += plain_text

	return html, plain



def get_sections(txt):
	"Finds the heading with average number of characters in each section clostest to 5000"
	sections = []
	sec_means = []
	for h in range(4):
		sec = [s.split(f'</h{h+1}>') for s in txt.split(f'<h{h+1}>')]
		sec = {s[0].strip():s[1] for s in sec[1:] if len(s[1])>100}
		sections.append(sec)
		sec_means.append(np.mean([len(sec[k]) for k in sec]))
	m = list(np.abs(np.array(sec_means)-5000))
	h = m.index(min(m))

	return sections[h]

def count_fonts(block, plain_count, heading_candidates, block_count):
	"for detecting headings"
	if not "lines" in block:
		return ''

	n = len(block["lines"])

	#headings
	for line in block["lines"]:
		for s in line["spans"]
			add_to_dict(heading_candidates, 
				f"{s['font']}:{s['size']}:{s['color']}"
				)
		


	#Normal font
	font = 'NA'
	if len(block["lines"]) > 3:
		for line in block["lines"]:
			s = line["spans"]
			font = plainfont(s[0])
			for span in s:
				if font !=  plainfont(span):
					return font
		add_to_dict(plain_count, font)
	return font

def add_to_dict(d, key):
	if len(key.strip()) == 0:
		return
	if key in d:
		d[key] += 1
	else:
		d[key] = 1



def get_headings(heading_candidates, plain_srt, undesired_blocks, b):


	plain_text_size = float(plain_srt[0].split(':')[1])
	h, h_cnt = [], []
	for k in heading_candidates:
		heading_candidates[k]
		
	
	headings = np.array(h)[np.argsort(h_cnt)[::-1]][:4][::-1]

	return headings

def plainfont(span):
	s = f"{span['font']}:{ span['size']}"
	s = s.replace('-Bold','').replace('-Italics','').replace('-Book','').replace('-Light','')
	return s

def undesiredfont(block):
	"Creates keys to flag undesired repeated contents"
	keys = []
	for line in block["lines"]:
		for span in line["spans"]:
			s = span["text"].strip()
			if len(s) and not_int(s):#disregarding page numbers
				keys.append(f"{span["font"]}{span["size"]}:{span["text"]}")
	key = ';'.join(keys)
	return key

def headingfont(line):
	names = []
	for span in line["spans"]:
		names.append(f"{span["font"]}:{span["size"]}")
	return ';'.join(names)

def not_int(s):
	try:
		i = int(s)
	except:
		return True
	

def analyze_block(block, plain, headings, undesired_blocks):
	if undesiredfont(block) in undesired_blocks:
		return '', ''
	
	
	block_text = '\n'
	plain_text = '\n'
	for line in block["lines"]:
		block_text += analyze_line(line, True)
		plain_text += analyze_line(line, False)

		hf = headingfont(line)
		if hf in headings:
			level = list(headings).index(hf) + 1
			block_text = f'<h{level}>' + plain_text + f'</h{level}>\n'
		elif plain:
			block_text = '<p>' + block_text + '</p>\n'

	return block_text, plain_text

def analyze_line(line, add_tags):
	s = ''
	for span in line["spans"]:
		text = span["text"]
		font = span["font"]
		size = span["size"]

		# Check for boldness and italics in the font name as a simple heuristic
		if add_tags:
			text = "<b>" + text + "</b>" if "Bold" in font else text
				
			text = "<i>" + text + "</i>" if "Italic" in font else text
		
		s += f" {text} "


	return text

