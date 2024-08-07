# report/views.py
import pandas as pd
import json
import re
import logging
from django.http import HttpResponse
from django.shortcuts import render
 
from django.core.mail import EmailMessage
from django.conf import settings
import pdfkit
from datetime import datetime

logger = logging.getLogger(__name__)

def read_excel_file(path):
    try:
        df = pd.read_excel(path, header=1)
        return df
    except FileNotFoundError:
        logger.error("Excel file not found")
        raise

def clean_data(df):
    df['Domainexpertofrequirement'] = df['Domainexpertofrequirement'].fillna('Unknown')
    df['Used TBC'] = df['Used TBC'].astype(str).fillna('')
    df = df[df['Domainexpertofrequirement'] != 'Unknown']
    return df

def validate_columns(df, required_columns):
    for col in required_columns:
        if col not in df.columns:
            logger.error(f"Excel file is missing required column: {col}")
            raise ValueError(f"Excel file is missing required column: {col}")

def categorize_results(df):
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
    all_test_case_names = set(item['test_case_name'] for item in hvm_list + daf_list + far_list)
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

def generate_table_rows(df):
    table_rows = ""
    for _, row in df.iterrows():
        table_rows += f"<tr><td>{row['TS']}</td><td>{row['TCs']}</td><td>{row['FAR']}</td><td>{row['HVM']}</td><td>{row['DAF']}</td><td>{row['Comment']}</td></tr>"
    return table_rows

def count_status(df_column, status):
    return (df_column == status).sum()

def read_html_template(template_name):
    with open(f'{template_name}', 'r', encoding='utf-8') as f:
        return f.read()

def generate_comparison_summary(comparison_result):
    table_rows = generate_table_rows(pd.DataFrame(comparison_result))
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    passed_count = count_status(pd.DataFrame(comparison_result)['FAR'], 'passed✅') + \
                   count_status(pd.DataFrame(comparison_result)['HVM'], 'passed✅') + \
                   count_status(pd.DataFrame(comparison_result)['DAF'], 'passed✅')
    error_count = count_status(pd.DataFrame(comparison_result)['FAR'], 'error❌') + \
                  count_status(pd.DataFrame(comparison_result)['HVM'], 'error❌') + \
                  count_status(pd.DataFrame(comparison_result)['DAF'], 'error❌')

    far_passed_count = count_status(pd.DataFrame(comparison_result)['FAR'], 'passed✅')
    far_error_count = count_status(pd.DataFrame(comparison_result)['FAR'], 'error❌')
    hvm_passed_count = count_status(pd.DataFrame(comparison_result)['HVM'], 'passed✅')
    hvm_error_count = count_status(pd.DataFrame(comparison_result)['HVM'], 'error❌')
    daf_passed_count = count_status(pd.DataFrame(comparison_result)['DAF'], 'passed✅')
    daf_error_count = count_status(pd.DataFrame(comparison_result)['DAF'], 'error❌')

    html_template = read_html_template('index2.html')
    

    comparison_summary = html_template.replace('{{ table_rows }}', table_rows)
    comparison_summary = comparison_summary.replace('{{ passed_count }}', str(passed_count))
    comparison_summary = comparison_summary.replace('{{ error_count }}', str(error_count))
    comparison_summary = comparison_summary.replace('{{ far_passed_count }}', str(far_passed_count))
    comparison_summary = comparison_summary.replace('{{ far_error_count }}', str(far_error_count))
    comparison_summary = comparison_summary.replace('{{ hvm_passed_count }}', str(hvm_passed_count))
    comparison_summary = comparison_summary.replace('{{ hvm_error_count }}', str(hvm_error_count))
    comparison_summary = comparison_summary.replace('{{ daf_passed_count }}', str(hvm_error_count))
 
    comparison_summary = comparison_summary.replace('{{ daf_error_count }}', str(daf_error_count))
    comparison_summary = comparison_summary.replace('{{ current_date }}', current_date)
    
    return comparison_summary

def generate_pdf_from_html(html_content):
    options = {
        'page-size': 'A4',
        'encoding': 'UTF-8',
        'no-outline': None
    }
    pdf = pdfkit.from_string(html_content, False, options=options)
    return pdf

def upload_excel(request):
    if request.method == 'POST' and request.FILES['excel_file']:
        excel_file = request.FILES['excel_file']
        df = read_excel_file(excel_file)
        validate_columns(df, ['Test case name', 'Test case verdict', 'Domainexpertofrequirement', 'Used TBC', 'Report-ID (ATX-ID)', 'hw_sample'])
        df = clean_data(df)
        
        hvm_list, daf_list, far_list, result = categorize_results(df)
        comparison_result = get_final_results(hvm_list, daf_list, far_list)

        pdf_content = generate_pdf_from_html(generate_comparison_summary(comparison_result))

        email = EmailMessage(
            'Test Case Report',
            'Please find the attached report.',
            settings.DEFAULT_FROM_EMAIL,
            ['chamseddine.nacer@isimg.tn'],
        )
        email.attach('report.pdf', pdf_content, 'application/pdf')
        email.send()

        return HttpResponse('Report has been sent via email.')
    return render(request, 'upload.html')
