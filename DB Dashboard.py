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
                            dcc.Tab([html.Br(), 
                                html.H6('Points with discrepancies between names and settings'),
                                dbc.Checklist(
                                     options=[
                                            {"label": "Show only major issues", "value": 1}
                                        ],
                                        value=[1],
                                    id="switches-input",
                                    switch=True,
                                ), 
                                html.Div(id = 'names-settings-res')], 
                                    label = 'Names/Settings discrepancies', id='names-settings', value='settings-tab'),
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
            data_db = pd.read_csv('C:/Users/krama/Documents/work/SKF/Vibration - Analyst/Scripts/Customers DB validation/data/' + filename)
        except:
            #Need to have some wrror messages here, but only prevent update for now
            cust = 'Customer name: Unable to get the data for customer'
            db = 'DB name: Unable to get the data for customer'
            tblset = 'TablsetId: Unable to get the data for customer'
            fl_stat = '-'
            asset_stat = '-'
            mp_stat = '-'
            names_plot = html.Div('No data to display')
            dad_plot = html.Div()
            fk_plot = html.Div()
            data_db = None
            return data_db, cust, db, tblset, nodes_word, fl_stat, asset_stat, mp_stat, names_plot, dad_plot, fk_plot

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

@app.callback(
    #0.Names issues
    Output('names-issues', 'children'),
    #1. Names-settings_discrepancies
    #Output('names-settings-res', 'children'),
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
    Output('issues_memory', 'data'),
    Input('db-data-memory', 'data')
    #manager=long_callback_manager
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
        db_data.loc[db_data.CONTAINERTYPE == 4,'Path'] = db_data.loc[db_data.CONTAINERTYPE == 4,'Path'] + '/' + db_data.loc[db_data.CONTAINERTYPE == 4,'NAME']
        print('Path Defined')

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

        # Defining names problems
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
            # Table in dashboard should represent unique names in hierarchy, not all points
            #? groupby?

            gen_df = pd.DataFrame()
            for unique_name in wrong_names_table['Current name'].unique():
                tmp_df = wrong_names_table[wrong_names_table['Current name'] == unique_name]
                tmp_df.reset_index(inplace = True, drop = True)
                counter = len(tmp_df)
                sugg_name = list(tmp_df['Suggested name'].unique())[0]
                problem_uniq = list(tmp_df['Possible problem'].unique())[0]
                loc_uniq = list(tmp_df['PointLocation'].unique())
                if len(loc_uniq) > 1:
                    loc_uniq = ', '.join(loc_uniq)
                else:
                    loc_uniq = loc_uniq[0]
                asset_uniq = list(tmp_df['AssetType'].unique())
                if len(asset_uniq) > 1:
                    asset_uniq = ', '.join(asset_uniq)
                else:
                    asset_uniq = asset_uniq[0]
                orient_uniq = tmp_df['PointOrientation'].unique()
                if len(orient_uniq) > 1:
                    orient_uniq = ', '.join(orient_uniq)
                else:
                    orient_uniq = orient_uniq[0]
                unit_uniq = tmp_df['PointUnitType'].unique()
                if len(unit_uniq) > 1:
                    unit_uniq = ', '.join(unit_uniq)
                else:
                    unit_uniq = unit_uniq[0]
                env_uniq = tmp_df['FilterEnvelope'].unique()
                if len(env_uniq) > 1:
                    env_uniq = ', '.join(env_uniq)
                else:
                    env_uniq = env_uniq[0]
                path_example = tmp_df.loc[0, 'Path']
                res_tmp = pd.DataFrame({
                    'N occurencies': counter,
                    'Current name': unique_name,
                    'Suggested name': sugg_name,
                    'PointLocation': loc_uniq,
                    'PointOrientation': orient_uniq,
                    'PointUnitType': unit_uniq,
                    'Envelope': env_uniq,
                    'Possible problem': problem_uniq,
                    'AssetType': asset_uniq,
                    'Path': path_example
                }, index = [0])
                gen_df = pd.concat([gen_df, res_tmp])
            
            gen_df.sort_values('N occurencies', ascending= False, inplace = True)
            gen_df.reset_index(drop = True, inplace = True)

            # Here need to add confirmation that suggested name according to settings of the 
            # unit and envelope filter if exist. Location and orientation will not be 

        #Table here should be similar to the table in names/settings discrepancies.
            names_table = dt.DataTable(
                id='names-table', 
                data = gen_df.to_dict('records'),
                columns = [
                    {"name": ["", "N occurencies"], "id": "N occurencies"},
                    {"name": ["NAME", "Current"], "id": "Current name"},
                    {"name": ["NAME", "Suggested"], "id": "Suggested name"},
                    {"name": ["Current settings", "Location"], "id": "PointLocation"},
                    {"name": ["Current settings", "Orientation"], "id": "PointOrientation"},
                    {"name": ["Current settings", "Unit"], "id": "PointUnitType"},
                    {"name": ["Current settings", "Envelope"], "id": "Envelope"},
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
        # Counting unique problems
        gen_df1 = pd.DataFrame()
        for unique_name in resulted['NAME'].unique():
            tmp_df1 = resulted[resulted['NAME'] == unique_name]
            tmp_df1.reset_index(inplace = True, drop = True)
            counter = len(tmp_df1)
            loc_uniq = list(tmp_df1['Location'].unique())
            if len(loc_uniq) > 1:
                loc_uniq = ', '.join(loc_uniq)
            else:
                loc_uniq = loc_uniq[0]
            orient_uniq = tmp_df1['Orientation'].unique()
            if len(orient_uniq) > 1:
                orient_uniq = [str(x) for x in orient_uniq]
                orient_uniq = ', '.join(orient_uniq)
            else:
                orient_uniq = orient_uniq[0]
            unit_uniq = tmp_df1['Type'].unique()
            if len(unit_uniq) > 1:
                unit_uniq = ', '.join(unit_uniq)
            else:
                unit_uniq = unit_uniq[0]
            env_uniq = tmp_df1['Envelope'].unique()
            if len(env_uniq) > 1:
                env_uniq = ', '.join(env_uniq)
            else:
                env_uniq = env_uniq[0]
            
            loc_sgst = list(tmp_df1['Location_sgst'])[0]
            orient_sgst = list(tmp_df1['Orientation_sgst'])[0]
            #unit_sgst = list(tmp_df1['Type_sgst'])
            #if len(unit_sgst) == 0:
            #    unit_sgst = None
            #else:
            #    unit_sgst = unit_sgst[0]
            env_sgst = list(tmp_df1['Envelope_sgst'])
            if len(env_sgst) == 0:
                env_sgst = None
            else:
                env_sgst = env_sgst[0]

   
            path_example = tmp_df1.loc[0, 'Path']
            res_tmp = pd.DataFrame({
                'N occurencies': counter,
                'NAME': unique_name,
                'Location': loc_uniq,
                'Orientation': orient_uniq,
                'Type': unit_uniq,
                'Envelope': env_uniq,
                'Location_sgst': loc_sgst,
                'Orientation_sgst': orient_sgst,
                #'Type_sgst': unit_sgst,
                'Envelope_sgst': env_sgst,
                'Path': path_example
            }, index = [0])
            gen_df1 = pd.concat([gen_df1, res_tmp])
            
        gen_df1.sort_values('N occurencies', ascending= False, inplace = True)
        gen_df1.reset_index(drop = True, inplace = True)

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
            id='no-thresholds-table', 
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

    return (names_table, hierarhy_table, thresholds_table, fl_wo_sit_table, few_sit_fl_table, motor_wo_sit_table, other_w_sit_table, disabled_table, gen_df1.to_dict()) #settings_table,

@app.callback(
    Output('names-settings-res', 'children'),
    Input('issues_memory', 'data'),
    Input('switches-input', 'value')
)
def filter_table(table_data, switcher):
    if table_data is None:
        return no_update
    else:
        table_data = pd.DataFrame(table_data)
        if len(switcher) == 1:
            table_data = table_data[~table_data.Type.isna() & ~table_data.Envelope.isna()]
        print(len(switcher) == 1)
        settings_table =  dt.DataTable(
            id='settings-table', 
            data = table_data.to_dict('records'),
            columns = [
                {"name": ["", "N occurencies"], "id": "N occurencies"},
                {"name": ["", "NAME"], "id": "NAME"},
                {"name": ["Current settings", "Location"], "id": "Location"},
                {"name": ["Current settings", "Orientation"], "id": "Orientation"},
                {"name": ["Current settings", "Unit"], "id": "Type"},
                {"name": ["Current settings", "Envelope"], "id": "Envelope"},
                {"name": ["Suggested settings", "Location"], "id": "Location_sgst"},
                {"name": ["Suggested settings", "Orientation"], "id": "Orientation_sgst"},
                {"name": ["Suggested settings", "Unit"], "id": "Type_sgst"},
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
        settings_table = html.Div(settings_table)
        return settings_table


if  __name__ == '__main__':
    app.run_server(debug=True)