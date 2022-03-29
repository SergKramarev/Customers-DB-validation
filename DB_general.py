import os
import numpy as np
import pandas as pd
import sys
import plotly.express as px
import logging
import json_log_formatter
import dash
import uuid
from numba import jit
from dash import no_update, dcc, html
from dash import dash_table as dt
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from DB_validation import *

# The best option will be to feed list of unique values to this function
def check_names(mp_names = [], logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    #Validation of input
    if not isinstance(mp_names, list):
        log.error(f'Check names recieved wrong data structure. Accepted structure: list')
        return None
    
    # Checking for regular vibration points
    regex_vibr = '^((MA)|(MI)|(ME)|(OS)|(TO)|(DV)|(OI))?( |^)\d{2}(A|H|V|R)(A|T|V|S|B|P|G|D|(E1)|(E2)|(E3)|(E4)) ?.*? ?((DE)|(NDE))? ?(.{1,})?$'
    r = re.compile(regex_vibr)
    good_list = list(filter(r.match, mp_names))
    log.info('Names checked for vibration patterns.', extra={'point_names': good_list})
    first_rejected = list(set(mp_names) - set(good_list))
    if len(first_rejected) > 0:
        log.warning('DB contains names with wrong naming conventions', extra= {'checked_list': mp_names, 'wrong_names': first_rejected})
    else:
        log.info('All points have names according naming conventions')
    
    # Checking for MI SIT
    regex_misit = 'M(I|A) SIT'
    r_sit = re.compile(regex_misit)
    misit_list = list(filter(r_sit.match, first_rejected))
    log.info('Names checked for SIT points patterns', extra={'point_names': misit_list})
    second_rejected = list(set(first_rejected) - set(misit_list))
    if len(second_rejected)>0:
        log.warning('DB contains SIT points', extra= {'checked_list': first_rejected, 'wrong_names': second_rejected})
    else:
        log.info('DB doesn\'t contain SIT points')
    
    #Checking for points that are 01S Manual entry REP
    regex_manentry = '[0-9]{2}S [Mm]anual [Ee]ntry'
    r_manentry = re.compile(regex_manentry)
    manentry_list = list(filter(r_manentry.match, second_rejected))
    log.info(f'Among {len(second_rejected)} unique names, {len(manentry_list)} names with paterrns Manual Entry')
    third_rejected = list(set(second_rejected) - set(manentry_list))
    log.info(f'{len(third_rejected)} unique names has pattern that are not vibrationa and not MI|A SIT and not Manual entry points')

    #Checking for speed and temperature points which don't have orientation notation
    regex_temp_speed = '[0-9]{2}(S|T)( |$)'
    r_temp_speed = re.compile(regex_temp_speed)
    temp_speed_list = list(filter(r_temp_speed.match, third_rejected))
    log.info(f'Among {len(third_rejected)} unique names, {len(temp_speed_list)} names with speed or temp pattern')
    fourth_rejected = list(set(third_rejected) - set(temp_speed_list))
    log.info(f'{len(fourth_rejected)} unique names has pattern that are not not vibrational not SIT mot Manual entry RPM and not temperature')

    #Crating a list of good names
    good_names = list(set(mp_names) - set(fourth_rejected))
    
    return {'good_names': good_names, 'wrong_names': fourth_rejected}
    
# Function for checking for problems in rejected names. Function should check for few main problems with the names
#1. Check for wrong first two letters. Wrong Device
#2. Lack or excessive digits in the begining
#3. Wrong orientation
#4. Wrong Measurement type
#5. Extra spaces between number/orientation and Measurement type? Not sure how to identify! :(
#6. Unknown problems
# The result of the function should be dictionary with identified problems

def define_names_problems(wrong_names = [],
                          logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    #Validation of input
    if not isinstance(wrong_names, list):
        log.error(f'Define problems recieved wrong data structure. Accepted structure: list')
        return None
    if len(wrong_names) == 0:
        log.warning('There is no wrong names provided. Skipping problems detection.')
        return None
    
    names_problems = {}
    log.info('Creating a dictionary for results storage.')
    for name in wrong_names:
        names_problems[name] = []
    
    #Checking for wrong two letters
    regex_device = '^(?:(?=\w{2})((MA)|(MI)|(ME)|(OS)|(TO)|(DV)|(OI)))|((?=\d)\d)'
    r_device = re.compile(regex_device)
    good_device = list(filter(r_device.match, wrong_names))
    log.info(f'{len(good_device)} have proper or no device identification in the name.')
    wrong_device = list(set(wrong_names) - set(good_device))
    
    if len(wrong_device) > 0:
        log.warning(f'{len(wrong_device)} unique names with wrong device identification.')
        for name in wrong_device:
            names_problems[name].append('Device identification')
    
    # Checking for lack or excessive numbers in name
    regex_numbers = '(^\w*)?( |^)\d{2}([a-zA-Z]| )'
    r_numbers = re.compile(regex_numbers)
    good_numbers = list(filter(r_numbers.match, wrong_names))
    log.info(f'{good_numbers} points has names with proper bearing number.')
    wrong_numbers = list(set(wrong_names) - set(good_numbers))
    
    if len(wrong_numbers) > 0:
        log.warning(f'{len(wrong_numbers)} unique names with wrong bearing number. Bearing number should have two digits.')
        for name in wrong_numbers:
            names_problems[name].append('Bearing number')
            
    # Checking for correct orientation
    regex_orient = '(^\w*)?( |^)\d*(A|H|V|R)'
    r_orient = re.compile(regex_orient)
    good_orient = list(filter(r_orient.match, wrong_names))
    log.info(f'{len(good_orient)} points has good orientation notation.')
    wrong_orient = list(set(wrong_names) - set(good_orient))
    
    if len(wrong_orient) > 0:
        log.warning(f'{len(wrong_orient)} unique names with wrong orientation notation.')
        for name in wrong_orient:
            names_problems[name].append('Orientation notation')
    
    # Checking for correct measurement type
    regex_meastype = '(^\w*)?( |^)\d*.*(A|T|V|S|B|P|G|D|(E1)|(E2)|(E3)|(E4))( |$)'
    r_meastype = re.compile(regex_meastype)
    good_meastype = list(filter(r_meastype.match, wrong_names))
    log.info(f'{len(good_meastype)} have proper measurement type notation')
    wrong_meastype = list(set(wrong_names) - set(good_meastype))
    
    if len(wrong_meastype) > 0:
        log.warning(f'{len(wrong_meastype)} unique names with wrong measurement type')
        for name in wrong_meastype:
            names_problems[name].append('Measurement type')
    
    # Unknown problems. All the points for which the problem wasn't identified 
    # to unknown problems. All the points which have more than one problem has
    # Unknown or multiple problems
    for name in names_problems:
        if len(names_problems[name]) != 1:
            log.warning(f'Point {name}  has multiple or unknon problems.')
            names_problems[name] = [f'Unidentified or multiple problems. Possible suggestions: {", ".join(names_problems[name]) }']
    
    return names_problems

#Need function for checking that names are consistent with settings
def check_names_consistency(mp_names = [],
                            mp_settings = pd.DataFrame(),
                            logger = ''):
    #Setting logger
    log = logging.getLogger(logger)

    #Validation of the input
    if not isinstance(mp_names, list):
        log.error(f'Check names consistency recieved wrong data structure for names of MP. Accepted structure: list')
        return None
    if not isinstance(mp_settings, pd.DataFrame):
        log.error(f'Check names consistency recieved wrong data structure for settings of MP. Accepted structure: pandas Data Frame')
        return None
    if len(mp_settings)  == 0:
        log.error(f'Data frame for point settings has zero rows. Cannot compare.')
        return None

def prepare_hierarchy(treelem = pd.DataFrame(),
                      logger = ''):
    
    # Setting logger
    log = logging.getLogger(logger)
    
    #Validationof the input
    if not validate_treelems(treelem, logger):
        return None
    
    #Creating path for easier identification
    levels = list(treelem.BRANCHLEVEL.unique())
    levels.sort()
    log.info(f'Creating PATH for each element of tree. Hierary in total has following unique levels: {levels}')
    treelem['PATH'] = ""
    for level in levels:
        if level == 0:
            continue
        tmp_df = treelem[(treelem.BRANCHLEVEL == level)]
        log.info(f'Creating hierarchy for {level} level. Level has {len(tmp_df)} elements. Element names are {tmp_df["NAME"]}')
        for element in tmp_df.TREEELEMID.unique():
            parent_id = treelem.loc[treelem.TREEELEMID == element, 'PARENTID'].item()
            parent_path = treelem.loc[treelem.TREEELEMID == parent_id, 'PATH'].item()
            element_name = treelem.loc[treelem.TREEELEMID == element, 'NAME'].item()
            treelem.loc[treelem.TREEELEMID == element, 'PATH'] = parent_path + "/" + element_name
    
    #Creating list of  measurement point, assets and fls
    mps = treelem.loc[treelem.CONTAINERTYPE == 4, ['NAME', 'TREEELEMID']]
    assets = treelem.loc[treelem.CONTAINERTYPE == 3, ['NAME', 'TREEELEMID']]
    fls = treelem.loc[(treelem.CONTAINERTYPE == 2) & (treelem.BRANCHLEVEL >= (max(levels) - 2)), ['NAME', 'TREEELEMID']]
    log.info(f'Hierarchy has {len(fls)} Functional locations, {len(assets)} assets and {len(mps)} measurement points')
    
    #Creating clear identification for disabled points
    for fl in fls.TREEELEMID:
        if treelem.loc[treelem.TREEELEMID == fl, 'ELEMENTENABLE'].item() == 0:
            log.warning(f'FL with ID {fl} completely disabled. All assets and mp indide it will be marked and counted as disabled.')
            dis_assets = list(treelem.loc[treelem.PARENTID == fl, 'TREEELEMID'])
            treelem.loc[treelem.TREEELEMID.isin(dis_assets), 'ELEMENTENABLE'] = 0
    for asset in assets.TREEELEMID:
        if treelem.loc[treelem.TREEELEMID == asset, 'ELEMENTENABLE'].item() == 0:
            log.warning(f'Asset with ID {asset} completely disabled all mp inside will be marked and counted as disabled.')
            treelem.loc[treelem.PARENTID == asset, 'ELEMENTENABLE'] = 0
            
    results = {'mp_names': mps, 'assets_names': assets, 'fl_names': fls, 'hierarchy_depth': max(levels), 'treeelem': treelem}
    
    return results

def check_sit(treelem = pd.DataFrame(),
              logger = ''):
    
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the imput.
    if not validate_treelems(treelem, logger):
        return None
    
    # Checking for MI SIT point in each FL if we have at least half of the FL with them
    mp_names = list(treelem.loc[treelem.CONTAINERTYPE == 4, 'NAME'])
    regex_misit = 'M(I|A) SIT'
    r_sit = re.compile(regex_misit)
    misit_list = list(filter(r_sit.match, mp_names))
    
    # Creating list of MPs for each functional location
    #List of FL
    mask_fl = (treelem.CONTAINERTYPE == 2) & (treelem.BRANCHLEVEL >= (max(treelem.BRANCHLEVEL) - 2))
    fls = treelem.loc[mask_fl, ['NAME', 'TREEELEMID']]
    mp_in_fl = {}
    for fl_id in list(fls['TREEELEMID']):
        mp_in_fl[fl_id] = []
    for fl_id in list(fls['TREEELEMID']):
        asset_ids = list(treelem.loc[treelem.PARENTID == fl_id, 'TREEELEMID'])
        for asset_id in asset_ids:
            mp = list(treelem.loc[treelem.PARENTID == asset_id, 'NAME'])
            mp_in_fl[fl_id] = mp_in_fl[fl_id] + mp
        log.info(f'FL with id {fl_id} has {len(mp_in_fl[fl_id])} measurement points with following names: {mp_in_fl[fl_id]}')
    
    # Checking the rule that if customer uses MI SIT than each maesurement location 
    # should have at least one and it should be located in Motor component! 
    log.info(f'Checking hierachy for SIT points potential problems')
    sit_problems = {'missing_sit': [], 'excessive_sit': [], 'good_sit': []}
    if len(misit_list) > len(fls)/2:
        for fl_id in mp_in_fl.keys():
            misit_in_fl = list(filter(r_sit.match, mp_in_fl[fl_id]))
            if len(misit_in_fl) == 0:
                log.warning(f'FL with ID {fl_id} has no SIT point in any asset. Need to add')
                sit_problems['missing_sit'].append(fl_id)
            if len(misit_in_fl) > 1:
                log.warning(f'FL with ID {fl_id} has more than one SIT points. Need to remove excessive points.')
                sit_problems['excessive_sit'].append(fl_id)
            if len(misit_in_fl) == 1:
                log.info(f'FL with ID {fl_id} has SIT point.')
                sit_problems['good_sit'].append(fl_id)
                
    # Checking the problem that MI SIT points should be presented in Motor component
    # list of assets:
    mask_asset = treelem.CONTAINERTYPE == 3
    assets = treelem.loc[mask_asset, ['NAME', 'TREEELEMID', 'FilterKey']]
    #Checking for assets without Filter Key Assigned
    assets_wo_filterkey = assets.loc[assets.FilterKey.isna(), ['NAME', 'TREEELEMID']]
    if len(assets_wo_filterkey) > 0:
        log.warning(f'There are {len(assets_wo_filterkey)} assets without defined filter key. The names are: {list(assets_wo_filterkey.NAME)}')
    else:
        log.info('All assets have assigned filter key.')
        
    assets_motors = assets.loc[assets.FilterKey == '*Motor', ['NAME', 'TREEELEMID', 'FilterKey']]
    assets_other = assets.loc[assets.FilterKey != '*Motor', ['NAME', 'TREEELEMID', 'FilterKey']]
    
    #Checking that all Motor Assets has MI SIT
    sit_problems['motors_wo_SIT'] = []
    sit_problems['duplicated_SIT_in_motor'] = []
    sit_problems['other_components_w_SIT'] = []
    
    if len(misit_list) > len(fls)/2:
        for motor in assets_motors.TREEELEMID:
            mp_asset = treelem.loc[treelem.PARENTID == motor, 'NAME']
            misit_in_asset = list(filter(r_sit.match, mp_asset))
            if len(misit_in_asset) == 0:
                log.warning(f'Asset with ID {motor} and filter Key Motor has no SIT point in any asset. Need to add')
                sit_problems['motors_wo_SIT'].append(motor)
            if len(misit_in_asset) > 1:
                log.warning(f'Asset with ID {motor} and Filter Key has more than one SIT points. Need to remove excessive points.')
                sit_problems['duplicated_SIT_in_motor'].append(motor)
            if len(misit_in_asset) == 1:
                log.info(f'Asset with ID {motor} and Filter Key Motor has SIT point.')
        for component in assets_other.TREEELEMID:
            mp_asset = treelem.loc[treelem.PARENTID == component, 'NAME']
            misit_in_asset = list(filter(r_sit.match, mp_asset))
            if len(misit_in_asset) == 0:
                log.info(f'Asset with ID {component} and filter key {treelem.loc[treelem.TREEELEMID == component, "FilterKey"].item()} has no MI SIT points')
            if len(misit_in_asset) >= 1:
                log.warning(f'Asset with ID {component} and Filter Key {treelem.loc[treelem.TREEELEMID == component, "FilterKey"].item()} has SIT points.')
                sit_problems['other_components_w_SIT'].append(component)

    
    return {'sit_issues': sit_problems}

def check_duplications(treelem = pd.DataFrame(), 
                       logger = ''):
    
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the imput.
    if not validate_treelems(treelem, logger):
        return None
    
    #Duplications problems
    log.info(f'Checking hierarchy for ducplicated names in the same FL')
    duplication_problems = {'dupl_in_fl': {},
                            'dupl_in_assets': {}}
    levels = list(treelem.BRANCHLEVEL.unique())
    fls_id = set(treelem.loc[treelem.CONTAINERTYPE == 3, 'PARENTID'])
    fls = treelem.loc[treelem.TREEELEMID.isin(list(fls_id)), ['NAME', 'TREEELEMID']]
    for fl_id in fls.TREEELEMID:
        mp_in_fl = []
        assets = treelem.loc[treelem.PARENTID == fl_id, 'TREEELEMID']
        for asset in assets:
            mp_in_asset = list(treelem.loc[treelem.PARENTID == asset, 'NAME'])
            mp_in_fl = mp_in_fl + mp_in_asset
            #Checking for duplications in asset
            first_in_asset = True
            for name in set(mp_in_asset):
                name_count = mp_in_asset.count(name)
                if (name_count > 1) & first_in_asset:
                    duplication_problems['dupl_in_assets'][asset] = []
                    first_in_asset = False
                
                if name_count > 1:
                    duplication_problems['dupl_in_assets'][asset].append(name)
                    log.warning(f'Asset {asset} contains points with duplicated names: List of duplicated names are: {", ".join(duplication_problems["dupl_in_assets"][asset])}')
        
        #Counting duplications for FL
        first_in_fl = True
        for name in set(mp_in_fl):
            name_count = mp_in_fl.count(name)
            if (name_count > 1) & first_in_fl:
                duplication_problems['dupl_in_fl'][fl_id] = []
                first_in_fl = False
            if name_count > 1:
                duplication_problems['dupl_in_fl'][fl_id].append(name)
                log.warning(f'FL {fl_id} contains points with duplicated names: List of duplicated names are: {", ".join(duplication_problems["dupl_in_fl"][fl_id])}')
    
    #Generating common table with issues
    resulted_table = pd.DataFrame()
    for fl_problem_id in duplication_problems['dupl_in_fl'].keys():
        tmp_row = treelem.loc[treelem.TREEELEMID == fl_problem_id, ['TREEELEMID', 'Path']]
        tmp_row['Problem'] = f'FL has points with duplicated names: {duplication_problems["dupl_in_fl"][fl_problem_id]}'
        resulted_table = pd.concat([resulted_table, tmp_row])
    for asset_problem_id in duplication_problems['dupl_in_assets'].keys():
        tmp_row = treelem.loc[treelem.TREEELEMID == asset_problem_id, ['TREEELEMID', 'Path']]
        tmp_row['Problem'] = f'FL has points with duplicated names: {duplication_problems["dupl_in_assets"][asset_problem_id]}'
        resulted_table = pd.concat([resulted_table, tmp_row])    
    resulted_table.reset_index(drop = True, inplace = True)
    
    return resulted_table
                
def validate_treelems(tree_df = pd.DataFrame(), 
                      logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    validated = True
    if not isinstance(tree_df, pd.DataFrame):
        log.warning(f'Provided input has incorrect type. Required type: pd.DatFrame, received input: {type(tree_df)}')
        return None
    
    required_columns = ['TREEELEMID', 'PARENTID', 'CONTAINERTYPE', 'NAME', 
                        'ELEMENTENABLE', 'PARENTENABLE', 'ChannelEnable', 'HIERARCHYTYPE',
                        'TBLSETID', 'BRANCHLEVEL', 'PointUnitType', 'FilterEnvelope',
                        'PointSensorUnitType', 'PointOrientation', 'PointLocation', 'DADType',
                        'FilterKey', 'SCALARALRMID', 'ALARMMETHOD', 'DANGERHI', 'DANGERLO',
                        'ALERTHI', 'ALERTLO', 'ENABLEALERTHI', 'ENABLEALERTLO',
                        'ENABLEDANGERHI', 'ENABLEDANGERLO']
    if set(required_columns).issubset(tree_df.columns):
        log.info(f'Provided dataframe has all necessary information for the analysis: {tree_df.columns}')
    else:
        missing_columns = list(set(required_columns) - set(tree_df.columns))
        log.warning(f'Provided dataframe contains not all information needed. Check the input. Missing columns: {missing_columns}')
        validated = False
    
    if len(tree_df) == 0:
        log.warning(f'Provided dataframe is empty.')
        validated = False
    
    return validated
   
@jit(nopython = True)
def checkTh(data):
    result = []
    for i in range(data.shape[0]):
        enabled = []
        if data[i,5] != 0:
            enabled.append(data[i, 1])
        if data[i,6] != 0:
            enabled.append(data[i, 2])
        if data[i,7] != 0:
            enabled.append(data[i, 3])
        if data[i,8] != 0:
            enabled.append(data[i, 4])
        if enabled != sorted(enabled):
            result.append(data[i, 0])
    return result


def check_thresholds(treelem = pd.DataFrame(), 
                    logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    #Validationof the input
    if not validate_treelems(treelem, logger):
        return None
    
    #Creatnig list of points without thresholds
    points_wo_alarms = treelem.loc[(treelem.CONTAINERTYPE == 4) & 
                               treelem.SCALARALRMID.isna() &  
                               ~treelem.NAME.isin(['MA SIT', 'MI SIT']), ['TREEELEMID','NAME', 'Path']]

    #Checking if the thresholds are in correct sequence
    tmp_df = treelem[~treelem.SCALARALRMID.isna()]
    tmp_df.reset_index(drop = True, inplace = True)

    thresh_array = tmp_df[['TREEELEMID', 'DANGERLO',
                           'ALERTLO', 'ALERTHI', 'DANGERHI',
                           'ENABLEDANGERLO', 'ENABLEALERTLO',
                           'ENABLEALERTHI', 'ENABLEDANGERHI']]
    thresh_array.TREEELEMID = pd.to_numeric(thresh_array.TREEELEMID)
    thresh_array = np.array(thresh_array)

    wrong_th = checkTh(thresh_array)
    wrong_th = [str(x) for x in wrong_th]
    results_thresh = {'wrong_alarms': wrong_th}

    wrong_alarms = treelem.loc[treelem.TREEELEMID.isin(results_thresh['wrong_alarms']), ['TREEELEMID', 'NAME', 'Path']]   
    return {'threshold_issues': wrong_alarms,
            'points_wo_alarms': points_wo_alarms}
            
def check_location(treelem = pd.DataFrame(), 
                    logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the input
    if not validate_treelems(treelem, logger):
        return None
    
    tmp_df = treelem[(treelem.CONTAINERTYPE == 4) & (~treelem.NAME.isin(['MI SIT', 'MA SIT']))]
    tmp_df.reset_index(drop = True, inplace = True)
    #treelem['PointLocation'] = [np.NaN if pd.isnull(x) else x for x in treelem['PointLocation']]
    
    locations_name = []
    for name in tmp_df['NAME']:
        try:
            number = re.search('[0-9]{1,3}', name).group(0)
            locations_name.append(str(int(number)))
        except AttributeError:
            locations_name.append(None)
    locations_set = list(tmp_df['PointLocation'])
    for i in range(len(locations_set)):
        try: 
            locations_set[i] = str(int(locations_set[i]))
        except:
            locations_set[i] = str(locations_set[i])

    locations_set = [str(x) for x in locations_set]
    
    diff = [lset != lname for lset, lname in zip(locations_set, locations_name)]
    tmp_df['Location'] = locations_set
    results_df = tmp_df.loc[diff, ['TREEELEMID', 'NAME', 'Location', 'Path']]
    #results_df['Path'] = [create_path(node_id = x, treelem = treelem) for x in results_df.TREEELEMID]

    return results_df.to_dict()
    
def check_orientation(treelem = pd.DataFrame(),
                      logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the input
    if not validate_treelems(treelem, logger):
        return None
    
    tmp_df = treelem[(treelem.CONTAINERTYPE == 4) & (~treelem.NAME.isin(['MI SIT', 'MA SIT']))]
    tmp_df.reset_index(drop = True, inplace = True)
    #treelem['PointLocation'] = [np.NaN if pd.isnull(x) else x for x in treelem['PointLocation']]
    
    orientations_name = []
    orientation_mapping = {'H': 'Horizontal', 'V': 'Vertical', 'A': 'Axial', 'R': 'Radial'}
    for name in tmp_df['NAME']:
            try:
                orientation = re.search('(^\w{2})?( |^)[0-9]{1,3}(A|H|V|R)', name).group(0)
                orientations_name.append(orientation_mapping[orientation[-1]])
            except AttributeError:
                orientations_name.append(None)
    orientations_set = list(tmp_df['PointOrientation'])
    
    diff = [oset != oname for oset, oname in zip(orientations_set, orientations_name)]
    
    tmp_df['Orientation'] = orientations_set
    results_df = tmp_df.loc[diff, ['TREEELEMID', 'NAME', 'Orientation', 'Path']]
    #results_df['Path'] = [create_path(node_id = x, treelem = treelem) for x in results_df.TREEELEMID]

    return results_df.to_dict()
   
def db_stat(treelem = pd.DataFrame(), 
            logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the input
    if not validate_treelems(treelem, logger):
        return None
    
    #Creating statistics
    assets = treelem.loc[treelem.CONTAINERTYPE == 3, ['NAME', 'TREEELEMID', 'PARENTID', 'NodePriority']]
    fl_id = list(assets.PARENTID.unique())
    fls = treelem.loc[treelem.TREEELEMID.isin(fl_id), ['NAME', 'TREEELEMID']]
    #General statistics
    n_mp = len(treelem[treelem.CONTAINERTYPE == 4])
    n_assets = len(assets)
    n_fl = len(fls)
    
    #Disabled Statistics
    #Creating clear identification for disabled points
    for fl in fls.TREEELEMID:
        if treelem.loc[treelem.TREEELEMID == fl, 'ELEMENTENABLE'].item() == 0:
            log.warning(f'All assets inside FL will be marked and counted as disabled.', extra= {'type of node': 'FL', 'Node ID': fl, 'disability status': 'disabled'})
            treelem.loc[treelem.PARENTID == fl, 'ELEMENTENABLE'] = 0
    for asset in assets.TREEELEMID:
        if treelem.loc[treelem.TREEELEMID == asset, 'ELEMENTENABLE'].item() == 0:
            log.warning(f'All mp inside asset will be marked and counted as disabled.', extra = {'type of node': 'Asset', 'Node ID': asset, 'disability status': 'disabled'})
            treelem.loc[treelem.PARENTID == asset, 'ELEMENTENABLE'] = 0

    n_dis_mp = len(treelem[(treelem.CONTAINERTYPE == 4) & (treelem.ELEMENTENABLE == 0)])
    n_dis_mp_perc = round(n_dis_mp/n_mp*100, 2)
    
    n_dis_assets = len(treelem[(treelem.CONTAINERTYPE == 3)&(treelem.ELEMENTENABLE == 0)])
    n_dis_assets_perc = round(n_dis_assets/n_assets*100, 2)
    
    mask_disfl = (treelem.TREEELEMID.isin(fl_id))&(treelem.ELEMENTENABLE == 0) 
    n_dis_fl = len(treelem[mask_disfl])
    n_dis_fl_perc = round(n_dis_fl/n_fl*100, 2)

    if n_dis_mp > 0:
        log.info('Customer has disabled nodes', extra= {'disabled_mp': n_dis_mp, 'disabled_assets': n_dis_assets, 'disabled_fl': n_dis_fl})
    else:
        log.info('Customer doesn\'t have disabled assets')
    
    #FilterKey Statistics
    filter_key_stat = treelem.loc[treelem.CONTAINERTYPE == 3, 'FilterKey'].value_counts(dropna=False)
            
    #Names Statistics
    names = treelem.loc[treelem.CONTAINERTYPE == 4, 'NAME'].value_counts(dropna = False)
    
    #Points with Thresholds
    n_alarms = len(treelem[(treelem.CONTAINERTYPE == 4) & (~pd.isnull(treelem.SCALARALRMID))])
    mp_w_alarm_perc = round(n_alarms/n_mp*100, 2)
    points_wo_alarms = treelem.loc[(treelem.CONTAINERTYPE == 4) & (pd.isnull(treelem.SCALARALRMID)), ['TREEELEMID']]
    points_wo_alarms.set_index('TREEELEMID', inplace = True)
    

    #DAD statistics
    dad_map = {
        1960: 'Microlog Analyzer',
        887: 'Microlog Analyzer',
        1403: 'PONTO derivado',
        184: 'Manual Point', 
        792: 'Derived Point',
        1159: 'Manual Point'}
    DAD_types = treelem.loc[treelem.CONTAINERTYPE == 4, ['DADType', 'TREEELEMID']]
    DAD_types['DADType'] = [dad_map[x] if x in dad_map.keys() else x for x in DAD_types['DADType']]
    DAD_types.set_index('TREEELEMID', inplace = True)
    DAD_types = DAD_types['DADType'].value_counts(dropna = False)
    # Need to add mapping to DAD types in order to present not values but Names of the DAD

    #Priority statistics
    priorities_map = {
        0: 'Not set',
        1: 'Critical',
        2: 'High',
        3: 'Medium',
        4: 'Low',
        5: 'Lowest'
    }
    assets['NodePriority'] = [priorities_map[x] if x in priorities_map.keys() else x for x in assets['NodePriority']]
    priority = assets['NodePriority'].value_counts(dropna = False)


    fl_line = f'FL: {n_fl} incl. {n_dis_fl} ({n_dis_fl_perc}% disabled.)'
    asset_line = f'Assets: {n_assets} incl. {n_dis_assets} ({n_dis_assets_perc}% disabled.)'
    mp_line = f'MP: {n_mp} incl. {n_dis_mp} ({n_dis_mp_perc}% disabled.)'
    
    result = {'FL': fl_line,
             'assets': asset_line,
             'MP': mp_line, 
             'filter_key_stat': filter_key_stat,
             'names_stat': names,
             'alarms': {'points_w_alarms': {'n': n_alarms, 
                                            'perc': mp_w_alarm_perc},
                       'points_wo_alarms': points_wo_alarms.to_dict()},
             'DAD': DAD_types,
             'priorities': priority}
    
    return result
        
def create_path(node_id = 1, 
               treelem = pd.DataFrame(), 
               logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the input
    if not validate_treelems(treelem, logger):
        return None
    
    level = treelem.loc[treelem.TREEELEMID == node_id, 'BRANCHLEVEL'].item()
    node_name = treelem.loc[treelem.TREEELEMID == node_id, 'NAME'].item()
    path = str(node_name)
    while level > treelem.BRANCHLEVEL.min()+1:
        parent_id = treelem.loc[treelem.TREEELEMID == node_id, 'PARENTID'].item()
        parent_name = treelem.loc[treelem.TREEELEMID == parent_id, 'NAME'].item()
        level = treelem.loc[treelem.TREEELEMID == parent_id, 'BRANCHLEVEL'].item()
        node_id = parent_id
        path = parent_name + "/" + path
    return path

def check_type_enveleope(treelem = pd.DataFrame(),
                   logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
       
    # Validation of the input
    if not validate_treelems(treelem, logger):
        return None
    
    #Retrieving Points 
    points = treelem[(treelem.CONTAINERTYPE == 4) & ~treelem.NAME.isin(['MA SIT', 'MI SIT'])]
    
    units_maping = {'in/s': 'velocity',
                    'mm/s': 'velocity',
                    'g': 'acceleration',
                    'gE': 'envelope',
                    'RPM': 'speed',
                    'Hz': 'speed',
                    'F': 'temp',
                    'C': 'temp'}
    regex_types = {
        'velocity': '(^\w*)?( |^)\d*.*V( |$)',
        'temp': '(^\w*)?( |^)\d*.*T( |$)',
        'speed': '(^\w*)?( |^)\d*.*S( |$)',
        'envelope': '(^\w*)?( |^)\d*.*((E1)|(E2)|(E3)|(E4))( |$)',
        'acceleration': '(^\w*)?( |^)\d*.*A( |$)'
    }
    points['meas_type'] = [units_maping[x] if x in units_maping.keys() else 'undefined' for x in points.PointUnitType]
    types_in_treelem = list(set(points.meas_type))
    print(types_in_treelem)
    settings_prob = {'TREEELEMID': [],
                     'NAME': [],
                     'Type': [],
                     'Envelope': [],
                     'Path': []}
    for point_type in types_in_treelem:
        print(point_type)
        if point_type == 'undefined':
            continue
        point_names = points.loc[points.meas_type == point_type, ['NAME', 'TREEELEMID', 'FilterEnvelope', 'PointUnitType', 'Path']]
        regex = regex_types[point_type]
        r_point_type = re.compile(regex)
        bad_meastype = point_names[~point_names.NAME.str.contains(regex)]
        if len(bad_meastype) > 0:
            log.warning(f'Following points has discrepancies between settings and name: {[bad_meastype.TREEELEMID]}')
            settings_prob['TREEELEMID'] = settings_prob['TREEELEMID'] + list(bad_meastype.TREEELEMID)
            settings_prob['NAME'] = settings_prob['NAME'] + list(bad_meastype.NAME)
            settings_prob['Type'] = settings_prob['Type'] + list(bad_meastype.PointUnitType)
            settings_prob['Envelope'] = settings_prob['Envelope'] + len(bad_meastype.PointUnitType)*[np.NaN]
            settings_prob['Path'] = settings_prob['Path'] + list(bad_meastype.Path)
        if point_type == 'envelope':
            point_names.FilterEnvelope = ['E'+str(int(x) - 20599) if x in [20600, 20601, 20602, 20603] else 'Undefined Filter in DB' for x in point_names.FilterEnvelope]
            bad_filter = point_names[[y not in x for x,y in zip(point_names.NAME, point_names.FilterEnvelope)]]
            if len(bad_filter) > 0:
                log.warning(f'Following points has wrong envelope filter: {[bad_filter.TREEELEMID]}')
                settings_prob['TREEELEMID'] = settings_prob['TREEELEMID'] + list(bad_filter.TREEELEMID)
                settings_prob['NAME'] = settings_prob['NAME'] + list(bad_filter.NAME)
                settings_prob['Type'] = settings_prob['Type'] + len(bad_filter.FilterEnvelope)*[np.NaN]
                settings_prob['Envelope'] = settings_prob['Envelope'] + list(bad_filter.FilterEnvelope)
                settings_prob['Path'] = settings_prob['Path'] + list(bad_filter.Path)
    
    #settings_prob['Path'] = [create_path(node_id = x, treelem = treelem) for x in settings_prob['TREEELEMID']]
    
    return settings_prob

#More efficient code with numpy arrays.
# Think about creating hierarchy for max asset levels. That can help with performance issues, especially for very big customers.
# The idea is to create path for assets and for measurement points just add path to specific asset.
def define_path(data, logger = ''):
    log = logging.getLogger(logger)
    path = [[x] for x in data[:, 2]]
    levels = np.unique(data[:, 4])
    data = np.insert(data, 5, '', axis =1)
    for level in levels:
        if level == 0:
            continue
        tmp_df = data[(data[:,4] == level)]
        for element in np.unique(tmp_df[:, 0]):
            parent_id = data[data[:, 0] == element, 1]
            parent_path = data[data[:, 0] == parent_id, 5]
            element_name = data[data[:, 0] == element, 2]
            try:
                data[data[:, 0] == element, 5] = parent_path + "/" + element_name
            except:
                log.warning('unable to update path', extra={'element_name': element_name, 'element_id': element, 'parent_id': parent_id})
                pass
    data = pd.DataFrame(data)
    data.columns = ['TREEELEMID', 'PARENTID', 'NAME', 'CONTAINERTYPE', 'BRANCHLEVEL', 'Path']
    return data

def check_duplications(treelem = pd.DataFrame(), 
                       logger = ''):
    
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the imput.
    if not validate_treelems(treelem, logger):
        return None
    
    #Duplications problems
    log.info(f'Checking hierarchy for ducplicated names in the same FL')
    duplication_problems = {'dupl_in_fl': {},
                            'dupl_in_assets': {}}
    fls_id = set(treelem.loc[treelem.CONTAINERTYPE == 3, 'PARENTID'])
    fls = treelem.loc[treelem.TREEELEMID.isin(list(fls_id)), ['NAME', 'TREEELEMID']]
    for fl_id in fls.TREEELEMID:
        mp_in_fl = []
        assets = treelem.loc[treelem.PARENTID == fl_id, 'TREEELEMID']
        for asset in assets:
            mp_in_asset = list(treelem.loc[treelem.PARENTID == asset, 'NAME'])
            mp_in_fl = mp_in_fl + mp_in_asset
            #Checking for duplications in asset
            first_in_asset = True
            for name in set(mp_in_asset):
                name_count = mp_in_asset.count(name)
                if (name_count > 1) & first_in_asset:
                    duplication_problems['dupl_in_assets'][asset] = []
                    first_in_asset = False
                
                if name_count > 1:
                    duplication_problems['dupl_in_assets'][asset].append(name)
        
        #Counting duplications for FL
        first_in_fl = True
        for name in set(mp_in_fl):
            name_count = mp_in_fl.count(name)
            if (name_count > 1) & first_in_fl:
                duplication_problems['dupl_in_fl'][fl_id] = []
                first_in_fl = False
            if name_count > 1:
                duplication_problems['dupl_in_fl'][fl_id].append(name)
                log.warning(f'FL {fl_id} contains points with duplicated names: List of duplicated names are: {", ".join(duplication_problems["dupl_in_fl"][fl_id])}')
    
    #Generating common table with issues
    resulted_table = pd.DataFrame()
    for fl_problem_id in duplication_problems['dupl_in_fl'].keys():
        tmp_row = treelem.loc[treelem.TREEELEMID == fl_problem_id, ['TREEELEMID', 'Path']]
        tmp_row['Problem'] = f'FL has points with duplicated names: {duplication_problems["dupl_in_fl"][fl_problem_id]}'
        resulted_table = pd.concat([resulted_table, tmp_row])
    for asset_problem_id in duplication_problems['dupl_in_assets'].keys():
        tmp_row = treelem.loc[treelem.TREEELEMID == asset_problem_id, ['TREEELEMID', 'Path']]
        tmp_row['Problem'] = f'FL has points with duplicated names: {duplication_problems["dupl_in_assets"][asset_problem_id]}'
        resulted_table = pd.concat([resulted_table, tmp_row])    
    resulted_table.reset_index(drop = True, inplace = True)
    
    return resulted_table

def check_hierarchy(treelem = pd.DataFrame(), 
                       logger = ''):
    
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the imput.
    if not validate_treelems(treelem, logger):
        return None
    # Checking that the hierarchy has at least certain amount of layers
    wrong_hier_mask = (treelem.CONTAINERTYPE == 3) & (treelem.BRANCHLEVEL <= 1)
    df_wrong = treelem.loc[wrong_hier_mask, ['TREEELEMID', 'Path']]
    df_wrong['Problem'] = 'Too short hierarchy'
    
    return df_wrong

def check_sequence(treelem = pd.DataFrame(), 
                       logger = ''):
    
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the imput.
    if not validate_treelems(treelem, logger):
        return None
    
    fls_id = set(treelem.loc[treelem.CONTAINERTYPE == 3, 'PARENTID'])
    #Check if we have wrong hierarchy than we can have fl_id which is the same as hierarchy ID
    if treelem.loc[treelem.BRANCHLEVEL == 0, 'TREEELEMID'].item() in list(fls_id):
        fls_id.remove(treelem.loc[treelem.BRANCHLEVEL == 0, 'TREEELEMID'].item())
    fls = treelem.loc[treelem.TREEELEMID.isin(list(fls_id)), ['NAME', 'TREEELEMID']]
    mp_in_fl = {}
    for fl_id in list(fls['TREEELEMID']):
        mp_in_fl[fl_id] = []
        asset_ids = list(treelem.loc[treelem.PARENTID == fl_id, 'TREEELEMID'])
        for asset_id in asset_ids:
            mp_names = list(treelem.loc[(treelem.PARENTID == asset_id) & (treelem.CONTAINERTYPE == 4), 'NAME'])
            mp_in_fl[fl_id] = mp_in_fl[fl_id] + mp_names
        log.info(f'FL with id {fl_id} has {len(mp_in_fl[fl_id])} measurement points with following names: {mp_in_fl[fl_id]}')
    
    
    sequence_problems = {}        
    for fl_id in mp_in_fl.keys():
        sequence_in_fl = []
        for name in set(mp_in_fl[fl_id]):
            try:
                number = re.search('^((MA)|(MI)|(ME)|(OS)|(TO)|(DV)|(OI))?( |^)[0-9]{1,3}', name).group(0)
                number = re.search('[0-9]{1,3}', number).group(0)
                if int(number) > 99:
                    pass
                else:
                    sequence_in_fl.append(number)
            except AttributeError:
                pass
        sequence_in_fl = list(set(sequence_in_fl))
        sequence_in_fl = [int(x) for x in sequence_in_fl]
        if len(sequence_in_fl) > 0:
            meas_location_count = max(sequence_in_fl)
            meas_location_theory = set(range(1, int(meas_location_count) + 1))
            missing_meas_location = list(set(meas_location_theory) - set(sequence_in_fl))
        else:
            missing_meas_location = []
        if len(missing_meas_location) > 0:
            log.warning(f'We have a missing measurement location in the FL {fl_id}. Missing measurement locations are: {missing_meas_location}')
            sequence_problems[fl_id] = missing_meas_location
    
    resulted_table = pd.DataFrame()
    for id_wrong_seq in sequence_problems.keys():
        df_wrong = treelem.loc[treelem.TREEELEMID == id_wrong_seq, ['TREEELEMID', 'Path']]
        df_wrong['Problem'] = f'Locations {", ".join([str(x) for x in sequence_problems[id_wrong_seq]])} is/are missing in FL' 
        resulted_table = pd.concat([resulted_table, df_wrong])
    resulted_table.reset_index(drop = True, inplace = True)
    return resulted_table

def check_motors(treelem = pd.DataFrame(), 
                       logger = ''):
    
    # Setting logger
    log = logging.getLogger(logger)
    
    # Validation of the imput.
    if not validate_treelems(treelem, logger):
        return None
    motors_mask = (treelem.CONTAINERTYPE == 3) & (treelem.FilterKey.isin(['*Motor']))
    motors = treelem.loc[motors_mask, ['TREEELEMID', 'Path']]
    seq_in_motor = []
    resulted_table = pd.DataFrame()
    for motor_id in motors.TREEELEMID:
        motors_mps = treelem.loc[treelem.PARENTID == motor_id, ['TREEELEMID', 'NAME']]
        for name in set(motors_mps['NAME']):
            try:
                number = re.search('[1-9]{1,3}', name).group(0)
                seq_in_motor.append(number)
            except AttributeError:
                pass
        seq_in_motor = [int(x) for x in seq_in_motor]
        seq_in_motor = list(set(seq_in_motor))
        print(seq_in_motor)
        if len(seq_in_motor) != 0:
            if max(seq_in_motor) > 2:
                df_wrong = motors[motors.TREEELEMID == motor_id]
                wrong_ml = [set(seq_in_motor) - set([1,2])]
                wrong_ml = [str(x) for x in wrong_ml]
                df_wrong['Problem'] = f'Motor has more than 2 locations for MP(s): {", ".join(wrong_ml)}'                        
                resulted_table = pd.concat([resulted_table, df_wrong])
            if max(seq_in_motor) == 1:
                df_wrong = motors[motors.TREEELEMID == motor_id]
                df_wrong['Problem'] = f'Motor has less than 2 measurement locations'                        
                resulted_table = pd.concat([resulted_table, df_wrong])
        else:
            df_wrong = motors[motors.TREEELEMID == motor_id]
            df_wrong['Problem'] = f'Motor has no measurement locations or impossible to detect locations based on names'                        
            resulted_table = pd.concat([resulted_table, df_wrong])
                                               
    return resulted_table

def suggest_name(name = '', logger = ''):
    # Setting logger
    log = logging.getLogger(logger)

    #Check if we have manual entry RPM/Hz points
    reg_MERPM = re.compile('^manual {1,}entry {1,}\(?((rpm)|(hz))\)?', re.IGNORECASE)
    reg_motor = re.compile('motor', re.IGNORECASE)
    suggest_name = np.NaN
    if reg_MERPM.search(name):
        #Need to understand if we have Hz or RPM
        regRPM = re.compile('rpm', re.IGNORECASE)
        regHZ = re.compile('hz', re.IGNORECASE)
        if regRPM.search(name):
            suggested_name = '01S Manual Entry RPM'
        if regHZ.search(name):
            suggested_name = '01S Manual Entry Hz'
        return suggested_name

    #Device identification
    try:
        device = re.search('^\w{2} ', name).group(0)
        device = device.strip()
    except AttributeError:
        device = ''
    #Checking that device is correct, according to list
    if (device == '') or (device in ['MA', 'MI', 'ME', 'OS', 'TO', 'DV', 'OI']):
        pass
    else:
        #Check for mostly used device in the customer. Suggest this device.
        device = ''
        #If there is no inforamtion about mostly used devices suggest fist with smallest Levenstein distance
        
        
    # Checking nuber
    try:
        location = int(re.search('[0-9]{1,3}', name).group(0))
    except AttributeError:
        location = np.NaN
    
    if ~pd.isna(location):
        if location <= 99:
            location = format(location, '02d')
        else: location = np.NaN
    
    #Checking orientation
    try:
        orientation = re.search('( |^)[0-9]{1,3} ?(A|H|V|R)', name).group(0)
        orientation = orientation[-1]
    except AttributeError:
        orientation = ''
    
    #Checking type of measurements
    try:
        m_type = re.search('(^\w*)?( |^)\d*(A|H|V|R)(A|T|V|S|B|P|G|D|(E1)|(E2)|(E3)|(E4))', name).group(0)
        m_type = m_type.split(' ')[-1]
        m_type = re.search('(A|T|V|S|B|P|G|D|(E1)|(E2)|(E3)|(E4))$', m_type).group(0)
    except AttributeError:
        m_type = ''
    
    # Checking DE NDE
    try:
        de_nde = re.search('(DE)|(NDE)', name).group(0)
    except AttributeError:
        de_nde = '' 
    #Checking if we have obligatory parameters
    if ~pd.isna(location) and (orientation != '') and (m_type != ''):
        suggested_name = str(device) + ' ' + str(location) + str(orientation) + str(m_type) + ' ' + de_nde
        suggested_name = suggested_name.strip()
    else:
        suggested_name = np.NaN

    #Now it's obligatory to check if the proposed name is according to the settings of the point
    
    return suggested_name

def suggest_settings(resulted_table = pd.DataFrame(),
                    logger = ''):
    # Setting logger
    log = logging.getLogger(logger)
    
    #Case for points Manual Entry RPM

    #Case for regular points
    regex = {'Location': '[0-9]{1,3}',
            'Orientation': '( |^)[0-9]{2}(A|H|V|R)',
            'Envelope': '(^\w*)?( |^)[0-9]{2}(A|H|V|R)((E1)|(E2)|(E3)|(E4))'}

    orientation_mapping = {
        'H': 'Horizontal',
        'V': 'Vertical',
        'A': 'Axial',
        'R': 'Radial'
    }
    
    settings_columns = ['Location', 'Orientation', 'Envelope']
    for setting in settings_columns:
        resulted_table[setting + "_sgst"] = None
        resulted_list= []
        reg = regex[setting]
        for point_name in resulted_table.loc[~resulted_table[setting].isna(), 'NAME']:

            try:
                point_name = re.search(reg, point_name).group(0)
                if setting == 'Location':
                    point_name = int(point_name)
                if setting == 'Orientation':
                    point_name = point_name[-1]
                    #Changing short notation from Bearing name to long word in settings
                    point_name = orientation_mapping[point_name] if point_name in orientation_mapping.keys() else point_name
                if (setting =='Orientation') & ('01S Manual' in str(point_name)):
                    point_name = None
                if setting == 'Envelope':
                    point_name = point_name[-2:]
                resulted_list.append(point_name)
            except AttributeError:
                resulted_list.append(None)
                
        resulted_table.loc[~resulted_table[setting].isna(), setting + "_sgst"] = resulted_list
            
    return resulted_table

#Setting up a logger in order to be able to save logs in json 
# and transfer them to datadog
formatter = json_log_formatter.JSONFormatter()
#Specify where to store the logs
os.makedirs('C:/var/log/', exist_ok= True)
log_name = str(uuid.uuid4())
json_handler = logging.FileHandler(filename = '/var/log/'+ log_name +'.json')
json_handler.setFormatter(formatter)
#Creating the name of the logger
logger = logging.getLogger(log_name)
logger.addHandler(json_handler)
logger.setLevel(logging.INFO)

logger.warning('Here is some warning here', extra={'additional information:': 1256})

#Determination of executable path and creating path to cust_table excel file and data files
path_dir = os.path.dirname(os.__file__)
path_dir = path_dir.replace(os.sep, '/')
path_dir = 'C:/Users/krama/Documents/work/SKF/Vibration - Analyst/Scripts/Customers DB validation'
path_data = path_dir + '/data/'
# Reading excel file and creating a list of options for dropdown menu
# These lines should be modified in order to get information from SharePoint
cust_details = pd.read_excel(path_data + 'cust_details.xlsx')
options_c = []
for cust in cust_details.customer:
    label = cust_details.loc[cust_details.customer == cust, "customer"].item()
    value = cust_details.loc[cust_details.customer == cust, "short_name"].item()
    options_c.append({'label': label, 'value': value})
info_wrong_convention = """
The table presented informtion about the measurement points\nwith wrong naming conventions.\n
Names presented in the table represent only unique names.\nNumber of times wrong name appeared in the DB prsented\nin column "N occurencies".
Each column of the tabl has its own filter where it's\npossible to search for specific name/value in a column. 
"""
info_name_settings = """
The table represents measurement points where settings\nof the point don't correspond with the name of the point.\nNames presented in the table represent only unique names.\nNumber of times wrong name appeared in the DB prsented\nin column "N occurencies". If few points has same name\nbu different settings all the settings will be presented\nin current settings column.
Since Location and Orientation are the most frequent\nproblems but not the worst one toggle "Show only major\nissues" will display only points with envelope\nfilter or when the type of the point doesn't match to\nthe name of the point.
Each column of the tabl has its own filter where it's\npossible to search for specific name/value in a column.
"""


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
                                html.Div([html.H6('Points with the names which are not according to the naming conventions: '), html.Abbr(u"\U0001F6C8", title=info_wrong_convention)], style={'display': 'inline-flex'}),
                                html.Div([], id = 'names-issues')], label = 'Names Issues', value='names-tab'),
                            dcc.Tab([html.Br(), 
                                html.Div([html.H6('Points with discrepancies between names and settings'), html.Abbr(u"\U0001F6C8", title=info_name_settings)], style={'display': 'inline-flex'}),
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
            data_db = pd.read_csv(path_data + filename)
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
            stat = db_stat(treelem = data_db, logger=log_name)
        except:
            # Final words regardnig problems in stat calculation
            print('Something wrong with statistics calculation')
            raise PreventUpdate
        if stat == None:
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
            
        fl_stat = stat['FL']
        asset_stat = stat['assets']
        mp_stat = stat['MP']
        #3. Statistic plots
        #Names plot
        names_hist = pd.DataFrame(stat['names_stat'])
        name_plot = px.bar(y = names_hist.index, 
                        x = names_hist.NAME, 
                        orientation='h',  
                        labels = {'x': 'Number of MP\'s name occurencies in DB', 'y': 'Name of MP in DB'}, 
                        height=20*len(names_hist))
        name_plot.update_layout(yaxis= {'categoryorder': 'total ascending'},
                                xaxis = {'side': 'top', 'mirror': 'allticks'})
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
        #Here we need to try to define path. It can be unsuccessfull for many reasons
        try:
            pathdf = define_path(for_path)
        except Exception as e:
            print(e)
            pathdf = pd.DataFrame(columns= ['TREEELEMID', 'Path'])
        db_data = pd.merge(db_data, pathdf[['TREEELEMID', 'Path']], how = 'left', on = 'TREEELEMID')
        for asset in db_data.loc[db_data.CONTAINERTYPE == 3, 'TREEELEMID']:
            db_data.loc[db_data.PARENTID == asset, 'Path'] = db_data.loc[db_data.TREEELEMID == asset, 'Path'].item()
        db_data.loc[db_data.CONTAINERTYPE == 4,'Path'] = db_data.loc[db_data.CONTAINERTYPE == 4,'Path'] + '/' + db_data.loc[db_data.CONTAINERTYPE == 4,'NAME']

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
        names_issues = check_names(mp_names=names, logger=log_name)
        if len(names_issues['wrong_names']) == 0:
            names_table = html.Div('There were no issues with the names for the customer')
        else:
            problems = define_names_problems(wrong_names = names_issues['wrong_names'], logger=log_name)
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
                    loc_uniq = [str(x) for x in loc_uniq]
                    loc_uniq = ', '.join(loc_uniq)
                else:
                    loc_uniq = loc_uniq[0]
                asset_uniq = list(tmp_df['AssetType'].unique())
                if len(asset_uniq) > 1:
                    asset_uniq = [str(x) for x in asset_uniq]
                    asset_uniq = ', '.join(asset_uniq)
                else:
                    asset_uniq = asset_uniq[0]
                orient_uniq = tmp_df['PointOrientation'].unique()
                if len(orient_uniq) > 1:
                    orient_uniq = [str(x) for x in orient_uniq]
                    orient_uniq = ', '.join(orient_uniq)
                else:
                    orient_uniq = orient_uniq[0]
                unit_uniq = tmp_df['PointUnitType'].unique()
                if len(unit_uniq) > 1:
                    unit_uniq = [str(x) for x in unit_uniq]
                    unit_uniq = ', '.join(unit_uniq)
                else:
                    unit_uniq = unit_uniq[0]
                env_uniq = tmp_df['FilterEnvelope'].unique()
                if len(env_uniq) > 1:
                    env_uniq = [str(x) for x in env_uniq]
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
        #try:
        location = pd.DataFrame(check_location(treelem=points_w_good_names))
        orientation = pd.DataFrame(check_orientation(treelem=points_w_good_names))
        type = pd.DataFrame(check_type_enveleope(treelem=points_w_good_names))
        resulted = pd.merge(location, orientation, on = ['TREEELEMID', 'NAME', 'Path'], how  = 'outer')
        resulted = pd.merge(resulted, type, on = ['TREEELEMID', 'NAME', 'Path'], how  = 'outer')
        resulted = suggest_settings(resulted)
        #except Exception as e:
        #    print(e)
        #    resulted = pd.DataFrame(columns=['NAME', 'Location', 'Orientation', 'Type', 'Envelope',
        #    'Location_sgst', 'Orientation_sgst', 'Envelope_sgst', 'Path'])

        
        # Counting unique problems
        gen_df1 = pd.DataFrame()
        for unique_name in resulted['NAME'].unique():
            tmp_df1 = resulted[resulted['NAME'] == unique_name]
            tmp_df1.reset_index(inplace = True, drop = True)
            counter = len(tmp_df1)
            loc_uniq = list(tmp_df1['Location'].unique())
            if len(loc_uniq) > 1:
                loc_uniq = [str(x) for x in loc_uniq]
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
                unit_uniq = [str(x) for x in unit_uniq]
                unit_uniq = ', '.join(unit_uniq)
            else:
                unit_uniq = unit_uniq[0]
            env_uniq = tmp_df1['Envelope'].unique()
            if len(env_uniq) > 1:
                env_uniq = [str(x) for x in env_uniq]
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
            table_data = table_data[~table_data.Type.isna() + ~table_data.Envelope.isna()]
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


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8080, debug=False, use_reloader=False)