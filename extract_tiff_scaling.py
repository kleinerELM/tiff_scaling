import os, sys, getopt, tifffile, numpy, mmap
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = 1000000000 # prevent decompressionbomb warning for typical images
from PIL.TiffTags import TAGS

home_dir = os.path.dirname(os.path.realpath(__file__))

def programInfo():
    print("#########################################################")
    print("# A Script to extract the scaling in TIFFs created by   #")
    print("# FEI SEMs, Oxford Aztec EDS images or ImageJ           #")
    print("#                                                       #")
    print("# © 2021 Florian Kleiner                                #")
    print("#   Bauhaus-Universität Weimar                          #")
    print("#   F. A. Finger-Institut für Baustoffkunde             #")
    print("#                                                       #")
    print("#########################################################")
    print()


# Initial function to load the settings
def getBaseSettings():
    settings = {
        "showDebuggingOutput"    : False,
        "home_dir"               : os.path.dirname(os.path.realpath(__file__)),
        "workingDirectory"       : "",
        "actionType"             : "d",  # directory = d or file = f
        "outputDirectory"        : "extracted_scaling",
        "save_with_new_scalebar" : True
    }
    return settings

#### process given command line arguments
def processArguments():
    settings = getBaseSettings()
    argv = sys.argv[1:]
    usage = sys.argv[0] + " [-h] [-o] [-f] [-s] [-d]"
    try:
        opts, args = getopt.getopt(argv,"hosd",[])
    except getopt.GetoptError:
        print( usage )
    for opt, arg in opts:
        if opt == '-h':
            print( 'usage: ' + usage )
            print( '-h,                  : show this help' )
            print( '-o,                  : setting output directory name [{}]'.format(settings["outputDirectory"]) )
            print( '-f:,                  : process only a single file' )
            print( '-s                   : do not save images with a simplyfied scalebar' )
            print( '-d                   : show debug output' )
            print( '' )
            sys.exit()
        elif opt in ("-o"):
            settings["outputDirectory"] = arg
            print( 'Changed output directory to {}'.format(settings["outputDirectory"]) )
        elif opt in ("-s"):
            settings["save_with_new_scalebar"] = True
            print( 'Won\'t save images with a simplyfied scalebar.' )
        elif opt in ("-f"):
            settings["actionType"] = 'f'
            print( 'Single file processing.' )
        elif opt in ("-d"):
            print( 'Show debugging output.' )
            settings["showDebuggingOutput"] = True
    print( '' )
    return settings

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
        #print('{} {} -> {} {} '.format( value, from_unit, result, to_unit ) )
        return result

    def convert_to_nm( self, value, unit, squared=False):
        self.convert_from_to_unit( value, unit, 'nm', squared )

    def make_length_readable( self, value, unit, decimal = -1 ):
        pos = -1
        f = 1
        if unit in self.unitArray:
            if unit != 'nm': value = self.convert_to_nm(value, unit)
            for factor in self.unitFactorArray:
                if value*10 > factor:
                    f = factor
                    pos += 1
                else:
                    break
        else:
            print( 'The unit {} is not valid'.format(unit) )
        return_value = value/f if decimal < 0 else round(value/f, decimal)
        return return_value, self.unitArray[pos]

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
                if i > 0: factorPos = i - 1
                break

        return self.unitFactorArrayInv[factorPos], self.unitArray[factorPos]


def getEmptyScaling():
    return { 'x' : 1, 'y' : 1, 'unit' : 'px', 'editor':None}

def setImageJScaling( scaling, verbose=False ):
    if verbose: print('  set ImageJ scaling...', scaling)
    info = {}
    info[282] = round(1/scaling['x'], 6)
    info[283] = round(1/scaling['y'], 6)
    if ( not 'editor' in scaling or scaling['editor'] == '' ):
        scaling['editor'] = 'FA.FIB.Toolbox'#'F.A. FIB Toolbox'
    if scaling['editor'] == None: scaling['editor'] = '-'
    info[270] = "ImageJ=" + scaling['editor'] + "\nunit=" + scaling['unit']
    return info

