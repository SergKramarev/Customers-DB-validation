import logging
from msilib.schema import Error
import re
import pandas as pd
import numpy as np
import pyodbc

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
    log.info(f'Among {len(mp_names)} unique names, {len(good_list)} names with good patter for vibration points.')
    first_rejected = list(set(mp_names) - set(good_list))
    log.info(f'{len(first_rejected)} unique names have patetrn that are different from vibration points')
    
    # Checking for MI SIT
    regex_misit = 'M(I|A) SIT'
    r_sit = re.compile(regex_misit)
    misit_list = list(filter(r_sit.match, first_rejected))
    log.info(f'Among {len(first_rejected)} unique names, {len(misit_list)} names with paterrns MI SIT/MA SIT')
    second_rejected = list(set(first_rejected) - set(misit_list))
    log.info(f'{len(second_rejected)} unique names has pattern that are not vibrationa and not MI|A SIT')
    
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
    
    results_thresh = {'wrong_alarms': []}
    #Analysing 
    for i in range(len(tmp_df)):
        alarms = list(tmp_df.loc[i, ['DANGERLO', 'ALERTLO', 'ALERTHI', 'DANGERHI']])
        enabled = list(tmp_df.loc[i, ['ENABLEDANGERLO', 'ENABLEALERTLO', 'ENABLEALERTHI', 'ENABLEDANGERHI']])
        enabled_alarms = [x for y, x in enumerate(alarms) if enabled[y] != 0]
        good_alarms = all(enabled_alarms[i] < enabled_alarms[i+1] for i in range(len(enabled_alarms) - 1))
        if not good_alarms:
            results_thresh['wrong_alarms'].append(tmp_df.loc[i, 'TREEELEMID'])
            log.warning(f'MP with ID {tmp_df.loc[i, "TREEELEMID"]} has a wrong thresholds set.')

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
            log.warning(f'FL with ID {fl} completely disabled. All assets and mp indide it will be marked and counted as disabled.')
            treelem.loc[treelem.PARENTID == fl, 'ELEMENTENABLE'] = 0
    for asset in assets.TREEELEMID:
        if treelem.loc[treelem.TREEELEMID == asset, 'ELEMENTENABLE'].item() == 0:
            log.warning(f'Asset with ID {asset} completely disabled all mp inside will be marked and counted as disabled.')
            treelem.loc[treelem.PARENTID == asset, 'ELEMENTENABLE'] = 0

    n_dis_mp = len(treelem[(treelem.CONTAINERTYPE == 4) & (treelem.ELEMENTENABLE == 0)])
    n_dis_mp_perc = round(n_dis_mp/n_mp*100, 2)
    
    n_dis_assets = len(treelem[(treelem.CONTAINERTYPE == 3)&(treelem.ELEMENTENABLE == 0)])
    n_dis_assets_perc = round(n_dis_assets/n_assets*100, 2)
    
    mask_disfl = (treelem.TREEELEMID.isin(fl_id))&(treelem.ELEMENTENABLE == 0) 
    n_dis_fl = len(treelem[mask_disfl])
    n_dis_fl_perc = round(n_dis_fl/n_fl*100, 2)
    
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
def define_path(data):
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
                print(parent_id, element_name, element)
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

def create_connection(server = '', db = '', uid = '', pwd = ''):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    credentials = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db};UID={uid};PWD={pwd}"
    conn = None
    try:
        conn = pyodbc.connect(credentials)
    except Error as e:
        print(e)

    return conn

