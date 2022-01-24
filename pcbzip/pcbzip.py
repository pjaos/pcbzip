#!/usr/bin/env python3

from   os import listdir, getcwd, system
from   os.path import isfile, join, dirname, join, isfile
import zipfile
import tempfile
import shutil

from   optparse import OptionParser
from   PIL import Image

class MakeError(Exception):
  pass


PCBWAY_REQUIRED_FILES = ["F.Cu.gbr", "F.SilkS.gbr", "F.Mask.gbr", "B.Cu.gbr", "B.SilkS.gbr", "Edge.Cuts.gbr", "B.Mask.gbr", ".drl"]
SEED_STUDIO_REQUIRED_FILES = ["F.SilkS.gto", "F.Cu.gtl", "F.Paste.gtp", "F.Mask.gts", "B.Paste.gbp", "B.Cu.gbl", "B.SilkS.gbo", "B.Mask.gbs", "Dwgs.User.gbr", "Edge.Cuts.gm1", ".drl"]
JCLPCB_REQUIRED_FILES = ["F_Cu.gbr", "F_SilkS.gbr", "F_Mask.gbr", "B_Cu.gbr", "B_SilkS.gbr", "Edge_Cuts.gbr", "B_Mask.gbr", ".drl"]
JCLPCB_REQUIRED_FILES_V6 = ["F_Cu.gtl", "B_Cu.gbl", "F_Paste.gtp", "B_Paste.gbp", "F_Silkscreen.gto", "B_Silkscreen.gbo", "F_Mask.gts", "B_Mask.gbs", "Edge_Cuts.gm1", ".drl"]

def getSortedFileList(fileList):
    """@brief Sort into a sequence that shows the layers stacked from top to bottom in the gerber viewer.
       @param The input file list
       @return The sorted file list."""
    for pcbFile in fileList:

        if pcbFile.endswith(PCBWAY_REQUIRED_FILES[0]):
            mfgFileList = PCBWAY_REQUIRED_FILES
            break

        if pcbFile.endswith(SEED_STUDIO_REQUIRED_FILES[0]):
            mfgFileList = SEED_STUDIO_REQUIRED_FILES
            break

        if pcbFile.endswith(JCLPCB_REQUIRED_FILES[0]):
            mfgFileList = JCLPCB_REQUIRED_FILES
            break

        if pcbFile.endswith(JCLPCB_REQUIRED_FILES_V6[0]):
            mfgFileList = JCLPCB_REQUIRED_FILES_V6
            break

    sortedFileList = []
    for mfgFileEnd in mfgFileList:
        for pcbFile in fileList:
            if pcbFile.endswith(mfgFileEnd):
                sortedFileList.append(pcbFile)

    return sortedFileList

def gerbvFiles(zipFile, gerbview):
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

        fileList = getSortedFileList(fileList)

        if gerbview:

            fileListStr = " ".join(fileList)
            cmdLine = "gerbview %s" % (fileListStr)
            print("CMDLINE: '%s'" % (cmdLine))
            system( cmdLine )

        else:

            fileListStr = " ".join(fileList)
            cmdLine = "gerbv %s" % (fileListStr)
            print("CMDLINE: '%s'" % (cmdLine))
            system( cmdLine )


    finally:
        shutil.rmtree(dirpath)

def zipFiles():
    """@brief Zip up the required gerber files in the current working dir.
       @return The zip file containing the gerber files."""

    print("Supported manufacturers")
    print("SeedStudio:        1")
    print("PCBWay:            2")
    print("JCLPCB (Kicad V5): 3")
    print("JCLPCB (Kicad V6): 4")
    mfg = input("Manufacturer: ")
    if mfg not in ["1", "2", "3", "4"]:
        raise MakeError("Current supported manufacturers are 1, 2, 3 or 4.")
    if mfg == '1':
        REQUIRED_FILES = list(SEED_STUDIO_REQUIRED_FILES)
        mfg="seedstudio"
    elif mfg == '2':
        REQUIRED_FILES = list(PCBWAY_REQUIRED_FILES)
        mfg="pcbway"
    elif mfg == '3': 
        REQUIRED_FILES = list(JCLPCB_REQUIRED_FILES)
        mfg="jclpcb"
    elif mfg == '4': 
        REQUIRED_FILES = list(JCLPCB_REQUIRED_FILES_V6)
        mfg="jclpcb"
    else:
        raise Exception("Invalid MFG ID")
    expectedFiles = REQUIRED_FILES[:]
    
    projectName = input("Enter the project name: ")
    
    version = input("Enter the version of the board: ")
    
    if len(projectName) > 0 and len(version) > 0:
        
        opFile = "%s_v%s_%s.zip" % (projectName, version, mfg)
        
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
            for reqF in REQUIRED_FILES:
                if currentF.endswith(reqF):
                    REQUIRED_FILES.remove(reqF)
                    
        if len(REQUIRED_FILES) > 0:
            print("Expected filename extension list")
            for eFile in expectedFiles:
                print(eFile)

            print("Missing filename extension list")
            for mFile in REQUIRED_FILES:
                print(mFile)
            
            raise MakeError("Not all required files are present (%s are missing)." % (REQUIRED_FILES) )
            
        zf = zipfile.ZipFile(opFile, "w")			
        for f in gerberFileList:
            zf.write(f)
    
        zf.close()
        print("Created %s" % (opFile))
        
        return opFile
	
def showKicadSettings():
    """@brief show the kicad settings required to generate files for the MFG"""

    plotImage = join(dirname(__file__), "jclpcb_kicad_v6_plot.png")
    drillImage = join(dirname(__file__), "jclpcb_kicad_v6_drill.png")
    
    if not isfile(plotImage):
        raise Exception("{} file not found.".format(plotImage))
    
    if not isfile(drillImage):
        raise Exception("{} file not found.".format(drillImage))
    
    im = Image.open(plotImage)
    im.show()

    im = Image.open(drillImage)
    im.show()

if __name__ == "__main__":
    
    opts=OptionParser(usage='Helper program for building PCB gerber zip files prior to MFG.')
    opts.add_option("-n",           help="Do not preview files.", action="store_true", default=False)
    opts.add_option("-s",           help="Show the Kicad settings required to generate gerbers for JCLPCB.", action="store_true")
    opts.add_option("-v",           help="View zip file.", default=None)
    opts.add_option("--gerbview",   help="Use gerbview (Included with KiCad) not the default gerbv program to view gerbers.", action="store_true", default=False)

    try:
        (options, args) = opts.parse_args()
        
        if options.v:
            gerbvFiles(options.v, options.gerbview)

        elif options.s:
            showKicadSettings()
            
        elif options.gerbview:
            zipFile = zipFiles()
            gerbvFiles(zipFile, options.gerbview)
            
        else:
            zipFile = zipFiles()

        
    #If the program throws a system exit exception
    except SystemExit:
      pass
    #Don't print error information if CTRL C pressed
    except KeyboardInterrupt:
      pass
    except:
      raise
       
