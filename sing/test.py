

# TT_PLAYBOOK_RUN_ID
# Report-ID (ATX-ID)


import pandas as pd
from jira import JIRA
import logging
from dotenv import load_dotenv
import os
import json
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pdfkit
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

 

 
load_dotenv()
jira_server = os.getenv('JIRA_SERVER')
jira_user = os.getenv('JIRA_USER')
jira_token = os.getenv('JIRA_TOKEN')

 
# Email configuration from environment variables
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT')

jira = JIRA(server=jira_server, basic_auth=(jira_user, jira_token))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

  

# Excel file paths
current_week_file_path =  r'C:\Users\chamsa\Desktop\IPFahren\apk\test.xlsx'
current_week_file_path2 = r'C:\Users\chamsa\Desktop\stage_prim\IPFahren\apk\test2.xlsx'



html_file_path = 'index.html'
pdf_file_path = 'output.pdf'
pdf_report_path = 'report.pdf'
email_subject = "Weekly Test Case Comparison Results"

 

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
 
    # headers = ['TS', 'TCs', 'FAR C01','FAR C02' ,'HVM C01', 'HVM C02', 'DAF C01','DAF C02', 'Comment']


def create_table(table_data):
    """Creates a formatted table from the given DataFrame."""
    headers = [
        'TS', 'TCs', 'FAR C01', 'FAR C02', 'HVM C01', 'HVM C02',
        'DAF C01', 'DAF C02', 
        'Comment'
    ]
    table_header = "|| " + " || ".join(f"*{header}*" for header in headers) + " ||"

    
    table_rows = []
    current_ts = None
    
    def extract_numbers(ids):
        """Extract numeric parts from a list of IDs."""
        return ', '.join(id.split('_')[1] for id in ids)


    grouped_links = {}
    for ticket in table_data:
        ts = ticket['TS']
        if ts not in grouped_links:
            grouped_links[ts] = {
                'FAR C01': '',
                'FAR C02': '',
                'HVM C01': '',
                'HVM C02': '',
                'DAF C01': '',
                'DAF C02': ''
            }
        used_ids = ticket['link'].split(', ')
        for id in used_ids:
            if id.startswith('far_') and id.endswith('_C01'):
                grouped_links[ts]['FAR C01'] = id
            elif id.startswith('far_') and id.endswith('_C02'):
                grouped_links[ts]['FAR C02'] = id
            elif id.startswith('hvm_') and id.endswith('_C01'):
                grouped_links[ts]['HVM C01'] = id
            elif id.startswith('hvm_') and id.endswith('_C02'):
                grouped_links[ts]['HVM C02'] = id
            elif id.startswith('daf_') and id.endswith('_C01'):
                grouped_links[ts]['DAF C01'] = id
            elif id.startswith('daf_') and id.endswith('_C02'):
                grouped_links[ts]['DAF C02'] = id

    lnk = 'https://ddad.artifactory.cc.bmwgroup.net/ui/native/'

    for ticket in table_data:
        if ticket['TS'] != current_ts:
            current_ts = ticket['TS']
            
          
            links = grouped_links.get(current_ts, {})

        
            far_c01 = lnk + extract_numbers([links['FAR C01']]) if links['FAR C01'] else ''
            far_c02 = lnk + extract_numbers([links['FAR C02']]) if links['FAR C02'] else ''
            hvm_c01 = lnk + extract_numbers([links['HVM C01']]) if links['HVM C01'] else ''
            hvm_c02 = lnk + extract_numbers([links['HVM C02']]) if links['HVM C02'] else ''
            daf_c01 = lnk + extract_numbers([links['DAF C01']]) if links['DAF C01'] else ''
            daf_c02 = lnk + extract_numbers([links['DAF C02']]) if links['DAF C02'] else ''

            empt_row = (
                f"| | |  |  |  | | | "
                f" | | |"
            )
            # table_rows.append(empt_row)

            
            link_row = (
                f"|| *urls* ||  || {far_c01} || {far_c02} || {hvm_c01} || {hvm_c02} || "
                f"{daf_c01} || {daf_c02} || ||"
            )
            table_rows.append(link_row)


        
        data_row = "| " + " |".join(
            f"{ticket.get(header, '')}"   
            for header in headers
        ) + " |"
        table_rows.append(data_row)
    
    return f"{table_header}\n" + "\n".join(table_rows)