def get_data(conn, tablset = 1):
    #Preparation of the quesry for data fetching
    cur = conn.cursor()
    # Main query for data fetching with imputed tablsetid
    query = f""" 
    SELECT
        s.TREEELEMID,
        s.PARENTID,
        s.CONTAINERTYPE,
        s.NAME,
        s.ELEMENTENABLE, --Disabled/Enabled
        s.PARENTENABLE, --Sometimes we have all asset disabled. This will be visible here
        s.ChannelEnable,
        s.HIERARCHYTYPE,
        s.TBLSETID,
        s.BRANCHLEVEL,
        put.VALUESTRING as PointUnitType, -- Units. Should be according to names of MP
        fr.VALUESTRING as FilterEnvelope, -- Filter range for enveloped acceleration.
        psut.VALUESTRING as PointSensorUnitType, --Which sensor used. Don't know if it's necessary
        po.VALUESTRING as PointOrientation, --Orientation of the point (H,V,A,R)
        pl.VALUESTRING as PointLocation, --Location of the point
        dad.VALUESTRING as DADType, -- DAD type
        pcct.VALUESTR as FilterKey, --Filter Key 
        sa.SCALARALRMID,
        sa.ALARMMETHOD,
        sa.DANGERHI,
        sa.DANGERLO,
        sa.ALERTHI,
        sa.ALERTLO,
        sa.ENABLEALERTHI,
        sa.ENABLEALERTLO,
        sa.ENABLEDANGERHI,
        sa.ENABLEDANGERLO,
        g.PRIORITY as NodePriority
    FROM
        skfuser1.TREEELEM s
        -- add overall alarms information 
        LEFT JOIN skfuser1.SCALARALARM sa ON sa.SCALARALRMID = (SELECT ALARMID FROM skfuser1.ALARMASSIGN aa WHERE aa.ELEMENTID = s.TREEELEMID and aa.TYPE = (SELECT REGISTRATIONID FROM skfuser1.REGISTRATION as r WHERE r.SIGNATURE  = 'SKFCM_ASAT_Overall') and aa.CHANNEL = 1)
        -- add additional point settings fields
        LEFT JOIN skfuser1.POINT put ON s.CONTAINERTYPE = 4 AND put.ELEMENTID = s.TREEELEMID and put.FIELDID = (SELECT REGISTRATIONID FROM skfuser1.REGISTRATION as r WHERE r.SIGNATURE  = 'SKFCM_ASPF_Full_Scale_Unit') --point unit type. (Need full list of units that are allowed here!)
        LEFT JOIN skfuser1.POINT psut ON s.CONTAINERTYPE = 4 AND psut.ELEMENTID = s.TREEELEMID and psut.FIELDID = (SELECT REGISTRATIONID FROM skfuser1.REGISTRATION as r WHERE r.SIGNATURE  = 'SKFCM_ASPF_Sensor') --point sensor type
        LEFT JOIN skfuser1.POINT po ON s.CONTAINERTYPE = 4 AND po.ELEMENTID = s.TREEELEMID and po.FIELDID = (SELECT REGISTRATIONID FROM skfuser1.REGISTRATION as r WHERE r.SIGNATURE  = 'SKFCM_ASPF_Orientation') --point orientation
        LEFT JOIN skfuser1.POINT pl ON s.CONTAINERTYPE = 4 AND pl.ELEMENTID = s.TREEELEMID and pl.FIELDID = (SELECT REGISTRATIONID FROM skfuser1.REGISTRATION as r WHERE r.SIGNATURE  = 'SKFCM_ASPF_Location') --point location (01-99)
        LEFT JOIN skfuser1.POINT dad ON s.CONTAINERTYPE = 4 AND dad.ELEMENTID = s.TREEELEMID and dad.FIELDID = (SELECT REGISTRATIONID FROM skfuser1.REGISTRATION as r WHERE r.SIGNATURE  = 'SKFCM_ASPF_Dad_Id') --dad type (Need to do reverse engineering!)
        LEFT JOIN skfuser1.POINT fr ON s.CONTAINERTYPE = 4 AND fr.ELEMENTID = s.TREEELEMID and fr.FIELDID = (SELECT REGISTRATIONID FROM skfuser1.REGISTRATION as r WHERE r.SIGNATURE  = 'SKFCM_ASPF_Input_Filter_Range') --filter range (Value - 20599 = Filter range)
        LEFT JOIN skfuser1.GROUPTBL g ON s.TREEELEMID = g.ELEMENTID 
        -- add filter keys details
        LEFT JOIN (SELECT DISTINCT pt.ELEMENTID, ct.VALUESTR FROM skfuser1.POINTCAT pt, skfuser1.CATEGORY ct WHERE pt.CATEGORYID=ct.CATEGORYID AND ct.VALUESTR LIKE '*%') as pcct ON s.TREEELEMID = pcct.ELEMENTID  --Filter Key
    WHERE
        s.TBLSETID = {tablset}
        AND s.HIERARCHYTYPE = 1 -- only standard hierarchy node, no route nodes
        AND s.PARENTID != 2147000000 -- deleted/invalid nodes have this id
    """
    #Executing the query and closing the connection
    try:
        data = pd.read_sql(query,conn)
    except:
        data = None
    conn.close()
    return data