import numpy as np
import pandas as pd
# Function to sanitize LaTeX special characters
def sanitize_latex(s):
	if not type(s)==str:
		return s
	for r in [('_', '\\_'), 
			('&', '\\&'), 
			('%', '\\%'), 
			('$', '\\$'), 
			('#', '\\#'), 
			('^', '\\textasciicircum{} '), 
			('{', '\\{'), 
			('}', '\\}'), 
			('~', '\\textasciitilde{} '),
			('>', '\\textgreater '),
			('<', '\\textless '), 
			('|', '\\textbar ')]:
		
		s = s.replace(*r)
	return s

def format(x):
	if int(x)==x or abs(x)>100:
		return str(int(x))
	if abs(x)>0.0005:
		return str(np.round(x,3))
	if abs(x)<1e-8:
		return '0.00'
	return f'{x:.2e}'

# Function to generate LaTeX table
def generate_latex_table(df, caption, label):
	# Sanitize column names and index
	df.columns = [sanitize_latex(col) for col in df.columns]
	df.index = [sanitize_latex(str(idx)) for idx in df.index]
	cformat = "l" + "r"*(df.shape[1]-1)
	latex_table = df.to_latex(caption=caption, label=label, longtable=False, escape=False, column_format = cformat)
	latex_table = latex_table.replace(r'\midrule',r'\midrule\addlinespace[0.4mm]\midrule') #adding doble line after header
	return latex_table

# Function to generate LaTeX table
def generate_latex_tables(dfs, dfheadings, caption, label):
	# Sanitize column names and index
	for i, df in enumerate(dfs):
		if not df is None:
			dfs[i].columns= [sanitize_latex(col) for col in df.columns]
			dfres = pd.DataFrame(columns=dfs[i].columns)
	
	for i in range(len(dfs)):
		header = pd.DataFrame({col: pd.NA for col in dfres.columns}, index=[dfheadings[i]])
		dfres = pd.concat([dfres, header])
		if not dfs[i] is None:
			dfres = pd.concat((dfres, dfs[i]))

	dfres.index = [sanitize_latex(str(idx)) for idx in dfres.index]
	cformat = "l" + "r"*df.shape[1]
	latex_table = dfres.to_latex(caption=caption, label=label, longtable=False, escape=False, column_format = cformat)
	latex_table = latex_table.replace(r'\midrule',r'\midrule\addlinespace[0.4mm]\midrule') #adding doble line after header
	return latex_table.replace('NaN','')


# Function to generate results table
def generate_result_tables(tbls, years,caption, label):

	s = TOPTBL %(caption,label)
	lend = " \\\\\n" 
	s +=  " ".join([f"& \\textbf {{{y}}}" for y in years]) + lend
	s += "\\midrule\\addlinespace[0.4mm]\n"
	for name in tbls:
		s += r"\textbf{"+ sanitize_latex(name) + r"} & &" + lend
		for group in tbls[name]:
			coefs, stdes = '', ''
			for year in tbls[name][group]:
				cof, se, p = tbls[name][group][year][['mean', 'std err', 'P>|t|']]
				coefs += ' & ' + str(cof)
				stdes += f' & ({se}){significance_code(p)}'
			s += r"\quad "+ sanitize_latex(group) + coefs + lend
			s += stdes + lend

	s += BOTTOMTBL


	return s



def significance_code(p):
	p = float(p)
	if p < 0.0001:
		return "$^{***}$"
	elif p < 0.001:
		return "$^{**}$"
	elif p < 0.01:
		return "$^{*}$"
	elif p < 0.05:
		return " ."
	elif p < 0.1:
		return " $|$"
	return ''


TOPTBL = r"""
\begin{table}[ht]
\centering
\caption{%s}
\label{%s}
\begin{tabular}{lcc}
\toprule
"""



BOTTOMTBL = r""" 
\bottomrule
\end{tabular}
\footnotesize \\
$^{***}$, $^{**}$, $^{*}$, . and $|$, indicate 0.01, 0.1, 1, 5 and 10 \% significance
\end{table}
"""