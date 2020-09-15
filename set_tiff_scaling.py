import os, sys, getopt
import tkinter as tk
import tifffile
from PIL import Image
from PIL.TiffTags import TAGS
from tkinter import filedialog
import datetime

def programInfo():
    print("#########################################################")
    print("# A Script to set the scaling used in ImageJ in TIFFs   #")
    print("#                                                       #")
    print("# © 2020 Florian Kleiner                                #")
    print("#   Bauhaus-Universität Weimar                          #")
    print("#   F. A. Finger-Institut für Baustoffkunde             #")
    print("#                                                       #")
    print("#########################################################")
    print()

def setImageJScaling( scaling ):
    print('  set ImageJ scaling...')
    info = {}
    info[282] = round(1/scaling['x'], 6)
    info[283] = round(1/scaling['y'], 6)
    x = datetime.datetime.now()
    if ( not 'editor' in scaling or scaling['editor'] == '' ):
        scaling['editor'] = 'FA.FIB.Toolbox'#'F.A. FIB Toolbox'
    info[270] = "ImageJ=" + scaling['editor'] + "\nunit=" + scaling['unit']

    return info

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
    
    #print( 'Replace the processed file? y/n [n]', end=": " )
    #replaceFile = input()
    #if ( replaceFile == 'y' ): 
    #    file_prefix = ''
    #else:
    #    file_prefix = 'scaled_'
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
        settings["workingDirectory"] = filedialog.askdirectory(title='Please select the image / working directory')
        
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