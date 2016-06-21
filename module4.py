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
    try:
        arcpy.CreateFileGDB_management(Workspace,"GeopyGeodata.gdb") #Creates file geodatabase in user-defined workspace location.
        prjFile = os.path.join(arcpy.GetInstallInfo()["InstallDir"],
                            "Coordinate Systems/Projected Coordinate Systems/State Plane/NAD 1983 (US Feet)/NAD 1983 StatePlane Washington North FIPS 4601 (US Feet).prj")
        spatialRef = arcpy.SpatialReference(prjFile)
        FD=arcpy.CreateFeatureDataset_management(Workspace+"\\GeopyGeodata.gdb", "GeopyFeatureData", spatialRef) #Creates feature dataset for point features.
    except:
        arcpy.AddMessage("GeodataSetup Not Successful... Attempting to continue\n")
        return


def TableExtract(SourceTable, Workspace, ID, AddrField):
    AddressList = []
    if ID==0:
        arcpy.TableToTable_conversion(SourceTable, Workspace, "Addresses.dbf", None)
        Dbase = Workspace+"\\Addresses.dbf"
        AddressCheck(Dbase,Workspace, AddrField[0])
        arcpy.AddField_management(Dbase,"AddressAll","TEXT")
        if len(AddrField) == 1:
            expression = '['+AddrField[0]+']'
        elif len(AddrField) == 2:
            expression = '['+AddrField[0]+'] & "," & '+'['+AddrField[1]+']'
        elif len(AddrField) == 3:
             expression = '['+AddrField[0]+'] & "," & '+'['+AddrField[1]+'] & ", " & '+'['+AddrField[2]+']'
        elif len(AddrField) == 4:
            expression = '['+AddrField[0]+'] & "," & '+'['+AddrField[1]+'] & ", " & '+'['+AddrField[2]+'] & ", " & '+'['+AddrField[3]+']'

        arcpy.CalculateField_management(Dbase,"AddressAll", expression, "VB")
    else:
        Dbase = SourceTable
    try:
        with arcpy.da.SearchCursor(Dbase, "AddressAll") as cursor:
            for row in cursor:
                for i in row:
                    AddressList.append(str(i))
                del row
        del cursor
        lst = arcpy.ListFields(Workspace+"\\Addresses.dbf")
    except:
        pass
    try:
        arcpy.AddField_management("Addresses.dbf","FID","DOUBLE")
        arcpy.AddField_management("Addresses.dbf","Return","TEXT")
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

def AddressCheck(table,Workspace, addr):
    arcpy.AddField_management(table,"FieldError","TEXT")
    rows = arcpy.UpdateCursor(table)
    check=False
    try:
        for row in rows:
            if "-" in row.getValue(addr):
                check=True
                row.FieldError = "ERROR"
                rows.updateRow(row)
            else:
                row.FieldError = "None"
                rows.updateRow(row)
            del row
        del rows
    except:
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
        elif "Yahoo" in callindex:
            coder = geocoders.Yahoo('gnlL.tLV34HMbeXJAadqK9PFHeedqomQKyWQbC3tRQrZwwvJkVshznyn7LNH.KVp7OE5')
            CallID = 1
            return coder, CallID
        elif "Geocoder.us" in callindex:
            coder = 'geo = geocoders.GeocoderDotUS()'
            CallID = 2
            return coder, CallID
        elif "GeoNames" in callindex:
            coder = 'geo = geocoders.MediaWiki("http://wiki.case.edu/%s")'
            CallID = 3
            return coder, CallID
        elif "MediaWiki" in callindex and not "Semantic" in callindex:
            coder = "geo = geocoders.SemanticMediaWiki('http://wiki.case.edu/%s', attributes=['Coordinates'], relations=['Located in'])"
            CallID = 4
            return coder, CallID

def USGeocode(Workspace,AddressList,Coder,CallID,LoopCount, CoderName): # Utilizes Google geopy module (imported as separate module).
    CoordList, FailList, AddressList2, FailFID = [],[],[],[]
    x,count,fails = 0,0,0
    SecondTry = False
    try:
        for i in AddressList:
            arcpy.AddMessage("\nGeocoding record: "+ i + " Using "+CoderName+" Geocoder")
            try:
                x=x+1
                exec Coder #Takes input address and returns lat/long values.
                place, gc = geo.geocode(i.lstrip(' '))
                if gc[0] != 0:
                    AddressList2.append(i.lstrip(' '))
                    for j in gc:
                        CoordList.append(j)
                        count = count+1
                else:
                    FailList.append(i)
                    FailFID.append(x)
                    fails = fails+1
            except:  # Exeption allows failed geocoding objects to redirect to list for export operation.
                FailList.append(i.lstrip(' '))
                FailFID.append(x)
                fails = fails+1
                pass
    except:
        arcpy.GetMessages(3)
    arcpy.AddMessage("\nThe following " + str(count) + " addresses succeeded in processing: \n")
    arcpy.AddMessage(AddressList2)
    if not FailFID:
        arcpy.AddMessage("\nAll entries succeeded, no failures..\n")
        arcpy.AddMessage("\n\n----------------------\nError rate: 0%\n----------------------\n")
    if FailFID:
        DeleteRows(Workspace,FailFID)
        arcpy.AddMessage("\nThe following " + str(fails) + " requests failed to process: \n\n"+ str(FailList))
        SecondTry=True

    return CoordList