def clean_json_string(json_str):
    """Clean the JSON string by handling special characters and formatting."""
    corrected_str = re.sub(r"(?<!\\)'", '"', json_str).strip()
    return corrected_str

import pandas as pd

def create_hardware_table(df):
    controllers = ['FAR', 'HVM', 'DAF']
    hw_table = pd.DataFrame({
        'HW': controllers,
        'SAMPLE': ''
    })

    df['Used TBC'] = df['Used TBC'].fillna('')
    df['hw_sample'] = df['hw_sample'].fillna('')

    
    samples_dict = {controller: [] for controller in controllers}

    for controller in controllers:
      
        filtered_df = df[df['Used TBC'].str.contains(controller, na=False)]
        
        if not filtered_df.empty:
           
            samples = filtered_df['hw_sample'].unique()
            samples_dict[controller] = ', '.join(samples)

    
    for idx, controller in enumerate(controllers):
        hw_table.at[idx, 'SAMPLE'] = samples_dict[controller]

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
    if start_idx == -1:
        return None
    
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


def extract_correct_path(controller_fn, controller_name):
    """Extract the correct path for the given controller from the JSON string."""
    while controller_fn:
        corrected_json_str = clean_json_string(controller_fn)
        if corrected_json_str is None:
            return None

        corrected_json_str = re.sub(r"(?<!\\)'", '"', corrected_json_str).strip()
        try:
            data_dict = json.loads(corrected_json_str)
            link_fn = data_dict.get('path', '')
            if controller_name.lower() in link_fn:
                return link_fn
        except json.JSONDecodeError:
            pass
        
         
        next_start_idx = controller_fn.find('{', len(corrected_json_str))
        if next_start_idx == -1:
            break
        controller_fn = controller_fn[next_start_idx:]

    return None




def create_software_table(df):
    controllers = ['FAR', 'HVM', 'DAF']
    sw_table = pd.DataFrame({
        'Controller': controllers,
        # 'SW': '',  
        'Link': ['Not executed'] * len(controllers) 
    })
    
    df['Used TBC'] = df['Used TBC'].fillna('')
    
    for idx, controller in enumerate(controllers):
        filtered_df = df[df['Used TBC'].str.contains(controller, na=False)]
        if not filtered_df.empty:
            controller_fn = filtered_df['artifactory_upload_paths'].iloc[0]
            correct_path = extract_correct_path(controller_fn, controller)
            if correct_path:
                sw_table.at[idx, 'Link'] = "https://ddad.artifactory.cc.bmwgroup.net/ui/native/" + correct_path

    # headers = ['Controller', 'SW', 'Link']
    headers = ['Controller','Link']
    table_header = "|| " + " || ".join(f"*{header}*" for header in headers) + " ||"
    table_rows = "\n".join(
        "| " + " | ".join(f"{row[header]}" for header in headers) + " |"
        for _, row in sw_table.iterrows()
    )
    return f"{table_header}\n{table_rows}"







