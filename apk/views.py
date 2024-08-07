 

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from jira import JIRA
import json
import logging
from django.shortcuts import render
import pandas as pd
from dotenv import load_dotenv
import os

import re

load_dotenv()
jira_server = os.getenv('JIRA_SERVER')
jira_user = os.getenv('JIRA_USER')
jira_token = os.getenv('JIRA_TOKEN')

# client JIRA
jira = JIRA(server=jira_server, basic_auth=(jira_user, jira_token))
current_week_file_path = r'C:\Users\chamsa\Desktop\IPFahren\apk\test.xlsx'

logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)






 



@csrf_exempt
@api_view(['POST'])
def create_jira_ticket(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    summary = data.get('summary')
    description = data.get('description')
    table_data = data.get('table_data', [])

    if not summary:
        return JsonResponse({"error": "Summary is required"}, status=400)

    try:
        if table_data:
            headers = [
                'Test case name',
                'Test case verdict',
                'Domainexpert of requirement',
                'artifactory_upload_paths',
                'Used TBC',
                'Report-ID (ATX-ID)',
                'hw_sample'
            ]

           
            table_header = "|| " + " || ".join(headers) + " ||"
            table_rows = "\n".join(
                "| " + " | ".join(str(ticket.get(header, "")) for header in headers) + " |"
                for ticket in table_data
            )

            # Add the table to the description
            description += f"\n\n{table_header}\n{table_rows}"

    
        issue_dict = {
            'project': {'key': 'IP'},
            'summary': summary,
            'description': description,
            'issuetype': {'id': '10005'}
        }

        new_issue = jira.create_issue(fields=issue_dict)
        return JsonResponse({"message": "Ticket created successfully", "key": new_issue.key}, status=200)
    except Exception as e:
        logger.error(f"Error creating Jira ticket: {e}")
        return JsonResponse({"error": str(e)}, status=500)



 


 
 

@csrf_exempt
@api_view(['POST'])
def update_jira_ticket22_v0(request):
    excel_file_path = r'C:\Users\chamsa\Desktop\IPFahren\apk\test.xlsx'
    
    try:
        df = pd.read_excel(excel_file_path, header=1)  # Adjust header row if needed
    except FileNotFoundError:
        return JsonResponse({"error": "Excel file not found"}, status=400)
    
    # Specify the required columns
    required_columns = [
        'Test case name',
        'Test case verdict'
    ]

    # Ensure the required columns are present
    for col in required_columns:
        if col not in df.columns:
            return JsonResponse({"error": f"Excel file is missing required column: {col}"}, status=400)
    
  
    def determine_final_verdict(group):
        if any(group['Test case verdict'].str.lower() == 'failed'):
            return 'failed'
        if any(group['Test case verdict'].str.lower() == 'error'):
            return 'error'
        if any(group['Test case verdict'].str.lower() == 'none'):
            return 'none'
        return 'passed'
    
  
    grouped = df.groupby('Test case name').apply(lambda group: pd.Series({
        'Test case verdict': determine_final_verdict(group),
    })).reset_index()

 
    def create_table(table_data):
        headers = [
            'Test case name',
            'Test case verdict',
            'Domainexpert of requirement',
            'artifactory_upload_paths',
            'Used TBC',
            'Report-ID (ATX-ID)',
            'hw_sample'
        ]

       
        table_header = "|| " + " || ".join(f"*{header}*" for header in headers) + " ||"
        table_separator = "|| " + " || ".join(['' * len(header) for header in headers]) + " ||"

        table_rows = "\n".join(
            "|| " + " || ".join(
                f"{str(ticket.get(header, ''))} {'✅' if header == 'Test case verdict' and ticket.get(header, '').lower() == 'passed' else '❌' if header == 'Test case verdict' and ticket.get(header, '').lower() in ['error', 'failed'] else '⏹' if header == 'Test case verdict' and ticket.get(header, '').lower() == 'none' else ''}"
                for header in headers
            ) + " ||"
            for _, ticket in table_data.iterrows()
        )

     
        return f"{table_header}\n{table_separator}\n{table_rows}"

  
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    issue_key = data.get('issue_key')
    new_summary = data.get('summary')
    new_description = data.get('description')
    table_data = grouped 

    if not issue_key:
        return JsonResponse({"error": "Issue key is required"}, status=400)

    try:
        issue = jira.issue(issue_key)
        fields_to_update = {}

        if new_summary:
            fields_to_update['summary'] = new_summary
        if new_description or table_data:
            description = new_description if new_description else ""
            if table_data is not None:
              
                description += f"\n\n{create_table(table_data)}"
            
            fields_to_update['description'] = description

        if fields_to_update:
            issue.update(fields=fields_to_update)
            return JsonResponse({"message": "Ticket updated successfully"}, status=200)
        else:
            return JsonResponse({"error": "No fields to update"}, status=400)
    except Exception as e:
        logger.error(f"Error updating Jira ticket: {e}")
        return JsonResponse({"error": str(e)}, status=500)






 



def read_excel_file(path):
    try:
        df = pd.read_excel(path, header=1)
        return df
    except FileNotFoundError:
        logger.error("Excel file not found")
        raise



def clean_data(df):
    """Cleans the DataFrame."""
    df['Domainexpertofrequirement'] = df['Domainexpertofrequirement'].fillna('Unknown')
    df['Used TBC'] = df['Used TBC'].astype(str).fillna('')
    df = df[df['Domainexpertofrequirement'] != 'Unknown']
    return df



def validate_columns(df, required_columns):
    for col in required_columns:
        if col not in df.columns:
            logger.error(f"Excel file is missing required column: {col}")
            raise ValueError(f"Excel file is missing required column: {col}")
 

def create_table(table_data):
    """Creates a formatted table from the given DataFrame."""
    headers = ['TS', 'TCs', 'FAR', 'HVM', 'DAF', 'Comment']
    table_header = "|| " + " || ".join(f"*{header}*" for header in headers) + " ||"
    table_rows = "\n".join(
        "| " + " | ".join(
            f"{ticket.get(header, '')}"  # Use .get() to avoid KeyError if header is missing
            for header in headers
        ) + " |"
        for ticket in table_data
    )
    return f"{table_header}\n{table_rows}"


def create_hardware_table():
    HW = ['FAR', 'HVM', 'DAF']
    hw_table = pd.DataFrame({
        'HW': HW,
        'SAMPLE': ''
    })

    headers = ['HW', 'SAMPLE']
    table_header = "|| " + " || ".join(f"*{header}*" for header in headers) + " ||"
    table_rows = "\n".join(
        "| " + " | ".join(f"{row[header]}" for header in headers) + " |"
        for _, row in hw_table.iterrows()
    )
    return f"{table_header}\n{table_rows}"

def clean_json_string(json_string):
    """Clean and format the JSON string to extract the first object."""
  
    start_idx = json_string.find('{')
    
   
    end_idx = find_matching_bracket(json_string, start_idx)
    
   
    first_object = json_string[start_idx:end_idx+1]
    
    return first_object

def find_matching_bracket(string, start_idx):
    """Find the index of the closing curly brace that matches the opening curly brace at the given index."""
    count = 1
    for i in range(start_idx + 1, len(string)):
        if string[i] == '{':
            count += 1
        elif string[i] == '}':
            count -= 1
            if count == 0:
                return i
    return -1

def create_software_table(df):
    controllers = ['FAR', 'HVM', 'DAF']
    sw_table = pd.DataFrame({
        'Controller': controllers,
        'SW': '',  
        'Link': ['Not executed'] * len(controllers) 
    })
    
    
    df['Used TBC'] = df['Used TBC'].fillna('')
    
    for idx, controller in enumerate(controllers):
        filtered_df = df[df['Used TBC'].str.contains(controller, na=False)]
        if not filtered_df.empty:
            controller_fn = filtered_df['artifactory_upload_paths'].iloc[0]
            corrected_json_str = clean_json_string(controller_fn)
            corrected_json_str = re.sub(r"(?<!\\)'", '"', corrected_json_str).strip()
            data_dict = json.loads(corrected_json_str)
            link_fn = data_dict['path']
            sw_table.at[idx, 'Link'] = link_fn

    headers = ['Controller', 'SW', 'Link']
    table_header = "|| " + " || ".join(f"*{header}*" for header in headers) + " ||"
    table_rows = "\n".join(
        "| " + " | ".join(f"{row[header]}" for header in headers) + " |"
        for _, row in sw_table.iterrows()
    )
    return f"{table_header}\n{table_rows}"


 

def categorize_results(df):
    """Categorizes results into HVM, DAF, and FAR lists."""
    hvm_list = []
    daf_list = []
    far_list = []
    result = {}
    i = 0

    # Find the index of the first occurrence of IPF_Ctr_Kl30
    ipf_index = df[df['Test case name'].str.contains('IPF_Ctr_Kl30', na=False)].index.min()

    # If IPF_Ctr_Kl30 is not found, set ipf_index to None
    if pd.isna(ipf_index):
        ipf_index = None

    # Filter rows to include only those starting from the first occurrence of IPF_Ctr_Kl30
    if ipf_index is not None:
        df = df.loc[ipf_index:]
    
    for _, row in df.iterrows():
        test_case_name = row["Test case name"]
        used_tbc = row["Used TBC"]
        test_case_verdict = row["Test case verdict"]
        domain_expert = row["Domainexpertofrequirement"]
        used_ID = row["Report-ID (ATX-ID)"]

        if "IPF_Ctr_Kl30" in test_case_name:
            i += 1
            result[str(i)] = [[test_case_name, test_case_verdict]]
        else:
            if str(i) in result:
                result[str(domain_expert).lower()] = result.pop(str(i))

            if str(domain_expert).lower() in result:
                result[str(domain_expert).lower()].append([test_case_name, test_case_verdict])
            else:
                result[str(domain_expert).lower()] = [[test_case_name, test_case_verdict]]

            # Store additional information
            temp_dict = {
                'test_case_name': test_case_name,
                'test_case_verdict': test_case_verdict,
                'used_ID': used_ID,
                'Domainexpertofrequirement': domain_expert
            }
          
            
            if "HVM" in used_tbc:
                hvm_list.append(temp_dict)
            elif "DAF" in used_tbc:
                daf_list.append(temp_dict)
            elif "FAR" in used_tbc:
                far_list.append(temp_dict)

    return hvm_list, daf_list, far_list, result

def determine_final_verdict(verdicts):
    """Determines the final verdict based on the list of verdicts."""
    if 'ERROR' in verdicts:
        return 'error❌'
    if 'FAILED' in verdicts:
        return 'failed❌'
    if 'PASSED' in verdicts:
        return 'passed✅'
    if 'NONE' in verdicts:
        return 'none'
    return 'unknown'

def get_final_results(hvm_list, daf_list, far_list):
    """Determines the final verdict for each test case name based on categorized lists."""
    # Collect all test case names
    all_test_case_names = set(
        item['test_case_name'] for item in hvm_list + daf_list + far_list
    )
    
    results = []
    for test_case_name in all_test_case_names:
        verdicts = {'HVM': [], 'DAF': [], 'FAR': []}
        domain_experts = set()

        
        for item in hvm_list:
            if item['test_case_name'] == test_case_name:
                verdicts['HVM'].append(item['test_case_verdict'])
                domain_experts.add(item['Domainexpertofrequirement'])
        
        for item in daf_list:
            if item['test_case_name'] == test_case_name:
                verdicts['DAF'].append(item['test_case_verdict'])
                domain_experts.add(item['Domainexpertofrequirement'])
        
        for item in far_list:
            if item['test_case_name'] == test_case_name:
                verdicts['FAR'].append(item['test_case_verdict'])
                domain_experts.add(item['Domainexpertofrequirement'])
        
      
        final_verdicts = {
            'HVM': determine_final_verdict(verdicts['HVM']),
            'DAF': determine_final_verdict(verdicts['DAF']),
            'FAR': determine_final_verdict(verdicts['FAR']),
        }
        
        
        if 'none' not in final_verdicts.values():
            # Append result for each domain expert
            for domain_expert in domain_experts:
                results.append({
                    'TS': domain_expert.title(),
                    'TCs': test_case_name,
                    'HVM': final_verdicts['HVM'],
                    'DAF': final_verdicts['DAF'],
                    'FAR': final_verdicts['FAR'],
                    'Comment': ' '
                })
    results_sorted = sorted(results, key=lambda x: (x['TS'], x['TCs']))
    return results_sorted

 
 

def get_existing_issue_data(issue_key):
    try:
        issue = jira.issue(issue_key)
        return {
            "summary": issue.fields.summary,
            "description": issue.fields.description
        }
    except Exception as e:
        logger.error(f"Error fetching Jira issue: {e}")
        raise

def compare_and_display_changes(existing_data, new_summary, new_description, table_data, sw_table):
    changes = []
    if new_summary and new_summary != existing_data["summary"]:
        changes.append(f"Summary changed from '{existing_data['summary']}' to '{new_summary}'")
    
    existing_description = existing_data["description"]

    updated_description = new_description
    updated_description += f"\n\n *Hardware :* \n {create_hardware_table()}"
    updated_description += f"\n\n *Software :* \n {create_software_table(sw_table)}"
    updated_description += f"\n\n *Intake Result :*\n {create_table(table_data)}"
    
    if updated_description != existing_description:
        changes.append("Description changed")

    for change in changes:
        print(change)
    
    if not changes:
        print("No changes detected")

    return changes


def update_if_changed(issue_key, new_summary, new_description, table_data, sw_table):
    existing_data = get_existing_issue_data(issue_key)
    changes = compare_and_display_changes(existing_data, new_summary, new_description, table_data, sw_table)
    
    if changes:
        update_jira_ticket(issue_key, new_summary, new_description, table_data, sw_table)

def update_jira_ticket(issue_key, new_summary, new_description, table_data, sw_table):
    if not issue_key:
        logger.error("Issue key is required")
        raise ValueError("Issue key is required")

    try:
        issue = jira.issue(issue_key)
    except Exception as e:
        logger.error(f"Issue with key '{issue_key}' not found: {e}")
        raise

    updated_description = new_description
    updated_description += f"\n\n *Hardware :* \n {create_hardware_table()}"
    updated_description += f"\n\n *Software :* \n {create_software_table(sw_table)}"
    updated_description += f"\n\n *Intake Result :*\n {create_table(table_data)}"

    fields_to_update = {}
    if new_summary:
        fields_to_update['summary'] = new_summary
    fields_to_update['description'] = updated_description

    try:
        issue.update(fields=fields_to_update)
        print("Ticket updated successfully")
    except Exception as e:
        logger.error(f"Error updating Jira ticket: {e}")
        raise

    



@csrf_exempt
@api_view(['GET', 'POST'])
def update_jira_ticket22_with_summ(request):
    if request.method == 'POST':
    
        # Assuming you have logic to extract data from the request
        # Example:
        try:

            current_df = read_excel_file(current_week_file_path)
            required_columns = [
                'Test case name',
                'Test case verdict',
                'Domainexpertofrequirement',
                'artifactory_upload_paths',
                'Used TBC',
                'Report-ID (ATX-ID)',
                'hw_sample'
            ]

            validate_columns(current_df, required_columns)
            current_df = clean_data(current_df)
            hvm_list, daf_list, far_list, result = categorize_results(current_df)
            final_results = get_final_results(hvm_list, daf_list, far_list)
            final_df = pd.DataFrame(final_results).drop_duplicates()
            final_df_sorted = final_df.sort_values(by='TS', ascending=True)
            table_data = final_df_sorted.to_dict(orient='records')

            # issue_key = "IP-9"
            # new_summary = "Updated test"
            # new_description = "Updated Description."

            data = json.loads(request.body)
            issue_key = data.get('issue_key', '')
            new_summary = data.get('summary', '')
            new_description = data.get('description', '')

            # Assurez-vous que les variables ne sont pas None
            if issue_key is None:
                issue_key = ''
            if new_summary is None:
                new_summary = ''
            if new_description is None:
                new_description = ''

            df = read_excel_file(current_week_file_path)

            update_if_changed(issue_key, new_summary, new_description, table_data, df)
            message = f"Updating JIRA issue {issue_key} with summary '{new_summary}' and description '{new_description}'"
            print('aaaaaaaaaaaaaaaa',message)
  

            return JsonResponse({
                
                "table_data": create_table(table_data)
            })
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"error": "An unexpected error occurred."}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)























