from platform import node
from tabnanny import check
from xml.dom import WRONG_DOCUMENT_ERR
import plotly
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import dash_bootstrap_components as dbc
import pandas as pd
from sklearn import tree
import xlsxwriter
from datetime import datetime
from datetime import timedelta
from scipy import stats
import plotly.graph_objs as go
import os
import numpy as np
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px
import base64
import datetime
import io
from datetime import date
from DB_validation import *

# Reading excel file and creating a list of options for dropdown menu
cust_details = pd.read_excel('C:/Users/krama/Documents/work/SKF/Vibration - Analyst/Scripts/Customers DB validation/cust_details.xlsx')
options_c = []
for cust in cust_details.customer:
    label = cust_details.loc[cust_details.customer == cust, "customer"].item()
    value = cust_details.loc[cust_details.customer == cust, "short_name"].item()
    options_c.append({'label': label, 'value': value})


app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = html.Div([
    dcc.Store(id='db-data-memory'),
    dcc.Store(id='dropdown-value'),
    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                html.Br(),
                dbc.Col([
                    html.H5('Select customer'),
                    dcc.Dropdown(
                    id='customer-selection',
                    options=options_c,
                    placeholder ='Select customer from the list...' )
                ]),
                dbc.Col([
                    html.H5('Selected DB details:'),
                    html.H6('Customer name: -', id = 'cust-name-text'),
                    html.H6('DB name: -', id = 'db-name-text'),
                    html.H6('TablsetId: -', id = 'tblsetid-text')
                ]),
                dbc.Col([
                    html.H5('Nodes:', id='nodes-word'),
                    html.H6('FL: -', id='fl-stat'),
                    html.H6('Assets: -', id='asset-stat'),
                    html.H6('MP: -', id = 'mp-stat')
                ])
            ]),
            html.Br(),
            dcc.Tabs([
                dcc.Tab(html.Div([
                    dbc.Row([
                        dbc.Col(id='stat-col-1'),
                        dbc.Col(id='stat-col-2'),
                        dbc.Col(id='stat-col-3')
                    ])
                ]), label= 'Stat', id='stat-tab'),
                dcc.Tab([
                    dcc.Tabs([
                            dcc.Tab([
                                html.Br(),
                                html.H6('Points with the names which are not according to the naming conventions:'),
                                html.Div([], id = 'names-issues')], label = 'Names Issues', ),
                            dcc.Tab(html.Div([]), label = 'Names/Settings discrepancies', id='names-settings'),
                            dcc.Tab(html.Div([]), label = 'Hierarchy Issues', id = 'hierarchy-issues'),
                            dcc.Tab(html.Div([]), label = 'Thresholds', id = 'thresholds'),
                            dcc.Tab(
                                html.Div([
                                    dbc.Row([
                                        dbc.Col(
                                            [html.Div([], id = 'no-sit-fl')]
                                        ),
                                        dbc.Col(
                                            [html.Div([], id = 'few-sit-fl')]
                                        )
                                    ]),
                                    dbc.Row([
                                        dbc.Col(
                                            [html.Div([], id = 'motor-wo-sit')]
                                        ),
                                        dbc.Col(
                                            [html.Div([], id = 'other-w-sit')]
                                        )
                                    ])
                            ]), label = 'SIT points', id='sit-issues', value = 'sit-contents'),
                            dcc.Tab(html.Div([]), label = 'Disabled Points', id='disabled-points')
                    ], id='tabs-issues') 
                ], label= 'Issues', id='issues-tab')
            ], id='tabs-main')
        ])
    )
])



@app.callback(
    Output('db-data-memory', 'data'),
    Input('customer-selection', 'value')
)
def get_data_customer(selected_file):
    if selected_file == None:
        raise PreventUpdate
    else:
        #Need to add issue handling here
        filename = cust_details.loc[cust_details.short_name == selected_file, 'datafile'].item()
        data_db = pd.read_csv('C:/Users/krama/Documents/work/SKF/Vibration - Analyst/Scripts/Customers DB validation/' + filename)

    return data_db.to_dict()

@app.callback(
    Output('cust-name-text', 'children'),
    Output('db-name-text', 'children'),
    Output('tblsetid-text', 'children'),
    Input('customer-selection', 'value')
)
def select_customer(value):
    #Here we need to get information from the previously prepared csv with necessary data
    if value == None:
        cust = 'Customer name: -'
        db = 'DB name: -'
        tblset = 'TablsetId: -'
    else:
        cust = 'Customer name: ' + cust_details.loc[cust_details.short_name == value, 'customer'].item()
        db = 'DB name: ' + value
        tblset = 'TablsetId: ' + str(cust_details.loc[cust_details.short_name == value, 'tablesetID'].item())

    return (cust, db, tblset)

