#!/usr/bin/env python3

import zipfile
import tempfile
import shutil
import sys
import argparse
import wget
import csv
import contextlib
import sqlite3
import webbrowser
import os
import json

from   time import sleep, time
from   os import listdir, getcwd, system, path, makedirs, remove, environ
from   os.path import isfile, join, dirname, isdir
from   PIL import Image
from   urllib.request import urlopen
from   datetime import datetime

class MakeError(Exception):
  pass

class UIO(object):
    """@brief Handle user input and output."""
    
    def enableDebug(self, enabled):
        """@brief Enable/disable debugging.
           @param enabled If True debugging is enabled."""
        self._debug = enabled
        
    def info(self, msg):
        """@brief Display an info level message.
           @param msg The message text."""
        self._print("INFO:  {}".format(msg) )
        
    def error(self, msg):
        """@brief Display an error level message.
           @param msg The message text."""
        self._print("ERROR: {}".format(msg) )
        
    def debug(self, msg):
        """@brief Display a debug level message if debug is enabled.
           @param msg The message text."""
        if self._debug:
            self._print("DEBUG: {}".format(msg) )
        
    def _print(self, msg):
        """@brief Display a message.
           @param msg The message text."""
        print(msg)
        
    def input(self, prompt):
        """@brief Get input from user.
           @param prompt The text presented to the user.
           @return user input."""
        return input("INPUT: {}".format(prompt))
    
    def inputDecInt(self, prompt, minValue, maxValue):
        """@brief Get a decimal integer number.
           @param minValue The minimum acceptable value.
           @param prompt The text presented to the user.
           @param maxValue The maximum acceptable value.
           @return The number."""
        while True:
            response = self.input(prompt)
            try:
                value = int(response)

                if value < minValue:
                    self.error("{} is an invalid value (min = {}).".format(value, minValue))

                elif value > maxValue:
                    self.error("{} is an invalid value (max = {}).".format(value, maxValue))

                else:
                    return value

            except ValueError:
                self.error("{} is not a valid integer value.".format(response))
    
    def boolInput(self, prompt):
        """@brief ask for user y/n response.
           @param prompt The text presented to the user.
           @return True or False if y or n was entered by the user."""
        returnValue = None
        while True:
            response = self.input("{} y/n: ".format(prompt))
            response = response.lower()
            if response == 'y':
                returnValue = True
                break
            
            elif response == 'n':
                returnValue = False
                break
            
        return returnValue
                
def GetHomePath():
    """Get the user home path."""
    if "HOME" in environ:
        return environ["HOME"]

    elif "HOMEDRIVE" in environ and "HOMEPATH" in environ:
        return environ["HOMEDRIVE"] + environ["HOMEPATH"]

    elif "USERPROFILE" in environ:
        return environ["USERPROFILE"]

    return None
    