def categorize_results(df_week1, df_week2):
    def process_data(df):
        hvm_list = []
        daf_list = []
        far_list = []
        result = {}
        i = 0

        ipf_index = df[df['Test case name'].str.contains('IPF_Ctr_Kl30', na=False)].index.min()
        if pd.isna(ipf_index):
            ipf_index = None
        
        if ipf_index is not None:
            df = df.loc[ipf_index:]
        
        for _, row in df.iterrows():
            test_case_name = row["Test case name"]
            used_tbc = row["Used TBC"]
            test_case_verdict = row["Test case verdict"]
            domain_expert = row["Domainexpertofrequirement"]
            used_ID = row["Report-ID (ATX-ID)"]
            run_id = row["TT_PLAYBOOK_RUN_ID"]
            hw_sample = row["hw_sample"]
            
          
            if "IPF"  not in test_case_name:
                i += 1
                result[str(i)] = [[test_case_name, test_case_verdict]]
            else:
                if str(i) in result:
                    result[str(domain_expert).lower()] = result.pop(str(i))
                
                if str(domain_expert).lower() in result:
                    result[str(domain_expert).lower()].append([test_case_name, test_case_verdict])
                else:
                    result[str(domain_expert).lower()] = [[test_case_name, test_case_verdict]]
                
              
                temp_dict = {
                    'test_case_name': test_case_name,
                    'test_case_verdict': test_case_verdict,
                    'used_ID': used_ID,
                    'run_id': run_id,
                    'Domainexpertofrequirement': domain_expert,
                    'hw_sample': hw_sample
                }
               
                if "HVM" in used_tbc:
                    hvm_list.append(temp_dict)
                elif "DAF" in used_tbc:
                    daf_list.append(temp_dict)
                elif "FAR" in used_tbc:
                    far_list.append(temp_dict)
        # print(hvm_list)
        return hvm_list, daf_list, far_list, result
        
    
    hvm_list_week1, daf_list_week1, far_list_week1, result_week1 = process_data(df_week1)
    hvm_list_week2, daf_list_week2, far_list_week2, result_week2 = process_data(df_week2)
    
    comparison_results = {
        'HVM': {'Week 1': len(hvm_list_week1), 'Week 2': len(hvm_list_week2)},
        'DAF': {'Week 1': len(daf_list_week1), 'Week 2': len(daf_list_week2)},
        'FAR': {'Week 1': len(far_list_week1), 'Week 2': len(far_list_week2)}
    }
    
    return comparison_results, hvm_list_week1, daf_list_week1, far_list_week1, hvm_list_week2, daf_list_week2, far_list_week2



 

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
    return 'Not executed'
