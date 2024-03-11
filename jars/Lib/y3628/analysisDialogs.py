# User-facing blocking dialogs for analysis modules

from ij import IJ
from ij.gui import GenericDialog
from ij.io import OpenDialog
import csv

def movementAnalysisDialog():
    # Get unit time between frames. This information is not available in metadata.
    d = GenericDialog("Puncta Movement Settings")
    d.addStringField("Unit time (sec)","10")
    d.showDialog()
    unit_time = float(d.getNextString())
    return unit_time

def spotInRoiDialog():
    # Get (spot_csv_path, metadata_csv_path, params)
    #   spot_csv_path: Path to the csv containing spot locations
    #   params: dict, parameters for the analysis
    #       params = {z_slice_max: float}

    # Ask for the spot csv file
    IJ.showStatus("Choose the spot csv file...")
    d = OpenDialog("Choose the spot csv file...")
    spot_path = d.getPath()
    #   Parse the first line for setting use
    with open(spot_path, 'rb') as cf:
        rd = csv.reader(cf)
        headers = rd.next()
    # Settings dialog
    d = GenericDialog("Spot within ROI Settings")
    d.addStringField("Maximum Z-slice distance (allow decimal)","1")
    d.addStringField("Maximum XY pixel distance (allow decimal)","5")
    d.addStringField("Minimum score quantile (percent)","25")
    #   Column mapping
    #       which columns are x, y, z?
    #       minimum score for the spot to be considered?
    cols = ["x", "y", "z", "score"]
    d.addMessage("Mapping definition:\n")
    for c in cols:
        d.addChoice(c, headers, headers[0])
    d.showDialog()
    #       Fetch setting results
    zsm = float(d.getNextString())
    xym = float(d.getNextString())
    min_score = float(d.getNextString())
    cs = d.getChoices()
    cs = [c.getSelectedItem() for c in cs]

    # Ask for the metadata csv file
    #   Should contain the following columns
    #       tp: corresponding to the measured ROI timepoints
    #       meas: corresponding to the measured ROI Measurement#
    #       extra columns for mapping (tp, meas) <-> (extra columns in the spot CSV)
    IJ.showStatus("Choose the metadata csv file...")
    d = OpenDialog("Choose the metadata csv file...")
    meta_path = d.getPath()

    return (spot_path, meta_path, {"z_slice_max": zsm, "xy_max": xym, "min_score": min_score, "x": cs[0], "y": cs[1], "z": cs[2], "score": cs[3]})
