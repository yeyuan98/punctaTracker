## An ImageJ Plugin for semi-automated ROI measurement

A graphical interface for various image analysis tasks. Intentionally developed to be semi-automated so that you can browse images and perform old-school manual analysis with simple automation. Depend on the ImageJ legacy [ROI Manager](https://imagej.net/ij/developer/api/ij/ij/gui/Roi.html) and therefore is limited to 2D regions of interest (ROIs).

1. Intensity of 2D ROIs with background subtraction using a background ROI on the same Z-slice. 4D hyperstack (x,y,z,c).
2. Minimum XY distances of ROIs to an arbitrary boundary ROI on the same Z-slice. 4D hyperstack (x,y,z,c).
3. Velocity of ROI mass centers for timelapse imaging. 4D hyperstack (x,y,t,c).
4. Counting number of spots "within" 2D ROIs.

## License

GPLv3.

## Installation

This plugin is available on an unlisted ImageJ2 update site. Following these [steps](https://imagej.net/update-sites/following) to get the plugin. You need to install *all* files in the site for the plugin to work properly. You can find the plugin under Plugins/punctaTracker.

ImageJ update site: https://sites.imagej.net/Yuanye1998/

## Documentation

Detailed documentation on usage examples will be available at a later date.

## Citation

will be available at a later date.