#!/usr/bin/env python3

import zipfile
import tempfile
import shutil
import argparse
import os

from   os import listdir, getcwd, system, path, makedirs, environ
from   os.path import isfile, join, dirname, isdir
from   PIL import Image

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

    def input(self, prompt, stripWhiteSpace=True):
        """@brief Get input from user.
           @param prompt The text presented to the user.
           @param stripWhiteSpace If True then leading and trailing whitespace characters are removed from the user response.
           @return user input."""
        response = input("INPUT: {}".format(prompt))
        if stripWhiteSpace:
            response = response.strip()
        return response

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

            self._uio.info("Copied Gerber files to {}".format(self._pcbFileFolder))
            if self._options.assy:
                self._processBOMFiles()
                self._processPlacementFiles()

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
        bomImage = join(dirname(__file__), "jlcpcb_kicad_v6_bom.png")
        placementImage = join(dirname(__file__), "jlcpcb_kicad_v6_placement.png")

        if not isfile(plotImage):
            raise Exception("{} file not found.".format(plotImage))

        if not isfile(drillImage):
            raise Exception("{} file not found.".format(drillImage))

        if not isfile(bomImage):
            raise Exception("{} file not found.".format(bomImage))

        if not isfile(placementImage):
            raise Exception("{} file not found.".format(placementImage))

        im = Image.open(plotImage)
        im.show()

        im = Image.open(drillImage)
        im.show()

        im = Image.open(bomImage)
        im.show()

        im = Image.open(placementImage)
        im.show()

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
                raise Exception("Aborting updates to {}".format(self._pcbFileFolder))
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

    def _getPlacementFilenames(self):
        """@brief Get the placement file.
                  zipFiles() must have been called prior to calling this method.
           @return A list containing
                   A list containing
                   0 = The placement file
                   1 = The placement filename
                   2 = The side of the board"""
        retList = []
        searchPaths = PCBFileProcessor.ASSY_SEARCH_PATHS
        for side in (PCBFileProcessor.TOP, PCBFileProcessor.BOTTOM):
            placementFileName = "{}-{}-pos.csv".format(self._projectName, side)
            for placementPath in searchPaths:
                placementFile = path.join(placementPath, placementFileName)
                if path.isfile(placementFile):
                    retList.append( (placementFile, placementFileName, side) )
        return retList

    def _processPlacementFiles(self):
        """@brief Process the component placement files.
           @return A list of the processed placement files."""
        processedPlacementFiles = []
        #Process top and bottom placement files
        placementList = self._getPlacementFilenames()
        if len(placementList) == 0:
            self._uio.info("No component placement files found.")
        else:
            for placementFile, placementFileName, side in placementList:
                self._uio.info("Found {} component placement file.".format(placementFileName))
                outputPlacementFile = join(self._pcbFileFolder, placementFileName)
                # If the src placement file exists
                if os.path.isfile(placementFile):
                    fd = open(placementFile, 'r')
                    lines = fd.readlines()
                    fd.close()
                    newLines = []
                    updatedHeader = False
                    for line in lines:
                        if line.startswith("Ref,Val,Package,PosX,PosY,Rot,Side"):
                            newLines.append("Designator,Val,Package,Mid X,Mid Y,Rotation,Layer")
                            self._uio.info("Updated {} to JLCPCB column headers.".format(outputPlacementFile))
                            updatedHeader = True
                        else:
                            newLines.append(line)

                    if not updatedHeader:
                        raise Exception("Failed to update the header from the {} placement file.".format(placementFile))

                    outputPlacementFilename = "{}_{}_placement.csv".format(self._projectName,side)
                    outputPlacementFile = join(self._pcbFileFolder, outputPlacementFilename)
                    self._save(outputPlacementFile, newLines)
                    processedPlacementFiles.append(outputPlacementFile)
        return processedPlacementFiles

    def _checkBOMFormat(self, bomFile):
        """@brief Check the BOM file format and correct if possible."""
        fd = open(bomFile, 'r')
        lines = fd.readlines()
        fd.close()
        for line in lines:
            fieldList = self._getBOMFieldList(line)
            if len(fieldList) != 4:
                line=line.rstrip("\r\n")
                self._fixupBOM(bomFile)
                break

    def _processBOMFiles(self):
        """@brief Process the BOM files files.
           @return A list of the processed BOM files."""
        bomFileFound = None
        searchPaths = PCBFileProcessor.ASSY_SEARCH_PATHS
        bomFileName = "{}.csv".format(self._projectName)
        expectedBOMFileList = []
        for bomPath in searchPaths:
            bomFile = path.join(bomPath, bomFileName)
            expectedBOMFileList.append(bomFile)
            if path.isfile(bomFile):
                bomFileFound = bomFile
                self._uio.info("Found {} BOM file.".format(bomFileFound))
                break

        if bomFileFound is None:
            self._uio.info("Possible BOM input files.")
            for expectedBOMFile in expectedBOMFileList:
                self._uio.info(expectedBOMFile)
            raise Exception("Unable to find any of the above BOM files.")

        # We work on a copy of the BOM file in the assy output folder with the name that JLCPCB require
        bomOutputFile = join(self._pcbFileFolder, "{}_{}_bom.csv".format(self._projectName, self._projectVersion) )
        if os.path.isfile(bomOutputFile):
            if self._overWrite:
                shutil.copy(bomFileFound, bomOutputFile)
                self._info("Removed old {} file.".format(bomOutputFile))
                self._info("Copied {} to {}".format(bomFile, bomOutputFile))
        else:
            shutil.copy(bomFileFound, bomOutputFile)
            self._info("Copied {} to {}".format(bomFile, bomOutputFile))            
                            
        self._checkBOMFormat(bomOutputFile)

    def _getBOMFieldList(self, line):
        """@brief Get the list of fields expected in a BOM.
           @return A list of fields for the BOM"""
        line=line.rstrip("\r\n")
        elems = line.split('"')
        fieldList = []
        for elem in elems:
            if len(elem) > 0 and elem != ',':
                fieldList.append(elem)

        # If we don't have enough fields create empty ones
        if len(fieldList) < 4:
            while len(fieldList) < 4:
                fieldList.append("")

        return fieldList

    def _fixupBOM(self, bomFile):
        """@brief Fixup the BOM to the format required by JLCPCB."""
        fd = open(bomFile, 'r')
        lines = fd.readlines()
        fd.close()
        newLines = []
        foundDefaultFormat = True
        for line in lines:
            if line.find("Id") > 0 and\
               line.find("Designator") > 0 and\
               line.find("Package") > 0 and\
               line.find("Quantity") > 0 and\
               line.find("Designation") > 0 and\
               line.find("Supplier and ref") > 0:
               newLines.append('"Comment","Designator","Footprint","LCSC"')
               foundDefaultFormat = True
            elif foundDefaultFormat:
               elems = line.split(";")
               value=elems[4]
               designator=elems[1]
               footPrint=elems[2]
               pn=""
               newLines.append('{},{},{},{}'.format(value, designator, footPrint, pn))

        fd = open(bomFile, 'w')
        for line in newLines:
            fd.write("{}\n".format(line))
        fd.close()
        self._uio.info("Updated {} to JLCPCB BOM format.".format(bomFile))

