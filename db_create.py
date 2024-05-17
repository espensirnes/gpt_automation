

gpt_ann_rep="""CREATE TABLE [research].[dbo].[gpt_ann_rep](

        [ISIN] varchar(30) NULL, 
        [ISIN_db]  varchar(30) NULL, 
        [Name]  varchar(120) NULL, 
	[pval_alpha_1] float NULL, 
	[pval_beta_1] float NULL,
	[alpha_1] float NULL, 
	[beta_1] float NULL,
	[t_alpha_1] float NULL, 
	[t_beta_1] float NULL,
	[pval_alpha_2] float NULL, 
	[pval_beta_2] float NULL, 
	[alpha_2] float NULL, 
	[beta_2] float NULL,
	[t_alpha_2] float NULL, 
	[t_beta_2] float NULL,
	[Answer] int NULL, 
        [Explanation]  varchar(2000) NULL
        )"""




