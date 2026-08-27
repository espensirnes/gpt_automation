import numpy as np
import fitz  # PyMuPDF
import os
import pickle
import time


from PIL import Image
import pytesseract
import re
import fitz  # PyMuPDF
from fontTools.ttLib import TTFont, TTLibError
from fontTools.t1Lib import T1Font
from fontTools.ttLib import TTFont

import json

import sys
import subprocess
import shutil

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.path as mpath
import matplotlib

import io
from fontTools.pens.basePen import BasePen
import cv2



RESIZE = 0.06
CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
FONTDIR = 'fonts'
TEMP_FONT_PATH = FONTDIR+"/tmpfont."
matplotlib.use('Agg') 
cur_filepath = '/'.join(__file__.split('\\')[:-1])
DECR_EXT = '_decrypted.pdf'

if not os.path.exists(FONTDIR):
	os.makedirs(FONTDIR)


def decrypt(path, fname):
	if os.path.exists(fname + DECR_EXT):
		return fname + DECR_EXT
	doc = fitz.open(path)
	extract_all_fonts(doc, fname)
	doc.save(fname + DECR_EXT)
	doc.close()
	return fname + DECR_EXT
	a=0



def count_unreadable(text):
	n = 0
	for char in text:
		if '\ue000' <= char <= '\uf8ff' or '\U000f0000' <= char <= '\U000ffffd' or '\U00100000' <= char <= '\U0010fffd':
			n += 1
	return n

def extract_all_fonts(doc, fname):
	charmaps = {}
	if os.path.exists(fname + '.fonts'):
		with open(fname + '.fonts','rb') as f:
			charmaps = pickle.load(f)

	for xref in range(1, doc.xref_length()):
		process_xref(xref, doc, charmaps,fname)



def process_xref(xref, doc, charmaps, fname):
	obj = doc.xref_object(xref)
	if not 'FontName' in obj:
		return

	fstream, ext, font_name, font_xref = get_font_stream(xref, doc)
	if not fstream is None: #testing that this is a font stream
		print(f'Extracting font {font_name}')
		extract_gscript_glyphs(fstream, ext, f"{font_name}_{xref}", 
								  charmaps, fname, doc, font_xref)



def get_all_fonts(path):
	doc = fitz.open(path)
	font_dict = {}
	for xref in range(1, doc.xref_length()):
		extract_xref_font(xref, doc, font_dict)
	doc.close()
	return font_dict

def extract_xref_font(xref, doc, font_dict):
	obj = doc.xref_object(xref)
	if not 'FontName' in obj:
		return

	fstream, ext, font_name, font_xref = get_font_stream(xref, doc)
	if fstream is None:
		return
	
	stream = doc.xref_stream(font_xref)
	font, fontfile = get_font(stream, ext)

	font_dict[font_name] = font



		
def get_font_stream(xref, doc):
	obj = doc.xref_object(xref)
	if obj is None:
		return None, None, None
	a = [(r"/FontFile" + i, t) for i, t in [('', 'ptf'), ('2', 'ttf'), ('3', 'otf')]]
	if not any([f[0] in obj for f in a]):
		return None, None, None
	
	for f,t in a:
		match = re.compile(f + r" (\d+)").search(obj)
		if match:
			font_name = re.compile(r"/FontName /([^ ]+)\n").search(obj).group(1)
			font_name = f"{font_name}.{t}"
			break

	if not match:
		return None, None, None
	
	font_xref =  int(match.group(1))
	stream = doc.xref_stream(font_xref)
	return stream, t, font_name, font_xref


def extract_gscript_glyphs(stream, ext, font_name, charmaps, fname, doc, font_xref):
	CHECKPATH = cur_filepath+'/fonts/tmp.pdf'
	# Load the font file
	font, fontfile = get_font(stream, ext)
	
	if not 'cmap' in font:#This is a gscript font
		if font_name in charmaps:
			glyphs = charmaps[font_name]
		else:
			glyphs = translate_glyphs(font)
			charmaps[font_name] = glyphs
			with open(fname + '.fonts' ,'wb') as f:
				pickle.dump(charmaps, f)
		font_new = add_to_font(glyphs,font, fontfile)
		add_font_to_pdf(doc, font_new, font_xref, ext, fontfile, font_name)
		doc.save(CHECKPATH)
		#test doc:
		doc2 = fitz.open(CHECKPATH)
		doc2.close()
		a=0
	else:
		a=0


def add_font_to_pdf(doc, font, font_xref, ext, fontfile, font_name):
	
	with open(fontfile, 'rb') as f:
		font_data = f.read()
	doc.update_stream(font_xref, font_data)



def add_to_font(glyphs,font, fontfile):
	with open('cmap_data.json', 'w') as f:
		json.dump(glyphs, f)
	scriptfile = cur_filepath +'/fontforge_add.py'
	command = [r'C:\Program Files (x86)\FontForgeBuilds\bin\fontforge.exe', '-script', scriptfile, fontfile, fontfile]
	try:
		subprocess.run(command, check=True)
	except subprocess.CalledProcessError as e:
		print("Failed to add unicode:", e)
	font_new = TTFont(fontfile)
	return font_new

	