def getImageJScaling( filename, workingDirectory, verbose = False ):
    UC = unit()
    scaling = getEmptyScaling()
    with Image.open( workingDirectory + os.sep + filename ) as img:
        if ( 282 in img.tag ) and ( 283 in img.tag ):
            if verbose: print( 'tag[282]', img.tag[282] ) #x
            if verbose: print( 'tag[283]', img.tag[283] ) #y
            x_tag = img.tag[282][0]
            y_tag = img.tag[283][0]
            scaling['x'] = int( x_tag[1] )/ int( x_tag[0] )
            scaling['y'] = int( y_tag[1] )/ int( y_tag[0] )
        if 270 in img.tag:
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

            factor, scaling['unit'] = UC.autodetect_unit(scaling['x'])
            scaling['x'] *= factor
            scaling['y'] *= factor

            if save_scaled_image:
                with Image.open( workingDirectory + os.sep + filename ) as img:
                    filename_scaled = workingDirectory + os.sep + 'Scaled_' + filename if verbose else workingDirectory + os.sep + filename
                    img.save( filename_scaled, tiffinfo = setImageJScaling( scaling ) )

    return scaling

def get_eds_image_scaling( img, verbose=False ):
    pixel_size_data = img.tag[270][0].split('PixelWidth_um>')
    pixel_size_data = pixel_size_data[1].split('<')
    if verbose: print('eds', pixel_size_data)
    return float( pixel_size_data[0].replace(',','.') )*1000 # nm

def autodetectScaling( filename, workingDirectory, verbose = False ):
    scaling = getImageJScaling( filename, workingDirectory, verbose=verbose )
    if scaling['editor'] == None:
        if verbose: print('trying to detect FEI scaling')
        scaling = getFEIScaling( filename, workingDirectory, save_scaled_image=False, verbose=verbose )
    if scaling['editor'] == None:
        if verbose: print( '{} was not saved using ImageJ or a SEM by FEI / thermoScientific'.format(filename) )
    return scaling


def getContentHeightFromMetaData( file_path, verbose=False ):
    contentHeight = 0
    with open(file_path, 'rb', 0) as file, \
        mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
        ## get original image height
        if s.find(b'ResolutionY') != -1:
            file.seek(s.find(b'ResolutionY'))
            tempLine = str( file.readline() ).split("=",1)[1]
            contentHeight = float( tempLine.split("\\",1)[0] )
    if ( contentHeight > 0 ):
        if verbose: print( "  detected content height: {} px".format(contentHeight) )# + str( height ) + '|' + str(contentHeight))
    else:
        if verbose: print( "  content height not detected" )
    return contentHeight

def save_scalebar_image( pil_img, path, scaling ):
    UC = unit()
    w, h = pil_img.size
    tiffinfo = setImageJScaling( scaling )

    scale_width_dict = {800:500.0, 400:250.0, 200:100.0, 80:50.0, 40:25.0, 20:10.0, 8:5.0, 4:2.5}
    _, readable_unit = UC.make_length_readable( w * scaling['x']/10, scaling['unit'])
    if readable_unit != scaling['unit']:
        scaling['x'] = UC.convert_from_to_unit( scaling['x'], scaling['unit'], readable_unit )
        scaling['y'] = UC.convert_from_to_unit( scaling['y'], scaling['unit'], readable_unit )
        scaling['unit'] = readable_unit

    scaledImageWidth = w * scaling['x']

    scaleWidth = 1
    for i in scale_width_dict:
        if scaledImageWidth > i:
            scaleWidth = scale_width_dict[i]
            break
        #else:
            #<break

    scaleHeight = round( 0.004 * h )
    scaleHeight = scaleHeight if scaleHeight > 1 else 1
    fontSize = 6 * scaleHeight
    pad_right = round(0.015 * w)
    pad_bottom = round(0.01 * w)+2*scaleHeight+fontSize

    # convert 16 bit images to 8 bit images.
    # the font was somehow not displayed in 16 bit
    # Since the scalebar is mainly used for publications, which are displayed in 8-bit anyway, this seems to be an okay workaround...
    if pil_img.mode == 'I;16':
        pil_img = Image.fromarray((numpy.array(pil_img)/65535*255).astype(numpy.uint8))

    draw = ImageDraw.Draw(pil_img)

    if pil_img.mode == 'L':
        fill_color = 255
    elif pil_img.mode == 'I;16':
        fill_color = 0
    else:
        fill_color = (255,255,255)

    line_from = (round(w-(scaleWidth/scaling['x'] + pad_right)), h-pad_bottom)
    line_to   = (w-pad_right, h-pad_bottom)
    draw.line([line_from, line_to], fill=fill_color, width=scaleHeight)

    font_path = home_dir + os.sep + "LinotypeSyntaxCom-Regular.ttf"
    if not os.path.isfile(font_path):
        font_path = home_dir + os.sep + "RobotoMono-VariableFont_wght.ttf"
    fnt = ImageFont.truetype(font_path, fontSize)

    scaling_text = "{:.1f} {}".format(scaleWidth, readable_unit)
    tw, _ = draw.textsize(scaling_text, font=fnt)

    draw.text((round(w-((scaleWidth/scaling['x'])/2 + pad_right)-tw/2), h-pad_bottom+scaleHeight*2), scaling_text, font=fnt, fill=fill_color)
    pil_img.save(path, "tiff", compression='tiff_deflate', tiffinfo = tiffinfo)

