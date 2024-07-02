# Getting started

This is a recipe on how to make an acquisition. We recommend reading [optical
setup presentation page](./optical_setup/presentation.md) before trying to use
the setup.

## Load the membrane

Load the membrane and turn on the laser (follow more detailed instruction
provided in the experimental setup section)

## Start the software

1. On the QMPL desktop start LabOne and open jupyter notebook provided at
   `TODO` in the `work` Conda environment (this is the usual environment).
2. Launch the ThorCam software and open the pinhole camera `TODO SN pinhole camera`
3. Run the first cell of the notebook to initialize all the code (some initial
   settings are tunable. Refer to the reference [here](TODO) for more details)
4. Fill the folder to store the data in the next cell

!!! warning
    Don't try to open the imaging camera (TODO serial number) with the ThorCam
    software else your acquisition might fail.

## Find the eigen-frequency of the membrane

First check and align the defect of the membrane with the pinhole (more on
this [here](TODO)).

Then use LabOne to find the eigen-modes of the membrane

## Acquisition

The acquisition process is detailed [here](./programs/acquisition_tutorial.md)
and the file format is documented [here](./programs/file_format.md).

### Calibration data

 - **Turn off the drive** and let the membrane ringdown.
 - Run the calibration cell.

### Mode shape

 - Turn on the drive and find back the mode (you shouldn't need to do a sweep).
 - Run the acquisition cell.

## Analyze the data

Analyze the data in a separate notebook not to clutter the acquisition
notebook. Below is a example of what you can do. For more explanation see
[here](./programs/analysis.md).

```python
"""
TODO sample analysis script
"""
```