def get_font(stream, ext):
	fontfile = cur_filepath+'/' + TEMP_FONT_PATH+ext

	with open(fontfile, 'wb') as f:
		f.write(stream)

	
	if ext =='ttf' or ext=='ptf':
		try:
			font = TTFont(fontfile)
		except TTLibError:
			try:
				font = T1Font(fontfile)#should not work
				a=0
			except:
				pass
			fontfile = cur_filepath+'/' + TEMP_FONT_PATH +'otf'
			convert_font(fontfile, fontfile)
			font = TTFont(fontfile)
			
	else:
		try:
			font = T1Font(fontfile)
		except:
			try:
				font = TTFont(fontfile)#should not work
				a=0
			except:
				pass
			fontfile = cur_filepath+'/' + TEMP_FONT_PATH +'otf'
			convert_font(fontfile, fontfile)
			font = TTFont(fontfile)
			

	return font, fontfile



def convert_font(input_path, output_path):
	# Command to run FontForge with the script
	scriptfile = cur_filepath+'/fontforge.py'
	command = [r'C:\Program Files (x86)\FontForgeBuilds\bin\fontforge.exe', '-script', scriptfile, input_path, output_path]
	
	try:
		# Execute the command
		subprocess.run(command, check=True)
		print("Font converted successfully.")
	except subprocess.CalledProcessError as e:
		print("Failed to convert font:", e)



def translate_glyphs(font):

	glyfs = font['glyf']
	glyph_order = font.getGlyphOrder()
	best = []
	d = {}
	for i, glyph_name in enumerate(glyph_order):
		glyphpic = draw_glyph(glyph_name, glyfs, font)
		if not glyphpic is None:
			ocr_char, conf, chars = ocr(glyphpic, best)
			if conf>20 and ocr_char in CHARS:
				best.append([glyphpic, glyph_name])
			d[glyph_name] = ocr_char
	for j, (glyphpic, glyph_name) in enumerate(best[:5]):#The first characters have less context, so replacing them with the full context char set
		d[glyph_name] = chars[j]

	return d


def ocr(img, best):
	cimg = concat_img([i[0] for i in best] + [img])
	for train in ['nor_best', 'nor_fast', 'eng_best', 'eng_fast']:
		cnfg = f'--psm 10 --oem 1 -l {train}'
		data = pytesseract.image_to_data(cimg, config = cnfg)
		chars = ''
		for line in data.split('\n')[1:-1]:
			conf, char = line.split('\t')[-2:]
			chars += char
		conf = float(conf)
		char = chars[-1]
		if len(chars) == len(best)+1 and conf>0:
			return char, conf, chars

	return  '\ufffd', conf, chars


def concat_img(imgs):
	widts = [0] +  [i.width for i in imgs]
	lefts = np.cumsum(widts)
	new_width = max(lefts)
	new_height = max(i.height for i in imgs)
	new_img = Image.new('RGB', (new_width, new_height), "white")
	for i, img in enumerate(imgs):
		new_img.paste(img, (lefts[i], 0))
	return new_img


class GlyphPen(BasePen):
	def __init__(self, glyph_set):
		super().__init__(glyph_set)
		self.points = []

	def _moveTo(self, p0):
		self.points.append(('moveTo', p0))

	def _lineTo(self, p1):
		self.points.append(('lineTo', p1))

	def _curveToOne(self, p1, p2, p3):
		self.points.append(('curveTo', p1, p2, p3))

	def _closePath(self):
		self.points.append(('closePath',))

def draw_glyph(glyph_name, glyf_table, font):

	try:
		glyph_set = font.getGlyphSet()
	except:
		time.sleep(1)
		glyph_set = font.getGlyphSet()
	
	# Create a pen to draw the glyph
	pen = GlyphPen(glyph_set)
	glyph = glyf_table[glyph_name]
	glyph.draw(pen,glyf_table)
	if len(pen.points)==0:
		return
	img = drawimg(pen)

	return img
	
	
def drawimg(pen):
	# Plot the glyph
	fig, ax = plt.subplots()
	ax.set_aspect('equal')

	vertices = []
	codes = []

	for command in pen.points:
		if command[0] == 'moveTo':
			vertices.append(command[1])
			codes.append(mpath.Path.MOVETO)
		elif command[0] == 'lineTo':
			vertices.append(command[1])
			codes.append(mpath.Path.LINETO)
		elif command[0] == 'curveTo':
			vertices.extend([command[1], command[2], command[3]])
			codes.extend([mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4])
		elif command[0] == 'closePath':
			vertices.append(vertices[0])
			codes.append(mpath.Path.CLOSEPOLY)

	path = mpath.Path(vertices, codes)
	patch = patches.PathPatch(path, facecolor='black', edgecolor='black', lw=2)
	ax.add_patch(patch)
	ax.set_xlim([0, 2000])
	ax.set_ylim([-1000, 2000])
	ax.set_axis_off()
	buf = io.BytesIO()
	fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
	plt.close()
	buf.seek(0)
	image = Image.open(buf).convert('L')  # Convert the image to grayscale directly
	padded_image = cv2.copyMakeBorder(np.array(image), 200, 200, 0, 0, cv2.BORDER_CONSTANT, value=[255,255,255])
	image = Image.fromarray(padded_image) 

	#image.show()  # This will show the grayscale version of your plot
	image = image.resize((int(image.width * RESIZE), int(image.height * RESIZE)))


	return image





#for debug:
#decrypt('BMG2786A1062.pdf')
#decrypt('SG9999004477.pdf')