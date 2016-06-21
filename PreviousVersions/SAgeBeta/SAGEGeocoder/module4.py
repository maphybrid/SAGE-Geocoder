#-------------------------------------------------------------------------------
# Name:         Super-Accurate Geocoding Engine (SAGE)
# Purpose:     Multi-Stage batch geocoder encorporating Google, Yahoo, and ArcGIS.
#
# Author:       Andrew G. Tangeman
#
# Created:     29/06/2013
# Copyright:   (c) Home 2013
#-------------------------------------------------------------------------------


import arcpy, geopy, math, os, ast
from geopy import geocoders

#-------------------------------------------------------------------------------
##================= FUNCTIONS ==================================================
#-------------------------------------------------------------------------------

def Messages(index): # Prints messages in order based on list indexing of messages.
    messageList=["Initializing...", "Setting Environments", "Geocoding","Creating Table",\
    "Creating Geodatabase","Creating Feature Dataset", "Creating Feature",\
    "Geocoding Complete Please See Source Folder"] #List of specific messages in chronological order
    try:
        if (index >= 0): # Prints messages from messageList in chronological order using incremental object and indexing.
            arcpy.AddMessage(messageList[index]+"\n") # See application code below functions for incremental (count) object.

        elif (index < 0): # Overrides incremental list index value using specific index value of messageList in non-chronological order.
            arcpy.AddMessage(messageList[abs(index)]+"\n") # negative integer index values are made positive with absolute number function (abs).

    except: # Exception enables requests for success/failure messages via string operators.
        if index=="s":
            arcpy.AddMessage("Operation Success \n")
        else:
            arcpy.AddMessage("Message Function Failure\n")

def GeodataSetup(Projection,Workspace): #Spatial Reference Setting
    arcpy.CreateFileGDB_management(Workspace,"GeopyGeodata.gdb") #Creates file geodatabase in user-defined workspace location.
    prjFile = os.path.join(arcpy.GetInstallInfo()["InstallDir"],
                        "Coordinate Systems/Projected Coordinate Systems/State Plane/NAD 1983 (Meters)/NAD 1983 StatePlane Washington North FIPS 4601 (Meters).prj")
    spatialRef = arcpy.SpatialReference(prjFile)
    FD=arcpy.CreateFeatureDataset_management(Workspace+"\\GeopyGeodata.gdb", "GeopyFeatureData",spatialRef) #Creates feature dataset for point features.


def TableExtract(SourceTable, Workspace,ID):
    if ID==0:
        arcpy.TableToTable_conversion(SourceTable, Workspace, "Addresses.dbf", None)
        Dbase = Workspace+"\\Addresses.dbf"
        AddressCheck(Dbase,Workspace)
        arcpy.AddField_management(Dbase,"AddressAll","TEXT")
        expression = '[Address] & ", " & [City] & ", " & [State] & ", " & [Zip]'
        arcpy.CalculateField_management(Dbase,"AddressAll", expression, "VB")
    else:
        Dbase = SourceTable
    AddressList = []
    with arcpy.da.SearchCursor(Dbase, "AddressAll") as cursor:
        for row in cursor:
            for i in row:
                AddressList.append(str(i))
            del row
        del cursor
    lst = arcpy.ListFields(Workspace+"\\Addresses.dbf")
    try:
        arcpy.AddField_management("Addresses.dbf","FID","DOUBLE")
        rows = arcpy.UpdateCursor("Addresses.dbf")
        x=1
        for row in rows:
            row.FID_=x
            rows.updateRow(row)
            x=x+1
            del row
        del rows
    except:
        arcpy.AddMessage("Field FID Exists")
    return AddressList

def AddressCheck(table,Workspace):
    arcpy.AddField_management(table,"FieldError","TEXT")
    rows = arcpy.UpdateCursor(table)
    check=False
    for row in rows:
        if "-" in row.getValue("Address"):
            check=True
            row.FieldError = "ERROR"
            rows.updateRow(row)
        else:
            row.FieldError = "None"
            rows.updateRow(row)
        del row
    del rows
    if check==True:
        arcpy.AddMessage("Field errors found!")
    expression = arcpy.AddFieldDelimiters(table, "FieldError") + " = 'ERROR'"
    arcpy.TableToTable_conversion(table, Workspace, "Address_Errors.dbf", expression)
    rows = arcpy.UpdateCursor(table)
    for row in rows:
        if row.getValue("FieldError") == "ERROR":
            rows.deleteRow(row)
            del row
    del rows


