# Tiff Scaling

Collection of functions to extract the scaling of images created by ImageJ, Thermofische FEI SEMs and Images created by Oxford Aztec and to convert known scalings to the standard Tiff-scaling, readable by ImageJ.

# extract_tiff_scaling.py
Script to extract the Scaling from images saved using ImageJ.
If an image is created by a Phillips lightning / FEI / thermoScientific SEM or by Oxford Aztec, a ImageJ compatible Image with the correct scaling will be saved.
The script provides a class named Unit() which provides some basic unit translation functions.

## standalone
The script can be used standalone. It is callable using
```
python ./extract_tiff_scaling.py
```
The script will then aks you for a file or directory to create a Tif with the standard scaling.

## included

Use the function `autodetect_scaling( 'file.tif', '/folder/')` to get a scaling dictionary formatted as follows:
```
scaling = { 'x' : 1.337, 'y' : 1.337, 'unit' : 'nm', 'editor':'EDITORNAME'}
```

# install required packages
```
pip install -r requirements.txt
```

# Info
This script uses Roboto Mono by Google under Apache Licence 2.0:
https://fonts.google.com/specimen/Roboto+Mono?category=Monospace#standard-styles
