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

class unit:
    unitArray          = [  'nm',  'µm',  'mm',  'cm',  'dm',   'm' ]
    unitFactorArray    = [     1, 10**3, 10**6, 10**7, 10**8, 10**9 ]
    unitFactorArrayInv = [ 10**9, 10**6, 10**3, 10**2,    10,     1 ]

    def convert_from_to_unit( self, value, from_unit, to_unit, squared=False):
        result = value
        from_pos = -1
        to_pos = -1

        for i, u in enumerate(self.unitArray):
            if u == from_unit:
                from_pos = i
            if u == to_unit:
                to_pos = i

        if from_pos >= 0 and to_pos >= 0:
            f = self.unitFactorArray[from_pos] / self.unitFactorArray[to_pos]
            result = value*(f**2) if squared else value*f
        print('{} {} -> {} {} '.format( value, from_unit, result, to_unit ) )
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
            if unit != 'nm': value = self.convert_to_nm(value, unit)
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
        if verbose: print('  set ImageJ scaling...', scaling)
        info = {}
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
        tiff_info = [int( IMWRITE_TIFF_RESUNIT ), 3,
                     int( IMWRITE_TIFF_XDPI ), int( 1/scaling['x']*self.unitFactorArray[3] ),
                     int( IMWRITE_TIFF_YDPI ), int( 1/scaling['y']*self.unitFactorArray[3] )]
        return tiff_info

    def make_area_readable( self, value, unit, decimal = 0 ):
        unit = unit.replace('²','')
        pos = -1
        f = 1
        if unit in self.unitArray:
            if unit != 'nm': value = self.convert_to_nm(value, unit, True)
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

    #def __init__(self):
    #    self.initiated = True

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
                pixel_size = get_eds_image_scaling( img, verbose )
                scaling['x'] = pixel_size
                scaling['y'] = pixel_size
                scaling['unit'] = 'nm'
                scaling['editor'] = 'EDS image by Aztec'
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
                    print(IJSettingsArray['ImageJ'])
                    if ( 'FA.FIB.Toolbox' in IJSettingsArray['ImageJ'] ):
                        if verbose: print( '  Image edited using F.A. Finger Institute Toolbox' )
                        scaling['editor'] = 'F.A. FIB Toolbox'
                    if ( 'FEI-SEM' in IJSettingsArray['ImageJ'] ):
                        if verbose: print( '  Image edited using F.A. Finger Institute Toolbox using Metadata from a FEI / thermoScientific device' )
                        scaling['editor'] = 'F.A. FIB Toolbox'
                    if ( 'EDS image by Aztec' in IJSettingsArray['ImageJ'] ):
                        if verbose: print( '  Image edited using F.A. Finger Institute Toolbox using Metadata from Aztec / Oxford' )
                        scaling['editor'] = 'F.A. FIB Toolbox'
                    else:
                        if verbose: print( '  Image edited using {}'.format(IJSettingsArray['ImageJ']) )
                        scaling['editor'] = IJSettingsArray['ImageJ']
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
        # extract infos from metadata
        if ( tif.fei_metadata != None and tif.fei_metadata != {}):
            if verbose: print( 'SEM image saved by an FEI / thermoScientific device' )
            data = tif.fei_metadata
        elif (34682 in tif.pages[0].tags._dict): # this only happened for some images created in the FIB process....
            if verbose: print( 'SEM image saved by an FEI / thermoScientific device - probably created by FIB process' )
            data = tif.pages[0].tags.get(34682).value
        else:
            if verbose: print('  no FEI / thermoScientific-Image')
            data = None

        if data != None:
            scaling['editor'] = 'FEI-SEM'
            scaling['x'] = float( data['Scan']['PixelWidth'] )
            scaling['y'] = float( data['Scan']['PixelHeight'] )

            #print('autodetect unit', scaling)
            factor, scaling['unit'] = UC.autodetect_unit(scaling['x'])
            scaling['x'] *= factor
            scaling['y'] *= factor
            #print(scaling)
            #print(UC.setImageJScaling( scaling, True ))

            if save_scaled_image:
                with Image.open( workingDirectory + os.sep + filename ) as img:
                    filename_scaled = workingDirectory + os.sep + 'Scaled_' + filename if verbose else workingDirectory + os.sep + filename
                    img.save( filename_scaled, tiffinfo = UC.setImageJScaling( scaling ) )

    return scaling