def get_final_results(hvm_list_week1, daf_list_week1, far_list_week1, hvm_list_week2, daf_list_week2, far_list_week2):
    """Determines the final verdict for each test case name based on categorized lists for both weeks."""
    all_test_case_names = set(
        item['test_case_name'] for item in hvm_list_week1 + daf_list_week1 + far_list_week1
    )
    
    results = []
    for test_case_name in all_test_case_names:
        verdicts_week1 = {'HVM': {'C01': [], 'C02': []}, 'DAF': {'C01': [], 'C02': []}, 'FAR': {'C01': [], 'C02': []}}
        verdicts_week2 = {'HVM': {'C01': [], 'C02': []}, 'DAF': {'C01': [], 'C02': []}, 'FAR': {'C01': [], 'C02': []}}
        domain_experts = set()
        used_ID = set()  
        
       
        for item in hvm_list_week1:
            if item['test_case_name'] == test_case_name:
                hw_sample = item['hw_sample']
                
                if 'C01' in hw_sample:
                    verdicts_week1['HVM']['C01'].append(item['test_case_verdict'])
                    used_ID.add('hvm_' + str(item['used_ID'])+'_C01')
                if 'C02' in hw_sample:
                    verdicts_week1['HVM']['C02'].append(item['test_case_verdict'])
                    used_ID.add('hvm_' + str(item['used_ID'])+'_C02')
                    # print(hw_sample)
                    # print(used_ID)
                    # print(test_case_name)
                domain_experts.add(item['Domainexpertofrequirement'])
                
                
        for item in daf_list_week1:
            if item['test_case_name'] == test_case_name:
                hw_sample = item['hw_sample']
                if 'C01' in hw_sample:
                    verdicts_week1['DAF']['C01'].append(item['test_case_verdict'])
                    used_ID.add('daf_' + str(item['used_ID'])+'_C01')
                if 'C02' in hw_sample:
                    verdicts_week1['DAF']['C02'].append(item['test_case_verdict'])
                    used_ID.add('daf_' + str(item['used_ID'])+'_C02')
                domain_experts.add(item['Domainexpertofrequirement'])
                
        for item in far_list_week1:
            if item['test_case_name'] == test_case_name:
                hw_sample = item['hw_sample']
                if 'C01' in hw_sample:
                    verdicts_week1['FAR']['C01'].append(item['test_case_verdict'])
                    used_ID.add('far_' + str(item['used_ID'])+'_C01')
                if 'C02' in hw_sample:
                    verdicts_week1['FAR']['C02'].append(item['test_case_verdict'])
                    used_ID.add('far_' + str(item['used_ID'])+'_C02')
                domain_experts.add(item['Domainexpertofrequirement'])

        for item in hvm_list_week2:
            if item['test_case_name'] == test_case_name:
                hw_sample = item['hw_sample']
                if 'C01' in hw_sample:
                    verdicts_week2['HVM']['C01'].append(item['test_case_verdict'])
                    used_ID.add('hvm_' + str(item['used_ID'])+'_C01')
                if 'C02' in hw_sample:
                    verdicts_week2['HVM']['C02'].append(item['test_case_verdict'])
                    used_ID.add('hvm_' + str(item['used_ID'])+'_C02')
                domain_experts.add(item['Domainexpertofrequirement'])
                
        for item in daf_list_week2:
            if item['test_case_name'] == test_case_name:
                hw_sample = item['hw_sample']
                if 'C01' in hw_sample:
                    verdicts_week2['DAF']['C01'].append(item['test_case_verdict'])
                    used_ID.add('daf_' + str(item['used_ID'])+'_C01')
                if 'C02' in hw_sample:
                    verdicts_week2['DAF']['C02'].append(item['test_case_verdict'])
                    used_ID.add('daf_' + str(item['used_ID'])+'_C02')
                domain_experts.add(item['Domainexpertofrequirement'])
                
        for item in far_list_week2:
            if item['test_case_name'] == test_case_name:
                hw_sample = item['hw_sample']
                if 'C01' in hw_sample:
                    verdicts_week2['FAR']['C01'].append(item['test_case_verdict'])
                    used_ID.add('far_' + str(item['used_ID'])+'_C01')
                if 'C02' in hw_sample:
                    verdicts_week2['FAR']['C02'].append(item['test_case_verdict'])
                    used_ID.add('far_' + str(item['used_ID'])+'_C02')
                domain_experts.add(item['Domainexpertofrequirement'])
        
     
        final_verdicts_week1 = {
            'HVM': {k: determine_final_verdict(v) for k, v in verdicts_week1['HVM'].items()},
            'DAF': {k: determine_final_verdict(v) for k, v in verdicts_week1['DAF'].items()},
            'FAR': {k: determine_final_verdict(v) for k, v in verdicts_week1['FAR'].items()},
        }

        
        final_verdicts_week2 = {
            'HVM': {k: determine_final_verdict(v) for k, v in verdicts_week2['HVM'].items()},
            'DAF': {k: determine_final_verdict(v) for k, v in verdicts_week2['DAF'].items()},
            'FAR': {k: determine_final_verdict(v) for k, v in verdicts_week2['FAR'].items()},
        }
        
        used_ID_str = ', '.join(map(str, sorted(used_ID)))   
        # print(used_ID)
        
        if 'none' not in final_verdicts_week1.values() and 'none' not in final_verdicts_week2.values():
            for domain_expert in domain_experts:
                results.append({
                    'link': used_ID_str,  
                    'TS': domain_expert.title(),
                    'TCs': test_case_name,
                    'FAR C01': final_verdicts_week1['FAR']['C01'],
                    'FAR C02': final_verdicts_week1['FAR']['C02'],
                    'HVM C01': final_verdicts_week1['HVM']['C01'],
                    'HVM C02': final_verdicts_week1['HVM']['C02'],
                    'DAF C01': final_verdicts_week1['DAF']['C01'],
                    'DAF C02': final_verdicts_week1['DAF']['C02'],
                    'FAR C01_Week2': final_verdicts_week2['FAR']['C01'],
                    'FAR C02_Week2': final_verdicts_week2['FAR']['C02'],
                    'HVM C01_Week2': final_verdicts_week2['HVM']['C01'],
                    'HVM C02_Week2': final_verdicts_week2['HVM']['C02'],
                    'DAF C01_Week2': final_verdicts_week2['DAF']['C01'],
                    'DAF C02_Week2': final_verdicts_week2['DAF']['C02'],
                    'Comment': ' '
                })
    
    results_sorted = sorted(results, key=lambda x: (x['TS'], x['TCs']))
    return results_sorted





