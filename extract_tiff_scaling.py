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

    def convert_from_to_unit( self, value, from_unit, to_unit, squared=False):
        pos = 0
        result = value
        from_pos = -1
        to_pos = -1

        for i, u in enumerate(self.unitArray):
            if u == from_unit:
                from_pos = i
            if u == from_unit:
                to_pos = i

        if from_pos >= 0 and to_pos >= 0:
            if from_pos < to_pos:
                f = self.unitFactorArray[to_pos] / self.unitFactorArray[from_pos]
                result = value*(f**2) if squared else value*f
            elif from_pos > to_pos:
                f = self.unitFactorArray[from_pos] / self.unitFactorArray[to_pos]
                result = value*(f**2) if squared else value*f

        return result

    def convert_to_nm( self, value, unit, squared=False):
        self.convert_from_to_unit( value, unit, 'nm' )
        """
        pos = 0
        result = value
        for u in self.unitArray:
            if u == unit:
                result = value*(self.unitFactorArray[pos]**2) if squared else value*self.unitFactorArray[pos]
                break
            pos += 1

        return result
        """

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

    def setImageJScaling( self, scaling, verbose=False ):
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

    def setCVScaling( self, scaling, verbose=False ):
        IMWRITE_TIFF_RESUNIT = 256 # For TIFF, use to specify which DPI resolution unit to set; see libtiff documentation for valid values
        IMWRITE_TIFF_XDPI    = 257 # For TIFF, use to specify the X direction DPI
        IMWRITE_TIFF_YDPI    = 258 # For TIFF, use to specify the Y direction DPI
        tiff_info = [int(IMWRITE_TIFF_RESUNIT), 3,
                    int(IMWRITE_TIFF_XDPI   ), int(1/scaling['x']*self.unitFactorArray[3]),
                    int(IMWRITE_TIFF_YDPI   ), int(1/scaling['y']*self.unitFactorArray[3])]
        return tiff_info

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

            if img.tag[270][0].find('PixelWidth_um') > -1:
                pixel_size = get_eds_image_scaling( img )
                scaling['x'] = pixel_size
                scaling['y'] = pixel_size
                scaling['unit'] = 'nm'
                scaling['editor'] = 'EDS image of the FIB process'
                if verbose:
                    print( '  Image is an ' + scaling['editor'] )
                    print( '  {} x {} {}/px'.format(round( scaling['x'], 4), round( scaling['y'], 4), scaling['unit']) )
            else:
                # getimagej definitions
                IJSettingString = img.tag[270][0].split('\n')
                #print( IJSettingString )
                IJSettingsArray = {}
                for val in IJSettingString:
                    if ( val != '' ):
                        setting = val.split('=')
                        if (len(setting) > 1 ):
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

def get_eds_image_scaling( img ):
    pixel_size_data = img.tag[270][0].split('PixelWidth_um>')
    pixel_size_data = pixel_size_data[1].split('<')
    return float( pixel_size_data[0].replace(',','.') )*1000 # nm

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