@api_view(['GET'])
def list_all_issues(request):
    try:
       
        jql_query = 'project = IP ORDER BY created DESC'   
        issues = jira.search_issues(jql_query, maxResults=1000)  
        issues_list = []
        for issue in issues:
            issues_list.append({
                'key': issue.key,
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                'created': issue.fields.created,
                'updated': issue.fields.updated,
            })

        return JsonResponse({'issues': issues_list}, status=200)
    
    except Exception as e:
        logger.error(f"Error fetching issues: {e}")
        return JsonResponse({"error": "Error fetching issues"}, status=500)
    



 

def issues_list_view(request):
    return render(request, 'issues_list.html')


def index(request):
    
    return render(request, 'index.html')
  

 
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import pandas as pd

@csrf_exempt
def display_table(request):
    if request.method == 'POST' and request.FILES.get('file_excel'):
        excel_file = request.FILES['file_excel']
        
        try:
            df = pd.read_excel(excel_file, header=1)  
        except Exception as e:
            return JsonResponse({"error": f"Error reading Excel file: {str(e)}"}, status=400)
        
        required_columns = [
            'Test case name',
            'Test case verdict',
            'Domainexpertofrequirement',
            'artifactory_upload_paths',
            'Used TBC',
            'Report-ID (ATX-ID)',
            'hw_sample'
        ]

        for col in required_columns:
            if col not in df.columns:
                return JsonResponse({"error": f"Excel file is missing required column: {col}"}, status=400)
        
        df['Domainexpertofrequirement'] = df['Domainexpertofrequirement'].fillna('Unknown')
        df['Used TBC'] = df['Used TBC'].astype(str).fillna('')
        df = df[df['Domainexpertofrequirement'] != 'Unknown']
        
        def categorize_results(df):
            """Categorizes results into HVM, DAF, and FAR lists."""
            hvm_list = []
            daf_list = []
            far_list = []
            result = {}
            i = 0

            # Find the index of the first occurrence of IPF_Ctr_Kl30
            ipf_index = df[df['Test case name'].str.contains('IPF_Ctr_Kl30', na=False)].index.min()

            # If IPF_Ctr_Kl30 is not found, set ipf_index to None
            if pd.isna(ipf_index):
                ipf_index = None

            # Filter rows to include only those starting from the first occurrence of IPF_Ctr_Kl30
            if ipf_index is not None:
                df = df.loc[ipf_index:]
            
            for _, row in df.iterrows():
                test_case_name = row["Test case name"]
                used_tbc = row["Used TBC"]
                test_case_verdict = row["Test case verdict"]
                domain_expert = row["Domainexpertofrequirement"]
                used_ID = row["Report-ID (ATX-ID)"]

                if "IPF_Ctr_Kl30" in test_case_name:
                    i += 1
                    result[str(i)] = [[test_case_name, test_case_verdict]]
                else:
                    if str(i) in result:
                        result[str(domain_expert).lower()] = result.pop(str(i))

                    if str(domain_expert).lower() in result:
                        result[str(domain_expert).lower()].append([test_case_name, test_case_verdict])
                    else:
                        result[str(domain_expert).lower()] = [[test_case_name, test_case_verdict]]

                    # Store additional information
                    temp_dict = {
                        'test_case_name': test_case_name,
                        'test_case_verdict': test_case_verdict,
                        'used_ID': used_ID,
                        'Domainexpertofrequirement': domain_expert
                    }
                    
                    if "HVM" in used_tbc:
                        hvm_list.append(temp_dict)
                    elif "DAF" in used_tbc:
                        daf_list.append(temp_dict)
                    elif "FAR" in used_tbc:
                        far_list.append(temp_dict)

            return hvm_list, daf_list, far_list, result

        def determine_final_verdict(verdicts):
            """Determines the final verdict based on the list of verdicts."""
            if 'ERROR' in verdicts:
                return 'error❌'
            if 'FAILED' in verdicts:
                return 'failed❌'
            if 'PASSED' in verdicts:
                return 'passed✅'
            if 'NONE' in verdicts:
                return 'none'
            return 'unknown'
        
        def get_final_results(hvm_list, daf_list, far_list):
            """Determines the final verdict for each test case name based on categorized lists."""
            # Collect all test case names
            all_test_case_names = set(
                item['test_case_name'] for item in hvm_list + daf_list + far_list
            )
            
            results = []
            for test_case_name in all_test_case_names:
                verdicts = {'HVM': [], 'DAF': [], 'FAR': []}
                domain_experts = set()

                for item in hvm_list:
                    if item['test_case_name'] == test_case_name:
                        verdicts['HVM'].append(item['test_case_verdict'])
                        domain_experts.add(item['Domainexpertofrequirement'])
                
                for item in daf_list:
                    if item['test_case_name'] == test_case_name:
                        verdicts['DAF'].append(item['test_case_verdict'])
                        domain_experts.add(item['Domainexpertofrequirement'])
                
                for item in far_list:
                    if item['test_case_name'] == test_case_name:
                        verdicts['FAR'].append(item['test_case_verdict'])
                        domain_experts.add(item['Domainexpertofrequirement'])
                
                final_verdicts = {
                    'HVM': determine_final_verdict(verdicts['HVM']),
                    'DAF': determine_final_verdict(verdicts['DAF']),
                    'FAR': determine_final_verdict(verdicts['FAR']),
                }
                
                if 'none' not in final_verdicts.values():
                    # Append result for each domain expert
                    for domain_expert in domain_experts:
                        results.append({
                            'TS': domain_expert.title(),
                            'TCs': test_case_name,
                            'HVM': final_verdicts['HVM'],
                            'DAF': final_verdicts['DAF'],
                            'FAR': final_verdicts['FAR'],
                            'Comment': ' '
                        })
            results_sorted = sorted(results, key=lambda x: (x['TS'], x['TCs']))
            return results_sorted
        
        hvm_list, daf_list, far_list, result = categorize_results(df)
        final_results = get_final_results(hvm_list, daf_list, far_list)
        from collections import defaultdict
        
        
        def count_verdicts(final_results):
            counts = {
                'HVM': defaultdict(int),
                'DAF': defaultdict(int),
                'FAR': defaultdict(int)
            }
            
            for result in final_results:
                for category in ['HVM', 'DAF', 'FAR']:
                    verdict = result[category]
                    counts[category][verdict] += 1

            return counts

        verdict_counts = count_verdicts(final_results)

        combined_counts = {category: dict(verdicts) for category, verdicts in verdict_counts.items()}
        
        # Calculate counts
        counts = { 'passed✅': 0, 'failed❌': 0, 'error❌': 0, 'none': 0, 'unknown': 0 }
        for item in final_results:
            counts[item['HVM']] += 1
            counts[item['DAF']] += 1
            counts[item['FAR']] += 1

   

        totals = {
            'passed': counts.get('passed✅', 0),
            'failed': counts.get('failed❌', 0),
            'error': counts.get('error❌', 0),
            'none': counts.get('none', 0),
 
        }

        return JsonResponse({'table_data': final_results, 'totals': totals, 'verdict_counts': combined_counts})

    return JsonResponse({"error": "Invalid request method"}, status=400)



