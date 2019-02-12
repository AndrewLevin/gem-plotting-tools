from gempython.utils.gemlogger import getGEMLogger, printYellow

import pandas as pd

dbNameDev = "INT2R" # development
dbNamePro = "cms_omds_lb" # production

connection = "oracle://CMS_GEM_APPUSER_R:GEM_Reader_2015@"

knownViews = [
        #'GEM_VFAT2_CHIP_CONF_V_RH',
        'GEM_VFAT3_CHIP_CONF_V_RH',
        'GEM_VFAT3_PROD_SUMMARY_V_RH'
        ]

def getGemDBView(view, vfatList=None, fromProd=True, debug=False):
    """
    Gets the GEM DB view defined by view for the list of vfats provided by vfatList, or
    if no vfatList is provided the full view stored in the DB.

    Returns a pandas dataframe object storing the data read from the DB

    view        - Name of View to retrieve from GEM DB 
    vfatList    - list of VFAT Chip ID's, if None the full view is retrieved
    fromProd    - If True (False) the view is taken from the Production (Development) DB
    debug       - Prints additional info if true
    """

    import os
    if view not in knownViews:
        raise Exception("View {0} not in knownViews: {1}".format(view,knownViews),os.EX_USAGE)

    # Make base query
    query='select * from CMS_GEM_MUON_VIEW.{0} data'.format(view)
    
    # Add a filter on VFAT serial number?
    if vfatList is not None:
        query += getVFATFilter(vfatList)
        pass

    # get a pandas data frame object containing the db query
    if fromProd:
        df_gemView = pd.read_sql(query, con=(connection+dbNamePro))
    else:
        df_gemView = pd.read_sql(query, con=(connection+dbNameDev))
        pass

    if debug:
        df_gemView.info()
        print("Read {0} rows from view {1}".format(df_gemView.shape[0],view))
        pass

    if vfatList is not None:
        df_gemView = joinOnVFATSerNum(vfatList,df_gemView)
        
        if len(vfatList) != df_gemView.shape[1]:
            printYellow("Length of returned view does not match length of input vfat List")
            vfatsNotFound = [ str(hex(chipId)).strip('L') for chipId in vfatList if str(hex(chipId)).strip('L') not in list(df_gemView['vfat3_ser_num'])]
            printYellow("VFATs not found: {0}".format(vfatsNotFound))
            pass
        pass

    return df_gemView

def getVFAT3CalInfo(vfatList, fromProd=True, debug=False):
    """
    Gets from GEM_VFAT3_PROD_SUMMARY_V_RH view a subset of data that is necessary
    for VFAT calibration.  Specifically a pandas dataframe will be returned with
    only the following columns:

        ['vfatN','vfat3_ser_num', 'vfat3_barcode', 'iref', 'adc0m', 'adc1m', 'adc0b', 'adc1b', 'cal_dacm', 'cal_dacb']

    vfatList    - list of VFAT Chip ID's.
    fromProd    - If True (False) the view is taken from the Production (Development) DB
    debug       - Prints additional info if true
    """

    df_vfatCalInfo = getVFAT3ProdSumView(vfatList, fromProd, debug)

    return df_vfatCalInfo[['vfatN','vfat3_ser_num', 'vfat3_barcode', 'iref', 'adc0m', 'adc1m', 'adc0b', 'adc1b', 'cal_dacm', 'cal_dacb']]

def getVFAT3ConfView(vfatList, fromProd=True, debug=False):
    """
    Gets the GEM_VFAT3_CHIP_CONF_V_RH view in the GEM DB for a list of input VFATs.

    Returns a pandas dataframe object storing the data read from the DB

    vfatList    - list of VFAT Chip ID's.
    fromProd    - If True (False) the view is taken from the Production (Development) DB
    debug       - Prints additional info if true
    """

    return getGemDBView("GEM_VFAT3_CHIP_CONF_V_RH",vfatList,fromProd,debug)

def getVFAT3ProdSumView(vfatList, fromProd=True, debug=False):
    """
    Gets the GEM_VFAT3_PROD_SUMMARY_V_RH view in the GEM DB for a list of input VFATs.

    Returns a pandas dataframe object storing the data read from the DB

    vfatList    - list of VFAT Chip ID's.
    fromProd    - If True (False) the view is taken from the Production (Development) DB
    debug       - Prints additional info if true
    """

    return getGemDBView("GEM_VFAT3_PROD_SUMMARY_V_RH",vfatList,fromProd,debug)

def getVFATFilter(vfatList):
    """
    Returns a string that can be used as a filter in an SQL query.

    vfatList - list of VFAT Chip ID's
    """

    strRetFilter = " WHERE ("
    for idx, vfatID in enumerate(vfatList):
        if idx == 0:
            strRetFilter += " data.VFAT3_SER_NUM='{0}'".format(str(hex(vfatID)).strip('L'))
        else:
            strRetFilter += " OR data.VFAT3_SER_NUM='{0}'".format(str(hex(vfatID)).strip('L'))
            pass
        pass
    strRetFilter += " )\n"

    return strRetFilter

def joinOnVFATSerNum(vfatList, dfGemView):
    """
    Creates a dataframe object from vfatList with keys 'vfat3_ser_num' and 'vfatN'.
    Then it joins this dataframe with dfGemView using the 'vfat3_ser_num'.

    vfatList - A list of vfat ChipID's ordered by vfat position (sw)
    dfGemView - A pandas dataframe containing the column name 'vfat3_ser_num'
    """

    if 'vfat_ser_num' in dfGemView.columns:
        dfVFATPos = pd.DataFrame(
                    {   'vfatN':[vfat for vfat in range(24)], 
                        'vfat_ser_num':[str(hex(id)).strip('L') for id in vfatList]}
                )

        dfGemView.join(dfVFATPos.set_index('vfat_ser_num'), on='vfat_ser_num')
    else:
        printYellow("column 'vfat_ser_num' not in input dataframe columns: {0}".format(dfGemView.columns))
        pass

    return dfGemView