def GeocodeCaller(callindex):
        if "GoogleV3" in callindex:
            coder = 'geo = geocoders.GoogleV3()'
            CallID = 0
            return coder, CallID
        elif "Geocoder.us" in callindex:
            coder = 'geo = geocoders.GeocoderDotUS()'
            CallID = 1
            return coder, CallID
        elif "GeoNames" in callindex:
            coder = 'geo = geocoders.MediaWiki("http://wiki.case.edu/%s")'
            CallID = 2
            return coder, CallID
        elif "MediaWiki" in callindex:
            coder = "geo = geocoders.SemanticMediaWiki('http://wiki.case.edu/%s', attributes=['Coordinates'], relations=['Located in'])"
            CallID = 3
            return coder, CallID
        elif "Semantic" in callindex:
            coder = "geo = geocoders.GeoNames()"
            CallID = 4
            return coder, CallID

def USGeocode(Workspace,AddressList,Coder,CallID,LoopCount): # Utilizes Google geopy module (imported as separate module).
    CoordList, FailList, AddressList2, FailFID = [],[],[],[]
    x,count,fails = 0,0,0
    check = False
    try:
        for i in AddressList:
            try:
                x=x+1
                exec Coder #Takes input address and returns lat/long values.
                place, gc = geo.geocode(i)
                check = True
                if check == True:
                    if gc[0] != 0:
                        AddressList2.append(i)
                        for j in gc:
                            CoordList.append(j)
                            count = count+1
                            check=False
                else:
                    FailList.append(i)
                    FailFID.append(x)
                    fails = fails+1
            except:  # Exeption allows failed geocoding objects to redirect to list for export operation.
                FailList.append(i)
                FailFID.append(x)
                fails = fails+1
                pass
    except:
        arcpy.GetMessages()
    arcpy.AddMessage("\nThe following addresses succeeded in processing: \n")
    arcpy.AddMessage(AddressList2)
    if not FailFID:
        arcpy.AddMessage("\nAll entries succeeded, no failures..\n")
        FailTable=None
    else:
        FailTable=CreateFailTable(Workspace,FailFID,FailList,CallID,LoopCount)
        arcpy.AddMessage("\nThe following " + str(fails) + " requests failed to process: \n\n"+ str(FailList))
        arcpy.AddMessage("\nList of failures (FailTable"+str(CallID)+".dbf) created in output directory: " + Workspace+"\n")
    return CoordList,FailTable

def CreateFailTable(Workspace, FailFID, FailList,callindex,LoopCount):
    row_values=zip(FailFID,FailList)
    table=arcpy.CreateTable_management(Workspace,"FailTable"+str(callindex)+".dbf")
    tabledir = Workspace+"\\FailTable"+str(callindex)+".dbf"
    arcpy.AddField_management(table,"FID","TEXT")
    arcpy.AddField_management(table,"AddressAll","TEXT")
    cursor = arcpy.da.InsertCursor(table,
                               ("FID_", "AddressAll"))
    for row in row_values:
        cursor.insertRow(row)
    if LoopCount == 0:
        DeleteRows(Workspace,FailFID)
    return tabledir
    arcpy.AddMessage("\nFail table did not complete\n")


def DeleteRows(Workspace,FailFID):
    for i in FailFID:
        rows = arcpy.UpdateCursor(Workspace + "\\Addresses.dbf")
        for row in rows:
            if row.getValue("FID_") == i:
                arcpy.AddMessage(i)
                rows.deleteRow(row)
                del row
        del rows


def AddField(AddressTable): # Parses lat/long values into new table in preparation for later join.
    Fields = ["Latitude","Longitude"]
    for var in Fields:
        arcpy.AddField_management(AddressTable,var,"DOUBLE") #Field for lat (y) and long (x) coordinates.


