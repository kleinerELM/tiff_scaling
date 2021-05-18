import os, sys, getopt
import tkinter as tk
import tifffile
from PIL import Image
from PIL.TiffTags import TAGS
from tkinter import filedialog

def programInfo():
    print("#########################################################")
    print("# A Script to set the scaling used in ImageJ in TIFFs   #")
    print("#                                                       #")
    print("# © 2021 Florian Kleiner                                #")
    print("#   Bauhaus-Universität Weimar                          #")
    print("#   F. A. Finger-Institut für Baustoffkunde             #")
    print("#                                                       #")
    print("#########################################################")
    print()

unitArray          = [  'nm',  'µm',  'mm',  'cm',  'dm',   'm' ]
unitFactorArray    = [     1, 10**3, 10**6, 10**7, 10**8, 10**9 ]

def setImageJScaling( scaling, verbose=False ):
    if verbose: print('  set ImageJ scaling...')
    info = {}
    #if scaling['x'] < 1
    info[282] = round(1/scaling['x'], 6)
    info[283] = round(1/scaling['y'], 6)
    if ( not 'editor' in scaling or scaling['editor'] == '' ):
        scaling['editor'] = 'FA.FIB.Toolbox'#'F.A. FIB Toolbox'
    if scaling['editor'] == None: scaling['editor'] = '-'
    info[270] = "ImageJ=" + scaling['editor'] + "\nunit=" + scaling['unit']

    return info

def setCVScaling( scaling, verbose=False ):
    IMWRITE_TIFF_RESUNIT = 256 # For TIFF, use to specify which DPI resolution unit to set; see libtiff documentation for valid values
    IMWRITE_TIFF_XDPI    = 257 # For TIFF, use to specify the X direction DPI
    IMWRITE_TIFF_YDPI    = 258 # For TIFF, use to specify the Y direction DPI
    tiff_info = [int(IMWRITE_TIFF_RESUNIT), 3,
                 int(IMWRITE_TIFF_XDPI   ), int(1/scaling['x']*unitFactorArray[3]),
                 int(IMWRITE_TIFF_YDPI   ), int(1/scaling['y']*unitFactorArray[3])]

### actual program start
if __name__ == '__main__':
    #remove root windows
    root = tk.Tk()
    root.withdraw()

    ### global settings
    programInfo()

    settings = {}

    print( "Set the scale for a single file (f) or all files in a directory (d), [f]", end=": " )
    actionType = input()

    print( 'Set the output folder name (if empty, the new file will be saved with a filename prefix)', end=": " )
    output_folder_name = input()
    if ( output_folder_name == '' ):
        file_prefix = 'scaled_'
    else:
        output_folder_name = output_folder_name + os.sep
        file_prefix = ''

    print( "Set the unit of scaling [nm]", end=": " )
    unit = input()
    if unit == '': unit = 'nm'

    print( 'Set the scaling of the image. Input example: 2.123456' )
    print( 'Scaling [' + unit + '/px]', end=": " )
    scale = float( input() )
    scaling = { 'x' : scale, 'y' : scale, 'unit' : unit}

    if ( actionType == 'd' ):
        print( "Please select a working directory", end="\r" )
        settings["workingDirectory"] = filedialog.askdirectory(title='Please select the directory containing the images')

        if ( output_folder_name != '' ):
            if not os.path.exists(settings["workingDirectory"] + os.sep + output_folder_name):
                os.makedirs(settings["workingDirectory"] + os.sep + output_folder_name)

        fileCount = 0
        position = 0
        for file in os.listdir( settings["workingDirectory"] ):
            if ( file.endswith(".tif") or file.endswith(".TIF")):
                fileCount += 1
        for file in os.listdir( settings["workingDirectory"] ):
            if ( file.endswith(".tif") or file.endswith(".TIF")):
                filename = os.fsdecode(file)
                position = position + 1
                print( " Processing " + filename + " (" + str(position) + " / " + str(fileCount) + ") :" )
                with Image.open( settings["workingDirectory"] + os.sep + filename ) as img:
                    img.save( settings["workingDirectory"] + os.sep + output_folder_name + file_prefix + filename, tiffinfo = setImageJScaling( scaling ) )
        print( "The ImageJ scaling in " + str( position ) + " files is set to " + str( scale ) + " " + unit + "." )
    else:
        settings["filepath"] = filedialog.askopenfilename(title='Please select the image',filetypes=[("Tiff images", "*.tif;*.tiff")])
        settings["workingDirectory"] = os.path.dirname( settings["filepath"] )
        if ( output_folder_name != '' ):
            if not os.path.exists(settings["workingDirectory"] + os.sep + output_folder_name):
                os.makedirs(settings["workingDirectory"] + os.sep + output_folder_name)

        with Image.open( settings["workingDirectory"] + os.sep + os.path.basename( settings["filepath"] ) ) as img:
            img.save( settings["workingDirectory"] + os.sep + output_folder_name + file_prefix + os.path.basename( settings["filepath"] ), tiffinfo = setImageJScaling( scaling ) )
        print( "The ImageJ scaling in the file './" + output_folder_name + file_prefix + os.path.basename( settings["filepath"] ) + "' is set to " + str( scale ) + " " + unit + "." )
    print( "Script DONE!" )