class JLCPCBDatabase(object):
    """@brief responsible for downloading searching the JLCPCB parts database."""
    
    JLCPCB_CSV_FILENAME = "parts.csv"
    JLCPCB_PARTS_FOLDER = join(GetHomePath(), ".jlcpcb")
    JLCPCB_CSV_DATE_FILE = join(JLCPCB_PARTS_FOLDER, JLCPCB_CSV_FILENAME + ".date")
    JLCPCB_CSV_FILE = join(JLCPCB_PARTS_FOLDER, JLCPCB_CSV_FILENAME)
    JLCPCB_SQLITE_DB_FILE = path.join(JLCPCB_PARTS_FOLDER, "parts.db")
    JLCPCB_KICAD_HELP_PAGE = "https://support.jlcpcb.com/article/84-how-to-generate-the-bom-and-centroid-file-from-kicad"
    CSV_URL = "https://jlcpcb.com/componentSearch/uploadComponentInfo"
    
    # All fields in the database.
    LCSC_PART = "LCSC Part"
    FIRST_CATEGORY = "First Category"
    SECOND_CATEGORY = "Second Category"
    MFG_PART = "MFR.Part"
    PACKAGE = "Package"
    SOLDER_JOINT = "Solder Joint"
    MANUFACTURER = "Manufacturer"
    LIBRARY_TYPE = "Library Type"
    DESCRIPTION = "Description"
    DATASHEET = "Datasheet"
    PRICE = "Price"
    STOCK = "Stock"
    FIELD_LIST = (LCSC_PART,
                  FIRST_CATEGORY,
                  SECOND_CATEGORY,
                  MFG_PART,
                  PACKAGE,
                  SOLDER_JOINT,
                  MANUFACTURER,
                  LIBRARY_TYPE,
                  DESCRIPTION,
                  DATASHEET,
                  PRICE,
                  STOCK) 
    
    VERTICAL_TABLE_BORDER_CHAR = "|"
    HORIZONTAL_TABLE_BORDER_CHAR = "-"
    
    def __init__(self, uio):
        self._uio = uio
        self._dBSearch = DBSearch()
        self._dBSearch.load()
        self._rowLength = None
        
    def _info(self, msg):
        """@brief Display an info level message.
           @param msg The message to display."""
        if self._uio:
            self._uio.info(msg)
            
    def _error(self, msg):
        """@brief Display an error level message.
           @param msg The message to display."""
        if self._uio:
            self._uio.error(msg)
            
    def updateAssyFiles(self):
        """@brief search for an update the assembly files."""
        if self._mfg != JLCPCBDatabase.VENDOR_JLCPCB:
            raise Exception("Currently assembly files are only generated for JCBPCB")
        
        self._processPlcaementFile()
        self._processBOMFile()
       
    def _createTopLevel(self):
        """Create the meta table."""
        with contextlib.closing(sqlite3.connect(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)) as con:
            with con as cur:
                cur.execute(
                    f"CREATE TABLE IF NOT EXISTS meta ('filename', 'size', 'partcount', 'date', 'last_update')"
                )
                cur.commit()
            
    def _removePartsT(self):
        """Delete the parts table."""
        with contextlib.closing(sqlite3.connect(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)) as con:
            with con as cur:
                cur.execute(f"DROP TABLE IF EXISTS parts")
                cur.commit()
                
    def _makePartT(self, columns):
        """Create the parts table."""
        with contextlib.closing(sqlite3.connect(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)) as con:
            with con as cur:
                colList = []
                for col in columns:
                    if col == "Stock" or col == "Solder Joint":
                        colList.append("'{}' int".format(col))
                    else:
                        colList.append("'{}'".format(col))

                cols = ",".join(colList)
                sqlCmd = f"CREATE TABLE IF NOT EXISTS parts ({cols})"
                cur.execute(sqlCmd)
                cur.commit()

    def updateMetaData(self, filename, size, partcount, date, last_update):
        """Update the meta data table."""
        with contextlib.closing(sqlite3.connect(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)) as con:
            with con as cur:
                cur.execute(f"DELETE from meta")
                cur.commit()
                cur.execute(
                    f"INSERT INTO meta VALUES (?, ?, ?, ?, ?)",
                    (filename, size, partcount, date, last_update),
                )
                cur.commit()

    def _showSearchHelp(self):
        """@brief Show the search help text."""
        self._info("")
        self._info("Options.")
        self._info("C -  Enter a part category.")
        self._info("M -  Enter the MFG part number.")
        self._info("D -  Enter a part description.")
        self._info("P -  Enter a part package.")
        self._info("J -  JLCPCB part number.")
        self._info("T -  Enter a part type (Basic or Extended).")
        self._info("R -  Reset/Clear search parameters.")
        self._info("S -  Search parts database using the selected parameters.")
        self._info("SP - Toggle Show only parts where stock > 0.")
        self._info("OP - Toggle One Off Only Pricing.")
        self._info("FL - Enter a list of fields/columns to display.")
        self._info("OF - Enter the field/column to order to display.")
        self._info("CS - Enter a list of field/column sizes.")
        self._info("MA - Enter the maximum number of parts to display.")
        self._info("")
        
    def _showSearchParams(self):
        """@brief Show the parts DB search parameters."""
        lines = self._dBSearch.getLines()
        self._info("")
        self._info("SELECTED SEARCH PARAMETERS")
        self._info("")
        for line in lines:
            self._info(line)
        
    def search(self):
        """Search the database for parts that meet the given parameters."""
        while True:
            self._showSearchParams()
            self._showSearchHelp()
            response = self._uio.input("Option: ")
            
            if response.lower() == 'c':
                self._selectCategory()
                
            elif response.lower() == 'm':
                self._info("You may enter a comma separated list of the text matches required in the MFG part number field.")
                self._info("")
                self._dBSearch.mfgPartNumber = self._uio.input("Enter the MFG part number: ")

            elif response.lower() == 'd':
                self._info("You may enter a comma separated list of the text matches required in the description field.")
                self._info("")
                self._dBSearch.description = self._uio.input("Enter the description text to search for: ")

            elif response.lower() == 'p':
                self._dBSearch.package = self._uio.input("Enter the package text to search for: ")
                
            elif response.lower() == 'j':
                self._dBSearch.jclPcbPartNumber = self._uio.input("Enter the JLCPCB part number to search for: ")
                
            elif response.lower() == 't':
                self._dBSearch.type = self._uio.input("Enter the type of part (Basic or Extended): ")

            elif response.lower() == 'sp':
                self._dBSearch.stockOnly = not self._dBSearch.stockOnly
                
            elif response.lower() == 'op':
                self._dBSearch.oneOffPricingOnly = not self._dBSearch.oneOffPricingOnly
                
            elif response.lower() == 'fl':
                self._enterFieldList()
                
            elif response.lower() == 'cs':
                self._entercolumnWidthList()
                
            elif response.lower() == 'of':
                self._enterOrderField()
                
            elif response.lower() == 'ma':
                self._dBSearch.maxPartCount = self._uio.inputDecInt("Enter the max number of searched parts to display: ", 1, 1000000)

            elif response.lower() == 'r':
                self._dBSearch.init()
                
            self._dBSearch.save()
                
            if response.lower() == 's':
                self._searchD()
                 
    def _selectCategory(self):
        """@brief SElect category."""
        self._info("Category List.")
        queryStr = 'SELECT DISTINCT "{}" FROM parts ORDER BY "{}"'.format(JLCPCBDatabase.FIRST_CATEGORY, JLCPCBDatabase.FIRST_CATEGORY)
        with contextlib.closing(sqlite3.connect(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)) as con:
            with con as cur:
                print(JLCPCBDatabase.HORIZONTAL_TABLE_BORDER_CHAR*54)
                print(JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR + " Category                                           " + JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR)    
                print(JLCPCBDatabase.HORIZONTAL_TABLE_BORDER_CHAR*54)
                results =  cur.execute(queryStr).fetchall()
                for result in results:
                    rowText = JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR + " " + self._getColText(result[0], 50) + " " + JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR
                    print(rowText)
                print(JLCPCBDatabase.HORIZONTAL_TABLE_BORDER_CHAR*54)
        
        self._dBSearch.catagory = self._uio.input("Enter the catagory text to search for: ")
                                
    def _enterFieldList(self):
        """@brief Allow the user to enter the field list."""
        titleLine = "| ID   | NAME                      | Default |"

        self._info("-"*len(titleLine))
        self._info(titleLine)
        self._info("-"*len(titleLine))
        id = 1
        for fName in JLCPCBDatabase.FIELD_LIST:
            if fName in DBSearch.DEFAULT_COLUMN_LIST:
                default = "Yes"
            else:
                default = ""
            self._info("| {: <4} | {: <25} | {: <7} |".format(id, fName, default))
            id += 1
        self._info("-"*len(titleLine))
        
        while True:
            response = self._uio.input("Enter a comma separated list of the ID's of each column included in search output: ")
            id = ""
            try:
                elems = response.split(",")
                if len(elems) == 1 and elems[0] == '': 
                    self._error("At least one ID must be entered.")
                    continue
                fieldList = []
                for elem in elems:
                    id = int(elem)
                    if id < 0 or id > len(JLCPCBDatabase.FIELD_LIST):
                        raise ValueError("")
                    fieldList.append(JLCPCBDatabase.FIELD_LIST[id-1])
                self._dBSearch.fieldList = ",".join(fieldList)
                break
                    
            except ValueError:
                self._error("{} is an invalid ID".format(id))
                
    def _showSelectedFieldTable(self):
        """@brief Show the table of the selcted fields."""
        titleLine = "| ID   | NAME                      |"
        self._info("Selected Fields/Columns")
        self._info("-"*len(titleLine))
        self._info(titleLine)
        self._info("-"*len(titleLine))
        id = 1
        fieldList = self._dBSearch.fieldList.split(",")
        for fName in fieldList:
            self._info("| {: <4} | {: <25} |".format(id, fName))
            id += 1
        self._info("-"*len(titleLine))
        
    def _entercolumnWidthList(self):
        """@brief Allow the user to enter the size of each output column."""
        self._showSelectedFieldTable()
        fieldList = self._dBSearch.fieldList.split(",")
        colListEntered = False
        while not colListEntered:
            response = self._uio.input("Enter a comma separated list of the sizes of each column: ")
            elems = response.split(",")
            if len(elems) == len(fieldList):
                try:
                    columnWidthList = []
                    for valueStr in elems:
                        value = int(valueStr)
                        if value < 1:
                            raise ValueError("")
                        if value > 132:
                            raise ValueError("")
                        columnWidthList.append(value)
                    self._dBSearch.columnWidthList = ",".join( map(str,columnWidthList) )
                    colListEntered = True
                    break
                except ValueError:
                    self._error("{} is an invalid column size (1-132 are valid).")
                    
            else:
                self._error("{} values were defined. {} values are required (one for each column).".format(len(elems), len(fieldList)))

    def _enterOrderField(self):
        """@brief Enter the field to order the output on."""
        self._showSelectedFieldTable()
        fieldList = self._dBSearch.fieldList.split(",")
        while True:
            orderFieldID = self._uio.inputDecInt("Enter the ID of the field to order the search results: ", minValue=1, maxValue=len(fieldList))
            if orderFieldID < 1 or orderFieldID > len(fieldList):
                self._error("{} is an invalid field ID.".format(orderFieldID))
            else:
                self._dBSearch.orderFieldID = orderFieldID
                break
    
    def _getSQLSearchCmd(self, addDataSheet=False):
        """@brief Get the SQL command to search the data base.
           @param addDataSheet If True then add the data sheet column to the results.
           @return A tuple
                   0: The SQL query string.
                   1: A list of search fields."""
        fields = self._dBSearch.fieldList.split(",")
        if addDataSheet:
            if "Datasheet" not in fields:
                fields.append("Datasheet")
        dispColStr = ",".join(f'"{c}"' for c in fields)
        queryStr = 'SELECT {} FROM parts WHERE '.format(dispColStr)
        qList = []
        
        searchValid = False
        if len(self._dBSearch.catagory) > 0:
            qList.append('"First Category" LIKE "%{}%"'.format(self._dBSearch.catagory))
            searchValid = True

        if len(self._dBSearch.mfgPartNumber) > 0:
            elems = self._dBSearch.mfgPartNumber.split(",")
            if len(elems) > 0:
                for sText in elems:
                    qList.append('"MFR.Part" LIKE "%{}%"'.format(sText))
            searchValid = True

        if len(self._dBSearch.description) > 0:
            elems = self._dBSearch.description.split(",")
            if len(elems) > 0:
                for sText in elems:
                    qList.append('"Description" LIKE "%{}%"'.format(sText))
            searchValid = True

        if len(self._dBSearch.package) > 0:
            qList.append('"Package" LIKE "%{}%"'.format(self._dBSearch.package))
            searchValid = True

        if len(self._dBSearch.jclPcbPartNumber) > 0:
            elems = self._dBSearch.jclPcbPartNumber.split(",")
            if len(elems) > 0:
                for sText in elems:
                    qList.append('"LCSC Part" LIKE "%{}%"'.format(sText))
            searchValid = True

        if len(self._dBSearch.type) > 0:
            qList.append('"Library Type" LIKE "%{}%"'.format(self._dBSearch.type))
            searchValid = True

        if not searchValid:
            self._error("No search parameters entered.")
            return
        
        queryStr += " AND ".join(qList)
        queryStr += ' ORDER BY "{}"'.format(fields[self._dBSearch.orderFieldID-1])
        queryStr += " LIMIT {}".format(self._dBSearch.maxPartCount)
        return (queryStr, fields)
    
    def _search(self):
        """@brief Perform the database search and display the results.
           @return The db search results."""
        queryStr, fields = self._getSQLSearchCmd()
        colWidthList = self._dBSearch.columnWidthList.split(",")
        self._uio.debug("SQL query: {}".format(queryStr))
        with contextlib.closing(sqlite3.connect(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)) as con:
            with con as cur:
                self._showTableHeader()
                results =  cur.execute(queryStr).fetchall()
                itemCount = 1
                for result in results:
                    colIndex=0
                    rowText = JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR + " " + self._getColText(itemCount, 4) + " " + JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR
                    ignorePart = False
                    for col in result:
                        colName = fields[colIndex]
                        colWidth = int( colWidthList[colIndex] )
                        
                        # If this is the price column and the user is only interested in parts where stock > 0
                        if colName == JLCPCBDatabase.STOCK and self._dBSearch.stockOnly:
                            if col == '0':
                                ignorePart = True
                                break                                                           
                        
                        # If this is the price column
                        if colName == JLCPCBDatabase.PRICE:
                            # If the user is only interested in parts that have a one off pricing
                            if self._dBSearch.oneOffPricingOnly and not col.startswith("1-"):
                                # Ignore parts that don't have one off pricing.
                                ignorePart = True
                                break
                            else:
                                colText = self._getPrice(col, colWidth)
                        else:
                            colText = self._getColText(col, colWidth)                            
                        
                        rowText = rowText + " " + colText + " " + JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR
                        colIndex += 1
                    if not ignorePart:
                        print(rowText)
                        itemCount += 1

                print(JLCPCBDatabase.HORIZONTAL_TABLE_BORDER_CHAR*self._rowLength)
                
        return results

    def _searchD(self):
        """@brief Search for parts and allow the user to view data sheets."""
        while True:
            searchResults = self._search()
            self._info("- Enter the item number to view the datasheet on a part.")
            self._info("- Press enter to return to parts selection.")
            response = self._uio.input("")
            try:
                itemNumber = int(response)
                self._showDataSheet(itemNumber)
            except ValueError:
                break
            
    def _showDataSheet(self, itemNumber):
        """@brief Show the datasheet for the item.
           @param itemNumber The number of the data sheet in the search results."""
        queryStr, fields = self._getSQLSearchCmd(addDataSheet=True)
        self._uio.debug("SQL query: {}".format(queryStr))
        with contextlib.closing(sqlite3.connect(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)) as con:
            with con as cur:
                self._showTableHeader()
                results =  cur.execute(queryStr).fetchall()
                dataSheetURL = str(results[itemNumber-1][-1])
                self._info("Opening {}".format(dataSheetURL))
                webbrowser.open(dataSheetURL, new=2)
                           
    def _getPrice(self, colText, colWidth):
        """@brief Get the price string in a more readable format."""
        priceList=[]
        elems = colText.split(",")
        for elem in elems:
            _elems = elem.split(":")
            if len(_elems) == 2:
                try:
                    qty=_elems[0]
                    price=float(_elems[1])
                    priceList.append("{}:${:.2f}".format(qty,price))
                except ValueError:
                    pass
        return self._getColText(" ".join(priceList), colWidth)      
    
    def _showTableHeader(self):
        """@brief Show the result able header."""
        fields = self._dBSearch.fieldList.split(",")
        colWidthList = self._dBSearch.columnWidthList.split(",")
        rowText = JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR + " Item " + JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR
        colIndex = 0
        for field in fields:
            colWidth = int( colWidthList[colIndex] )
            colText = self._getColText(field, colWidth)
            rowText = rowText + " " + colText + " " + JLCPCBDatabase.VERTICAL_TABLE_BORDER_CHAR
            colIndex += 1
        self._rowLength = len(rowText)
        print(JLCPCBDatabase.HORIZONTAL_TABLE_BORDER_CHAR*self._rowLength)
        print(rowText)        
        print(JLCPCBDatabase.HORIZONTAL_TABLE_BORDER_CHAR*self._rowLength)
        
    def _getColText(self, colText, colWidth):
        _colText = str(colText)
        if len(_colText) > colWidth:
            colStr = colText[0:colWidth]
        else:
            extraCharCount = colWidth-len(_colText)
            colStr = str(colText)+" "*extraCharCount
        return colStr
        
    def _getCSVCreationDate(self):
        """@brief Get the date of the CSV file.
           @return The date string when the CSV file was created."""
        dateStr = None
        fd = open(JLCPCBDatabase.JLCPCB_CSV_DATE_FILE, 'r')
        lines = fd.readlines()
        fd.close()
        if len(lines) > 0:
            dateStr = lines[0].rstrip("\r\n")
        return dateStr
                
    def downloadJLCPCBPartsdDB(self):
        jlcpcbPartsFolder = JLCPCBDatabase.JLCPCB_PARTS_FOLDER
        if not isdir(jlcpcbPartsFolder):
            makedirs(jlcpcbPartsFolder)
            self._info("Created {}".format(jlcpcbPartsFolder))
        
        csvFile = JLCPCBDatabase.JLCPCB_CSV_FILE
        csvDateFile = JLCPCBDatabase.JLCPCB_CSV_DATE_FILE
            
        if isfile(csvFile):
            remove(csvFile)
            self._info("Deleted existing {} file.".format(csvFile))

        csvServerFileDate=None
        with urlopen(JLCPCBDatabase.CSV_URL) as f:
            csvServerFileDate = dict(f.getheaders())['Date']
            
        self._info("Downloading {}".format(JLCPCBDatabase.CSV_URL))
        startTime = time()    
        wget.download(JLCPCBDatabase.CSV_URL, out=csvFile)
        sleep(1.5)
        elapsedSeconds = time()-startTime
        self._info("Took {:.1f} seconds to download {}".format(elapsedSeconds, csvFile))
                  
        fd = open(csvDateFile, 'w')
        # First line is the date created on the server
        fd.write("{}\n".format(csvServerFileDate))
        # Second date is the date it was written locally
        fd.write("{}\n".format(datetime.now().isoformat()))
        fd.close()
        self._info("Updated {} with creation date.".format(csvDateFile))

    def createPartsDB(self):
        """@brief Create the sqllite parts database from a downloaded CSV file."""
        csvFile = JLCPCBDatabase.JLCPCB_CSV_FILE
        csvFileSize = path.getsize(csvFile)
        
        startTime = time()
        if isfile(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE):
            remove(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)
            self._info("Deleted existing {} file.".format(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE))
        self._info("Creating {} file from {} file...".format(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE, csvFile))
        self._createTopLevel()
        self._removePartsT()
        
        with open(csvFile, 'r', encoding="latin-1") as lines:
            reader = csv.reader(lines)
            headers = next(reader)
            self._makePartT(headers)
            
            buffer = []
            part_count = 0
            with contextlib.closing(sqlite3.connect(JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE)) as con:
                cols = ",".join(["?"] * len(headers))
                query = f"INSERT INTO parts VALUES ({cols})"
    
                for count, row in enumerate(reader):
                    row.pop()
                    buffer.append(row)
                    if count % 1000 == 0:
                        con.executemany(query, buffer)
                        buffer = []
                    part_count = count
                if buffer:
                    con.executemany(query, buffer)
                con.commit()
            self.updateMetaData(JLCPCBDatabase.JLCPCB_CSV_FILENAME, csvFileSize, part_count, self._getCSVCreationDate(), datetime.now().isoformat())
        
        elapsedSeconds = time()-startTime
        self._info("Took {:.1f} seconds to create {}".format(elapsedSeconds, JLCPCBDatabase.JLCPCB_SQLITE_DB_FILE))

