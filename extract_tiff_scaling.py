import os, sys, getopt
import tkinter as tk
import tifffile
from PIL import Image
Image.MAX_IMAGE_PIXELS = 1000000000 # prevent decompressionbomb warning for typical images
from PIL.TiffTags import TAGS
from tkinter import filedialog
import set_tiff_scaling

def programInfo():
    print("#########################################################")
    print("# A Script to extract the scaling in TIFFs edited by    #")
    print("# ImageJ                                                #")
    print("#                                                       #")
    print("# © 2021 Florian Kleiner                                #")
    print("#   Bauhaus-Universität Weimar                          #")
    print("#   F. A. Finger-Institut für Baustoffkunde             #")
    print("#                                                       #")
    print("#########################################################")
    print()

class unit():
    unitArray          = [  'nm',  'µm',  'mm',  'cm',  'dm',   'm' ]
    unitFactorArray    = [     1, 10**3, 10**6, 10**7, 10**8, 10**9 ]
    unitFactorArrayInv = [ 10**9, 10**6, 10**3, 10**2,    10,     1 ]

    def convert_to_nm( self, value, unit, squared=False):
        pos = 0
        result = value
        for u in self.unitArray:
            if u == unit:
                result = value*(self.unitFactorArray[pos]**2) if squared else value*self.unitFactorArray[pos]
                break
            pos += 1

        return result

    def make_length_readable( self, value, unit, decimal = 0 ):
        pos = 0
        f = 1
        if unit in self.unitArray:
            if unit != 'nm': value = convert_to_nm(value, unit)
            for factor in self.unitFactorArray:
                if value*(10**decimal) > factor:
                    f = factor
                    pos += 1
                else:
                    break
        else:
            print( 'The unit {} is not valid'.format(unit) )

        return value/f, self.unitArray[pos]

    def make_area_readable( self, value, unit, decimal = 0 ):
        unit = unit.replace('²','')
        pos = -1
        f = 1
        if unit in self.unitArray:
            if unit != 'nm': value = convert_to_nm(value, unit, True)
            for factor in self.unitFactorArray:
                if value*(10**decimal) > factor**2:
                    f = factor**2
                    pos += 1
                else:
                    break
        else:
            print( 'The unit {} is not valid'.format(unit) )
        if pos < 0: pos = 0
        #print(value, unit, value/f, self.unitArray[unit_pos]+'²', unit_pos)
        return value/f, self.unitArray[pos]+'²'

    def get_area_in_unit( self, value, unit, to_unit ):
        to_unit = to_unit.replace('²','')
        unit = unit.replace('²','')
        if to_unit in self.unitArray and unit in self.unitArray:
            pos = 0
            for u in self.unitArray:
                if u == to_unit:
                    break
                pos += 1
            value = value/(self.unitFactorArray[pos]**2)
        else:
            print( 'The units {} and/or {} are not valid'.format(unit, to_unit) )
        return value

    def autodetect_unit(self, value):
        unit = 'px'
        factorPos = 0
        for i, factor in enumerate(self.unitFactorArrayInv):
            if ( value * factor > 1 and unit == 'px'):
                #print(value * factor)
                if i > 0: factorPos = i - 1
                break

        #print( '  {:.4f} {}/px'.format(value*self.unitFactorArrayInv[factorPos], self.unitArray[factorPos]) )
        return self.unitFactorArrayInv[factorPos], self.unitArray[factorPos]

def getEmptyScaling():
    return { 'x' : 1, 'y' : 1, 'unit' : 'px', 'editor':None}

def getImageJScaling( filename, workingDirectory, verbose = False ):
    UC = unit()
    scaling = getEmptyScaling()
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
            if ( 'ImageJ' in IJSettingsArray ):
                if ( IJSettingsArray['ImageJ'] == 'FA.FIB.Toolbox' ):
                    if verbose: print( '  Image edited using F.A. Finger Institute Toolbox' )
                    scaling['editor'] = 'F.A. FIB Toolbox'
                if ( IJSettingsArray['ImageJ'] == 'FEI-SEM' ):
                    if verbose: print( '  Image edited using F.A. Finger Institute Toolbox using Metadata from a FEI / thermoScientific device' )
                    scaling['editor'] = 'F.A. FIB Toolbox'
                else:
                    if verbose: print( '  Image edited using ImageJ ' + IJSettingsArray['ImageJ'] )
                    scaling['editor'] = 'ImageJ ' + IJSettingsArray['ImageJ']
            if ( 'unit' in IJSettingsArray ):
                scaling['unit'] = IJSettingsArray['unit']
                # images < 1 nm/px were recognized falsely in previeous versions and no valid unit was assigned.
                if not scaling['unit'] in UC.unitArray and scaling['x'] < 1 and scaling['x'] > 0 :
                    if verbose: print('scale given but unit {} seems wrong'.format(scaling['unit']))
                    factor, scaling['unit'] = UC.autodetect_unit(scaling['x'])
                    scaling['x'] *= factor
                    scaling['y'] *= factor
                if verbose: print( '  {} x {} {}/px'.format(round( scaling['x'], 4), round( scaling['y'], 4), scaling['unit']) )
            elif verbose:
                print( '  unitless scaling: {} x {}'.format(round( scaling['x'], 4), round( scaling['y'], 4)) )
    if verbose: print()
    return scaling

def isFEIImage( filename, workingDirectory, verbose = False ):
    with tifffile.TiffFile( workingDirectory + os.sep + filename ) as tif:
        if ( tif.fei_metadata != None ):
            return True
        else:
            if verbose: print('  no FEI / thermoScientific-Image')
    return False

def getFEIScaling( filename, workingDirectory, verbose=False, save_scaled_image=False ):
    scaling = getEmptyScaling()
    UC = unit()
    with tifffile.TiffFile( workingDirectory + os.sep + filename ) as tif:
        #print(tif.pages[0].tags)
        if ( tif.fei_metadata != None ):
            if verbose: print( 'SEM image saved by an FEI / thermoScientific device' )
            scaling['editor'] = 'FEI-SEM'
            scaling['x'] = float( tif.fei_metadata['Scan']['PixelWidth'] )
            scaling['y'] = float( tif.fei_metadata['Scan']['PixelHeight'] )

            #print('autodetect unit', scaling)
            factor, scaling['unit'] = UC.autodetect_unit(scaling['x'])
            scaling['x'] *= factor
            scaling['y'] *= factor
            #print(scaling)
            #print(set_tiff_scaling.setImageJScaling( scaling, True ))

            if save_scaled_image:
                with Image.open( workingDirectory + os.sep + filename ) as img:
                    filename_scaled = workingDirectory + os.sep + 'Scaled_' + filename if verbose else workingDirectory + os.sep + filename
                    img.save( filename_scaled, tiffinfo = set_tiff_scaling.setImageJScaling( scaling ) )
        else:
            if verbose: print('  no FEI / thermoScientific-Image')

    return scaling

def autodetectScaling( filename, workingDirectory, verbose = False ):
    scaling = getImageJScaling( filename, workingDirectory, verbose=verbose )
    if scaling['editor'] == None:
        print('trying to detect FEI scaling')
        scaling = getFEIScaling( filename, workingDirectory, save_scaled_image=False, verbose=verbose )
    if scaling['editor'] == None:
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