
from openai import OpenAI
import re
import os
import shutil
from datetime import date
from datetime import timedelta
import statsmodels.api as sm
import numpy as np
import response
import parsepdf
import connect
import db
import pandas as pd
from statsmodels.stats.stattools import durbin_watson


ANALYZED_SAVE_DIR = r"Z:\OSE\accountingdata\annual_reports_extract" + '\\'


DAYS = [0,-1, -2, 1, -3, 2, -4, 3, 4]

FORWARD_LOOKING = True
TBL = 'gpt_ann_rep_forw'

def analyze_dir(dir):
	client = OpenAI()
	conn, crsr = connect.connect()
	isin_year = db.get_isin_year_in_db(crsr, TBL)

	# Iterating over files:
	for entry in os.listdir(dir):
		isin_, t, year  = get_isin_dates(entry, FORWARD_LOOKING)
		name, intcode, sid, isin = get_comp_info(isin_, crsr)
		if year < 2015 and (not f"{isin_}_{year}" in isin_year):#isin == 'NO0003033102' and year==2011:
			path = os.path.join(dir, entry)
			a = analyze_report(path, client, crsr, isin_, isin, t, year, name, intcode, sid)
			db.add_to_db(a, conn, crsr, TBL)
		else:
			a=0

	conn.close()

def parseonly(dir):
	conn, crsr = connect.connect()
	for entry in os.listdir(dir):
		path = os.path.join(dir, entry)
		if 'BMG2786A1062' in path or True: #edit to only parse specific files
			if not os.path.isfile(path):
				print(f'{path} not a file or not found')
				return
			isin_, t, year = get_isin_dates(path)
			name, intcode, sid, isin = get_comp_info(isin_, crsr)
			fname = ANALYZED_SAVE_DIR + f"{year}_{isin_}_{sid}"
			sections = parsepdf.open_pdf(path, year, isin_, intcode, sid, fname, name, True)


def analyze_report(path, client, crsr, isin_, isin, t, year, name, intcode, sid):
	
	if not os.path.isfile(path):
		print(f'{path} not a file or not found')
		return
	
	res = [isin_, isin, year, name, intcode, sid]
	nonres = res+ (len(db.COLS)-len(res))*[None]

	fname = ANALYZED_SAVE_DIR + f"{year}_{isin_}_{sid}"

	for i in range(2):
		r = GetAlpha(isin,t[0], t[1], t[i+2], crsr).results
		res.extend(r)
	
	
	if res[1] is None:
		print(f'Valid ISIN not found')
		nonres[-1] = 'Valid ISIN not found'
		return nonres
	if ((res[6] is None) and (res[14] is None)):
		print(f'Unable to estimate alpha')
		nonres[-1] = 'Unable to estimate alpha'
		return nonres
	
	sections = parsepdf.open_pdf(path, year, isin_, intcode, sid, fname, name)

	grade, expl = None, None
	if sections[0] in ['no content', 'unreadable']:
		grade, expl = None, sections[0]
	elif len(sections) and isnummeric(r[1]):
		grade, expl = response.get(sections, client, name, year, fname, isin_)
		print(f"{isin}: {grade};{expl}")
	res.extend([grade, expl])

	
	assert( len(db.COLS) == len(res))
	return res

def isnummeric(x):
	try:
		x = x*1
		return True
	except:
		return False
	
def get_isin_dates(path, forward_looking):
	
	fname_itms = path.split('\\')[-1].split('_')
	year = int(fname_itms [0])
	s = fname_itms[5]
	if forward_looking:
		t= [date(year + t, 6, 1) for t in range(4)]
	else:
		t= [date(year + t - 1, 1, 1) for t in range(4)]
	
	return s, t, year


