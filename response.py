import prompts
import os
import re


def get(sections, client, name, year, fname, isin):


		
	summary = summarize(sections, client, name, year, fname, isin)
	print(f'Final evaluation for {name}({year}) - {isin} ... ')
	answ, expl = conclude(summary, client, fname)
	print("... done")

	return answ, expl 

def summarize(sections, client, name, year, fname, isin):

	if  os.path.exists(f'{fname}{'_summary.txt'}'):
		with open(f'{fname}{'_summary.txt'}', 'r', encoding='utf-8') as f:
			summary = f.read()
			return summary
		
	# Call the model and print the response
	n = len(sections)

	full_response = ''

	for i in range(n):
		print(f'Evaluating section {i} for {name}({year}) - {isin}')
		res, heading = get_summary(sections, i, client)
		if not res is None:
			full_response += f"{heading}\n\n{res}\n\n"

	with open(f'{fname}{'_summary.txt'}', 'w', encoding='utf-8') as f:
		f.write(full_response)
	return full_response

def get_summary(sections, i, client):

	
	s = sections[i]
	if s == '':
		return None, None

	heading = f'# Section {i}:'
	if "<h1>" in s:
		heading = f'# Section {i}:' + s[s.index("<h1>")+3:s.index("</h1>")-1]
	completion = client.chat.completions.create(
		model="gpt-4o",
		messages= [
			{"role": "system", "content": prompts.summarize},
			{"role": "user", "content": f"Here is section {i+1}:\n{s}"}], 
		temperature = 0
		)

	response =completion.choices[0].message.content



	return response, heading

	


def conclude(summary , client, fname):

	if  os.path.exists(f'{fname}{'_conclusion.txt'}'):
		with open(f'{fname}{'_conclusion.txt'}', 'r', encoding='utf-8') as f:
			conclusion = f.read()
			grade, answ = split_response(conclusion)
			return grade, answ
		
	# Call the model and print the response
	
	completion = client.chat.completions.create(
		model="gpt-4o",
		messages=[
			{"role": "system", "content": prompts.conclude},
			{"role": "user", "content": f"Here is the summary of the annual report:\n\n {summary}"},
		], 
		temperature = 0
		)
	resp = completion.choices[0].message.content 
	with open(f'{fname}{'_conclusion.txt'}', 'w', encoding='utf-8') as f:
		f.write(resp)

	grade, answ = split_response(resp)

	return grade, answ 



def split_response(resp):
	if ';' in resp:
		grade, answ = resp.split(';')
		if grade == 'None':
			return None, answ
		return int(grade), answ
	else:
		m = re.search(r'\b\d{1,2}\b', resp[:40])
		if (m is None) and ('None' in resp[:10]):
			return None, resp[5:]
		grade = int(m.group(0))
		answ = resp[resp.index(str(grade))+2:]
	return grade, answ