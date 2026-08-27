#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pymssql 
import numpy as np
import db_create
import connect




COLS = ['ISIN','ISIN_db', 'Year', 'Name', 'intcode', 'sid',
		'mean_ret_company1','mean_ret_index1', 'n01', 'n1',

		'idx01', 'idx11', 'p01', 'p11',

		'pval_alpha_1', 'pval_beta_1' , 'alpha_1', 'beta_1' , 't_alpha_1', 't_beta_1',
		'dw1', 'rsq_adj1', 'cond_no1', 
		'pval_alpha_1M', 'pval_beta_1M' , 'alpha_1M', 'beta_1M' , 't_alpha_1M', 't_beta_1M',
		'dw1M', 'rsq_adj1M', 'cond_no1M', 

		'mean_ret_company2','mean_ret_index2', 'n02', 'n2',

		'idx02', 'idx12', 'p02', 'p12',

		'pval_alpha_2', 'pval_beta_2' , 'alpha_2', 'beta_2' , 't_alpha_2', 't_beta_2',
		'dw2', 'rsq_adj2', 'cond_no2', 
		'pval_alpha_2M', 'pval_beta_2M' , 'alpha_2M', 'beta_2M' , 't_alpha_2M', 't_beta_2M',
		'dw2M', 'rsq_adj2M', 'cond_no2M', 

		'Answer', 'Explanation']


def add_to_db(res, conn, crsr, tbl):	
	if not table_exist(connect.DBNAME,tbl,crsr ):
		create_table(tbl, conn, crsr, connect.DBNAME, droptable=True)
	
	if isin_exists(crsr, res[0], res[2]):
		return 
	
	n = len(COLS)
	cols = '['+'], ['.join(COLS)+']'
	sstr = ','.join(['%s']*n)
	sqlstr = (f"INSERT INTO [research].[dbo].[{tbl}] ({cols})  VALUES ({sstr})")
	execute(sqlstr, conn, crsr, res)	


def table_exist(db,table,crsr):
	SQLExpr="""SELECT Distinct TABLE_NAME 
                FROM %s.information_schema.TABLES
                where TABLE_NAME='%s'""" %(db,table)
	crsr.execute(SQLExpr)
	r=crsr.fetchall()
	return len(r)==1

def isin_exists(crsr, isin, year):
	crsr.execute("SELECT [ISIN] FROM [research].[dbo].[gpt_ann_rep] "
			  	F"WHERE [ISIN] = '{isin}' AND [Year]={year}")
	r=crsr.fetchall()
	return len(r)>0

def get_isin_year_in_db(crsr, tbl):
	crsr.execute(f"SELECT [ISIN],[Year] FROM [research].[dbo].[{tbl}]")
	r=crsr.fetchall()
	a = [f"{isin}_{year}" for isin, year in r]
	return a

def fetch(sqlstr,crsr):
	crsr.execute(sqlstr)
	r=crsr.fetchall()
	return r

def execute(sqlstr,conn,crsr, values = None):
	if values == None:
		crsr.execute(sqlstr)
	else:
		values = [int(x) if isinstance(x, np.integer) else x for x in values]
		crsr.execute(sqlstr, values)
	conn.commit()


def create_table(tbl, conn, crsr, db = None,droptable=False):
	"""crating a generic table"""
	if droptable:
		drop_table(tbl, conn, crsr,db)
	r = fetch(f"SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{tbl}' ", crsr)
	if len(r):
		return
	
	SQLStr=vars(db_create)[tbl]
	
	crsr.execute(SQLStr)
	conn.commit()
	tblProps=[get_col_names(crsr,tbl,db)]
	add_primary_key(crsr,conn,tbl)	
	return tblProps[0]


def get_col_names(crsr,tblname,db=None):
	SQLstr="EXEC sp_columns @table_name = '%s';" %(tblname)
	crsr.execute(SQLstr)
	r=crsr.fetchall()
	if len(r)==0 and not db is None:
		conn,crsr=connect.connect(db)
		crsr.execute(SQLstr)
		r=crsr.fetchall()	
		conn.close()
	r=np.array(r).T

	return r[3:8]


def drop_table(table,conn,crsr,db=None):
	"Deletes a table"
	try:
		if db is None:
			crsr.execute("DROP TABLE [%s];" %(table))
		else:
			crsr.execute("DROP TABLE [%s].[dbo].[%s];" %(db,table))
		conn.commit()
	except:
		pass



def add_primary_key(crsr,conn,tbl,db=None,createID=False):
	if createID:
		try:
			if db is None:
				crsr.execute("""ALTER TABLE [%s] ADD ID INT IDENTITY""" %(db,tbl))
			else:
				crsr.execute("""ALTER TABLE [%s].[dbo].[%s] ADD ID INT IDENTITY""" %(tbl))
			conn.commit()
		except:
			pass
	try:
		if db is None:
			crsr.execute("""ALTER TABLE [%s] ADD CONSTRAINT
				PK_%s PRIMARY KEY CLUSTERED (ID)""" %(tbl,tbl))
		else:
			crsr.execute("""ALTER TABLE [%s].[dbo].[%s] ADD CONSTRAINT
					    PK_%s PRIMARY KEY CLUSTERED (ID)""" %(db,tbl,tbl))			
		conn.commit()	
	except:
		pass


	