def get_existing_issue_data(issue_key):
    try:
        issue = jira.issue(issue_key)
        status = issue.fields.status.name
        invalid_statuses = {'Closed', 'Resolved', 'Done', 'Fixed', 'Completed', 'Terminé(e)'}
     
        if status in invalid_statuses:
            print(f"Ticket {issue_key} is not valid. Status: {status}")
            return False
        else:
            print(f"Ticket {issue_key} is valid. Status: {status}")
            # return True
        
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
    updated_description += f"\n\n *Hardware :* \n {create_hardware_table(sw_table)}"
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
    if(existing_data):

        changes = compare_and_display_changes(existing_data, new_summary, new_description, table_data, sw_table)
        
        if changes:
            update_jira_ticket(issue_key, new_summary, new_description, table_data, sw_table)
            generate_pdf_from_html(html_file_path, pdf_file_path)

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
    updated_description += f"\n\n *Hardware :* \n {create_hardware_table(sw_table)}"
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

    















def read_html_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        html_template = file.read()
    return html_template


from datetime import datetime

def replace_placeholders_in_template(html_template, stats):
  
    placeholders = {
     
        'passed_count': str(stats.get('passed_count', '0')),
        'error_count': str(stats.get('error_count', '0')),
        'far_passed_count': str(stats.get('far_passed_count', '0')),
        'far_error_count': str(stats.get('far_error_count', '0')),
        'hvm_passed_count': str(stats.get('hvm_passed_count', '0')),
        'hvm_error_count': str(stats.get('hvm_error_count', '0')),
        'daf_passed_count': str(stats.get('daf_passed_count', '0')),
        'daf_error_count': str(stats.get('daf_error_count', '0')),
        'current_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    
    for key, value in placeholders.items():
        html_template = html_template.replace(f'{{{{ {key} }}}}', value)
    
    return html_template

 

def generate_table_rows(comparison_result):
    table_rows = ""
    for index, row in comparison_result.iterrows():
        table_rows += f"""
           
            <tr>
                <td><span class="highlight">{row['TS']}</span></td>
                <td><span class="highlight">{row['TCs']}</span></td>
                <td>
                    FAR C01: {row['FAR C01']},<br><hr>
                    FAR C02: {row['FAR C02']},<br><hr>
                    HVM C01: {row['HVM C01']},<br><hr>
                    HVM C02: {row['HVM C02']},<br><hr>
                    DAF C01: {row['DAF C01']},<br><hr>
                    DAF C02: {row['DAF C02']}
                </td>
               
                <td>
                    FAR C01: {row['FAR C01_Week2']},<br><hr>
                    FAR C01: {row['FAR C02_Week2']},<br><hr>
                    HVM C01: {row['HVM C01_Week2']},<br><hr>
                    HVM C01: {row['HVM C02_Week2']},<br><hr>
                    DAF C01: {row['DAF C01_Week2']},<br><hr>
                    DAF C01: {row['DAF C02_Week2']}
                </td>


            </tr>
        """
    return table_rows


 
from datetime import datetime

def count_status(df, status):
    """Compte le nombre de fois qu'un statut spécifique apparaît dans un DataFrame."""
    return df.value_counts().get(status, 0)

def generate_comparison_summary(comparison_result):
    table_rows = generate_table_rows(comparison_result)

    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    cols_week1 = ['FAR C01', 'FAR C02', 'HVM C01', 'HVM C02', 'DAF C01', 'DAF C02']
    cols_week2 = [col + '_Week2' for col in cols_week1]

  
    passed_count = sum(count_status(comparison_result[col], 'passed✅') for col in cols_week1)
    error_count = sum(count_status(comparison_result[col], 'error❌') for col in cols_week1)
    
    passed_count_week2 = sum(count_status(comparison_result[col], 'passed✅') for col in cols_week2)
    error_count_week2 = sum(count_status(comparison_result[col], 'error❌') for col in cols_week2)

  
    far_passed_count = sum(count_status(comparison_result[col], 'passed✅') for col in ['FAR C01', 'FAR C02'])
    far_error_count = sum(count_status(comparison_result[col], 'error❌') for col in ['FAR C01', 'FAR C02'])
    hvm_passed_count = sum(count_status(comparison_result[col], 'passed✅') for col in ['HVM C01', 'HVM C02'])
    hvm_error_count = sum(count_status(comparison_result[col], 'error❌') for col in ['HVM C01', 'HVM C02'])
    daf_passed_count = sum(count_status(comparison_result[col], 'passed✅') for col in ['DAF C01', 'DAF C02'])
    daf_error_count = sum(count_status(comparison_result[col], 'error❌') for col in ['DAF C01', 'DAF C02'])

    far_passed_count_week2 = sum(count_status(comparison_result[col], 'passed✅') for col in ['FAR C01_Week2', 'FAR C02_Week2'])
    far_error_count_week2 = sum(count_status(comparison_result[col], 'error❌') for col in ['FAR C01_Week2', 'FAR C02_Week2'])
    hvm_passed_count_week2 = sum(count_status(comparison_result[col], 'passed✅') for col in ['HVM C01_Week2', 'HVM C02_Week2'])
    hvm_error_count_week2 = sum(count_status(comparison_result[col], 'error❌') for col in ['HVM C01_Week2', 'HVM C02_Week2'])
    daf_passed_count_week2 = sum(count_status(comparison_result[col], 'passed✅') for col in ['DAF C01_Week2', 'DAF C02_Week2'])
    daf_error_count_week2 = sum(count_status(comparison_result[col], 'error❌') for col in ['DAF C01_Week2', 'DAF C02_Week2'])

 
    html_template = read_html_template('index.html')

  
    comparison_summary = html_template.replace('{{ table_rows }}', table_rows)
    comparison_summary = comparison_summary.replace('{{ passed_count }}', str(passed_count))
    comparison_summary = comparison_summary.replace('{{ error_count }}', str(error_count))
    comparison_summary = comparison_summary.replace('{{ passed_count_week2 }}', str(passed_count_week2))
    comparison_summary = comparison_summary.replace('{{ error_count_week2 }}', str(error_count_week2))
    comparison_summary = comparison_summary.replace('{{ far_passed_count }}', str(far_passed_count))
    comparison_summary = comparison_summary.replace('{{ far_error_count }}', str(far_error_count))
    comparison_summary = comparison_summary.replace('{{ hvm_passed_count }}', str(hvm_passed_count))
    comparison_summary = comparison_summary.replace('{{ hvm_error_count }}', str(hvm_error_count))
    comparison_summary = comparison_summary.replace('{{ daf_passed_count }}', str(daf_passed_count))
    comparison_summary = comparison_summary.replace('{{ daf_error_count }}', str(daf_error_count))
    comparison_summary = comparison_summary.replace('{{ far_passed_count_week2 }}', str(far_passed_count_week2))
    comparison_summary = comparison_summary.replace('{{ far_error_count_week2 }}', str(far_error_count_week2))
    comparison_summary = comparison_summary.replace('{{ hvm_passed_count_week2 }}', str(hvm_passed_count_week2))
    comparison_summary = comparison_summary.replace('{{ hvm_error_count_week2 }}', str(hvm_error_count_week2))
    comparison_summary = comparison_summary.replace('{{ daf_passed_count_week2 }}', str(daf_passed_count_week2))
    comparison_summary = comparison_summary.replace('{{ daf_error_count_week2 }}', str(daf_error_count_week2))
    comparison_summary = comparison_summary.replace('{{ current_date }}', current_date)
    
    return comparison_summary







config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

def generate_pdf_from_html(html_file_path, pdf_file_path):
    pdfkit.from_file(html_file_path, pdf_file_path, configuration=config)
    print(f"PDF generated successfully: {pdf_file_path}")
    # send_email(email_subject, EMAIL_HOST_USER, EMAIL_RECIPIENT, EMAIL_HOST_PASSWORD, pdf_file_path)

def send_email(subject, from_email, to_email, password, pdf_file_path=None, pdf_report_path=None):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

  
    if pdf_file_path:
        with open(pdf_file_path, 'rb') as file:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={os.path.basename(pdf_file_path)}',
            )
            msg.attach(part)

    if pdf_report_path:
        with open(pdf_report_path, 'rb') as file:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={os.path.basename(pdf_report_path)}',
            )
            msg.attach(part)

 
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")





