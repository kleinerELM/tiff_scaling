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

def getImageJScaling( filename, workingDirectory ):
    scaling = { 'x' : 1, 'y' : 1, 'unit' : 'px', 'editor':None}
    with Image.open( workingDirectory + '/' + filename ) as img:
        if ( 282 in img.tag ) and ( 283 in img.tag ):
            print( img.tag[282] ) #x
            print( img.tag[283] ) #y
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
                    print( '  Image edited using F.A. Finger Institute Toolbox' )
                    scaling['editor'] = 'F.A. FIB Toolbox'
                if ( IJSettingsArray['ImageJ'] == 'FEI-SEM' in IJSettingsArray ):
                    print( '  Image edited using F.A. Finger Institute Toolbox using Metadata from a FEI / thermoScientific device' )
                    scaling['editor'] = 'F.A. FIB Toolbox'
                else:
                    print( '  Image edited using ImageJ ' + IJSettingsArray['ImageJ'] )
                    scaling['editor'] = 'ImageJ ' + IJSettingsArray['ImageJ']
            if ( 'unit' in IJSettingsArray ):
                scaling['unit'] = IJSettingsArray['unit']
                print( '  ' + str( round( scaling['x'], 4) ) + ' x ' + str( round( scaling['y'], 4) ) + ' ' + scaling['unit'] )
            else :
                print( '  unitless scaling: ' + str( round( scaling['x'], 4) ) + ' x ' + str( round( scaling['y'], 4) ) )
    print()
    return scaling

def getFEIScaling( filename, workingDirectory ):
    unitArray = [ 'm', 'mm', 'µm', 'nm' ]
    unitFactorArray = [ 1, 1000, 1000000, 1000000000 ]
    scaling = { 'x' : 1, 'y' : 1, 'unit' : 'px', 'editor':None}
    with tifffile.TiffFile( workingDirectory + '/' + filename ) as tif:
        if ( tif.fei_metadata != None ):
            print( 'SEM image saved by an FEI / thermoScientific device' )
            scaling['editor'] = 'FEI-SEM'
            scaling['x'] = float( tif.fei_metadata['Scan']['PixelWidth'] )
            scaling['y'] = float( tif.fei_metadata['Scan']['PixelHeight'] )
            factorPos = 0
            for factor in unitFactorArray:
                if ( scaling['x'] * factor >=1 and scaling['unit'] == 'px'):
                    scaling['unit'] = unitArray[factorPos]
                    scaling['x'] = scaling['x'] * factor
                    scaling['y'] = scaling['y'] * factor
                    print( '  ' + str( scaling['x'] ) + ' ' + scaling['unit'] )
                else:
                    factorPos += 1

            with Image.open( workingDirectory + '/' + filename ) as img:
                img.save( workingDirectory + '/Scaled_' + filename, tiffinfo = set_tiff_scaling.setImageJScaling( scaling ) )
        else:
            print('  no FEI / thermoScientific-Image')

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
    if ( showDebuggingOutput ) : print( "I am living in '" + home_dir + "'" )
    settings["filepath"] = filedialog.askopenfilename(title='Please select the reference image',filetypes=[("Tiff images", "*.tif;*.tiff")])
    settings["workingDirectory"] = os.path.dirname( settings["filepath"] )

    scaling = getImageJScaling( os.path.basename( settings["filepath"] ), settings["workingDirectory"] )
    if ( scaling['editor'] == None ):
        scaling = getFEIScaling( os.path.basename( settings["filepath"] ), settings["workingDirectory"] )
    if ( scaling['editor'] == None ):
        print( 'The file was not saved using ImageJ or a SEM by FEI / thermoScientific' )

    print( "Script DONE!" )