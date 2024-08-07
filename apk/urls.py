from django.urls import path,include
from .views import  *
from .views1 import  *

urlpatterns = [  

 
path('create_jira_ticket/', create_jira_ticket, name='create_jira_ticket'),
path('update-jira-ticket/', update_jira_ticket22_v0, name='update_jira_ticket'),
path('update_jira_ticket22/', update_jira_ticket22_with_summ, name='update_jira_ticket22_with_summ'),
path('list_all_issues/', list_all_issues, name='list_all_issues'),
path('issues_list/', issues_list_view, name='issues_list'),
path('display_table/', display_table, name='display_table'),
path('', index, name='index'),

path('upload/', upload_excel, name='upload_excel'),



]