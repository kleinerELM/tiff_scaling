import os, sys, getopt
import tkinter as tk
import tifffile
from PIL import Image
from PIL.TiffTags import TAGS
from tkinter import filedialog
import set_tiff_scaling

def programInfo():
    print("#########################################################")
    print("# A Script to extract the scaling in TIFFs edited by    #")
    print("# ImageJ                                                #")
    print("#                                                       #")
    print("# © 2020 Florian Kleiner                                #")
    print("#   Bauhaus-Universität Weimar                          #")
    print("#   F. A. Finger-Institut für Baustoffkunde             #")
    print("#                                                       #")
    print("#########################################################")
    print()

def getImageJScaling( filename, workingDirectory, verbose = False ):
    scaling = { 'x' : 1, 'y' : 1, 'unit' : 'px', 'editor':None}
    with Image.open( workingDirectory + os.sep + filename ) as img:
        if ( 282 in img.tag ) and ( 283 in img.tag ):
            if verbose: print( img.tag[282] ) #x
            if verbose: print( img.tag[283] ) #y
            x_tag = img.tag[282][0]
            y_tag = img.tag[283][0]
            scaling['x'] = int( x_tag[1] )/ int( x_tag[0] )
            scaling['y'] = int( y_tag[1] )/ int( y_tag[0] )
        if 270 in img.tag:         
            #print( img.tag[270] )   
            # getimagej definitions
            IJSettingString = img.tag[270][0].split('\n')
            #print( IJSettingString )   
            IJSettingsArray = {}
            for val in IJSettingString:
                if ( val != '' ):
                    setting = val.split('=')
                    IJSettingsArray[setting[0]] = setting[1]
            #print(IJSettingsArray)
            if ( 'ImageJ' in IJSettingsArray ):
                if ( IJSettingsArray['ImageJ'] == 'FA.FIB.Toolbox' in IJSettingsArray ):
                    if verbose: print( '  Image edited using F.A. Finger Institute Toolbox' )
                    scaling['editor'] = 'F.A. FIB Toolbox'
                if ( IJSettingsArray['ImageJ'] == 'FEI-SEM' in IJSettingsArray ):
                    if verbose: print( '  Image edited using F.A. Finger Institute Toolbox using Metadata from a FEI / thermoScientific device' )
                    scaling['editor'] = 'F.A. FIB Toolbox'
                else:
                    if verbose: print( '  Image edited using ImageJ ' + IJSettingsArray['ImageJ'] )
                    scaling['editor'] = 'ImageJ ' + IJSettingsArray['ImageJ']
            if ( 'unit' in IJSettingsArray ):
                scaling['unit'] = IJSettingsArray['unit']
                print( '  {} x {} {}/px'.format(round( scaling['x'], 4), round( scaling['y'], 4), scaling['unit']) )
            else :
                print( '  unitless scaling: {} x {}'.format(round( scaling['x'], 4), round( scaling['y'], 4)) )
    print()
    return scaling

def getFEIScaling( filename, workingDirectory, verbose = False ):
    unitArray = [ 'm', 'mm', 'µm', 'nm' ]
    unitFactorArray = [ 1, 1000, 1000000, 1000000000 ]
    scaling = { 'x' : 1, 'y' : 1, 'unit' : 'px', 'editor':None}
    with tifffile.TiffFile( workingDirectory + os.sep + filename ) as tif:
        if ( tif.fei_metadata != None ):
            if verbose: print( 'SEM image saved by an FEI / thermoScientific device' )
            scaling['editor'] = 'FEI-SEM'
            scaling['x'] = float( tif.fei_metadata['Scan']['PixelWidth'] )
            scaling['y'] = float( tif.fei_metadata['Scan']['PixelHeight'] )
            factorPos = 0
            for factor in unitFactorArray:
                if ( scaling['x'] * factor >=1 and scaling['unit'] == 'px'):
                    scaling['unit'] = unitArray[factorPos]
                    scaling['x'] = scaling['x'] * factor
                    scaling['y'] = scaling['y'] * factor
                    print( '  {} {}/px'.format(scaling['x'], scaling['unit']) )
                else:
                    factorPos += 1

            with Image.open( workingDirectory + os.sep + filename ) as img:
                filename_scaled = workingDirectory + os.sep + 'Scaled_' + filename if verbose else workingDirectory + os.sep + filename
                img.save( filename_scaled, tiffinfo = set_tiff_scaling.setImageJScaling( scaling ) )
        else:
            if verbose: print('  no FEI / thermoScientific-Image')

    return scaling

def autodetectScaling( filename, workingDirectory, verbose = False ):
    scaling = getImageJScaling( filename, workingDirectory )
    if ( scaling['editor'] == None ):
        scaling = getFEIScaling( filename, workingDirectory )
    if ( scaling['editor'] == None ):
        print( '{} was not saved using ImageJ or a SEM by FEI / thermoScientific'.format(filename) )
    return scaling

### actual program start
if __name__ == '__main__':
    #remove root windows
    root = tk.Tk()
    root.withdraw()
  
    ### global settings    
    programInfo()

    #### directory definitions
    home_dir = os.path.dirname(os.path.realpath(__file__))
    showDebuggingOutput = True

    settings = {}

    ### actual program start
    if ( showDebuggingOutput ) : print( "I am living in '{}'".format(home_dir) )
    settings["filepath"] = filedialog.askopenfilename(title='Please select the reference image',filetypes=[("Tiff images", "*.tif;*.tiff")])
    settings["workingDirectory"] = os.path.dirname( settings["filepath"] )
    
    scale = autodetectScaling( os.path.basename( settings["filepath"] ), settings["workingDirectory"] )

    print(scale)

    print( "Script DONE!" )