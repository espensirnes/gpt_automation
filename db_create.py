

gpt_ann_rep="""CREATE TABLE [research].[dbo].[gpt_ann_rep](

        [ISIN] varchar(30) NULL, 
        [ISIN_db]  varchar(30) NULL, 
		[Year] bigint NULL,
        [Name]  varchar(120) NULL, 
		[intcode]  bigint NULL, 
		[sid]  bigint NULL, 


	[mean_ret_company1] float NULL,
	[mean_ret_index1] float NULL,
	
	[n01] bigint NULL,
	[n1] bigint NULL,
	[idx01] float NULL, 
	[idx11] float NULL, 
	[p01] float NULL, 
	[p11] float NULL,
	[pval_alpha_1] float NULL, 
	[pval_beta_1] float NULL,
	[alpha_1] float NULL, 
	[beta_1] float NULL,
	[t_alpha_1] float NULL, 
	[t_beta_1] float NULL,

	[dw1]  float NULL,
	[rsq_adj1]  float NULL,
	[cond_no1]  float NULL,


	[pval_alpha_1M] float NULL, 
	[pval_beta_1M] float NULL,
	[alpha_1M] float NULL, 
	[beta_1M] float NULL,
	[t_alpha_1M] float NULL, 
	[t_beta_1M] float NULL,

	[dw1M]  float NULL,
	[rsq_adj1M]  float NULL,
	[cond_no1M]  float NULL,

	[mean_ret_company2] float NULL,
	[mean_ret_index2] float NULL,
	
	[n02] bigint NULL,
	[n2] bigint NULL,
	[idx02] float NULL, 
	[idx12] float NULL, 
	[p02] float NULL, 
	[p12] float NULL,
	[pval_alpha_2] float NULL, 
	[pval_beta_2] float NULL, 
	[alpha_2] float NULL, 
	[beta_2] float NULL,
	[t_alpha_2] float NULL, 
	[t_beta_2] float NULL,

	[dw2]  float NULL,
	[rsq_adj2]  float NULL,
	[cond_no2]  float NULL,


	[pval_alpha_2M] float NULL, 
	[pval_beta_2M] float NULL, 
	[alpha_2M] float NULL, 
	[beta_2M] float NULL,
	[t_alpha_2M] float NULL, 
	[t_beta_2M] float NULL,

	[dw2M]  float NULL,
	[rsq_adj2M]  float NULL,
	[cond_no2M]  float NULL,

	[Answer] int NULL, 
	[Explanation] NVARCHAR(MAX)
	
        )"""




