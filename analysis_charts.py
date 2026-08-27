
import connect
import db
import pandas as pd
import matplotlib.pyplot as plt


def main():
	df = get_df()

	# Plotting
	plt.figure(figsize=(10, 6))
	plt.bar(df['Year'], df['PercentageIncrease'])
	plt.xlabel('Year')
	plt.ylabel('Percentage Increase (%)')
	plt.grid(True)

	# Adding the percentage values on the plot
	for i in range(len(df)):
		plt.text(df['Year'][i], df['PercentageIncrease'][i] + 0.1, f"{df['PercentageIncrease'][i]:.1f}%", ha='center')

	#plt.show()
	plt.savefig('output/returns.png')




def get_df():
	conn, crsr = connect.connect()

	data = db.fetch(sqlstr1, crsr)
	df = pd.DataFrame(data, columns=[desc[0] for desc in crsr.description])

	return df


sqlstr1 = """
WITH MinDateForYear AS (
    SELECT
        YEAR([Date]) AS Year,
        MIN([Date]) AS ClosestJune1Date
    FROM
        [euronext_ose].[dbo].[indicies]
    WHERE
        [Date] >= DATEFROMPARTS(YEAR([Date]), 6, 1) AND [Date] < DATEFROMPARTS(YEAR([Date]), 7, 1)
    GROUP BY
        YEAR([Date])
), June1Values AS (
    SELECT
        YEAR(d.[Date]) AS Year,
        d.[Date],
        d.[OSEBXLinked]
    FROM
        [euronext_ose].[dbo].[indicies] d
    INNER JOIN
        MinDateForYear m ON d.[Date] = m.ClosestJune1Date
)
SELECT 
    j1.Year,
    j1.[Date] AS StartDate,
    j1.[OSEBXLinked] AS StartValue,
    j2.[Date] AS EndDate,
    j2.[OSEBXLinked] AS EndValue,
    ((j2.[OSEBXLinked] - j1.[OSEBXLinked]) / j1.[OSEBXLinked]) * 100 AS PercentageIncrease
FROM 
    June1Values j1
INNER JOIN 
    June1Values j2
    ON j1.Year = j2.Year - 1
ORDER BY 
    j1.Year;
"""


main()