def get_eds_image_scaling( img, verbose=False ):
    pixel_size_data = img.tag[270][0].split('PixelWidth_um>')
    pixel_size_data = pixel_size_data[1].split('<')
    if verbose: print('eds', pixel_size_data)
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
    showDebuggingOutput = False

    if ( showDebuggingOutput ) : print( "I am living in '{}'".format(home_dir) )

    settings = {}

    ### actual program start

    UC = unit()

    print( "Extract the scale for a single file (f) or all files in a directory (d), [f]", end=": " )
    actionType = input()

    output_folder_name_std = 'extracted_scaling'
    file_prefix = ''
    print( 'Set the output folder name [{}]'.format(output_folder_name_std), end=": " )
    output_folder_name = input()
    if ( output_folder_name == '' ):
        output_folder_name = output_folder_name_std + os.sep
    else:
        output_folder_name = output_folder_name + os.sep

    print( "Set the unit of scaling [nm]", end=": " )
    standard_unit = input()
    if standard_unit == '': standard_unit = 'nm'

    """
    print( 'Set the scaling of the image. Input example: 2.123456' )
    print( 'Scaling [' + unit + '/px]', end=": " )
    scale = float( input() )
    scaling = { 'x' : scale, 'y' : scale, 'unit' : unit}
    """

    if ( actionType == 'd' ):
        print( "Please select a working directory", end="\r" )
        settings["workingDirectory"] = filedialog.askdirectory(title='Please select the directory containing the images')

        if ( output_folder_name != '' ):
            if not os.path.exists(settings["workingDirectory"] + os.sep + output_folder_name):
                os.makedirs(settings["workingDirectory"] + os.sep + output_folder_name)

        fileCount = 0
        position = 0
        successfull_files = 0
        for file in os.listdir( settings["workingDirectory"] ):
            if ( file.endswith(".tif") or file.endswith(".TIF")):
                fileCount += 1
        for file in os.listdir( settings["workingDirectory"] ):
            if ( file.endswith(".tif") or file.endswith(".TIF")):
                filename = os.fsdecode(file)
                position = position + 1
                print( " Processing " + filename + " (" + str(position) + " / " + str(fileCount) + ") :" )
                scale = autodetectScaling( file, settings["workingDirectory"], True )
                if scale['editor'] != None:
                    with Image.open( settings["workingDirectory"] + os.sep + filename ) as img:
                        data = list(img.getdata())
                        metafree_img = Image.new(img.mode, img.size)
                        metafree_img.putdata(data)
                        metafree_img.save( settings["workingDirectory"] + os.sep + output_folder_name + file_prefix + filename, compression='tiff_lzw', tiffinfo = UC.setImageJScaling( scale ) )#, resolution=UC.convert_from_to_unit(scale['x'],scale['unit'], 'cm'), resolution_unit=3 )#
                        successfull_files += 1
                    set_scale = autodetectScaling( file_prefix + file, settings["workingDirectory"] + os.sep + output_folder_name )
                    if set_scale['x'] == scale['x']:
                        print( "    {:.2f} {}".format(scale['x'], standard_unit) )
                    else:
                        print( "    scale is {:.2f} {}, but saving failed!" )
                else:
                    print( "    no scaling information found in the image" )

                print('-'*50)

        print()
        print( "Detected and set ImageJ scaling in {} of {} images files".format(successfull_files, position ) )
    else:
        settings["filepath"] = filedialog.askopenfilename(title='Please select the image',filetypes=[("Tiff images", "*.tif;*.tiff")])
        settings["workingDirectory"] = os.path.dirname( settings["filepath"] )
        if ( output_folder_name != '' ):
            if not os.path.exists(settings["workingDirectory"] + os.sep + output_folder_name):
                os.makedirs(settings["workingDirectory"] + os.sep + output_folder_name)

        with Image.open( settings["workingDirectory"] + os.sep + os.path.basename( settings["filepath"] ) ) as img:
            data = list(img.getdata())
            metafree_img = Image.new(img.mode, img.size)
            metafree_img.putdata(data)
            scale = autodetectScaling( os.path.basename( settings["filepath"] ), settings["workingDirectory"] )
            metafree_img.save( settings["workingDirectory"] + os.sep + output_folder_name + file_prefix + os.path.basename( settings["filepath"] ), compression='tiff_lzw', tiffinfo = UC.setImageJScaling( scale ) )

        print( "The ImageJ scaling in the file './{}' is set to {:.2f} {}.".format(output_folder_name + file_prefix + os.path.basename( settings["filepath"] ), scale['x'], standard_unit) )

    print( "Script DONE!" )