class GetAlpha:
		
	def __init__(self, isin, t_1, t0, t1, crsr):
		self.crsr = crsr
		self.isin = isin
		self.fetch_data(t0, t1)

		if len(self.df) < 5:
			self.results = 20*[None]#needs to correspond, in # of items, to output variable below
			return

		res, df = self.regress(['rm', 'SMB','HML','LIQ','MOM'])

		res_m, df_m = self.regress(['rm'])

		mean_ret_company = np.mean(df['rx'])
		mean_ret_index = np.mean(df['rm'])

		n0 = self.count_period(t_1, t0)
		n = len(df)

		output = [mean_ret_company, mean_ret_index,n0, n, 
			self.idx0, self.idx1, self.p0, self.p1,
			*res.pvalues[0:2], *res.params[0:2], *res.tvalues[0:2], 
			durbin_watson(res.resid), res.rsquared_adj, res.condition_number,
			*res_m.pvalues[0:2], *res_m.params[0:2], *res_m.tvalues[0:2],
			durbin_watson(res_m.resid), res_m.rsquared_adj, res_m.condition_number
			
			] #Needs to correspond, in # of items, to the abort result above
			

		
		self.filter(output)

		self.results = output

	def fetch_data(self, t0, t1):
		self.crsr.execute(f"""
			SELECT DISTINCT [ISIN] ,[Name], [Date],[SMB] ,[HML] ,[LIQ] ,[MOM] 
						,[lnDeltaP]-[bills_3month_Lnrate] as [rx]
						,[lnDeltaOSEBX]- [bills_3month_Lnrate] as [rm]
			FROM [OSE].[dbo].[equity]
			WHERE [ISIN] = '{self.isin}'
				AND [Date] BETWEEN '{t0}' and '{t1}'
			ORDER BY [Date]
			""")
		r = np.array(self.crsr.fetchall())
		if len(r)==0:
			self.df = pd.DataFrame({k[0]:[] for i,k in enumerate(self.crsr.description)})
			self.idx0, self.idx1, self.p0, self.p1 = None, None, None, None
			return 
		d = {k[0]:r[:,i] for i,k in enumerate(self.crsr.description)}
		self.df = pd.DataFrame(d)
		self.df['Date'] = pd.to_datetime(self.df['Date'])
		self.df.set_index('Date', inplace=True)
		self.df = self.df.apply(pd.to_numeric, errors='coerce')
		if True:#True for weekly observations
			weekly_df = self.df.resample('W').sum()
			self.df = weekly_df.reset_index()

		
		self.idx0 = self.get_index('OSEBX', t0)
		self.idx1 = self.get_index('OSEBX', t1)
		self.p0 = self.get_price(t0)
		self.p1 = self.get_price(t1)


	def count_period(self, t_1, t0):
		self.crsr.execute(f"""
			SELECT DISTINCT COUNT(*) FROM [OSE].[dbo].[equity]
			WHERE [ISIN] = '{self.isin}'  AND [Date] BETWEEN '{t_1}' and '{t0}'
			""")
		n0 = np.array(self.crsr.fetchall())[0][0]
		return n0

	def regress(self, indeps):
		df = self.df
		df_x = df[indeps]
		x = np.array(sm.add_constant(df_x))
		y = np.array(df[['rx']])
		try:
			model = sm.OLS(y, x)
			return model.fit(), df
		except:
			pass

		nacount = df_x.isna().sum()
		deldf = nacount[nacount>0.5*len(df_x)]
		if len(deldf):
			for k in deldf:
				df_x.pop(k)
		else:
			df = df[indeps + ['rx']]
			df = df.dropna()
			df_x = df[indeps]
			y = np.array(df[['rx']])
		x = np.array(sm.add_constant(df_x))
		model = sm.OLS(y, x)
		return model.fit(), df

	def filter(self, res):
		for i, r in enumerate(res):
			if isnummeric(r):
				if np.isnan(r):
					#removing nans
					res[i] = None



	def get_index(self, symbol, date):
		for day in DAYS:
			sqlstr = f"""SELECT distinct [Date],[Last]
						FROM [OSE].[dbo].[equityindex]
						WHERE [Symbol]='{symbol}'  AND  [Date] = '{date+timedelta(day)}'"""
			r = db.fetch(sqlstr, self.crsr)
			if len(r):
				break

		dt, idx = r[0]
		return idx


	def get_price(self,  date):
		for day in DAYS:#iterating over week to make sure we find a day with observations
			sqlstr = f"""SELECT DISTINCT [Date],[ISIN],[AdjustedPrice]
						FROM [OSE].[dbo].[equity]
						WHERE [ISIN]='{self.isin}'  AND  [Date] = '{date+timedelta(day)}'"""
			r = db.fetch(sqlstr, self.crsr)
			if len(r):
				break
		if len(r) == 0:
			return None
		dt, isin_, p = r[0]
		return p

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











#analyze_dir(r"C:\Users\esi000\OneDrive - UiT Office 365\Documents\Forskning\gpt_automation\Årsrapporter")
analyze_dir(r'Z:\OSE\accountingdata\Årsrapporter\2010-2014')
#parseonly(r'Z:\OSE\accountingdata\Årsrapporter\2010-2014')