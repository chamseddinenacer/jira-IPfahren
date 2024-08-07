# modif just le ligne de table sans ajouter autre



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
jira = JIRA(server=jira_server, basic_auth=(jira_user, jira_token))

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

 
# Email configuration from environment variables
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT')

# Excel file paths
current_week_file_path = r'C:\Users\chamsa\Desktop\IPFahren\apk\test.xlsx'
previous_week_file_path = r'C:\Users\chamsa\Desktop\IPFahren\apk\test.xlsx'

def read_excel_file(path):
    try:
        df = pd.read_excel(path, header=1)
        return df
    except FileNotFoundError:
        logger.error("Excel file not found")
        raise

def validate_columns(df, required_columns):
    for col in required_columns:
        if col not in df.columns:
            logger.error(f"Excel file is missing required column: {col}")
            raise ValueError(f"Excel file is missing required column: {col}")



def create_table(table_data):
    headers = ['TS', 'TCs', 'FAR', 'HVM', 'DAF', 'Comment']
    table_header = "|| " + " || ".join(f"*{header}*" for header in headers) + " ||"
    table_rows = "\n".join(
        "| " + " | ".join(
            f"{ticket[header]}" if header not in ['FAR', 'HVM', 'DAF'] else 
            'passed✅' if ticket[header] == 'passed✅' else 'Error❌'
            for header in headers
        ) + " |"
        for _, ticket in table_data.iterrows()
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
    # Find the index of the first opening curly brace
    start_idx = json_string.find('{')
    
    # Find the index of the closing curly brace that matches the first opening curly brace
    end_idx = find_matching_bracket(json_string, start_idx)
    
    # Extract the first object
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
    
    # Fill NaN values with empty string
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

# def send_email(subject, body, from_email, to_email, password):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    part1 = MIMEText(body, 'plain')
    part2 = MIMEText(body, 'html')

    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")

def generate_table_rows(comparison_result):
    table_rows = ""
    for index, row in comparison_result.iterrows():
        table_rows += f"""
            <tr>
                <td><span class="highlight">{row['TS']}</span></td>
                <td><span class="highlight">{row['TCs']}</span></td>
                <td>
                    FAR: {row['FAR_current']},<br>
                    HVM: {row['HVM_current']},<br>
                    DAF: {row['DAF_current']}
                </td>
                <td>
                    FAR: {row['FAR_previous']},<br>
                    HVM: {row['HVM_previous']},<br>
                    DAF: {row['DAF_previous']}
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
    passed_count = comparison_result['FAR_current'].str.count('passed✅').sum() + \
                   comparison_result['HVM_current'].str.count('passed✅').sum() + \
                   comparison_result['DAF_current'].str.count('passed✅').sum()
    error_count = comparison_result['FAR_current'].str.count('error❌').sum() + \
                  comparison_result['HVM_current'].str.count('error❌').sum() + \
                  comparison_result['DAF_current'].str.count('error❌').sum()
    
    # Calculer les statistiques détaillées pour FAR, HVM, DAF
    far_passed_count = count_status(comparison_result['FAR_current'], 'passed✅')
    far_error_count = count_status(comparison_result['FAR_current'], 'error❌')
    hvm_passed_count = count_status(comparison_result['HVM_current'], 'passed✅')
    hvm_error_count = count_status(comparison_result['HVM_current'], 'error❌')
    daf_passed_count = count_status(comparison_result['DAF_current'], 'passed✅')
    daf_error_count = count_status(comparison_result['DAF_current'], 'error❌')
    
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

    # Attach the body
    # part1 = MIMEText(body, 'plain')
    # part2 = MIMEText(body, 'html')
    # msg.attach(part1)
    # msg.attach(part2)

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
    # Read current and previous week's data
    current_df = read_excel_file(current_week_file_path)
    previous_df = read_excel_file(previous_week_file_path)
    
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
    validate_columns(previous_df, required_columns)

 
    current_df['Used TBC'] = current_df['Used TBC'].astype(str).fillna('')
    previous_df['Used TBC'] = previous_df['Used TBC'].astype(str).fillna('')

    # Group by 'Domain expert of requirement' (TS) and then by 'Test case name'
    grouped_current = current_df.groupby(['Domainexpertofrequirement']).apply(
        lambda group: group.groupby('Test case name').apply(
            lambda sub_group: pd.Series({
                'TS': sub_group['Domainexpertofrequirement'].iloc[0].title(),
                'TCs': sub_group['Test case name'].iloc[0],
                'FAR': 'passed✅' if ('FAR' in sub_group['Used TBC'].iloc[0]) and (sub_group['Test case verdict'].iloc[0].strip().lower() == 'passed') else 'error❌',
                'HVM': 'passed✅' if ('HVM' in sub_group['Used TBC'].iloc[0]) and (sub_group['Test case verdict'].iloc[0].strip().lower() == 'passed') else 'error❌',
                'DAF': 'passed✅' if ('DAF' in sub_group['Used TBC'].iloc[0]) and (sub_group['Test case verdict'].iloc[0].strip().lower() == 'passed') else 'error❌',
                'Comment': 'Check the variant coverage.'  # Example comment
            })
        ).drop_duplicates(subset=['TCs'])
    ).reset_index(drop=True)

    grouped_previous = previous_df.groupby(['Domainexpertofrequirement']).apply(
        lambda group: group.groupby('Test case name').apply(
            lambda sub_group: pd.Series({
                'TS': sub_group['Domainexpertofrequirement'].iloc[0].title(),
                'TCs': sub_group['Test case name'].iloc[0],
                'FAR': 'passed✅' if ('FAR' in sub_group['Used TBC'].iloc[0]) and (sub_group['Test case verdict'].iloc[0].strip().lower() == 'passed') else 'error❌',
                'HVM': 'passed✅' if ('HVM' in sub_group['Used TBC'].iloc[0]) and (sub_group['Test case verdict'].iloc[0].strip().lower() == 'passed') else 'error❌',
                'DAF': 'passed✅' if ('DAF' in sub_group['Used TBC'].iloc[0]) and (sub_group['Test case verdict'].iloc[0].strip().lower() == 'passed') else 'error❌',
                'Comment': 'Check the variant coverage.'  # Example comment
            })
        ).drop_duplicates(subset=['TCs'])
    ).reset_index(drop=True)

    # Compare the results
    comparison_result = grouped_current.merge(
        grouped_previous,
        on=['TS', 'TCs'],
        suffixes=('_current', '_previous'),
        how='outer',
        indicator=True
    )

    table_data = grouped_current
    issue_key = "IP-9"
    new_summary = "Updated Summary"
    new_description = "Updated Description."
    df = read_excel_file(current_week_file_path)

    update_if_changed(issue_key, new_summary, new_description, table_data, df)

    # Generate and send the email
    comparison_summary_html = generate_comparison_summary(comparison_result)
    # Write the HTML summary to a file
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(comparison_summary_html)

    html_file_path = 'index.html'
    pdf_file_path = 'output.pdf'
    generate_pdf_from_html(html_file_path, pdf_file_path)

    email_subject = "Weekly Test Case Comparison Results"
    # send_email(email_subject, "Please find the attached PDF.", EMAIL_HOST_USER, EMAIL_RECIPIENT, EMAIL_HOST_PASSWORD, pdf_file_path)
    send_email(email_subject, EMAIL_HOST_USER, EMAIL_RECIPIENT, EMAIL_HOST_PASSWORD,pdf_file_path)
