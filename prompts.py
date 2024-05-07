




#promt for analyzing all:

analyze_all = """

As a financial analyst evaluating company performance and growth potential, you will be given information in two batches:

* First, you will receive narrative text summaries for each section.
* Second, you will be presented with table summaries for each table.

Your task is to assign a grade from 0 to 10, indicating how well the company is managed and its potential for growth. 
Define each score by specific financial metrics and strategic considerations; for example, a score of 0 suggests poor 
performance and minimal growth potential due to declining revenues and high debt, while a score of 10 signifies excellent 
performance and significant growth potential, evidenced by strong revenue growth and market leadership. Additionally, provide 
a brief summary of your overall impression, focusing on key financial outcomes, strategic initiatives, and market positioning; 
separate this summary from the grade with a semicolon.

Examples of Responses:

Example 1:
7; The company has shown consistent revenue growth over the past few years, with healthy profit margins and a strong balance sheet. 
However, there are concerns regarding its increasing debt levels and the need for strategic diversification to sustain future growth.

Example 2:
3; The company's revenue has declined recently, and its equity is running low. It has ambitious plans for cost-cutting measures and 
restructuring, which might help in revitalizing the business. Yet, the market competition and economic uncertainties pose significant 
challenges to its recovery.


"""

analyze_text = """
As a financial analyst evaluating company performance and growth potential, you will be given a specific section of the report. 
Provide a short summary of the section, and evaluate to what extent it furthers the company's performance and growth potential. 
If the section is of low relevance or there is insufficient information to make an evaluation, respond with "NONE".

If the section appears to be a table or contains mostly tabular data, ignore it and also respond with "NONE".

"""


analyze_table = """
As a financial analyst evaluating company performance and growth potential, you will be provided with a specific table from the report. Provide a short summary of the table, and evaluate how significantly it contributes to the company's performance and growth potential.

Pay close attention to the following details:
- If the headings are years, note any decline or increase in the figures.
- An increase in debt is typically negative.
- An increase in equity and revenue is positive.
- An increase in costs is generally negative, unless accompanied by an increase in profits, which could indicate potential growth.

Also, be vigilant for other relevant information that may impact your evaluation.

If the table lacks relevance or sufficient information for a comprehensive evaluation, respond with "NONE."

"""

#promt for fixing table, assuming there is no missing header row:
fix_table_simple = """
**Your Objectives**:
1. **Reformat the Data**: Organize this data into clearly structured markdown tables, ensuring that each piece of data is correctly aligned under the appropriate column headers.
2. **Address Merged Columns**: Pay particular attention to columns that might have been mistakenly merged due to formatting issues. Separate these into distinct columns as intended.

**Instructions**:
- **Reformat and Align**: Ensure all entries are clearly formatted in the markdown table format. Each table column should be clearly distinguishable with headers and corresponding data aligned properly.
- **Column Separation**: Identify and separate merged columns based on their data type and intended separation. Columns should be logically organized to reflect distinct data fields.

**Example of Raw Input**:
The raw input may appear with merged columns and without clear separation. For example:
|2010 2009|2008\nRevenue|$1,793.7 $1,645.1|$1,555.1\nProfit|$160.9 $123.6|$100.6\n...

**Expected Output Format**:
After processing, the table should be restructured to clearly display data for each year under its own header. The output should look like this:

|          | 2010      | 2009     | 2008     |
|----------|-----------|----------|----------|
| Revenue  | $1,793.7  | $1,645.1 | $1,555.1 |
| Profit   | $160.9    | $123.6   | $100.6   |
...
						  
"""

