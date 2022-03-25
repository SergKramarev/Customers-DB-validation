import os
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import plotly.express as px
import diskcache
import dash
from dash import no_update, dcc, html
from dash import dash_table as dt
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash.long_callback import DiskcacheLongCallbackManager
from dash.long_callback import CeleryLongCallbackManager
from celery import Celery
import dash_bootstrap_components as dbc
from DB_validation import *

# Reading excel file and creating a list of options for dropdown menu
cust_details = pd.read_excel('C:/Users/krama/Documents/work/SKF/Vibration - Analyst/Scripts/Customers DB validation/cust_details.xlsx')
options_c = []
for cust in cust_details.customer:
    label = cust_details.loc[cust_details.customer == cust, "customer"].item()
    value = cust_details.loc[cust_details.customer == cust, "short_name"].item()
    options_c.append({'label': label, 'value': value})

## Diskcache
cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)
#Celery
celery_app = Celery(__name__, backend='redis://localhost:6379', broker='redis://localhost:6379')
long_callback_manager1 = CeleryLongCallbackManager(celery_app)


app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = html.Div([
    dcc.Store(id='db-data-memory', data = None),
    dcc.Store(id='issues_memory', data = None),
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
                ]), label= 'Stat', id='stat-tab', value='stat-tab'),
                dcc.Tab([
                    dcc.Tabs([
                            dcc.Tab([
                                html.Br(),
                                html.H6('Points with the names which are not according to the naming conventions:'),
                                html.Div([], id = 'names-issues')], label = 'Names Issues', value='names-tab'),
                            dcc.Tab(html.Div([]), label = 'Names/Settings discrepancies', id='names-settings', value='settings-tab'),
                            dcc.Tab(html.Div([]), label = 'Hierarchy Issues', id = 'hierarchy-issues', value='hierarchy-tab'),
                            dcc.Tab(html.Div([]), label = 'Thresholds', id = 'thresholds', value='thresholds-tab'),
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
                            ]), label = 'SIT points', id='sit-issues', value = 'sit-tab'),
                            dcc.Tab(html.Div([]), label = 'Disabled Points', id='disabled-points', value='disabled-tab')
                    ], id='tabs-issues', value='names-tab') 
                ], label= 'Issues', id='issues-tab', value='issues-tab')
            ], id='tabs-main', value = 'stat-tab')
        ])
    )
])



@app.callback(
    #0. Save data to Store component
    Output('db-data-memory', 'data'),
    #Here we need to add all statistics that are needed for the first page
    #1. Selected DB details
    Output('cust-name-text', 'children'),
    Output('db-name-text', 'children'),
    Output('tblsetid-text', 'children'),
    #2. Nodes details
    Output('nodes-word', 'children'),
    Output('fl-stat', 'children'),
    Output('asset-stat', 'children'),
    Output('mp-stat', 'children'),
    #3. Plots
    Output('stat-col-1', 'children'),
    Output('stat-col-2', 'children'),
    Output('stat-col-3', 'children'),
    Input('customer-selection', 'value')
)
def update_stat(selected_file):
    nodes_word = 'Nodes:'
    if selected_file == None:
            raise PreventUpdate
    else:
        #Need to add issue handling here
        #Instead of following lines here we can have a function which will send a request to SQL db
        try:
            filename = cust_details.loc[cust_details.short_name == selected_file, 'datafile'].item()
            data_db = pd.read_csv('C:/Users/krama/Documents/work/SKF/Vibration - Analyst/Scripts/Customers DB validation/' + filename)
        except:
            #Need to have some wrror messages here, but only prevent update for now
            print('Something with the file')
            raise PreventUpdate
        #1. Selected DB details
        cust = 'Customer name: ' + cust_details.loc[cust_details.short_name == selected_file, 'customer'].item()
        db = 'DB name: ' + selected_file
        tblset = 'TablsetId: ' + str(cust_details.loc[cust_details.short_name == selected_file, 'tablesetID'].item())
        #2. Nodes statistics
        try:
            stat = db_stat(treelem = data_db)
        except:
            print('Something wrong with statistics calculation')
            raise PreventUpdate
        fl_stat = stat['FL']
        asset_stat = stat['assets']
        mp_stat = stat['MP']
        #3. Statistic plots
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
        names_plot = html.Div(dcc.Graph(figure = name_plot, style= {'height': 20*len(names_hist)}), style={'overflowY': 'scroll', 'height': 700, 'width': '100%'})
        #Dad types stat
        dad_pie_df = pd.DataFrame(stat['DAD'])
        dad_pie = px.pie(values = dad_pie_df.DADType, 
                        names = dad_pie_df.index, 
                        title = 'DAD types distribution')
        dad_pie.update_layout(title_x = 0.5)
        #Priorities stat
        prio = pd.DataFrame(stat['priorities'])
        prio_pie = px.pie(values=prio.NodePriority,
                        names = prio.index,
                        title = 'Assets criticalities')
        prio_pie.update_layout(title_x = 0.5)

        dad_plot = html.Div([
            dcc.Graph(figure = dad_pie),
            dcc.Graph(figure = prio_pie)], style={'width': '100%'})
        #Filter Key stat
        fk_pie_df = pd.DataFrame(stat['filter_key_stat'])
        fk_pie = px.pie(values=fk_pie_df.FilterKey,
                        names = fk_pie_df.index,
                        title = 'Filter Key distribution')
        fk_pie.update_layout(title_x = 0.5)
        fk_plot = html.Div(dcc.Graph(figure = fk_pie), style = {'width': '100%'})

    return data_db.to_dict(), cust, db, tblset, nodes_word, fl_stat, asset_stat, mp_stat, names_plot, dad_plot, fk_plot

