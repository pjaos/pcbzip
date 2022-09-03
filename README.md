# pcbzip

## Description
A command line tool to ease the process of creating the files required to manufacture a PCB
using KiCad.

# Installation

- Clone the git repo.

```
git clone git@github.com:pjaos/pcbzip.git
```

- cd into the folder containg the repo contents.

```
cd pcbzip
```

- Install the pcbzip command line tool on your local machine by running the following command.

```
sudo ./install.sh
Processing /tmp/pcbzip
  Preparing metadata (setup.py) ... done
Requirement already satisfied: pillow>=9.0.0 in /usr/local/lib/python3.8/dist-packages (from pcbzip==1.5) (9.0.1)
Building wheels for collected packages: pcbzip
  Building wheel for pcbzip (setup.py) ... done
  Created wheel for pcbzip: filename=pcbzip-1.5-py3-none-any.whl size=13808 sha256=5f9646e0abaca97b1fef54d3ab35b5fd45396fe8cdd5e2a00caeeac498d2b8a6
  Stored in directory: /tmp/pip-ephem-wheel-cache-9eyalw2n/wheels/82/a8/08/8562420c5236c6f7ce7a4ccefb4025f6a8aa2b8878706b0903
Successfully built pcbzip
Installing collected packages: pcbzip
  Attempting uninstall: pcbzip
    Found existing installation: pcbzip 1.5
    Uninstalling pcbzip-1.5:
      Successfully uninstalled pcbzip-1.5
Successfully installed pcbzip-1.5
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv
```

This should be installed onto a Linux machine that has KiCad installed.
gerbv should also be installed onto the local machine ('sudo apt install gerbv').

# Using the tool

The pcbzip tool allows the user to create a zip file containing the gerber files for a PCB which can be supplied to the
manufacturer so that they can make the PCB. Also (if Kicad 6 and JLCPCB is selected) it allows the user to create the
Bill Of MAterials (BOM) file and component placement files required for PCB assembly.


## Creating a PCB using JLCPCB

To use the tool you need to open a terminal window in folder that holds the KiCad gerber files
and then enter.

