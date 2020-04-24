# extract_tiff_scaling.py
Script to extract the Scaling from images saved using ImageJ. If an Images is created by an Phillips lightning / FEI / thermoScientific SEM, a ImageJ compatible Image with the correct scaling will be saved.

# set_tiff_scaling.py
Script to (manually) set the scaling of an image to be readable by ImageJ.
The function "setImageJScaling()" expect an array as follows:

```
scaling = { 'x' : 1.337, 'y' : 1.337, 'unit' : 'nm', 'editor':'EDITORNAME'}
```

The scripts are intended to be used as libaries for other scripts, but can also be used standalone.