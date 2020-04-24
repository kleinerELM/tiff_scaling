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

    info = {}#img.tag
    info[282] = round(1/scaling['x'], 6)
    info[283] = round(1/scaling['y'], 6)
    x = datetime.datetime.now()
    if ( not 'editor' in scaling or scaling['editor'] == '' ):
        scaling['editor'] = 'FA.FIB.Toolbox'#'F.A. FIB Toolbox'
    info[270] = "ImageJ=" + scaling['editor'] + "\nunit=" + scaling['unit']#(( scaling['editor'] + '=' + x.strftime("%Y.%m.%d") + "\nunit=" + scaling['unit'] ), )

    return info

### actual program start
if __name__ == '__main__':
    #remove root windows
    root = tk.Tk()
    root.withdraw()
  
    ### global settings    
    programInfo()

    settings = {}
    settings["filepath"] = filedialog.askopenfilename(title='Please select the image',filetypes=[("Tiff images", "*.tif;*.tiff")])
    settings["workingDirectory"] = os.path.dirname( settings["filepath"] )
    
    print( "Set the unit of scaling. Input example: 2.123456" )
    print( "Set the unit of scaling (Standard nm)", end=": " )
    unit = input()
    if unit == '': unit = 'nm'

    print( 'Set the scaling of the image. Input example: 2.123456' )
    print( 'Scaling [' + unit + '/px]', end=": " )
    scale = float( input() )

    scaling = { 'x' : scale, 'y' : scale, 'unit' : unit}

    with Image.open( settings["workingDirectory"] + '/' + os.path.basename( settings["filepath"] ) ) as img:
        img.save( settings["workingDirectory"] + '/Scaled_' + os.path.basename( settings["filepath"] ), tiffinfo = setImageJScaling( scaling ) ) 

    print( "Script DONE!" )