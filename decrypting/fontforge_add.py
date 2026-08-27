import fontforge
import json
import sys


input_font_path = sys.argv[1]
output_font_path = sys.argv[2]


def load_cmap_data(file_path):
	""" Load the cmap data from a JSON file """
	with open(file_path, 'r') as f:
		return json.load(f)

def apply_cmap_to_font(cmap_data, input_font_path, output_font_path):
	""" Load a font, apply cmap data, and save the modified font """
	font = fontforge.open(input_font_path)
	
	# Clear existing cmap
	font.encoding = "UnicodeFull"
	font.clear()  # Be careful, this removes all existing glyph mappings!
	# Apply new cmap
	for glyph_name, char  in cmap_data.items():
		if not glyph_name in font and glyph_name.startswith('glyph') and len(glyph_name) > 5:
			glyph_name = 'glyph' + str(int(glyph_name[5:])) 
		if glyph_name in font:
			glyph = font[glyph_name]  # Directly access the glyph by name
			glyph.unicode = ord(char)  # Set the Unicode point directly on the glyph
	# Save the modified font
	font.generate(output_font_path)

def standardize_name(name):
	if name.startswith('glyph') and len(name) > 5:
		return  # Convert to integer to remove leading zeros
	return name



# Load the cmap data
cmap_data = load_cmap_data('cmap_data.json')

# Apply the cmap to the font
apply_cmap_to_font(cmap_data, input_font_path, output_font_path)