@app.callback(
    Output('nodes-word', 'children'),
    Output('fl-stat', 'children'),
    Output('asset-stat', 'children'),
    Output('mp-stat', 'children'),
    Output('stat-col-1', 'children'),
    Output('stat-col-2', 'children'),
    Output('stat-col-3', 'children'),
    Input('customer-selection', 'value')
)
def stat_and_issues(value):
    nodes_word = 'Nodes'
    if value == None:
        fl_stat = 'FL: -'
        asset_stat = 'Assets: -'
        mp_stat = 'MP: -'
        names_plot = html.Div([])
        dad_plot = html.Div([])
        fk_plot = html.Div([])
    else:
        filename = cust_details.loc[cust_details.short_name == value, 'datafile'].item()
        print(filename, datetime.now())
        data_db = pd.read_csv('C:/Users/krama/Documents/work/SKF/Vibration - Analyst/Scripts/Customers DB validation/' + filename)
        print('File read', datetime.now())
        #data_db = prepare_hierarchy(treelem=data_db)
        stat = db_stat(treelem = data_db)
        fls = stat['nodes_statistics']['fl_number']
        assets = stat['nodes_statistics']['assets_number']
        mps = stat['nodes_statistics']['mp_number']
        fls_dis = stat['disabled_nodes']['disabled_fl']['n'], stat['disabled_nodes']['disabled_fl']['perc']
        assets_dis = stat['disabled_nodes']['disabled_assets']['n'], stat['disabled_nodes']['disabled_assets']['perc']
        mp_dis = stat['disabled_nodes']['disabled_mp']['n'], stat['disabled_nodes']['disabled_mp']['perc']
        fl_stat = f'FL: {fls} incl. {fls_dis[0]} disabled ({fls_dis[1]}%)'
        asset_stat = f'Assets: {assets} incl. {assets_dis[0]} disabled ({assets_dis[1]}%)'
        mp_stat = f'MP: {mps} incl. {mp_dis[0]} disabled ({mp_dis[1]}%)'
        #Names plot
        names_hist = pd.DataFrame(stat['names_stat'])
        name_plot = px.bar(y = names_hist.index, 
                        x = names_hist.NAME, 
                        orientation='h', 
                        title='MP names in DB', 
                        labels = {'x': 'Number of occurencies in DB', 'y': 'MP name'}, 
                        height=20*len(names_hist))
        name_plot.update_layout(yaxis= {'categoryorder': 'total ascending'},
                                title_x = 0.5)
        names_plot = html.Div(dcc.Graph(figure = name_plot), style={'overflowY': 'scroll', 'height': 700, 'width': '100%'})
        #Dad types stat
        dad_pie_df = pd.DataFrame(stat['DAD'])
        print(dad_pie_df.dtypes)
        dad_pie = px.pie(values = dad_pie_df.DADType, 
                        names = dad_pie_df.index, 
                        title = 'DAD types distribution')
        dad_pie.update_layout(title_x = 0.5)
        dad_plot = html.Div(dcc.Graph(figure = dad_pie), style={'width': '100%'})
        #Filter Key stat
        fk_pie_df = pd.DataFrame(stat['filter_key_stat'])
        fk_pie = px.pie(values=fk_pie_df.FilterKey,
                        names = fk_pie_df.index,
                        title = 'Filter Key distribution')
        fk_pie.update_layout(title_x = 0.5)
        fk_plot = html.Div(dcc.Graph(figure = fk_pie), style = {'width': '100%'})



    return (nodes_word, fl_stat, asset_stat, mp_stat, names_plot, dad_plot, fk_plot)

@app.callback(
    Output('names-issues', 'children'),
    Input('db-data-memory', 'data')
)
def names_issues(data):
    if data is None:
        raise PreventUpdate
    else:
        db_data = pd.DataFrame(data)
        names= list(set(db_data.loc[db_data.CONTAINERTYPE == 4, 'NAME']))
        names_issues = check_names(mp_names=names)
        if len(names_issues['wrong_names']) == 0:
            return html.Div('There were no issues with the names for the customer')
        problems = define_names_problems(wrong_names = names_issues['wrong_names'])
        mask1 = (db_data.CONTAINERTYPE == 4) & (db_data.NAME.isin(names_issues['wrong_names']))
        wrong_names_table = db_data.loc[ mask1, ['TREEELEMID', 'NAME']]
        wrong_names_table.reset_index(drop = True, inplace = True)
        wrong_names_table['Possible problem'] = [problems[x][0] for x in wrong_names_table.NAME]
        wrong_names_table['Path'] = [create_path(node_id = x, treelem = db_data) for x in wrong_names_table.TREEELEMID]
        wrong_names_table['Confirm change'] = False
        wrong_names_table.rename(columns={'NAME': 'Current name'}, inplace = True)
        problems_table = dt.DataTable(
            id='names-table', 
            data = wrong_names_table.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['Current name', 'Suggested name', 'Possible problem','Path' ]],
            page_size=15,
            editable = True,
            row_selectable='multi',
            filter_action="native",
            sort_action="native",
            style_cell={
                'textAlign': 'left',
                'height': 'auto',
                'width': 'auto',
                'fontFamily': 'Calibri',
                'whiteSpace': 'normal',
                'fontSize': '14px'},
             style_header = {
                'fontWeight': 'bold',
                'fontFamily': 'Calibri',
                'fontSize': '14px'
            },
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])

    return html.Div([
        html.Br(),
        html.Div(problems_table, style = {'margin': '10px'})
    ])