def UpdateField(AddressTable,CoordList): # modified from j = not j to check = true
    lat,lng = [],[]
    j = False
    for i in CoordList:
        j = not j
        if j:
            lat.append(i)
        if not j:
            lng.append(i)
    Count=int(arcpy.GetCount_management(AddressTable).getOutput(0))
    rows = arcpy.UpdateCursor(AddressTable)
    k=0
    while k < Count -1:
        for row in rows:
            row.Latitude=float(lat[k])
            row.Longitude=float(lng[k])
            rows.updateRow(row)
            del row
            k=k+1
    del rows


def CreateFeature(table, Workspace,count):
    try:
        Messages(-6)
        prjfile = r"Coordinate Systems/Geographic Coordinate Systems/Spheroid-Based/WGS 1984 Major Auxiliary Sphere.prj" #Google utilizes WGS84 as native datum
        GeocodeResult=arcpy.MakeXYEventLayer_management(table,"Longitude","Latitude","test",prjfile)
        arcpy.FeatureClassToFeatureClass_conversion(GeocodeResult,Workspace+"\\GeopyGeodata.gdb\\GeopyFeatureData","GeocodeResult"+str(count))
    except:
        arcpy.GetMessages()

##-------###########################################----------------------------
##       #             FUNCTIONS END               #
##-------###########################################----------------------------

#--------#------------APPLICATION START------------#----------------------------

#============ PARAMETERS =================##-----------------------------------------#
                                          ## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
SourceTable=arcpy.GetParameterAsText(0)   ## lOCATION OF SOURCE TABLE                #
Workspace=arcpy.GetParameterAsText(1)     ## WORKSPACE LOCATION                      #
Address1=arcpy.GetParameterAsText(2)      ## LOCATION OF ADDRESS 1 FIELD             #
City=arcpy.GetParameterAsText(3)          ## LOCATION OF CITY FIELD (OPTIONAL)       #
State=arcpy.GetParameterAsText(4)         ## LOCATION OF STATE FIELD (OPTIONAL)      #
Zip=arcpy.GetParameterAsText(5)           ## LOCATION OF ZIP (OPTIONAL)              #
CoderID=arcpy.GetParameterAsText(6)        ## BOOTLEAN CHOICE OF GEOCODER GOOGLE      #
                                          ## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#=========================================##=========================================#

####################
#   BEGIN SCRIPT   #
####################

arcpy.env.workspace = Workspace
string = str(CoderID)
CoderLst=[x.strip("'") for x in string.split(';')]
count=0
for CoderID in CoderLst:
    i=0
    arcpy.AddMessage("\n"+str(CoderID)+"\n")
    Messages(i)
    i=i+1
    Messages(i)
    i=i+1
#---environment settings--------------------------------------------------------
    if count==0:
        arcpy.ResetEnvironments()
        GeodataSetup(None,Workspace)
        Messages("s")
#---address list----------------------------------------------------------------
    addressList = TableExtract(SourceTable, Workspace,count)
#---geocoder--------------------------------------------------------------------
    Coder, CallID = GeocodeCaller(CoderID)
    arcpy.AddMessage("")
    Messages(i)
    CoordList,FailTable = USGeocode(Workspace,addressList,Coder,CallID,count)
    Messages("s")
    i=i+1
#--coordinate storage-----------------------------------------------------------
    Messages(i)
    if count == 0:
        AddressTable = Workspace + "\\Addresses.dbf"
    else:
        AddressTable = SourceTable
    AddField(AddressTable)
    check = True
    try:
        UpdateField(AddressTable,CoordList)
        arcpy.AddMessage("\nGeoprocessing operation "+str(count+1)+" successful! :D\n")
        check=True
    except:
        arcpy.AddMessage("\nGeoprocessing operation "+str(count+1)+" unsuccessful :(\n")
        check=False
    i=i+1
#--feature creation-------------------------------------------------------------
    if check==True:
        CreateFeature(AddressTable,Workspace,count)
        Messages(i)
    if FailTable is None:
        arcpy.AddMessage("\nOperation Success\n")
        sys.exit()
    else:
        SourceTable = FailTable
        count=count+1
