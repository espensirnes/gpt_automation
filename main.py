
from openai import OpenAI
import re
import os
import shutil
from datetime import date
import statsmodels.api as sm
import numpy as np
import response
import parsepdf

ANALYZED_SAVE_DIR = r"Z:\OSE\accountingdata\annual_reports_extract" + '\\'

try:
	import db
except:
	db = None



RECORDS = 'rec.csv'
COLS = ['ISIN', 'Name', 
		'pval_alpha_1', 'pval_beta_1' , 'tval_alpha_1', 'tval_beta_1',
		'pval_alpha_2', 'pval_beta_2' , 'tval_alpha_2', 'tval_beta_2',
		'Answer', 'Explanation']



#TITLON SCRIPT HERE:
#*********************************


import pandas as pd
import pymssql
con = pymssql.connect(host='titlon.uit.no', 
					user="esi000@uit.no", 
					password  = "pw",
					database='OSE')  
crsr=con.cursor()

#*********************************

def analyze_dir(dir):
	client = OpenAI()
	# Iterating over files
	recs = get_recs()
	for entry in os.listdir(dir):
		if 'BMG3597X1039' in entry:
			path = os.path.join(dir, entry)
			a = analyze_report(path, client)
			recs = add_rec(recs, a)
			if not db is None:
				db.add_to_db(a)


def analyze_report(path, client):
	
	if not os.path.isfile(path):
		print(f'{path} not a file or not found')
		return
	isin_, t, year = get_isin_dates(path)
	name, intcode, sid, isin = get_comp_info(isin_)
	res = [isin_, isin]
	nonres = [isin_, isin]+ (len(COLS)-1)*[None]

	fname = ANALYZED_SAVE_DIR + f"{year}_{isin_}_{sid}"

	r = get_alpha(isin, t[0], t[1])
	if r is None:
		print(f'No observations of {isin_} for the period')
		return nonres

	res.extend(r)
	for i in range(1,2):
		r = get_alpha(isin, t[0], t[i+1])
		if r is None:
			res.extend(4*[None])
		else:
			res.extend(r[1:])

	sections = parsepdf.open_pdf(path, year, isin_, intcode, sid, fname, name)
	grade, expl = response.get(sections, client, name, year, fname, isin_)
	print(f"{isin}: {grade};{expl}")
	res.extend([grade, expl])
	

	return res

def get_isin_dates(path):
	fname_itms = path.split('\\')[-1].split('_')
	year = int(fname_itms [0])
	s = fname_itms [5]
	t= [date(year + t, 6, 1) for t in range(3)]
	return s, t, year

def get_alpha(isin, t0, t1):
	crsr.execute(f"""
		SELECT DISTINCT [ISIN] ,[Name], [Date],[SMB] ,[HML] ,[LIQ] ,[MOM] 
					,[lnDeltaP]-[bills_3month_Lnrate] as [rx]
					,[lnDeltaOSEBX]- [bills_3month_Lnrate] as [rm]
		FROM [OSE].[dbo].[equity]
		WHERE [ISIN] = '{isin}'
			AND [Date] BETWEEN '{t0}' and '{t1}'
		""")
	r = np.array(crsr.fetchall())

	if len(r)==0:
		return None

	d = {k[0]:r[:,i] for i,k in enumerate(crsr.description)}
	df = pd.DataFrame(d).apply(pd.to_numeric, errors='coerce')
	df_x = df[['rm', 'SMB','HML','LIQ','MOM']]

	x = np.array(sm.add_constant(df_x))
	y = np.array(df[['rx']])
	try:
		model = sm.OLS(y, x)
	except:
		nacount = df_x.isna().sum()
		deldf = nacount[nacount>0.5*len(df_x)]
		if len(deldf):
			for k in deldf:
				df_x.pop(k)
		else:
			df = df[['rx','rm', 'SMB','HML','LIQ','MOM']]
			df = df.dropna()
			df_x = df[['rm', 'SMB','HML','LIQ','MOM']]
			y = np.array(df[['rx']])
		x = np.array(sm.add_constant(df_x))
		model = sm.OLS(y, x)
	res = model.fit()

	isin,name = r[0][:2]

	return name, *res.pvalues[0:2], *res.params[0:2]

def get_comp_info(isin):
	crsr.execute(f"""
		SELECT DISTINCT [Name], [Internal code], [SecurityId], [ISIN] FROM [OSE].[dbo].[equity]
		WHERE [ISIN] = '{isin}'
		""")
	r=crsr.fetchall()
	if len(r):
		name, intcode, sid, isin = r[0]
		return name, intcode, sid, isin
	crsr.execute(f"""
		SELECT DISTINCT [Name], [Internal code],T2.[SecurityId] ,T2.[ISIN]
		FROM [OSE].[dbo].[AllISINS] T1
		LEFT JOIN
		(SELECT DISTINCT [SecurityId] ,[ISIN]
		FROM [OSE].[dbo].[equity]) T2
		ON T1.[SecurityId]=T2.[SecurityId]
		WHERE T1.[ISIN] = '{isin}'
		""")
	r=crsr.fetchall()
	if len(r):#This means the ISIN exist, but it is not found in the main table, so new isin is fetched
		name, intcode, sid, isin = r[0]
		return name, intcode, sid, isin

	
	return None, None, None, None


def get_isins():
	crsr.execute("""
		SELECT DISTINCT T1.[SecurityId],T1.[CompanyId],T2.[ISIN]

		FROM [OSEData].[dbo].[equityfeed_EquityInformation] T1
		LEFT JOIN
		(SELECT DISTINCT [SecurityId],[ISIN]
		FROM [OSEData].[dbo].[equityfeed_EquitySecurityInformation]) T2
		ON T1.[SecurityId] = T2.[SecurityId]
		ORDER BY T1.[SecurityId],T1.[CompanyId],T2.[ISIN]""")
	r=crsr.fetchall()




def add_rec(recs, data):
	if data is None:
		return recs
	data = [str(i) for i in data]
	recs += '\n' + ';'.join(data)
	shutil.copy(RECORDS, RECORDS+'~')
	with open(RECORDS,'w') as f:
		f.write(recs)
	os.remove(RECORDS+'~')
	return recs

def get_recs():
	if os.path.exists(RECORDS):
		with open(RECORDS,'r') as f:
			recs = f.read()
		return recs
	else:
		with open(RECORDS,'w') as f:
			f.write(';'.join(COLS))
		return ''



#analyze_dir(r"C:\Users\esi000\OneDrive - UiT Office 365\Forskning\gpt_automation\Årsrapporter")
analyze_dir(r'Z:\OSE\accountingdata\Årsrapporter\2010-2014')