import matplotlib.pyplot as plt

# def plot_verdict_distribution(hvm_list, daf_list, far_list, filename='verdict_distribution.png'):
#     categories = ['HVM', 'DAF', 'FAR']
#     verdict_counts = {
#         'PASSED': [0, 0, 0],
#         'ERROR': [0, 0, 0]
#     }

   
#     for lst, i in zip([hvm_list, daf_list, far_list], range(3)):
#         for item in lst:
#             verdict = item['test_case_verdict']
#             if verdict == 'PASSED':
#                 verdict_counts['PASSED'][i] += 1
#             elif verdict == 'ERROR':
#                 verdict_counts['ERROR'][i] += 1

 
#     fig, ax = plt.subplots()
#     bar_width = 0.35
#     index = range(len(categories))

#     bar1 = ax.bar(index, verdict_counts['PASSED'], bar_width, label='PASSED')
#     bar2 = ax.bar([p + bar_width for p in index], verdict_counts['ERROR'], bar_width, label='ERROR')

#     ax.set_xlabel('Categories')
#     ax.set_ylabel('Counts')
#     ax.set_title('Verdict Distribution by Variant')
#     ax.set_xticks([p + bar_width / 2 for p in index])
#     ax.set_xticklabels(categories)
#     ax.legend()
#     plt.savefig(filename)
#     plt.show()