@app.callback(
    Output('no-sit-fl', 'children'),
    Output('few-sit-fl', 'children'),
    Output('motor-wo-sit', 'children'),
    Output('other-w-sit', 'children'),
    Input('db-data-memory', 'data'),
    Input('sit-issues', 'value')
)
def update_sit_page(data, tab):
    print(tab)
    if (data is not None) and (tab == 'sit-contents'):
        
        data = pd.DataFrame(data)
        sit_stat = check_sit(treelem=data)['sit_issues']
        print(sit_stat)
        fl_wo_sit = data.loc[data.TREEELEMID.isin(sit_stat['missing_sit']), ['TREEELEMID']]
        fl_wo_sit['Path'] = [create_path(node_id = x, treelem = data) for x in sit_stat['missing_sit']]
        fl_wo_sit_table = dt.DataTable(
            id='fl-wo-sit-table', 
            data = fl_wo_sit.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'Path']],
            page_size=8,
            style_cell={
                'textAlign': 'left',
                'height': 'auto',
                'width': 'auto',
                'fontFamily': 'Calibri',
                'whiteSpace': 'normal',
                'fontSize': '14px'},
             style_header = {
                'fontWeight': 'bold',
                'fontFamily': 'Calibri',
                'fontSize': '14px'
            },
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        few_sit_fl = data.loc[data.TREEELEMID.isin(sit_stat['excessive_sit']), ['TREEELEMID']]
        few_sit_fl['Path'] = [create_path(node_id = x, treelem = data) for x in sit_stat['excessive_sit']]
        few_sit_fl_table = dt.DataTable(
            id='few-sit-fl-table', 
            data = few_sit_fl.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'Path']],
            page_size=8,
            style_cell={
                'textAlign': 'left',
                'height': 'auto',
                'width': 'auto',
                'fontFamily': 'Calibri',
                'whiteSpace': 'normal',
                'fontSize': '14px'},
             style_header = {
                'fontWeight': 'bold',
                'fontFamily': 'Calibri',
                'fontSize': '14px'
            },
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        motor_wo_sit = data.loc[data.TREEELEMID.isin(sit_stat['motors_wo_SIT']), ['TREEELEMID']]
        motor_wo_sit['Path'] = [create_path(node_id = x, treelem = data) for x in sit_stat['motors_wo_SIT']]
        motor_wo_sit_table = dt.DataTable(
            id='motor_wo_sit-table', 
            data = motor_wo_sit.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'Path']],
            page_size=8,
            style_cell={
                'textAlign': 'left',
                'height': 'auto',
                'width': 'auto',
                'fontFamily': 'Calibri',
                'whiteSpace': 'normal',
                'fontSize': '14px'},
             style_header = {
                'fontWeight': 'bold',
                'fontFamily': 'Calibri',
                'fontSize': '14px'
            },
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        other_w_sit = data.loc[data.TREEELEMID.isin(sit_stat['other_components_w_SIT']), ['TREEELEMID', 'FilterKey']]
        other_w_sit['Path'] = [create_path(node_id = x, treelem = data) for x in sit_stat['other_components_w_SIT']]
        other_w_sit_table = dt.DataTable(
            id='other-w-sit-table', 
            data = other_w_sit.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'Path', 'FilterKey']],
            page_size=8,
            style_cell={
                'textAlign': 'left',
                'height': 'auto',
                'width': 'auto',
                'fontFamily': 'Calibri',
                'whiteSpace': 'normal',
                'fontSize': '14px'},
             style_header = {
                'fontWeight': 'bold',
                'fontFamily': 'Calibri',
                'fontSize': '14px'
            },
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
    else:
        raise PreventUpdate

    return (html.Div([html.Br(),html.H6('FL without SIT points'), fl_wo_sit_table]),
            html.Div([html.Br(),html.H6('FL with few SIT points'), few_sit_fl_table]),
            html.Div([html.Br(),html.H6('Motor assets without SIT points'), motor_wo_sit_table]),
            html.Div([html.Br(),html.H6('SIT points in NON Motor assets'), other_w_sit_table]))


if  __name__ == '__main__':
    app.run_server(debug=True)