#promt for fixing table, taking into account a possibly missing header rwo:
fix_table_header = """
**Your Objectives**:
1. **Reformat the Data**: Organize this data into clearly structured markdown tables, ensuring that each piece of data is correctly aligned under the appropriate column headers.
2. **Address Merged Columns**: Pay particular attention to columns that might have been mistakenly merged. Separate these into distinct columns as intended.
3. **Handle Missing Headers**: Use the first line marked as "Possible header row: <possible header row>" as the header if it appears that the header row is missing, unless it clearly does not represent column titles. Integrate this header appropriately into the structured table.

**Instructions**:
- **Reformat and Align**: Reformat and align all entries clearly in the markdown table format.
- **Column Separation**: Separate merged columns based on data type and logical separation.
- **Header Decision**: Use the provided "Possible header row" if no other headers are apparent and it fits the data columns

**Example of Raw Input**:
- **Use "Possible header row"**: 
  "Possible header row:Millons US$ 2010 2009 2008\n\nRevenue|$1,793.7 $1,645.1|$1,555.1\nProfit|$160.9 $123.6|$100.6\n..."
- **Ignore "Possible header row"**: 
  "Possible header row: This table shows the key figures\n\nMillons US$|2010 2009 |2008\nRevenue|$1,793.7 $1,645.1|$1,555.1\nProfit|$160.9 $123.6|$100.6\n..."   

**Expected Output Format**:
  | Millons US$ | 2010      | 2009     | 2008     |
  |-------------|-----------|----------|----------|
  | Revenue     | $1,793.7  | $1,645.1 | $1,555.1 |
  | Profit      | $160.9    | $123.6   | $100.6   |
  ...
		  
"""

#promt for deciding which line should be used as table caption
decide_table_caption = """
**Task Overview**:
You will participate in a session where you will sequentially receive a list of possible captions followed by a table formatted in markdown. 
Your task is to determine which of the provided captions is most appropriate for the table, based on its content.

**Instructions**:
1. **Review the Captions**: Upon receiving the list of captions, examine each to understand their themes and assess which types of data they might best describe.
2. **Analyze the Table**: After receiving the table, carefully review its content, including headings, data points, and any summarizing or distinctive features.
3. **Select the Most Appropriate Caption**: Choose the caption that best aligns with the table’s data and thematic focus. Consider how well each caption encapsulates the information presented.
4. **Reformulate**: If necessary, adjust the wording of the chosen caption to make it more appropriate or caption-like.
5. **Provide Your Selection**: Respond with the chosen caption. If none of the captions are appropriate, respond with "None".

**Expectation for Messages**:
- **First Message**: You will receive a message containing a list of potential captions. Treat these as possible titles for the table.
- **Second Message**: You will then receive the table formatted in markdown. Utilize this data to identify the most fitting caption based on the data's relevance and how well it reflects the contents of the table.

**Expected Response**:
- **Appropriate Caption**: Provide the selected caption that best describes the table, adjusted for context if necessary.
- **If Inappropriate**: If no captions appropriately match the table, simply respond with "None".


"""



#promt for deciding if a table is mainly text:
is_mainly_text = """
**Task Description**: You will be presented with a table where columns are separated by the "|" symbol. Your objective is to analyze the content of each cell in the table to determine the predominant data type.

**Detailed Instructions**:
1. **Counting Text vs. Numeric Cells**: For each cell in the table, classify the content as either 'text' or 'numeric':
   - A 'text' cell contains mostly non-numeric words, phrases, or mixed alphanumeric characters where alphabetic characters dominate.
   - A 'numeric' cell contains purely numbers or monetary amounts (e.g., "123", "2.5", "$100").
2. **Criteria for Decision**:
   - If more than 50% of the cells in the table contain 'text' data, classify the entire table as "TEXT".
   - Otherwise, classify the table as "NUMERIC".

**Response Requirement**:
- After analyzing the table, respond only with "TEXT" if the majority of cells contain text data.
- Respond with only "NUMERIC" if the majority of cells contain numeric data.

**Example of a Table Analysis**:
Given the table:
| Name       | Age | Salary   |
| John Smith | 25  | $50,000  |
| Jane Doe   | 29  | $55,000  |

- Evaluate each cell:
  - "John Smith", "Jane Doe" are text.
  - "25", "29", "$50,000", "$55,000" are numeric.
- Numeric cells = 4, Text cells = 2.
- Since numeric cells represent the majority, the response would be "NUMERIC".
"""