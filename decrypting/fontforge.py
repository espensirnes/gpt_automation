# convert_font.pe
import fontforge
import sys


input_font_path = sys.argv[1]
output_font_path = sys.argv[2]

# Open the font
font = fontforge.open(input_font_path)

# Save the font in OpenType format
font.generate(output_font_path)