# open a grayscale FEI-Image without the standard scalebar
def get_image_without_scalebar(base_dir, filename, to_opencv=False, verbose=False ):
    file_path = base_dir + os.sep + filename
    scaling = autodetectScaling( filename, base_dir, verbose )
    contentHeight = getContentHeightFromMetaData( file_path, verbose=False )
    with Image.open( file_path ) as img:
        width, height = img.size
        #tiffinfo = setImageJScaling( scaling )

        if img.mode in ['L', 'P', 'RGB', 'RGBA', 'CMYK']:
            # somehow this does not work with 16 bit greyscale images...
            metafree_img = Image.new(img.mode, img.size)
            metafree_img.putdata( list(img.getdata()) )
        else :
            metafree_img = Image.fromarray(numpy.asarray(img))
        if contentHeight > 0:
            metafree_img = metafree_img.crop((0, 0, width, contentHeight))

        if to_opencv:
            metafree_img = numpy.array(metafree_img)
    return metafree_img, scaling

def save_scaling_in_image( base_dir, filename, save_with_new_scalebar, output_folder_name, verbose=True ):
    result = False

    scaling = autodetectScaling( filename, base_dir )
    if scaling['editor'] != None:
        file_path = base_dir + os.sep + filename

        of          = base_dir + os.sep + output_folder_name
        of_cut      = base_dir + os.sep + 'cut_' + output_folder_name
        of_scalebar = base_dir + os.sep + 'nsb_' + output_folder_name

        if ( output_folder_name != '' ):
            if not os.path.exists(of):
                os.makedirs(of)

        with Image.open( file_path ) as img:
            width, height = img.size
            tiffinfo = setImageJScaling( scaling )

            # create a new image to remove metadata
            if img.mode in ['L', 'P', 'RGB', 'RGBA', 'CMYK']:
                # somehow this does not work with 16 bit greyscale images...
                metafree_img = Image.new(img.mode, img.size)
                metafree_img.putdata( list(img.getdata()) )
            else :
                metafree_img = Image.fromarray(numpy.asarray(img))
            metafree_img.save( of + filename, compression='tiff_deflate', tiffinfo = tiffinfo )#, resolution=UC.convert_from_to_unit(scale['x'],scale['unit'], 'cm'), resolution_unit=3 )#


            # check if scalebar is detected without an error
            set_scaling = autodetectScaling( filename, of )

            UC = unit()
            if (    set_scaling['x']*1.01 > UC.convert_from_to_unit( scaling['x'], scaling['unit'], set_scaling['unit'])
                and set_scaling['x']      < UC.convert_from_to_unit( scaling['x'], scaling['unit'], set_scaling['unit'])*1.01):
                if verbose: print( "    {:.2f} {}/px".format(scaling['x'], scaling['unit']) )
                result = True
            elif verbose:
                print( "    Saving '{}' with the new scaling caused major deviations. Detected: {:.2f} {}/px, Saved: {:.2f} {}/px)".format(filename, scaling['x'], scaling['unit'], set_scaling['x'], set_scaling['unit']) )

            # cut old scalebar and add simplified scalebar for publications
            if save_with_new_scalebar:
                if not os.path.exists(base_dir + os.sep + 'nsb_' + output_folder_name):
                    os.makedirs(base_dir + os.sep + 'nsb_' + output_folder_name)

                contentHeight = getContentHeightFromMetaData( file_path, verbose=False )
                if contentHeight > 0:
                    if not os.path.exists(of_cut):
                        os.makedirs(of_cut)

                    metafree_img = metafree_img.crop((0, 0, width, contentHeight))
                    metafree_img.save( of_cut + filename, compression='tiff_deflate', tiffinfo = tiffinfo )

                save_scalebar_image(metafree_img, path=of_scalebar + filename, scaling=scaling)
    else:
        if verbose: print( "    no scaling information found in '{}'".format(filename) )

    return [result, scaling, filename]