class DBSearch(object):
    """@brief Holds the parameters to search through the parts database."""
    
    DEFAULT_COLUMN_LIST = (JLCPCBDatabase.LCSC_PART,
                           JLCPCBDatabase.STOCK,
                           JLCPCBDatabase.MFG_PART,
                           JLCPCBDatabase.PACKAGE,
                           JLCPCBDatabase.LIBRARY_TYPE,
                           JLCPCBDatabase.PRICE,
                           JLCPCBDatabase.DESCRIPTION)
    DEFAULT_COLUMN_SIZES = (9,7,25,25,8,12,90)
    JLCPCB_KICAD_URL = "https://support.jlcpcb.com/article/84-how-to-generate-the-bom-and-centroid-file-from-kicad"
    CONFIG_FILENAME = ".jclpcb_search_params.cfg"
    
    CATAGORY_ATTR               = "CATAGORY_ATTR"
    MFG_PART_NUMBER_ATTR        = "MFG_PART_NUMBER_ATTR"
    DESCRIPTION_ATTR            = "DESCRIPTION_ATTR"
    PACKAGE_ATTR                = "PACKAGE_ATTR"
    JLCPCB_PART_NUMBER_ATTR     = "JLCPCB_PART_NUMBER_ATTR"
    TYPE_ATTR                   = "TYPE_ATTR"
    STOCK_ONLY_ATTR             = "STOCK_ONLY_ATTR"
    ONE_OFF_PRICING_ONLY_ATTR   = "ONE_OFF_PRICING_ONLY_ATTR"
    ORDER_FIELD_ID_ATTR         = "ORDER_FIELD_ID_ATTR"
    FIELD_LIST_ATTR             = "FIELD_LIST_ATTR"
    COLUMN_WIDTH_LIST_ATTR      = "COLUMN_WIDTH_LIST_ATTR"
    MAX_PART_COUNT_ATTR         = "MAX_PART_COUNT_ATTR"

    @staticmethod
    def GetBoolString(boolValue):
        """@return the string that represents the boolena value."""
        if boolValue:
            return "Yes"
        return "No"
    
    @staticmethod
    def GetHomePath():
        """Get the user home path as this will be used to store config files"""
        if "HOME" in os.environ:
            return os.environ["HOME"]
    
        elif "HOMEDRIVE" in os.environ and "HOMEPATH" in os.environ:
            return os.environ["HOMEDRIVE"] + os.environ["HOMEPATH"]
    
        elif "USERPROFILE" in os.environ:
            return os.environ["USERPROFILE"]
    
        return None


    def __init__(self):
        self.init()
        
    def init(self):
        """@brief Reset all search parameters to the defaults."""               
        self.catagory           = ""
        self.mfgPartNumber      = ""
        self.description        = ""
        self.package            = ""
        self.jclPcbPartNumber   = ""
        self.type               = ""
        self.stockOnly          = True
        self.oneOffPricingOnly  = False
        self.orderFieldID       = 2
        self.fieldList          = ",".join(DBSearch.DEFAULT_COLUMN_LIST)
        self.columnWidthList    = ",".join(map(str, DBSearch.DEFAULT_COLUMN_SIZES))
        self.maxPartCount       = 1000   
        
        self._cfgFile = os.path.join( DBSearch.GetHomePath(), DBSearch.CONFIG_FILENAME)
        
    def save(self):
        """@brief Save the state of the instance to the config file."""
        saveDict = {DBSearch.CATAGORY_ATTR:             self.catagory,
                    DBSearch.MFG_PART_NUMBER_ATTR:      self.mfgPartNumber,
                    DBSearch.DESCRIPTION_ATTR:          self.description,
                    DBSearch.PACKAGE_ATTR:              self.package,
                    DBSearch.JLCPCB_PART_NUMBER_ATTR:   self.jclPcbPartNumber,
                    DBSearch.TYPE_ATTR:                 self.type,
                    DBSearch.STOCK_ONLY_ATTR:           self.stockOnly,
                    DBSearch.ONE_OFF_PRICING_ONLY_ATTR: self.oneOffPricingOnly,
                    DBSearch.ORDER_FIELD_ID_ATTR:       self.orderFieldID,
                    DBSearch.FIELD_LIST_ATTR:           self.fieldList,
                    DBSearch.COLUMN_WIDTH_LIST_ATTR:    self.columnWidthList,
                    DBSearch.MAX_PART_COUNT_ATTR:       self.maxPartCount
                    }
        json.dump(saveDict, open(self._cfgFile, "w"), sort_keys=True)

    def load(self):
        """@brief Load the state of the instance from the confile file."""
        try:
            fp = open(self._cfgFile, 'r')
            loadDict = json.load(fp)
            fp.close()
            
            self.catagory = loadDict[DBSearch.CATAGORY_ATTR]
            self.mfgPartNumber = loadDict[DBSearch.MFG_PART_NUMBER_ATTR]
            self.description = loadDict[DBSearch.DESCRIPTION_ATTR]
            self.package = loadDict[DBSearch.PACKAGE_ATTR]
            self.jclPcbPartNumber = loadDict[DBSearch.JLCPCB_PART_NUMBER_ATTR]
            self.type = loadDict[DBSearch.TYPE_ATTR]
            self.stockOnly = loadDict[DBSearch.STOCK_ONLY_ATTR]
            self.oneOffPricingOnly = loadDict[DBSearch.ONE_OFF_PRICING_ONLY_ATTR]
            self.orderFieldID = loadDict[DBSearch.ORDER_FIELD_ID_ATTR]
            self.fieldList = loadDict[DBSearch.FIELD_LIST_ATTR]
            self.columnWidthList = loadDict[DBSearch.COLUMN_WIDTH_LIST_ATTR]
            self.maxPartCount = loadDict[DBSearch.MAX_PART_COUNT_ATTR]
           
        except:
            pass

        
    def getLines(self):
        """@return The state of the object as a number of lines of text."""
        fields = self.fieldList.split(",")
        lines = []
        lines.append("Category:                    {}".format(self.catagory))
        lines.append("MFG Part Number:             {}".format(self.mfgPartNumber))
        lines.append("Description:                 {}".format(self.description))
        lines.append("Package:                     {}".format(self.package))
        lines.append("JLCPCB Part Number:          {}".format(self.jclPcbPartNumber))
        lines.append("Type:                        {}".format(self.type))
        lines.append("Show Only Stock > 0:         {}".format( DBSearch.GetBoolString( self.stockOnly )))
        lines.append("Show Only One Off Pricing:   {}".format( DBSearch.GetBoolString( self.oneOffPricingOnly) ))
        lines.append("Field List:                  {}".format( self.fieldList ))
        lines.append("Show Order Field:            {}".format( fields[self.orderFieldID-1] )) 
        lines.append("Field Column Width List:     {}".format( self.columnWidthList ))
        lines.append("Max Part Count:              {}".format(self.maxPartCount))
        return lines
    