def plot_verdict_distribution(hvm_list, daf_list, far_list, filename):
    categories = ['HVM', 'DAF', 'FAR']
    verdict_counts = {
        'PASSED': [0, 0, 0],
        'ERROR': [0, 0, 0]
    }

 
    for lst, i in zip([hvm_list, daf_list, far_list], range(3)):
        for item in lst:
            verdict = item['test_case_verdict']
            if verdict == 'PASSED':
                verdict_counts['PASSED'][i] += 1
            elif verdict == 'ERROR':
                verdict_counts['ERROR'][i] += 1


    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))  # 2 rows, 1 column

 
    bar_width = 0.35
    index = range(len(categories))

    ax1.bar(index, verdict_counts['PASSED'], bar_width, label='PASSED')
    ax1.bar([p + bar_width for p in index], verdict_counts['ERROR'], bar_width, label='ERROR')

    ax1.set_xlabel('Categories')
    ax1.set_ylabel('Counts')
    

    if 'week1' in filename.lower():
        ax1.set_title('Verdict Distribution by Variant (WEEK 1)')
        ax2.set_title('Overall Verdict Distribution (WEEK 1)')
    elif 'week2' in filename.lower():
        ax1.set_title('Verdict Distribution by Variant (WEEK 2)')
        ax2.set_title('Overall Verdict Distribution (WEEK 2)')
    else:
        ax1.set_title('Verdict Distribution by Variant')
        ax2.set_title('Overall Verdict Distribution')

    ax1.set_xticks([p + bar_width / 2 for p in index])
    ax1.set_xticklabels(categories)
    ax1.legend()

  
    total_counts = [sum(verdict_counts['PASSED']), sum(verdict_counts['ERROR'])]
    labels = ['PASSED', 'ERROR']
    colors = ['#ff9999', '#66b3ff']
    wedgeprops = dict(width=0.3, edgecolor='black')

    ax2.pie(total_counts, labels=labels, autopct='%1.1f%%', startangle=140,
            colors=colors, wedgeprops=wedgeprops)

    plt.tight_layout()
    plt.savefig(filename)
    plt.show()



