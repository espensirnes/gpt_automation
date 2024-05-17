#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pymssql 
import numpy as np
import db_create
import connect



TBL = 'gpt_ann_rep'
COLS = ['ISIN', 'ISIN_db', 'Name', 
		'pval_alpha_1', 'pval_beta_1' , 'alpha_1', 'beta_1' , 't_alpha_1', 't_beta_1',
		'pval_alpha_2', 'pval_beta_2' , 'alpha_2', 'beta_2' , 't_alpha_2', 't_beta_2',
		'Answer', 'Explanation']


def add_to_db(res, conn, crsr):	
	if not table_exist(connect.DBNAME,TBL,crsr ):
		create_table(TBL, conn, crsr, connect.DBNAME, droptable=True)
	
	if isin_exists(crsr, res[0]):
		return 
	
	n = len(COLS)
	cols = '['+'], ['.join(COLS)+']'
	sstr = ','.join(['%s']*n)
	sqlstr = (f"INSERT INTO [research].[dbo].[{TBL}] ({cols})  VALUES ({sstr})")
	execute(sqlstr, conn, crsr, res)	


def table_exist(db,table,crsr):
	SQLExpr="""SELECT Distinct TABLE_NAME 
                FROM %s.information_schema.TABLES
                where TABLE_NAME='%s'""" %(db,table)
	crsr.execute(SQLExpr)
	r=crsr.fetchall()
	return len(r)==1

def isin_exists(crsr, isin):
	crsr.execute("SELECT [ISIN] FROM [research].[dbo].[gpt_ann_rep]"
			  	F"WHERE [ISIN] = {isin}")
	r=crsr.fetchall()
	return len(r)>0

def fetch(sqlstr,crsr):
	crsr.execute(sqlstr)
	r=crsr.fetchall()
	return r

def execute(sqlstr,conn,crsr, values = None):
	if values == None:
		crsr.execute(sqlstr)
	else:
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


	