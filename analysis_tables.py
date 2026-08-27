import connect
import db
import pandas as pd
import numpy as np
import analysis_latex
from analysis_latex import format



def create():
	df = get_df()
	# Creating tables
	dfst, dfidx  = get_df_stats(df)
	comstat = calculate_statistics_all(dfst , "Comparative Statistics Table. Returns are log returns in decimals, not percentage.", "table:comparative_statistics", dfidx)
	
	df_mod = get_df_mod(df)
	mod = calculate_statistics_all(df_mod, "Risk Adjusted Excess Return and Market Risk. Returns are log returns in decimals, not percentage.", "table:risadjret")
	
	reports = conclusion_report()

	#saving the tables
	with open('output/comstat.tex', 'w') as f:
		f.write(comstat)
	with open('output/mod.tex', 'w') as f:
		f.write(mod)
	with open('output/reports.tex', 'w') as f:
		f.write(reports)

	a=0



def conclusion_report():
	conn, crsr = connect.connect()
	crsr.execute(SQL_REPORTS_COUNT)
	r = crsr.fetchall()
	d = {}
	n, k = len(r[0]), len(r)
	for i in range(n):
		heading = crsr.description[i][0].replace('_', ' ')
		a = []
		for j in range(k):
			a.append(r[j][i])
		d[heading] = a
	
	df = pd.DataFrame(d)
	df = df.set_index('Year').transpose()
	total = df.loc['Total']
	df = df.drop('Total')
	total_not_included = df.sum()
	df.loc['Total reports not included'] = total_not_included
	df.loc['Total included'] = total - total_not_included
	df.loc['Total reports'] = total
	ltx = df.to_latex(caption="Reports Included", label="table:numreports", longtable=False, escape=False, column_format = 'l'+(n-1)*'r')
	ltx = ltx.replace(r'\midrule', r'\midrule\addlinespace[0.4mm]\midrule')
	a = ltx.split('\n')
	a.insert(-5, r'\midrule') 
	a.insert(-8, r'\midrule') 
	ltx = '\n'.join(a)
	return ltx




def calculate_statistics_all(df,caption, label, dfidx=None):
	tbls = []
	years = [2011]
	for year in [2011]:
		dfy = df[df.index == year]
		stats = calculate_statistics(dfy)

		if not dfidx is None:
			dfidxy = dfidx[dfidx.index == year]
			stats = pd.concat((stats,pd.DataFrame(dfidxy.mean().apply(lambda x:format(x)),columns = ['Mean'])))
		tbls.append(stats)


	res = analysis_latex.generate_latex_tables(tbls, years, caption, label)

	return res

def calculate_statistics(df):
	df = df.select_dtypes(include='number')
	stats = pd.DataFrame({
		'Min': df.min().apply(lambda x:format(x)),
		'Max': df.max().apply(lambda x:format(x)),
		'Mean': df.mean().apply(lambda x:format(x)),
		'Std Dev': df.std().apply(lambda x:format(x)),
		'N': df.count().apply(lambda x:format(x))
	})
	
	#return analysis_latex.generate_latex_table(stats,caption, label)
	return stats

def get_df():
	conn, crsr = connect.connect()
	sqlstr = 	"""
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

	return df

def get_df_stats(df):
	dfst = pd.DataFrame()
	df_idx = pd.DataFrame()
	dfst['Stock ret. (1yr)'] = (df['p11']-df['p01'])/df['p01']
	df_idx['OSEBX ret. (1yr)'] = (df['idx11']-df['idx01'])/df['idx01']

	dfst['Stock ret. (2yrs)'] = (df['p12']-df['p02'])/df['p02']
	df_idx['OSEBX ret. (2yrs)'] = (df['idx12']-df['idx02'])/df['idx02']

	dfst['Change GPT rating'] = df['ChangeAnsw']
	#dfst = dfst.rename(columns={k:r'\quad '+ k for k in dfst.columns})
	dfst.index = df['Year'] 
	df_idx.index = df['Year'] 
	dfst = dfst.rename(columns={k:r'\quad '+ k for k in dfst.columns})
	df_idx = df_idx.rename(columns={k:r'\quad '+ k for k in df_idx.columns})

	return dfst, df_idx

def get_factors(year):
	sqlstr = f"""SELECT sum([SMB]) ,sum([HML]) ,sum([LIQ]) ,sum([MOM])
  FROM [OSE].[dbo].[factors]
  where [date] between '{year}-6-1' and '{year+1}'"""
	conn, crsr = connect.connect()
	

def get_df_mod(df):
	df_mod = pd.DataFrame()
	df_mod['Alpha (1yr) FF'] = df['alpha_1']
	df_mod['Beta (1yr) FF'] = df['beta_1']
	df_mod['Alpha (1yr) CAPM'] = df['alpha_1M']
	df_mod['Beta (1yr) CAPM'] = df['beta_1M']
	df_mod['Alpha (2yrs) FF'] = df['alpha_2']
	df_mod['Beta (2yrs) FF'] = df['beta_2']
	df_mod['Alpha (2yrs) CAPM'] = df['alpha_2M']
	df_mod['Beta (2yrs) CAPM'] = df['beta_2M']
	df_mod = df_mod.rename(columns={k:r'\quad '+ k for k in df_mod.columns})
	df_mod.index = df['Year'] 

	return df_mod





SQL_REPORTS_COUNT = """
SELECT 
    [Year],
	
    SUM(CASE WHEN Category = 'ISIN_not_found' THEN 1 ELSE 0 END) AS ISIN_not_found,
    SUM(CASE WHEN Category = 'Unreadable' THEN 1 ELSE 0 END) AS Unreadable,
    SUM(CASE WHEN Category = 'Insufficient_information' THEN 1 ELSE 0 END) AS Insufficient_information_for_GPT,
    SUM(CASE WHEN Category = 'Unable_to_estimate_alpha' THEN 1 ELSE 0 END) AS Unable_to_estimate_alpha, 
	COUNT(*) as Total
FROM 
(
    SELECT 
        [Year],
        CASE
            WHEN [ISIN_db] IS NULL THEN 'ISIN_not_found'
            WHEN [Explanation] LIKE '%unreadable%' OR [Explanation] LIKE '%corrupted%' THEN 'Unreadable'
			WHEN [alpha_1] IS NULL THEN 'Unable_to_estimate_alpha'
            WHEN [Answer] IS NULL THEN 'Insufficient_information'
            
            ELSE 'Other'
        END AS Category
    FROM 
        [research].[dbo].[gpt_ann_rep]
) AS InnerQuery
GROUP BY 
    [Year];
"""