class PCBFileProcessor(object):
    """@brief Responsible for processing Kicad PCB files for manufacture."""

    VENDOR_SEEDSTUDIO = "seedstudio"
    VENDOR_PCBWAY = "pcbway"
    VENDOR_JLCPCB = "jlcpcb"
    SEED_STUDIO_REQUIRED_FILES = ["F.SilkS.gto", "F.Cu.gtl", "F.Paste.gtp", "F.Mask.gts", "B.Paste.gbp", "B.Cu.gbl", "B.SilkS.gbo", "B.Mask.gbs", "Dwgs.User.gbr", "Edge.Cuts.gm1", ".drl"]
    PCBWAY_REQUIRED_FILES = ["F.Cu.gbr", "F.SilkS.gbr", "F.Mask.gbr", "B.Cu.gbr", "B.SilkS.gbr", "Edge.Cuts.gbr", "B.Mask.gbr", ".drl"]
    JLCPCB_REQUIRED_FILES = ["F_Cu.gbr", "F_SilkS.gbr", "F_Mask.gbr", "B_Cu.gbr", "B_SilkS.gbr", "Edge_Cuts.gbr", "B_Mask.gbr", ".drl"]
    JLCPCB_REQUIRED_FILES_V6 = ["F_Cu.gtl", "B_Cu.gbl", "F_Paste.gtp", "B_Paste.gbp", "F_Silkscreen.gto", "B_Silkscreen.gbo", "F_Mask.gts", "B_Mask.gbs", "Edge_Cuts.gm1", ".drl"]

    JLCPCB_KICAD_HELP_PAGE = "https://support.jlcpcb.com/article/84-how-to-generate-the-bom-and-centroid-file-from-kicad"
    CSV_URL = "https://jlcpcb.com/componentSearch/uploadComponentInfo"
    
    TOP = "top"
    BOTTOM = "bottom"
    
    ASSY_SEARCH_PATHS = [".",".."]
    
    JLCPCB_CSV_FILENAME = "parts.csv"
    JLCPCB_PARTS_FOLDER = join(GetHomePath(), ".jlcpcb")
    JLCPCB_CSV_DATE_FILE = join(JLCPCB_PARTS_FOLDER, JLCPCB_CSV_FILENAME + ".date")
    JLCPCB_CSV_FILE = join(JLCPCB_PARTS_FOLDER, JLCPCB_CSV_FILENAME)
    JLCPCB_SQLITE_DB_FILE = path.join(JLCPCB_PARTS_FOLDER, "parts.db")
        
    def __init__(self, uio, options):
        """@brief Contructor
           @param uio A UIO instance.
           @param options A argparse command line options instance."""
        self._uio            = uio
        self._options        = options
        self._projectName    = None
        self._requiredFiles  = None
        self._mfg            = None
        self._projectVersion = None
        self._overWrite      = False
        self._jlcPCBDatabase = JLCPCBDatabase(self._uio)
    
    def _info(self, msg):
        """@brief Display an info level message.
           @param msg The message to display."""
        if self._uio:
            self._uio.info(msg)
            
    def _error(self, msg):
        """@brief Display an error level message.
           @param msg The message to display."""
        if self._uio:
            self._uio.error(msg)
            
    def getSortedFileList(self, fileList):
        """@brief Sort into a sequence that shows the layers stacked from top to bottom in the gerber viewer.
           @param The input file list
           @return The sorted file list."""
        for pcbFile in fileList:
    
            if pcbFile.endswith(PCBFileProcessor.PCBWAY_REQUIRED_FILES[0]):
                mfgFileList = PCBFileProcessor.PCBWAY_REQUIRED_FILES
                break
    
            if pcbFile.endswith(PCBFileProcessor.SEED_STUDIO_REQUIRED_FILES[0]):
                mfgFileList = PCBFileProcessor.SEED_STUDIO_REQUIRED_FILES
                break
    
            if pcbFile.endswith(PCBFileProcessor.JLCPCB_REQUIRED_FILES[0]):
                mfgFileList = PCBFileProcessor.JLCPCB_REQUIRED_FILES
                break
    
            if pcbFile.endswith(PCBFileProcessor.JLCPCB_REQUIRED_FILES_V6[0]):
                mfgFileList = PCBFileProcessor.JLCPCB_REQUIRED_FILES_V6
                break
    
        sortedFileList = []
        for mfgFileEnd in mfgFileList:
            for pcbFile in fileList:
                if pcbFile.endswith(mfgFileEnd):
                    sortedFileList.append(pcbFile)
    
        return sortedFileList
    
    def gerbvFiles(self, zipFile, gerbview):
        """@brief Extract the files from the zip file and showthem using gerbv 
           which must be installed on the local machine.
           @param zipFile The zip file to create and view.
           @param gerbview If True use gerbview rather than the default gerbv program."""
    
        #Create a temp dir
        dirpath = tempfile.mkdtemp()
        
        try:
            fileList = []
            fh = open(zipFile, 'rb')
            z = zipfile.ZipFile(fh)
            for name in z.namelist():
                z.extract(name, dirpath)
                fileList.append( join(dirpath, name) )
            fh.close()
    
            fileList = self.getSortedFileList(fileList)
    
            if gerbview:
    
                fileListStr = " ".join(fileList)
                cmdLine = "gerbview %s" % (fileListStr)
                self._info("CMDLINE: '%s'" % (cmdLine))
                system( cmdLine )
    
            else:
    
                fileListStr = " ".join(fileList)
                cmdLine = "gerbv %s" % (fileListStr)
                self._info("CMDLINE: '%s'" % (cmdLine))
                system( cmdLine )
    
    
        finally:
            shutil.rmtree(dirpath)
    
    def getSelectedVendor(self):
        """@brief get the selected MFG from the user.
           @return A tuple containing
                   0: The required files.
                   1: The mfg ID."""
        self._info("Supported manufacturers")
        self._info("SeedStudio:        1")
        self._info("PCBWay:            2")
        self._info("JLCPCB (Kicad V5): 3")
        self._info("JLCPCB (Kicad V6): 4")
        mfg = self._uio.input("Manufacturer: ")
        if mfg not in ["1", "2", "3", "4"]:
            raise MakeError("Current supported manufacturers are 1, 2, 3 or 4.")
        if mfg == '1':
            requiredFiles = list(PCBFileProcessor.SEED_STUDIO_REQUIRED_FILES)
            mfg=PCBFileProcessor.VENDOR_SEEDSTUDIO
        elif mfg == '2':
            requiredFiles = list(PCBFileProcessor.PCBWAY_REQUIRED_FILES)
            mfg= PCBFileProcessor.VENDOR_PCBWAY
        elif mfg == '3': 
            requiredFiles = list(PCBFileProcessor.JLCPCB_REQUIRED_FILES)
            mfg= PCBFileProcessor.VENDOR_JLCPCB
        elif mfg == '4': 
            requiredFiles = list(PCBFileProcessor.JLCPCB_REQUIRED_FILES_V6)
            mfg=mfg= PCBFileProcessor.VENDOR_JLCPCB
        else:
            raise Exception("Invalid MFG ID")
        
        return (requiredFiles, mfg )
    
    def zipFiles(self):
        """@brief Zip up the required gerber files in the current working dir.
           @return The zip file containing the gerber files."""
        
        requiredFiles, mfg = self.getSelectedVendor()
        
        expectedFiles = requiredFiles[:]
        
        self._projectName = self._uio.input("Enter the project name: ")
        
        self._projectVersion = self._uio.input("Enter the version of the board: ")
                
        #Ensure the PCB output folder exists
        self._makeOutputFolder()
        
        if len(self._projectName) > 0 and len(self._projectVersion) > 0:
            
            opFile = "%s_v%s_%s.zip" % (self._projectName, self._projectVersion, mfg)
            opFile = join(self._pcbFileFolder, opFile)
            
            cwd = getcwd()
        
            fileList = [f for f in listdir(cwd) if isfile(join(cwd, f))]
        
            gerberFileList = []
            for f in fileList:
                if f.endswith(".gbr") or \
                   f.endswith(".drl") or \
                   f.endswith(".gtp") or \
                   f.endswith(".gbp") or \
                   f.endswith(".gbl") or \
                   f.endswith(".gtl") or \
                   f.endswith(".gto") or \
                   f.endswith(".gbo") or \
                   f.endswith(".gbs") or \
                   f.endswith(".gts") or \
                   f.endswith(".gm1"):
                    gerberFileList.append(f)
                    
            for currentF in gerberFileList:
                for reqF in requiredFiles:
                    if currentF.endswith(reqF):
                        requiredFiles.remove(reqF)
                        
            if len(requiredFiles) > 0:
                self._info("Expected filename extension list")
                for eFile in expectedFiles:
                    self._info(eFile)
    
                self._info("Missing filename extension list")
                for mFile in requiredFiles:
                    self._info(mFile)
                
                raise MakeError("Not all required files are present (%s are missing)." % (requiredFiles) )
                
            zf = zipfile.ZipFile(opFile, "w")			
            for f in gerberFileList:
                zf.write(f)
        
            zf.close()
            self._info("Created %s" % (opFile))
            
            self._requiredFiles = requiredFiles
            self._mfg = mfg
            
            return opFile
    	
    def showKicadSettings(self):
        """@brief show the kicad settings required to generate files for the MFG"""
    
        plotImage = join(dirname(__file__), "jlcpcb_kicad_v6_plot.png")
        drillImage = join(dirname(__file__), "jlcpcb_kicad_v6_drill.png")
        placementImage = join(dirname(__file__), "jclpcb_kicad_v6_placement.png")
        
        if not isfile(plotImage):
            raise Exception("{} file not found.".format(plotImage))
        
        if not isfile(drillImage):
            raise Exception("{} file not found.".format(drillImage))
        
        if not isfile(placementImage):
            raise Exception("{} file not found.".format(placementImage))
        
        im = Image.open(plotImage)
        im.show()
    
        im = Image.open(drillImage)
        im.show()

        im = Image.open(placementImage)
        im.show()

        webbrowser.open(DBSearch.JLCPCB_KICAD_URL, new=2)

    def _getAssySide(self):
        """@brief Get the selected for assembly. 
                  zipFiles() must have been called prior to calling this method.
           @return top or bottom"""
        while True:
            side = self._uio.input("PCB side to which SMD components are to be added, t (top) or b (bottom): ")
            if side.lower() == 't':
                side = PCBFileProcessor.TOP
                break

            elif side.lower() == 'b':
                side = PCBFileProcessor.BOTTOM
                break

        return side
        
    def _makeOutputFolder(self):
        """@brief Create the folder to hold the PCB files.
                  This sits in the folder where this program was executed."""
        self._pcbFileFolder = "./{}_{}_pcb_files".format(self._projectName, self._projectVersion)
        if isdir(self._pcbFileFolder):
            self._info("The {} folder already exists.".format(self._pcbFileFolder))
            self._overWrite = self._uio.boolInput("Overwrite ?")
            if self._overWrite:
                shutil.rmtree(self._pcbFileFolder)
                self._info("Removed the {} folder.".format(self._pcbFileFolder))
                makedirs(self._pcbFileFolder)
                self._info("Created the {} folder.".format(self._pcbFileFolder))
        else:
            makedirs(self._pcbFileFolder)
            self._info("Created the {} folder.".format(self._pcbFileFolder))
        
    def _getLines(self, theFile):
        """@brief Get the contents of a text files as a list of lines.
           @return The lines of text read from the file."""
        if isfile(theFile):
            fd = open(theFile, 'r')
            lines = fd.readlines()
            fd.close()
            return lines
        else:
            raise Exception("{} file not found.".format(theFile))
        
    def _save(self, theFile, lines):
        """@brief Save the contents of a text file.
           @param lines A list of the lines of text the file will contain after save is complete."""
        fd = open(theFile, 'w')
        for line in lines:
            line=line.rstrip("\r\n")
            fd.write("{}\n".format(line))
        fd.close()
        self._info("Saved {}".format(theFile))
    
    def _getExistingBOMLine(self, kicadBOMFileLine, existingBOMLines):
        """@brief Get a BOM file line from those that exist.
           @param kicadBOMFileLine The BOM file line read from the Kicad output file.
           @param existingBOMLines A list of all the existing BOM file lines.
           @return The existing BOM file line or None if not found."""
        matchedExistingBOMLine = None
        # Column 0 = Comment = Value
        # Column 1 = Designator
        # Column 2 = Footprint
        kicadBOMFileLineElems = kicadBOMFileLine.split(",")
        for existingBOMLine in existingBOMLines:
            existingBOMLineElems = existingBOMLine.split(",")
            # If the Comment, Designators and Footprints match then we assume that they refer to the same part
            if kicadBOMFileLineElems[0].lower() == existingBOMLineElems[0].lower() and \
               kicadBOMFileLineElems[1].lower() == existingBOMLineElems[1].lower() and \
               kicadBOMFileLineElems[2].lower() == existingBOMLineElems[2].lower():
                matchedExistingBOMLine = existingBOMLine
        return matchedExistingBOMLine

    def _mergeBOMFiles(self, kicadBOMFile, bomOutputFile):
        """@brief Merge the BOM files. This will copy the JLCPCB part number for all matching parts.
                  Matching parts must have the same Designator and Footprint."""
        kicadBOMFileLines = self._getLines(kicadBOMFile)
        self._info("Loaded {} lines from {}".format(len(kicadBOMFileLines), kicadBOMFile))   
        bomOutputFileLines = self._getLines(bomOutputFile)
        self._info("Loaded {} lines from {}".format(len(bomOutputFileLines), bomOutputFile))   
        outputFileLines = []
        for kicadBOMFileLine in kicadBOMFileLines:
            newLine = self._getExistingBOMLine(kicadBOMFileLine, bomOutputFileLines)
            if newLine is None:
                newLine = kicadBOMFileLine
            outputFileLines.append(newLine)                
                    
        fd = open(bomOutputFile, "w")
        for line in outputFileLines:
            line=line.rstrip("\r\n")
            fd.write("{}\n".format(line))
        fd.close()
        self._info("Merged {} with {}".format(kicadBOMFile, bomOutputFile))
        
    def _getBomFile(self):
        """@brief Get the BOM file.
                  zipFiles() must have been called prior to calling this method.
           @return The absolute filename of the BOM file to be edited.."""
        foundBOMFile = False
        searchPaths = PCBFileProcessor.ASSY_SEARCH_PATHS
        bomFileName = "{}.csv".format(self._projectName)
        for bomPath in searchPaths:
            bomFile = path.join(bomPath, bomFileName)
            if path.isfile(bomFile):
                foundBOMFile = True
                break
        if not foundBOMFile:
            raise Exception("Failed to find the BOM file ({}) in {}.".format(bomFileName, str(searchPaths) ))
        
        # We work on a copy of the BOM file in the assy output folder
        bomOutputFile = join(self._pcbFileFolder, "{}_{}_bom.csv".format(self._projectName, self._projectVersion) )
        
        if self._overWrite:
            shutil.copy(bomFile, bomOutputFile)
            self._info("Copied {} to {}".format(bomFile, bomOutputFile))
            
        # If the user does not want to overwrite the BOM output file.
        elif isfile(bomOutputFile):
            # Merge the contents of the BOM
            self._mergeBOMFiles(bomFile, bomOutputFile)
            
        else:
            raise Exception("{} file not found.".format(bomFile))
        
        return bomOutputFile

    def _updateJLCPCBPart(self, line):
        """@brief Allow the user to enter the JLCPCB part number.
           @return The JLCPCB part number of n = next part or p = previous part."""
        elems = line.split('"')
        fieldList = []
        for elem in elems:
            if len(elem) > 0 and elem != ',':
                fieldList.append(elem)

        # If JLCPCB part number is missing
        if len(fieldList) == 3:
            # Add empty element
            fieldList.append("")

        if len(fieldList) == 4:
            while True:
                comment = fieldList[0].strip('"')
                designator = fieldList[1].strip('"')
                footPrint = fieldList[2].strip('"')
                jlcPcbPartNumber = fieldList[3].strip('"')
                self._info("---------------------------------------------------------------------------")
                self._info("COMMENT:                 {}".format(comment))
                self._info("DESIGNATOR:              {}".format(designator))
                self._info("FOOTPRINT:               {}".format(footPrint))
                self._info("JLCPCB PART NUMBER:      {}".format(jlcPcbPartNumber))
                self._info("")
                self._info("Enter")
                self._info("- The JLCPCB part number")
                self._info("- F to move to the first part")
                self._info("- L to move to the last part")
                self._info("- N to move to the next part")
                self._info("- B to move back to the previous part")
                self._info("- A Abort BOM file edit.")
                jlcPcbPartNumber = self._uio.input("")
                jlcPcbPartNumber=jlcPcbPartNumber.strip('\r\n"')
                # If user wants to move to next or previous parts
                if jlcPcbPartNumber in ['n', 'b', 'l', 'f', 'a']:
                    return jlcPcbPartNumber

                self._info("Set JLCPCB part number to {}".format(jlcPcbPartNumber))
                return '"{}","{}","{}","{}"'.format(comment, designator, footPrint, jlcPcbPartNumber)

        else:
            self._error("Invalid BOM line: {}".format(line))
            raise Exception("Should have four fields (Comment,Designator,Footprint,LCSC)")

    def _processBOMFile(self):
        """@brief Check and process the BOM file."""
        bomFile = self._getBomFile()
                        
        lineIndex = 0
        while True:
            bomLines = self._getLines(bomFile)
            if lineIndex == len(bomLines):
                self._info("*** Completed BOM edit ***")
                break
            line = bomLines[lineIndex]

            line=line.rstrip("\r\n")
            if line.startswith("Comment"):
                # Don't change the header line
                pass

            else:
                self._info("---------------------------------------------------------------------------")
                # ! first line is the header line
                self._info("Editing part {} of {} parts from {}".format(lineIndex, len(bomLines)-1, bomFile))   
                newLine = self._updateJLCPCBPart(line)
                if newLine == 'f':
                    lineIndex = 0
                    continue

                elif newLine == 'l':
                    lineIndex = len(bomLines)-1
                    continue

                elif newLine == 'n':
                    if lineIndex < len(bomLines)-1:
                        lineIndex = lineIndex + 1
                    continue

                elif newLine == 'b':
                    if lineIndex > 0:
                        lineIndex = lineIndex -1
                    continue
                
                elif newLine == 'a':
                    self._info("User aborted BOM file edit.")
                    sys.exit(0)
                
                bomLines[lineIndex]=newLine
                self._save(bomFile, bomLines)
            lineIndex = lineIndex + 1
                
    def _getPlacementFilename(self, side):
        """@brief Get the placement file.
                  zipFiles() must have been called prior to calling this method.
           @param side The side of the PCB to be assembled.
           @return The absolute filename of the placement file."""
        searchPaths = PCBFileProcessor.ASSY_SEARCH_PATHS
        placementFileName = "{}-{}-pos.csv".format(self._projectName, side)
        for placementPath in searchPaths:
            placementFile = path.join(placementPath, placementFileName)
            if path.isfile(placementFile):
                return placementFile, placementFileName
            
        raise Exception("Failed to find the placement file ({}) in {}.".format(placementFileName, str(searchPaths) ))
    
    def _processPlcaementFile(self):
        """@brief Process the component placement file."""
        side = self._getAssySide()
        placementFile, placementFileName = self._getPlacementFilename(side)
        outputPlacementFile = join(self._pcbFileFolder, placementFileName)
        fd = open(placementFile, 'r')
        lines = fd.readlines()
        fd.close()
        newLines = []
        updatedHeader = False
        for line in lines:
            if line.startswith("Ref,Val,Package,PosX,PosY,Rot,Side"):
                newLines.append("Designator,Val,Package,Mid X,Mid Y,Rotation,Layer")
                updatedHeader = True
            else:
                newLines.append(line)
                
        if not updatedHeader:
            raise Exception("Failed to update the header from the {} placement file.".format(placementFile))
        
        outputPlacementFilename = "{}_{}_placement.csv".format(self._projectName,side)
        outputPlacementFile = join(self._pcbFileFolder, outputPlacementFilename)
        self._save(outputPlacementFile, newLines)

    def updateAssyFiles(self):
        """@brief search for an update the assembly files."""
        if self._mfg != PCBFileProcessor.VENDOR_JLCPCB:
            raise Exception("Currently assembly files are only generated for JCBPCB")
        
        self._processPlcaementFile()
        self._processBOMFile()
       
    def searchParts(self):
        """@brief Search parts database."""
        self._jlcPCBDatabase.search()
        
    def downloadJLCPCBDatabase(self):
        """@brief Download the latest JLC PCB parts database."""
        self._jlcPCBDatabase.downloadJLCPCBPartsdDB()
        self._jlcPCBDatabase.createPartsDB()