@app.long_callback(
    #0.Names issues
    Output('names-issues', 'children'),
    #1. Names-settings_discrepancies
    Output('names-settings', 'children'),
    #2. Hierarchy problems
    Output('hierarchy-issues', 'children'),
    #3. Thresholds problems
    Output('thresholds', 'children'),
    #4. SIT points
    Output('no-sit-fl', 'children'),
    Output('few-sit-fl', 'children'),
    Output('motor-wo-sit', 'children'),
    Output('other-w-sit', 'children'),
    #5. Disabled points
    Output('disabled-points', 'children'),
    Input('db-data-memory', 'data'),
    manager=long_callback_manager1
    #running = [(Output('issues-tab', 'disabled'), True, False)]
)
def update_issues(data):
    if data is None:
        return (no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update)
    else:
        db_data = pd.DataFrame(data)
        #Creation of "Path" column for easier identification
        tmp_db = db_data[db_data.CONTAINERTYPE != 4]
        for_path = np.array(tmp_db[['TREEELEMID', 'PARENTID', 'NAME', 'CONTAINERTYPE', 'BRANCHLEVEL']])
        pathdf = define_path(for_path)
        db_data = pd.merge(db_data, pathdf[['TREEELEMID', 'Path']], how = 'left', on = 'TREEELEMID')
        for asset in db_data.loc[db_data.CONTAINERTYPE == 3, 'TREEELEMID']:
            db_data.loc[db_data.PARENTID == asset, 'Path'] = db_data.loc[db_data.TREEELEMID == asset, 'Path'].item()
        db_data['Path'] = db_data['Path'] + '/' + db_data['NAME']
        print('Path Defined')
        #db_data['Path'] = pathdf['Path'].to_list()
        
        #Creating Clear identification of disabled points
        assets = db_data.loc[db_data.CONTAINERTYPE == 3, ['TREEELEMID', 'PARENTID', 'FilterKey']]
        fl_id = list(assets.PARENTID.unique())
        fls = db_data.loc[db_data.TREEELEMID.isin(fl_id), ['TREEELEMID', 'PARENTID']]
  
        #Creating clear identification for disabled points
        for fl in fls.TREEELEMID:
            if db_data.loc[db_data.TREEELEMID == fl, 'ELEMENTENABLE'].item() == 0:
                db_data.loc[db_data.PARENTID == fl, 'ELEMENTENABLE'] = 0
        for asset in assets.TREEELEMID:
            if db_data.loc[db_data.TREEELEMID == asset, 'ELEMENTENABLE'].item() == 0:
                db_data.loc[db_data.PARENTID == asset, 'ELEMENTENABLE'] = 0
        #Creating identification of Filter Key of assets for each measurement point
        db_data['AssetType'] = None
        for asset, filterkey in zip(assets.TREEELEMID, assets.FilterKey):
            db_data.loc[db_data.PARENTID == asset, 'AssetType'] = filterkey


        # Difining names problems
        names= list(set(db_data.loc[db_data.CONTAINERTYPE == 4, 'NAME']))
        names_issues = check_names(mp_names=names)
        if len(names_issues['wrong_names']) == 0:
            names_table = html.Div('There were no issues with the names for the customer')
        else:
            problems = define_names_problems(wrong_names = names_issues['wrong_names'])
            mask1 = (db_data.CONTAINERTYPE == 4) & (db_data.NAME.isin(names_issues['wrong_names']))
            wrong_names_table = db_data.loc[ mask1, ['TREEELEMID', 'NAME', 'Path', 'FilterKey', 'PointLocation', 'PointOrientation', 'PointUnitType', 'FilterEnvelope', 'AssetType']]
            wrong_names_table.FilterEnvelope = ['E'+str(int(x) - 20599) if x in [20600, 20601, 20602, 20603] else '' for x in wrong_names_table.FilterEnvelope]
            wrong_names_table.reset_index(drop = True, inplace = True)
            wrong_names_table['Possible problem'] = [problems[x][0] for x in wrong_names_table.NAME]
            wrong_names_table['Confirm change'] = False
            wrong_names_table.rename(columns={'NAME': 'Current name'}, inplace = True)
            suggested_name = []
            for wrong_name in names_issues['wrong_names']:
                suggested_name.append(suggest_name(wrong_name))
            suggestions = pd.DataFrame({
                'Current name': names_issues['wrong_names'],
                'Suggested name': suggested_name
                })
            wrong_names_table = pd.merge(wrong_names_table, suggestions, on = 'Current name', how  = 'left')
            #Filtering out points Manual Entry RPM HZ if they are located not in Motor
            try:
                mask_manual = wrong_names_table['Suggested name'].str.contains('01S Manual Entry') &  ((wrong_names_table['AssetType'].str.contains('Motor') == False) | wrong_names_table['AssetType'].isna())
                wrong_names_table.loc[mask_manual, 'Suggested name'] = np.NaN
            except:
                pass

        #Table here should be similar to the table in names/settings discrepancies.


        #Need to remove 01S Manual entry from RPM manual entry from not Motors
        #wrong_names_table.loc[wrong_names_table['Suggested name'].str.contains('01S Manual Entry') & (wrong)]

            names_table = dt.DataTable(
                id='names-table', 
                data = wrong_names_table.to_dict('records'),
                #columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID','Current name', 'Suggested name', 'Possible problem','Path' ]],
                columns = [
                    {"name": ["", "TREEELEMID"], "id": "TREEELEMID"},
                    {"name": ["NAME", "Current"], "id": "Current name"},
                    {"name": ["NAME", "Suggested"], "id": "Suggested name"},
                    {"name": ["Current settings", "Location"], "id": "PointLocation"},
                    {"name": ["Current settings", "Orientation"], "id": "PointOrientation"},
                    {"name": ["Current settings", "Type"], "id": "PointUnitType"},
                    {"name": ["Current settings", "Envelope"], "id": "FilterEnvelope"},
                    {"name": ["", "Possible problem"], "id": "Possible problem"},
                    {'name': ["", 'AssetType'], 'id': 'AssetType'},
                    {"name": ["", "Path"], "id": "Path"}
                ],
                page_size=15,
                editable = True,
                row_selectable='multi',
                filter_action="native",
                sort_action="native",
                merge_duplicate_headers=True,
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
                style_cell_conditional=[
                {'if': {'column_id': 'TREEELEMID'},
                'width': '5%'},
                {'if': {'column_id': 'Current name'},
                'width': '10%'},
                {'if': {'column_id': 'Suggested name'},
                'width': '10%'},
                {'if': {'column_id': 'PointLocation'},
                'width': '5%'},
                {'if': {'column_id': 'PointOrientation'},
                'width': '5%'},
                {'if': {'column_id': 'PointUnitType'},
                'width': '5%'},
                {'if': {'column_id': 'FilterEnvelope'},
                'width': '5%'},
                {'if': {'column_id': 'Possible problem'},
                'width': '25%'},
                {'if': {'column_id': 'AssetType'},
                'width': '5%'},
                {'if': {'column_id': 'Path'},
                'width': '25%'}
                ],
                style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'}
                ])

        problems_table = html.Div([
            html.Br(),
            html.Div(names_table, style = {'margin': '10px'})
            ])
        
        # Defining Name/Settings discrepancies
        db_data = db_data[db_data.DADType != 792]
        points_w_good_names = db_data[db_data.NAME.isin(names_issues['good_names'])]
        location = pd.DataFrame(check_location(treelem=points_w_good_names))
        orientation = pd.DataFrame(check_orientation(treelem=points_w_good_names))
        type = pd.DataFrame(check_type_enveleope(treelem=points_w_good_names))
        resulted = pd.merge(location, orientation, on = ['TREEELEMID', 'NAME', 'Path'], how  = 'outer')
        resulted = pd.merge(resulted, type, on = ['TREEELEMID', 'NAME', 'Path'], how  = 'outer')

        resulted = suggest_settings(resulted)

        settings_table =  dt.DataTable(
            id='settings-table', 
            data = resulted.to_dict('records'),
            #columns = [{'name': i, 'id': i, 'selectable': True} for i in resulted.columns],
            columns = [
                {"name": ["", "TREEELEMID"], "id": "TREEELEMID"},
                {"name": ["", "NAME"], "id": "NAME"},
                {"name": ["Current settings", "Location"], "id": "Location"},
                {"name": ["Current settings", "Orientation"], "id": "Orientation"},
                {"name": ["Current settings", "Type"], "id": "Type"},
                {"name": ["Current settings", "Envelope"], "id": "Envelope"},
                {"name": ["Suggested settings", "Location"], "id": "Location_sgst"},
                {"name": ["Suggested settings", "Orientation"], "id": "Orientation_sgst"},
                {"name": ["Suggested settings", "Type"], "id": "Type_sgst"},
                {"name": ["Suggested settings", "Envelope"], "id": "Envelope_sgst"},
                {"name": ["", "Path"], "id": "Path"},
            ],
            page_size=15,
            merge_duplicate_headers=True,
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
            style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
            {'if': {'column_id': 'NAME'},
            'width': '10%'},
             {'if': {'column_id': 'Location'},
            'width': '5%'},
            {'if': {'column_id': 'Orientation'},
            'width': '5%'},
            {'if': {'column_id': 'Type'},
            'width': '5%'},
            {'if': {'column_id': 'Envelope'},
            'width': '5%'},
             {'if': {'column_id': 'Location_sgst'},
            'width': '5%'},
            {'if': {'column_id': 'Orientation_sgst'},
            'width': '5%'},
            {'if': {'column_id': 'Type_sgst'},
            'width': '5%'},
            {'if': {'column_id': 'Envelope_sgst'},
            'width': '5%'},
            {'if': {'column_id': 'Path'},
            'width': '45%'}
            ],
             style_data_conditional = [
            {'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'}
            ]
        )
        settings_table = html.Div([html.Br(), html.H6('Points with discrepancies between names and settings'), settings_table])

        #Defining hierarchy problems
        dupl = check_duplications(treelem=db_data)
        hier = check_hierarchy(treelem=db_data)
        sequ = check_sequence(treelem=db_data)
        moto = check_motors(treelem=db_data)
        hierarchy = pd.concat([dupl, hier])
        hierarchy = pd.concat([hierarchy, sequ])
        hierarchy = pd.concat([hierarchy, moto])
        hierarhy_table =  dt.DataTable(
            id='settings-table', 
            data = hierarchy.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in hierarchy.columns],
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
            style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
            {'if': {'column_id': 'Path'},
            'width': '40%'},
             {'if': {'column_id': 'Problem'},
            'width': '55%'}
            ],
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }]
        )
        hierarhy_table = html.Div([html.Br(), html.H6('Problems with hierarchy:'),hierarhy_table])

        #Defining Thresholds problem
        thresh_issues = check_thresholds(treelem=db_data)

        no_thresholds_table = dt.DataTable(
            id='no_thresholds-table', 
            data = thresh_issues['points_wo_alarms'].to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'NAME', 'Path']],
            page_size=8,
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
            style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
            {'if': {'column_id': 'NAME'},
            'width': '40%'},
             {'if': {'column_id': 'Path'},
            'width': '55%'}
            ],
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])

        wrong_thresholds_issue = dt.DataTable(
            id='no_thresholds-table', 
            data = thresh_issues['threshold_issues'].to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'NAME', 'Path']],
            page_size=8,
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
                   style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
            {'if': {'column_id': 'NAME'},
            'width': '40%'},
             {'if': {'column_id': 'Path'},
            'width': '55%'}
            ],
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        thresholds_table = html.Div([
            html.H6('Points with no thresholds'),
            no_thresholds_table,
            html.H6('Points with wrongly set thresholds'),
            wrong_thresholds_issue
        ])
        #Defining SIT problems
        sit_stat = check_sit(treelem=db_data)['sit_issues']
        fl_wo_sit = db_data.loc[db_data.TREEELEMID.isin(sit_stat['missing_sit']), ['TREEELEMID', 'Path']]
        fl_wo_sit_table = dt.DataTable(
            id='fl-wo-sit-table', 
            data = fl_wo_sit.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'Path']],
            page_size=8,
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
            style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
             {'if': {'column_id': 'Path'},
            'width': '95%'}
            ],
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        fl_wo_sit_table = html.Div([html.Br(),html.H6('FL without SIT points'), fl_wo_sit_table])
        few_sit_fl = db_data.loc[db_data.TREEELEMID.isin(sit_stat['excessive_sit']), ['TREEELEMID', 'Path']]
        few_sit_fl_table = dt.DataTable(
            id='few-sit-fl-table', 
            data = few_sit_fl.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'Path']],
            page_size=8,
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
            style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
             {'if': {'column_id': 'Path'},
            'width': '95%'}
            ],
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        few_sit_fl_table = html.Div([html.Br(),html.H6('FL with few SIT points'), few_sit_fl_table])
        motor_wo_sit = db_data.loc[db_data.TREEELEMID.isin(sit_stat['motors_wo_SIT']), ['TREEELEMID', 'Path']]
        motor_wo_sit_table = dt.DataTable(
            id='motor_wo_sit-table', 
            data = motor_wo_sit.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'Path']],
            page_size=8,
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
            style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
             {'if': {'column_id': 'Path'},
            'width': '95%'}
            ],
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        motor_wo_sit_table = html.Div([html.Br(),html.H6('Motor assets without SIT points'), motor_wo_sit_table])
        other_w_sit = db_data.loc[db_data.TREEELEMID.isin(sit_stat['other_components_w_SIT']), ['TREEELEMID', 'FilterKey']]
        other_w_sit_table = dt.DataTable(
            id='other-w-sit-table', 
            data = other_w_sit.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'Path', 'FilterKey']],
            page_size=8,
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
            style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
             {'if': {'column_id': 'Path'},
            'width': '85%'},
            {'if': {'column_id': 'FilterKey'},
            'width': '10%'}
            ],
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        other_w_sit_table = html.Div([html.Br(),html.H6('SIT points in NON Motor assets'), other_w_sit_table])
        #Defining disabled points
        db_data['NodeType'] = 'System and higher'
        db_data.loc[db_data.CONTAINERTYPE == 3, 'NodeType'] = 'Asset'
        db_data.loc[db_data.CONTAINERTYPE == 4, 'NodeType'] = 'MP'
        db_data.loc[db_data.TREEELEMID.isin(fl_id), 'NodeType'] = 'FL'

        disabled = db_data.loc[db_data.ELEMENTENABLE == 0, ['TREEELEMID', 'NAME', 'Path', 'NodeType']]
        disabled_table = dt.DataTable(
            id='disabled-table', 
            data = disabled.to_dict('records'),
            columns = [{'name': i, 'id': i, 'selectable': True} for i in ['TREEELEMID', 'NAME','NodeType', 'Path']],
            page_size=15,
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
            style_cell_conditional=[
            {'if': {'column_id': 'TREEELEMID'},
            'width': '5%'},
            {'if': {'column_id': 'NAME'},
            'width': '20%'},
             {'if': {'column_id': 'NodeType'},
            'width': '20%'},
            {'if': {'column_id': 'Path'},
            'width': '55%'},
            ],
            style_data_conditional = [{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }])
        disabled_table = html.Div([html.Br(),html.H6('Disabled nodes'), disabled_table])

    return (names_table, settings_table, hierarhy_table, thresholds_table, fl_wo_sit_table, few_sit_fl_table, motor_wo_sit_table, other_w_sit_table, disabled_table)


if  __name__ == '__main__':
    app.run_server(debug=True)