If you intend to use JLCPCB to manufacture the PCB and assemble it then the [bom2grouped_csv_jlcpcb.xsl](https://gist.github.com/arturo182/a8c4a4b96907cfccf616a1edb59d0389)
must have been used to create the BOM for the board.

```
pcbzip
```

You will then be prompted to select the PCB manufacturer.

```
pcbzip
INFO:  Supported manufacturers
INFO:  SeedStudio:        1
INFO:  PCBWay:            2
INFO:  JLCPCB (Kicad V5): 3
INFO:  JLCPCB (Kicad V6): 4
INPUT: Manufacturer:
```

Enter option 4.

You will then be prompted to enter a project name for the PCB.

E.G

```
INPUT: Enter the project name: myproject
```

You will then be prompted to enter the version number for the project.

E.G

```
INPUT: Enter the version of the board: 1.0
```

Checks are then made that the required files are present. If so then a zip file is created containing gerber files.

```
INFO:  Created ./myproject_1.0_pcb_files/myproject_v1.0_jlcpcb.zip
INFO:  CMDLINE: 'gerbv /tmp/tmps__mohwu/batmon-F_Cu.gtl /tmp/tmps__mohwu/batmon-B_Cu.gbl /tmp/tmps__mohwu/batmon-F_Paste.gtp /tmp/tmps__mohwu/batmon-B_Paste.gbp /tmp/tmps__mohwu/batmon-F_Silkscreen.gto /tmp/tmps__mohwu/batmon-B_Silkscreen.gbo /tmp/tmps__mohwu/batmon-F_Mask.gts /tmp/tmps__mohwu/batmon-B_Mask.gbs /tmp/tmps__mohwu/batmon-Edge_Cuts.gm1 /tmp/tmps__mohwu/batmon-PTH.drl /tmp/tmps__mohwu/batmon-NPTH.drl'
```

The gerbv program will then be called to view the gerber files. When this is closed you will find that a folder (in this case myproject_1.0_pcb_files) has been created
containing the zip file containing the gerber files (in this case myproject_v1.0_jlcpcb.zip). This is the file that can be uploaded to JLCPCB in order to manufacture the PCB.


# Creating and assembling a PCB using JLCPCB

If you wish JLCPCB to manufacture a PCB and assemble it then along with the zip file you need to supply the following files.

- Zip file containing the gerber files.
- A Bill Of Materials (BOM) file.
- A component placement file.

Using pcbzip to create these files then you need to run

```
pcbzip -a
```

You will then be prompted to select the PCB manufacturer.

```
pcbzip
INFO:  Supported manufacturers
INFO:  SeedStudio:        1
INFO:  PCBWay:            2
INFO:  JLCPCB (Kicad V5): 3
INFO:  JLCPCB (Kicad V6): 4
INPUT: Manufacturer:
```

Enter option 4.

You will then be prompted to enter a project name for the PCB.

E.G

```
INPUT: Enter the project name: myproject
```

You will then be prompted to enter the version number for the project.

E.G

```
INPUT: Enter the version of the board: 1.1
```

The zip file containing the gerber files will then be created and you will then be asked which side of the PCB you wish JLCPCB to add parts to.

```
INFO:  Created the ./myproject_1.1_pcb_files folder.
INFO:  Created ./myproject_1.1_pcb_files/myproject_v1.1_jlcpcb.zip
INPUT: PCB side to which SMD components are to be added, t (top) or b (bottom): t
```

Note !!!
The project name must be the same as the KiCad project name.

If you created the project previously and partially updated the assembly information then You'll be
asked if you want to overwrite the project.

```
INFO:  The ./myproject_1.0_pcb_files folder already exists.
INPUT: Overwrite ? y/n: n
```

If you select 'y' then all previous data is overwritten and you'll need to enter all assembly data
again. Selecting 'n' will start from where you left the project previously.

If at this point you get the following error then you have not created the placement files using KiCad.

```
ERROR: Failed to find the placement file (myproject-top-pos.csv) in ['.', '..'].
```

If this occurs then open KiCad PCB and select 'File / Fabrication Outputs / Component Placement (pos)...'. Then select the 'Generate Position File' button. When you've created this file restart pcbzip.

If at this point you get the following error then you have not created the BOM files using KiCad.

```
ERROR: Failed to find the BOM file (myproject.csv) in ['.', '..'].
```

If this occurs then open KiCad PCB and select 'File / Fabrication Outputs / BOM)...'. Then select the 'Save' button. When you've created this file restart pcbzip.

The first time that you run pcbzip yu'll be asked if you wish to fixup the BOM file format as shown below.

```
ERROR: Invalid BOM line: "Id";"Designator";"Package";"Quantity";"Designation";"Supplier and ref";
ERROR: Should have four fields (Comment,Designator,Footprint,LCSC)
INPUT: Do you wish to fixup the BOM file format ? [y/n]: y
INFO:  Updated ../myproject.csv
```

Enter 'y' to fixup the BOM file to the formay required by JLCPCB.

When the KiCad BOM and component placement files are found the component placement file will be copied to the output folder and you will step through each component to assign a JLCPCB part number to each one that you wish JLCPCB to fit.

```
INFO:  Copied ../myproject.csv to ./myproject_1.1_pcb_files/myproject_1.1_bom.csv
INFO:  ---------------------------------------------------------------------------
INFO:  Editing part 1 of 37 parts from ./myproject_1.1_pcb_files/myproject_1.1_bom.csv
INFO:  ---------------------------------------------------------------------------
INFO:  COMMENT:                 100uf
INFO:  DESIGNATOR:              C1
INFO:  FOOTPRINT:               Capacitor_THT:CP_Radial_D10.0mm_P5.00mm
INFO:  JLCPCB PART NUMBER:      
INFO:  
INFO:  Enter
INFO:  - The JLCPCB part number
INFO:  - F to move to the first part
INFO:  - L to move to the last part
INFO:  - N to move to the next part
INFO:  - B to move back to the previous part
INFO:  - A Abort BOM file edit.
INPUT:
```

At this point you'll need another terminal window open displaying the JLCPCB parts database. Details on this can be found in the [Searching JLCPCB Parts Database](#Searching JLCPCB Parts Database) section of this document.

Once you have found the JLCPCB part number for the part to be fitted enter it. The next part in the BOM will then be displayed.

E.G

```
INFO:  ---------------------------------------------------------------------------
INFO:  Editing part 1 of 37 parts from ./myproject_1.1_pcb_files/myproject_1.1_bom.csv
INFO:  ---------------------------------------------------------------------------
INFO:  COMMENT:                 100uf
INFO:  DESIGNATOR:              C1
INFO:  FOOTPRINT:               Capacitor_THT:CP_Radial_D10.0mm_P5.00mm
INFO:  JLCPCB PART NUMBER:      
INFO:  
INFO:  Enter
INFO:  - The JLCPCB part number
INFO:  - F to move to the first part
INFO:  - L to move to the last part
INFO:  - N to move to the next part
INFO:  - B to move back to the previous part
INFO:  - A Abort BOM file edit.
INPUT: C216
INFO:  Set JLCPCB part number to C216
INFO:  Saved ./myproject_1.1_pcb_files/myproject_1.1_bom.csv
```

The part is saved to the bom file and then you will be presented with the next part to be assigned.

E.G

```
INFO:  ---------------------------------------------------------------------------
INFO:  Editing part 2 of 37 parts from ./myproject_1.1_pcb_files/myproject_1.1_bom.csv
INFO:  ---------------------------------------------------------------------------
INFO:  COMMENT:                 DNF
INFO:  DESIGNATOR:              C2,C5
INFO:  FOOTPRINT:               Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm_HandSolder
INFO:  JLCPCB PART NUMBER:      
INFO:  
INFO:  Enter
INFO:  - The JLCPCB part number
INFO:  - F to move to the first part
INFO:  - L to move to the last part
INFO:  - N to move to the next part
INFO:  - B to move back to the previous part
INFO:  - A Abort BOM file edit.
INPUT:
```

If you press enter without entering a part number then no JLCPCB part number is assigned to that part and JLCPCB will not fit it to the PCB.
If you wish to move backwards and forwards through the list of parts in the BOM then the F,L,N,B entries can be used. If you abort the BOM
file part assignment process then you can pick up where you left off at another time if required because as each part is entered the BOM
file is updated.


# Searching JLCPCB Parts Database

At this point you need to open a terminal window. The current state of the JLCPCB parts database should be downloaded using the following command so that you have a local, up to date copy of the available JLCPCB parts. Run the command below to do this.

```
pcbzip -u
INFO:  Deleted existing /home/auser/.jlcpcb/parts.csv file.
INFO:  Downloading https://jlcpcb.com/componentSearch/uploadComponentInfo
100% [......................................................................] 367401506 / 367401506
INFO:  Took 28.4 seconds to download /home/pja/.jlcpcb/parts.csv
INFO:  Updated /home/auser/.jlcpcb/parts.csv.date with creation date.
INFO:  Deleted existing /home/auser/.jlcpcb/parts.db file.
INFO:  Creating /home/auser/.jlcpcb/parts.db file from /home/auser/.jlcpcb/parts.csv file...
INFO:  Took 7.5 seconds to create /home/auser/.jlcpcb/parts.db
```

The time this takes to complete will be largely dependent upon your Internet access speed and how fast your Linux computer is.

Now you have a local copy of the parts database you can search it to find the part you require using the following command.

```
pcbzip -f
INFO:  
INFO:  Current Search Parameters
INFO:  Category:                    
INFO:  MFG Part Number:             
INFO:  Description:                 
INFO:  Package:                     
INFO:  Type:                        
INFO:  Show Only Stock > 0:         Yes
INFO:  Show Only One Off Pricing:   No
INFO:  Field List:                  LCSC Part,Stock,MFR.Part,Package,Library Type,Price,Description
INFO:  Show Order Field:            LCSC Part
INFO:  Field Column Width List:     4,7,25,25,8,12,90
INFO:  Max Part Count:  1000
INFO:  
INFO:  Options.
INFO:  C -  Enter a part category.
INFO:  M -  Enter the MFG part number.
INFO:  D -  Enter a part description.
INFO:  P -  Enter a part package.
INFO:  J -  JLCPCB part number.
INFO:  T -  Enter a part type (Basic or Extended).
INFO:  R -  Reset/Clear search parameters.
INFO:  S -  Search parts database using the selected parameters.
INFO:  SP - Toggle Show only parts where stock > 0.
INFO:  OP - Toggle One Off Only Pricing.
INFO:  FL - Enter a list of fields/columns to display.
INFO:  OF - Enter the field/column to order to display.
INFO:  CS - Enter a list of field/column sizes.
INFO:  MA - Enter the maximum number of parts to display.
INFO:  BA - JLCPCB Basic parts list.
INFO:  
INPUT: Option:
```

This menu provides a way to search the parts database.

E.G
Search for the ADS1115 part

```
INFO:  Options.
INFO:  C -  Enter a part category.
INFO:  M -  Enter the MFG part number.
INFO:  D -  Enter a part description.
INFO:  P -  Enter a part package.
INFO:  J -  JLCPCB part number.
INFO:  T -  Enter a part type (Basic or Extended).
INFO:  R -  Reset/Clear search parameters.
INFO:  S -  Search parts database using the selected parameters.
INFO:  SP - Toggle Show only parts where stock > 0.
INFO:  OP - Toggle One Off Only Pricing.
INFO:  FL - Enter a list of fields/columns to display.
INFO:  OF - Enter the field/column to order to display.
INFO:  CS - Enter a list of field/column sizes.
INFO:  MA - Enter the maximum number of parts to display.
INFO:  BA - JLCPCB Basic parts list.
INFO:  
INPUT: Option: M
INPUT: Enter the MFG part number: ADS1115
INFO:  
INFO:  Current Search Parameters
INFO:  Category:                    
INFO:  MFG Part Number:             ADS1115
INFO:  Description:                 
INFO:  Package:                     
INFO:  Type:                        
INFO:  Show Only Stock > 0:         Yes
INFO:  Show Only One Off Pricing:   No
INFO:  Field List:                  LCSC Part,Stock,MFR.Part,Package,Library Type,Price,Description
INFO:  Show Order Field:            LCSC Part
INFO:  Field Column Width List:     4,7,25,25,8,12,90
INFO:  Max Part Count:  1000
INFO:  
INFO:  Options.
INFO:  C -  Enter a part category.
INFO:  M -  Enter the MFG part number.
INFO:  D -  Enter a part description.
INFO:  P -  Enter a part package.
INFO:  J -  JLCPCB part number.
INFO:  T -  Enter a part type (Basic or Extended).
INFO:  R -  Reset/Clear search parameters.
INFO:  S -  Search parts database using the selected parameters.
INFO:  SP - Toggle Show only parts where stock > 0.
INFO:  OP - Toggle One Off Only Pricing.
INFO:  FL - Enter a list of fields/columns to display.
INFO:  OF - Enter the field/column to order to display.
INFO:  CS - Enter a list of field/column sizes.
INFO:  MA - Enter the maximum number of parts to display.
INFO:  BA - JLCPCB Basic parts list.
INFO:  
INPUT: Option: s
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
| Item | LCSC | Stock   | MFR.Part                  | Package                   | Library  | Price        | Description                                                                                |
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
| 1    | C375 | 2772    | ADS1115IDGSR              | MSOP-10_3.0x3.0x0.5P      | Extended | 1-9:$6.33 10 | 2,4 Differential, Single Ended 16 860 VSSOP-10 Analog To Digital Converters (ADCs) ROHS    |
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
INPUT: Press enter to return to parts selection:
```

Once you have the JLCPCB part number you can copy it into the terminal window under [Creating and assembling a PCB using JLCPCB](#Creating and assembling a PCB using JLCPCB) and an then move on to the next part.

The search tool provides the following functionality.

- C  : Select a part category for a part. This option displays a list of all the JLCPCB part categories.
- M  : The manufactures part number for the device/part that you wish to search for.
- D  : Enter text that occurs in the part description field.
- P  : Enter text that appears in the package type field.
- J  : Enter the text that occurs in the JLCPCB part number field.
- T  : The part type (Basic or Extended).
- R  : This resets the search parameters (Displayed under 'Current Search Parameters').
- S  : Search through the database for a matching part.
- SP : Toggle the option to only show parts where the stock is > 0.
- OP : Toggle the option that only shows parts that have a one off pricing.
- FL : This option allows the user to select which fields from the database should appear as columns in the search results.
- CS : Enter a list of column sizes for the selected fields. You may wish to truncate some columns depending upon the screen size on your computer.
- OF : This option allows you to select the field/column that you wish to order search results on.
- MA : Sets the limit on the maximum number of rows to be displayed.
- BA : The option displays the location of the CSV file containing all Basic JLCPCB parts to allow the user to pull them into a spreadsheet application.
       This makes it easier for users to include Basic parts into their PCB designs.

# Command line help

The following command line help is available for the pcbzip tool.

```
pcbzip -h
usage: pcbzip.py [-h] [-d] [-a] [-f] [-u] [-n] [-s] [-v] [--gerbview]

Helper program for building PCB gerber zip files prior to MFG.

optional arguments:
  -h, --help        show this help message and exit
  -d, --debug       Enable debugging.
  -a, --assy        In adition to the gerber files process the BOM and component placement files for PCB assembly.
  -f, --find        Find parts in the local copy of the JLCPCB parts database.
  -u, --update      Update the local copy of the JLCPCB parts database.
  -n, --no_preview  Do not preview files. The default is to preview the gerber files using either gerbv or the gerbview programs.
  -s                Show the Kicad settings required to generate gerbers for JLCPCB. Also the Kicad/JLCPCB helper link is opened using the default web browser.
  -v, --view_zip    View zip file. This option can be used if the user only wants to view the contents of an existing zip files containing PCB gerber files.
  --gerbview        Use gerbview (Included with KiCad) not the default gerbv program which must be installed separately ('sudo apt install gerbv') to view gerbers.
```
