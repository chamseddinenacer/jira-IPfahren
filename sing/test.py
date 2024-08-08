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
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

  

# Excel file paths
current_week_file_path = r'C:\Users\chamsa\Desktop\IPFahren\apk\test.xlsx'
 

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

    















def read_html_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        html_template = file.read()
    return html_template


from datetime import datetime

def replace_placeholders_in_template(html_template, stats):
    # Générer les lignes du tableau
    
    
    # Remplacer les placeholders avec les valeurs correspondantes
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
    
    # Remplacer les placeholders dans le template
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
                    FAR: {row['FAR']},<br>
                    HVM: {row['HVM']},<br>
                    DAF: {row['DAF']}
                </td>
               
            </tr>
        """
    return table_rows


 

def count_status(df, status):
    return df.value_counts().get(status, 0)

def generate_comparison_summary(comparison_result):
    table_rows = generate_table_rows(comparison_result)

    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Calculer les statistiques
    passed_count = count_status(comparison_result['FAR'], 'passed✅') + \
                   count_status(comparison_result['HVM'], 'passed✅') + \
                   count_status(comparison_result['DAF'], 'passed✅')
    error_count = count_status(comparison_result['FAR'], 'error❌') + \
                  count_status(comparison_result['HVM'], 'error❌') + \
                  count_status(comparison_result['DAF'], 'error❌')
    
    # Calculer les statistiques détaillées pour FAR, HVM, DAF
    far_passed_count = count_status(comparison_result['FAR'], 'passed✅')
    far_error_count = count_status(comparison_result['FAR'], 'error❌')
    hvm_passed_count = count_status(comparison_result['HVM'], 'passed✅')
    hvm_error_count = count_status(comparison_result['HVM'], 'error❌')
    daf_passed_count = count_status(comparison_result['DAF'], 'passed✅')
    daf_error_count = count_status(comparison_result['DAF'], 'error❌')
    
    # Lire le modèle HTML
    html_template = read_html_template('index.html')

    # Remplacer les espaces réservés dans le modèle HTML
    comparison_summary = html_template.replace('{{ table_rows }}', table_rows)
    comparison_summary = comparison_summary.replace('{{ passed_count }}', str(passed_count))
    comparison_summary = comparison_summary.replace('{{ error_count }}', str(error_count))
    comparison_summary = comparison_summary.replace('{{ far_passed_count }}', str(far_passed_count))
    comparison_summary = comparison_summary.replace('{{ far_error_count }}', str(far_error_count))
    comparison_summary = comparison_summary.replace('{{ hvm_passed_count }}', str(hvm_passed_count))
    comparison_summary = comparison_summary.replace('{{ hvm_error_count }}', str(hvm_error_count))
    comparison_summary = comparison_summary.replace('{{ daf_passed_count }}', str(daf_passed_count))
    comparison_summary = comparison_summary.replace('{{ daf_error_count }}', str(daf_error_count))
    comparison_summary = comparison_summary.replace('{{ current_date }}', current_date)
    
    return comparison_summary





# Spécifiez le chemin vers l'exécutable wkhtmltopdf
config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

def generate_pdf_from_html(html_file_path, pdf_file_path):
    pdfkit.from_file(html_file_path, pdf_file_path, configuration=config)
    print(f"PDF generated successfully: {pdf_file_path}")


def send_email(subject, from_email, to_email, password, pdf_file_path=None):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    # Attach PDF if provided
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

    # Send the email
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")


if __name__ == "__main__":
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

    issue_key = "IP-9"
    new_summary = "Updated test"
    new_description = "Updated Description."
    df = read_excel_file(current_week_file_path)

    update_if_changed(issue_key, new_summary, new_description, table_data, df)
 
    print("Hardware \n" ,create_hardware_table())
    print("Software  \n",create_software_table(df))
    print("Intake Result  \n",create_table(table_data))
  
    html_template = read_html_template('index.html')
    comparison_summary_html = generate_comparison_summary(final_df_sorted)

    # Write the HTML summary to a file
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(comparison_summary_html)

    html_file_path = 'index.html'
    pdf_file_path = 'output.pdf'
    generate_pdf_from_html(html_file_path, pdf_file_path)

    email_subject = "Weekly Test Case Comparison Results"
    # send_email(email_subject, EMAIL_HOST_USER, EMAIL_RECIPIENT, EMAIL_HOST_PASSWORD, pdf_file_path)