from fpdf import FPDF

def create_pdf_with_image(image_path, image_path2, pdf_path='report.pdf'):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
  
    pdf.cell(200, 10, txt="Verdict Distribution (2 WEEK)", ln=True, align='C')
    
 
    pdf.image(image_path, x=10, y=30, w=180)  
    
    
    pdf.ln(90) 
    pdf.image(image_path2, x=10, y=None, w=180) 
    
   
    pdf.output(pdf_path)
    print(f"PDF generated successfully: {pdf_path}")
 







if __name__ == "__main__":
   
    df_week1 = read_excel_file(current_week_file_path)
    df_week2 = read_excel_file(current_week_file_path2)
 
    required_columns = [
        'Test case name',
        'Test case verdict',
        'Domainexpertofrequirement',
        'artifactory_upload_paths',
        'Used TBC',
        'Report-ID (ATX-ID)',
        'hw_sample'
    ]
    validate_columns(df_week1, required_columns)
    df_week1 = clean_data(df_week1)
    validate_columns(df_week2, required_columns)
    df_week2 = clean_data(df_week2)
    

    comparison_results, hvm_list_week1, daf_list_week1, far_list_week1, hvm_list_week2, daf_list_week2, far_list_week2 = categorize_results(df_week1, df_week2)

    # print(hvm_list)
  
    final_results = get_final_results(
        hvm_list_week1, daf_list_week1, far_list_week1,
        hvm_list_week2, daf_list_week2, far_list_week2
    )

    # print(final_results)
    

    final_df = pd.DataFrame(final_results).drop_duplicates()
    final_df.to_csv('final_results_comparison.csv', index=False)
    final_df_sorted = final_df.sort_values(by='TS', ascending=True)
    table_data = final_df_sorted.to_dict(orient='records')
    # print(table_data)
     

    issue_key = "IP-9"
    new_summary = "Updated test"
    new_description = "Updated Description."
    df = read_excel_file(current_week_file_path)

    update_if_changed(issue_key, new_summary, new_description, table_data, df)


  
    print("Hardware \n" ,create_hardware_table())
    print("Software  \n",create_software_table(df))
    print("Intake Result  \n",create_table(table_data))
  
    html_template = read_html_template('index.html')
    html_template_init = read_html_template('index_init.html')
    

    with open('index.html', 'w', encoding='utf-8') as file:
        file.write(html_template_init)
        aa=True
    
    if(aa):
        

        comparison_summary_html = generate_comparison_summary(final_df_sorted)
        with open('index.html', 'w', encoding='utf-8') as file:
            file.write(comparison_summary_html)
 
  

     
    plot_verdict_distribution(hvm_list_week1, daf_list_week1, far_list_week1, 'verdict_distribution_week1.png')
    plot_verdict_distribution(hvm_list_week2, daf_list_week2, far_list_week2, 'verdict_distribution_week2.png')

  

    generate_pdf_from_html(html_file_path, pdf_file_path)
    create_pdf_with_image('verdict_distribution_week1.png', 'verdict_distribution_week2.png','report.pdf')
    send_email(email_subject, EMAIL_HOST_USER, EMAIL_RECIPIENT, EMAIL_HOST_PASSWORD, pdf_file_path,pdf_report_path)