if __name__ == "__main__":
    uio = UIO()

    try:
        parser = argparse.ArgumentParser(description="Helper program for building PCB gerber zip files prior to MFG.", formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("-d", "--debug",        help="Enable debugging.",     action='store_true')
        parser.add_argument("-a", "--assy",         help="In adition to the gerber files process the BOM and component placement files for PCB assembly.", action="store_true")
        parser.add_argument("-n", "--no_preview",   help="Do not preview files. The default is to preview the gerber files using either gerbv or the gerbview programs.", action='store_true')
        parser.add_argument("-s",                   help="Show the Kicad settings required to generate gerbers for JLCPCB. Also the Kicad/JLCPCB helper link is opened using the default web browser.", action="store_true")
        parser.add_argument("-v", "--view_zip",     help="The gerber zip file to view. This option can be used if the user only wants to view the contents of an existing zip files containing PCB gerber files.")
        parser.add_argument("--gerbview",           help="Use gerbview (Included with KiCad) not the default gerbv program which must be installed separately ('sudo apt install gerbv') to view gerbers.", action="store_true")

        options = parser.parse_args()

        pcbFileProcessor = PCBFileProcessor(uio, options)
        uio.enableDebug(options.debug)

        if options.view_zip:
            pcbFileProcessor.gerbvFiles(options.view_zip, options.gerbview)

        elif options.s:
            pcbFileProcessor.showKicadSettings()

        elif options.gerbview:
            zipFile = pcbFileProcessor.zipFiles()
            pcbFileProcessor.gerbvFiles(zipFile, options.gerbview)

        else:
            zipFile = pcbFileProcessor.zipFiles()
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
