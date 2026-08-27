import connect
import db
import pandas as pd
from  matplotlib import pyplot as plt
import statsmodels.api as sm
import scipy.stats as stats
import numpy as np
import analysis_latex
from analysis_latex import format
import analysis_tables


def main():
	runall()
	runall('M')



def runall(r = ''):
	analysis_tables.create()

	conn, crsr = connect.connect()
	sqlstr = """
SELECT * FROM
(SELECT T0.*, T1.[Answer] as [Answ2010], T0.[Answer] as [Answ2011], T0.[Answer] - T1.[Answer] AS [ChangeAnsw] FROM
(SELECT * FROM [research].[dbo].[gpt_ann_rep] where [Year]=2011) T0
left JOIN
(SELECT [iSIN_db], [Year], [Answer] FROM [research].[dbo].[gpt_ann_rep] where [Year]=2010) T1
ON T0.[iSIN_db] = T1.[iSIN_db]) T
where (NOT [ChangeAnsw] IS NULL) AND [n01]>150
"""
	data = db.fetch(sqlstr, crsr)
	df = pd.DataFrame(data, columns=[desc[0] for desc in crsr.description])

	histogram(df, r)

	df_res = df[['ChangeAnsw', 'alpha_2'+ r, 'alpha_1'+r, 'Year', 'dw1'+r, 'rsq_adj1'+r, 'cond_no1'+r]].dropna()
	df_res[['alpha_2'+r, 'alpha_1'+r]] = 52*df_res[['alpha_2'+r, 'alpha_1'+r]]

	fig,ax=plt.subplots(2,2, figsize = (8,6))
	tbls = {}
	tbls_det = []
	headings = []
	period = ['One', 'Two']
	panel = [['A', 'B'], ['C', 'D']]
	years = [2011]
	for i, year in enumerate(years):
		tbls_det.append(None)
		headings.append(f"{year}:")
		for j,l in enumerate([1,2]):
			groups = analyze(l, year, ax[i, j], df_res, panel[i][j], r)
			tbls_det.append(groups)
			headings.append(f'\\quad {period[j]} year alphas')
			name = f'{period[j]} year alphas'
			tbls[name] = tbls.get(name, {})
			for gname, g in groups.iterrows():
				tbls[name][gname] = tbls[name].get(gname, {})
				tbls[name][gname][year] = g
	
				


	caption = 'Mean multifactor alpha by annual GPT performance rating (10=best). Alphas from weekly data have been multiplied by 52. \n'
	if r=='M':
		caption = 'Mean CAPM alpha by annual GPT performance rating (10=best). Alphas from weekly data  have been multiplied by 52. \n'
	caption_tbl = caption.replace('(10=best).', '(10=best), detailed results.')

	results = analysis_latex.generate_result_tables(tbls, years, caption, 'table:results'+r)
	with open(f'output/results{r}.tex', 'w') as f:
		f.write(results)

	results_det = analysis_latex.generate_latex_tables(tbls_det, headings, caption_tbl, 'table:results_det'+r)
	results_det = results_det.replace('Group', r'\quad \quad Group')
	with open(f'output/results_detailed{r}.tex', 'w') as f:
		f.write(results_det)

	fig.suptitle(caption, fontsize=14)
	fig.subplots_adjust(top=0.85, hspace=0.5, wspace=0.5)
	fig.savefig(f'output/results{r}.png')


def histogram(df, r):
	fig, ax = plt.subplots()

	# 2. Plot a histogram for the 'values' column
	ax.hist(df['alpha_1'+r], bins=20)
	ax.set_xlabel('alpha')
	ax.set_ylabel('Frequency')
	fig.savefig(f'output/histogram_{r}.png')


def analyze(window, year, ax, df, panel, r):
	a = window
	df = df[df ['Year']==year]

	X = df['ChangeAnsw']  # Independent variable
	y = df[f'alpha_{a}{r}']  # Dependent variable
	X = sm.add_constant(X)
	model = sm.OLS(y, X).fit()
	print(model.summary())

	grouped = df.groupby('ChangeAnsw')[f'alpha_{a}{r}'].agg(['mean', 'sem'])

	df['Answer_Group'] = df['ChangeAnsw'].apply(lambda x: ['Group 1: <0', "Group 2: 0",'Group 3: >0'][(x>=0)+(x>0)])

	grouped = df.groupby('Answer_Group')[f'alpha_{a}{r}'].agg(['mean', 'sem', 'count'])
	grouped.loc['Group 1: <0', 'mean'] = grouped.loc['Group 1: <0', 'mean'] - grouped.loc["Group 2: 0", 'mean'] 
	grouped.loc['Group 3: >0', 'mean'] = grouped.loc['Group 3: >0', 'mean'] - grouped.loc["Group 2: 0", 'mean'] 

	grouped.loc['Group 1: <0', 'sem'] = (grouped.loc['Group 1: <0', 'sem']**2 + grouped.loc["Group 2: 0", 'sem']**2)**0.5
	grouped.loc['Group 3: >0', 'sem'] = (grouped.loc['Group 3: >0', 'sem']**2 + grouped.loc["Group 2: 0", 'sem']**2 )**0.5
	
	grouped = grouped.drop(["Group 2: 0"])


	stats_gr = (df.groupby('Answer_Group')['dw1'+r].agg(['mean']),
			 df.groupby('Answer_Group')['rsq_adj1'+r].agg(['mean']),
			 df.groupby('Answer_Group')['cond_no1'+r].agg(['median'])
	)
	grouped = pd.concat((grouped, *stats_gr),axis= 1)
	grouped.columns = ['mean', 'std err', 'N', 'DW', 'R2 adj', 'cond indx']
	grouped['t'] = grouped['mean'] / grouped['std err']
	grouped['P>|t|'] = grouped.apply(lambda x: (1 - stats.t.cdf(abs(x['t']), df=x['N'] - 1)), axis=1)
	alpha = 0.05
	grouped[f'[{alpha*0.5} '] = grouped.apply(lambda x: x['mean'] - stats.t.ppf(1 - alpha/2, x['N']-1) * x['std err'], axis=1)
	grouped[f' {1-alpha*0.5}]'] = grouped.apply(lambda x: x['mean'] + stats.t.ppf(1 - alpha/2, x['N']-1) * x['std err'], axis=1)
	grouped['ci'] = grouped.apply(lambda x: stats.t.ppf(1 - alpha/2, x['N']-1) * x['std err'], axis=1)


	# Display the result
	grp_tbl = grouped[['mean', 'std err', 't', 'P>|t|', f'[{alpha*0.5} ', f' {1-alpha*0.5}]', 'N', 'DW', 'R2 adj', 'cond indx']]
	grp_tbl = grp_tbl.applymap(lambda x: format(x))


	ax.bar(grouped.index, grouped['mean'], yerr=grouped['ci'], capsize=4, color='skyblue', ecolor='black')  # Using 'ci' for the error bars
	# Adding labels and title
	groupcaption = "GPT performance rating"
	alphacaption = ['One year window','Two year window'][a-1]
	ax.set_xlabel(groupcaption)
	ax.set_ylabel('Mean alpha')
	ax.set_xticks(grouped.index)  # Ensure ticks correspond to categories
	ax.tick_params(axis='x', labelsize=8)
	ax.set_title(f'Panel {panel}: {year}, {alphacaption}')
	
	return grp_tbl
	

main()
a=0