def DeleteRows(Workspace,FailFID):
    for i in arcpy.ListFiles("*"):
        if i == "Failures.dbf":
            arcpy.Delete_management(i)
            break
    table0= Workspace + "\\Addresses.dbf"
    for i in FailFID:
        with arcpy.da.UpdateCursor(table0, ["FID_", "Return"]) as dCursor:
            for row1 in dCursor:
                if row1[0] == i:
                    row1[1] = "ERROR"
                    dCursor.updateRow(row1)
                elif row1[1] != "ERROR":
                    row1[1] = "PASS"
                    dCursor.updateRow(row1)

    expression = arcpy.AddFieldDelimiters(table0, "Return") + " = 'ERROR'"
    arcpy.TableToTable_conversion(table0, Workspace, "Failures.dbf", expression)

    with arcpy.da.UpdateCursor(table0, ["Return"]) as dCursor2:
        for row2 in dCursor2:
            if row2[0] == "ERROR":
                dCursor2.deleteRow()


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


def CreateFeature(table, Workspace,count,FeatureName):
    try:
        arcpy.AddMessage("Creating Feature")
        prjfile = r"Coordinate Systems/Geographic Coordinate Systems/Spheroid-Based/WGS 1984 Major Auxiliary Sphere.prj" #Google utilizes WGS84 as native datum
        GeocodeResult=arcpy.MakeXYEventLayer_management(table,"Longitude","Latitude","test",prjfile)
        arcpy.FeatureClassToFeatureClass_conversion(GeocodeResult,Workspace+"\\GeopyGeodata.gdb\\GeopyFeatureData",FeatureName+str(count))
    except:
        arcpy.GetMessages()

##-------###########################################----------------------------
##       #             FUNCTIONS END               #
##-------###########################################----------------------------

#--------#------------APPLICATION START------------#----------------------------

#============ PARAMETERS =================##-----------------------------------------#

FeatName = arcpy.GetParameterAsText(0)                                         ## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
SourceTable=arcpy.GetParameterAsText(1)   ## lOCATION OF SOURCE TABLE                #
Workspace=arcpy.GetParameterAsText(2)     ## WORKSPACE LOCATION                      #
Address1=arcpy.GetParameterAsText(3)      ## LOCATION OF ADDRESS 1 FIELD             #
City=arcpy.GetParameterAsText(4)          ## LOCATION OF CITY FIELD (OPTIONAL)       #
State=arcpy.GetParameterAsText(5)         ## LOCATION OF STATE FIELD (OPTIONAL)      #
Zip=arcpy.GetParameterAsText(6)           ## LOCATION OF ZIP (OPTIONAL)              #
CoderID=arcpy.GetParameterAsText(7)        ## BOOTLEAN CHOICE OF GEOCODER GOOGLE      #
                                          ## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#=========================================##=========================================#

####################
#   BEGIN SCRIPT   #
####################

arcpy.env.workspace = Workspace
string = str(CoderID)
CoderLst=[x.strip("'") for x in string.split(';')]
count=0

DelList=["Address_Errors.dbf","Addresses.dbf","FailTable0.dbf","FailTable1.dbf",
        "FailTable2.dbf","FailTable3.dbf","FailTable4.dbf","Failures.dbf","Addresses.dbf","GeopyGeodata.gdb"]

AddrField = []

if Address1:
    AddrField.append(str(Address1))
    Address1 = False
if City:
    AddrField.append(str(City))
    City = False
if State:
    AddrField.append(str(State))
    State = False
if Zip:
    AddrField.append(str(Zip))
    Zip = False

arcpy.AddMessage(AddrField)

for CoderID in CoderLst:
    i=0
    Messages(i)
    i=i+1
    Messages(i)
    i=i+1
    if "fail" in SourceTable:
        count=1

#---environment settings--------------------------------------------------------
    if count==0:
        arcpy.ResetEnvironments()
        arcpy.env.workspace = Workspace
        for File in DelList:
            if File in arcpy.ListFiles("*"):
                arcpy.Delete_management(File)
        GeodataSetup(None,Workspace)
    Messages("s")
#---address list----------------------------------------------------------------
    addressList = TableExtract(SourceTable, Workspace,count,AddrField)
#---geocoder--------------------------------------------------------------------
    Coder, CallID = GeocodeCaller(CoderID)
    arcpy.AddMessage("")
    Messages(i)
    CoordList = USGeocode(Workspace,addressList,Coder,CallID,count, CoderID)
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
        arcpy.AddMessage("\nUpdate Field "+str(count+1)+" successful \n")
        check=True
    except:
        arcpy.AddMessage("\nUpdate Field "+str(count+1)+" unsuccessful :(\n")
        check=False
    i=i+1
#--feature creation-------------------------------------------------------------
    if check==True:
        CreateFeature(AddressTable,Workspace,count,FeatName)
        Messages(i)
    Success = True
    for i in arcpy.ListFiles("*"):
        if i == "Failures.dbf":
            SourceTable = "Failures.dbf"
            count=count+1
            Success = False
            break

    if Success:
        arcpy.AddMessage("\nOperation Success\n")
        sys.exit()