if __name__ == "__main__":
    uio = UIO()
    
    try:
        parser = argparse.ArgumentParser(description="Helper program for building PCB gerber zip files prior to MFG.", formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("-d", "--debug",        help="Enable debugging.",     action='store_true')
        parser.add_argument("-a", "--assy",         help="In adition to the gerber files process the BOM and component placement files for PCB assembly.", action="store_true")
        parser.add_argument("-f", "--find",         help="Find parts in the local copy of the JLCPCB parts database.", action='store_true')
        parser.add_argument("-u", "--update",       help="Update the local copy of the JLCPCB parts database.", action='store_true')
        parser.add_argument("-n", "--no_preview",   help="Do not preview files. The default is to preview the gerber files using either gerbv or the gerbview programs.", action='store_true')
        parser.add_argument("-s",                   help="Show the Kicad settings required to generate gerbers for JLCPCB. Also the Kicad/JLCPCB helper link is opened using the default web browser.", action="store_true")
        parser.add_argument("-v", "--view_zip",     help="View zip file. This option can be used if the user only wants to view the contents of an existing zip files containing PCB gerber files.", action="store_true")
        parser.add_argument("--gerbview",           help="Use gerbview (Included with KiCad) not the default gerbv program which must be installed separately ('sudo apt install gerbv') to view gerbers.", action="store_true")

        options = parser.parse_args()
        
        pcbFileProcessor = PCBFileProcessor(uio, options)
        uio.enableDebug(options.debug)
        
        if options.view_zip:
            pcbFileProcessor.gerbvFiles(options.v, options.gerbview)

        elif options.s:
            pcbFileProcessor.showKicadSettings()
            
        elif options.gerbview:
            zipFile = pcbFileProcessor.zipFiles()
            pcbFileProcessor.gerbvFiles(zipFile, options.gerbview)

        elif options.find:
            pcbFileProcessor.searchParts()
            
        elif options.update:
            pcbFileProcessor.downloadJLCPCBDatabase()
            
        else:
            zipFile = pcbFileProcessor.zipFiles()
            # Once gerber files have been viewed go on to process the assembly files
            if options.assy:
                pcbFileProcessor.updateAssyFiles()
            pcbFileProcessor.gerbvFiles(zipFile, options.gerbview)
                        
    #If the program throws a system exit exception
    except SystemExit:
        pass
    
    #Don't print error information if CTRL C pressed
    except KeyboardInterrupt:
        pass
    
    except Exception as ex:

        if options.debug:
            raise
        else:
            uio.error(str(ex))
       
