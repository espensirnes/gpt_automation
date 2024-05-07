import prompts


def get(pdf_tables, pdf_text, client):
	tblresponse = []
	txtresponse = []
	for k in pdf_tables:
		tblresponse.append(get_table(k, pdf_tables[k] , client))
	for k in pdf_tables:
		txtresponse.append(get_text(k, pdf_text[k] , client))

	compiled = get_all('\n'.join(txtresponse), '\n'.join(tblresponse))
	answ, expl = compiled.split(';')
	return answ, expl 

def get_all(text, tables, client):
	# Call the model and print the response
	
	completion = client.chat.completions.create(
		model="gpt-4-turbo",
		messages=[
			{"role": "system", "content": prompts.analyze_all},
			{"role": "user", "content": f"Here are the text summaries:\n{text}"},
			{"role": "user", "content": f"Here are the table summaries:\n{tables}"},
		], 
		temperature = 0
		)

	return completion.choices[0].message.content

def get_table(caption, table , client):
	# Call the model and print the response
	
	completion = client.chat.completions.create(
		model="gpt-3.5-turbo",
		messages=[
			{"role": "system", "content": prompts.analyze_table},
			{"role": "user", "content": f"{caption}\n\n {table}"},
		], 
		temperature = 0
		)

	return completion.choices[0].message.content 

def get_text(heading, text , client):
	# Call the model and print the response
	
	completion = client.chat.completions.create(
		model="gpt-3.5-turbo",
		messages=[
			{"role": "system", "content": prompts.analyze_text},
			{"role": "user", "content": f"{heading}\n\n {text}"},
		], 
		temperature = 0
		)

	return completion.choices[0].message.content 