# helper function for the multi file processing
result_list = {}
def log_result(result):
    global result_list
    if result[0]:
        result_list[result[2]] = result[1]

### actual program start
if __name__ == '__main__':
    import tkinter as tk
    from tkinter import filedialog
    import multiprocessing

    #remove root windows
    root = tk.Tk()
    root.withdraw()

    ### global settings
    programInfo()

    #### directory definitions
    showDebuggingOutput = False

    settings = processArguments()

    ### actual program start

    UC = unit()
    """
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

    print( "Save image with simplified scalebar [y/N]", end=": " )
    save_with_new_scalebar = ( input().upper() in ['Y', 'J'] )
    """
    settings['outputDirectory'] += os.sep
    if ( settings['actionType']  == 'd' ):
        print( "Please select a working directory", end="\r" )
        settings["workingDirectory"] = filedialog.askdirectory(title='Please select the directory containing the images')

        coreCount = multiprocessing.cpu_count()
        processCount = (coreCount - 1) if coreCount > 1 else 1

        if ( settings['showDebuggingOutput'] ) :
            print( 'Found {} CPU cores. Would use max. {} processes when not in debuggging mode.'.format(coreCount, processCount) )
            print( "I am living in '{}'".format( settings["home_dir"] ) )
            print( "Selected working directory: {}".format( settings["workingDirectory"] ), end='\n\n' )

        fileList = []
        for filename in os.listdir( settings["workingDirectory"] ):
            if ( filename.endswith(".tif") or filename.endswith(".TIF")):
                fileList.append( filename )

        successfull_files = 0
        if ( len(fileList) > 0 ):
            if not settings['showDebuggingOutput']:
                pool = multiprocessing.Pool(processCount)
            for position, filename in enumerate(fileList):
                if ( filename.endswith(".tif") or filename.endswith(".TIF")):
                    file_path = settings["workingDirectory"] + os.sep + filename
                    print( " processing '{}' ({} / {})".format(filename, position+1, len(fileList)) )
                    if settings['showDebuggingOutput']:
                        result = save_scaling_in_image(  settings["workingDirectory"], filename, settings['save_with_new_scalebar'], settings['outputDirectory'] )
                        log_result(result)
                        successfull_files += 1
                    else:
                        pool.apply_async(save_scaling_in_image, args=(  settings["workingDirectory"], filename, settings['save_with_new_scalebar'], settings['outputDirectory'], False ), callback = log_result)

            if not settings['showDebuggingOutput']:
                pool.close()
                pool.join()
                print('-'*20)
                for f in result_list:
                    print(" ./{}: {:.2f} {}/px".format(f, result_list[f]['x'], result_list[f]['unit']))
                    fileList.remove(f)
                if len(fileList) > 0:
                    print()
                    print(' found {} image(s) without known scale metadata'.format(len(fileList)))
                    for f in fileList:
                        print(" ./{}".format(f))

                successfull_files = len(result_list)
            print()
            print( "Detected and set ImageJ scaling in {} of {} images files".format(successfull_files, len(fileList)+len(result_list) ) )
        else:
            print( 'No Tif file found!' )

    else:
        settings["filepath"] = filedialog.askopenfilename(title='Please select the image',filetypes=[("Tiff images", "*.tif;*.tiff")])
        settings["workingDirectory"] = os.path.dirname( settings["filepath"] )
        filename = os.path.basename(settings["filepath"])
        #print( " Processing {}:".format(filename) )
        scaling = autodetectScaling( filename, settings["workingDirectory"], False )

        save_scaling_in_image( settings["workingDirectory"], filename, settings['save_with_new_scalebar'], settings['outputDirectory'] )

    print()
    print( "Script DONE!" )