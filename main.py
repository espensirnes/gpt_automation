
from openai import OpenAI
import re
import os
import shutil
from datetime import date
import statsmodels.api as sm
import numpy as np
import response
import parsepdf
import connect
import db
import pandas as pd

ANALYZED_SAVE_DIR = r"Z:\OSE\accountingdata\annual_reports_extract" + '\\'

RECORDS = 'rec.csv'

def analyze_dir(dir):
	client = OpenAI()
	# Iterating over files
	recs = get_recs()
	conn, crsr = connect.connect()
	for entry in os.listdir(dir):
		if True:#'BMG2786A1062' in entry:
			path = os.path.join(dir, entry)
			a = analyze_report(path, client, crsr)
			recs = add_rec(recs, a)
			db.add_to_db(a, conn, crsr)
	conn.close()



def analyze_report(path, client, crsr):
	
	if not os.path.isfile(path):
		print(f'{path} not a file or not found')
		return
	isin_, t, year = get_isin_dates(path)
	name, intcode, sid, isin = get_comp_info(isin_, crsr)
	res = [isin_, isin]
	nonres = [isin_, isin]+ (len(db.COLS)-2)*[None]

	fname = ANALYZED_SAVE_DIR + f"{year}_{isin_}_{sid}"

	for i in range(2):
		r = get_alpha(isin, t[0], t[i+1], crsr)
		res.extend(r[i>0:])
	
	if r[0] is None:
		print(f'No observations of {isin_} for the period')
		return nonres
	elif r[3] is None:
		print(f'No valid regression for the period for  {isin_} ')
		return nonres

	sections = parsepdf.open_pdf(path, year, isin_, intcode, sid, fname, name)

	grade, expl = None, None
	if len(sections) and isnummeric(r[1]):
		grade, expl = response.get(sections, client, name, year, fname, isin_)
		print(f"{isin}: {grade};{expl}")
	res.extend([grade])
	

	return res

def isnummeric(x):
	try:
		x = x*1
		return True
	except:
		return False
	
def get_isin_dates(path):
	fname_itms = path.split('\\')[-1].split('_')
	year = int(fname_itms [0])
	s = fname_itms [5]
	t= [date(year + t, 6, 1) for t in range(3)]
	return s, t, year

def get_alpha(isin, t0, t1, crsr):
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
		return 7*[None]

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

	return name, *res.pvalues[0:2], *res.params[0:2], *res.tvalues[0:2]

def get_comp_info(isin, crsr):
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






def add_rec(recs, data):
	if data is None:
		return recs
	data = [str(i).replace('\n', '\r') for i in data]
	assert len(data)==len(recs[0])
	recs.append(data)
	shutil.copy(RECORDS, RECORDS+'~')
	with open(RECORDS,'w') as f:
		for r in recs:
			f.write(';'.join(r) + '\n')
	os.remove(RECORDS+'~')
	return recs

def get_recs():
	if os.path.exists(RECORDS):
		with open(RECORDS,'r') as f:
			text = f.read()
			recs = [r.split(';') for r in text.split('\n')]
		return recs
	else:
		with open(RECORDS,'w') as f:
			f.write(';'.join(db.COLS))
			recs = [db.COLS]
		return recs
	




#analyze_dir(r"C:\Users\esi000\OneDrive - UiT Office 365\Forskning\gpt_automation\Årsrapporter")
analyze_dir(r'Z:\OSE\accountingdata\Årsrapporter\2010-2014')