#Puncta Tracker
#	Author: Ye Yuan (yeyu@umich.edu)
#Version info
#	R2.0 - fully rebuilt. based on bio-formats with real GUI and extendable analysis capability
#	R2.1 - ADDED FUNCTION: CHANNEL EXTRACT
#	R2.2 - ADDED FUNCTION: PERIPHERY DISTANCE ANALYSIS
#	R3.0 - refactored to package format to allow further extensions.
#testing bio-formats
#	https://downloads.openmicroscopy.org/bio-formats/6.2.1/api/loci/plugins/BF.html
#to merge different channels, use merge channels WITH make composite selected. otherwise will get RGB and lose data.

# Setup Scijava logging
# SciJava parameter annotation, to fetch LogService as object sjlogservice
#	Parameter annotation
#	
#	Use the Logger interface
#	https://javadoc.scijava.org/SciJava/org/scijava/log/Logger.html
from y3628 import sjlogging
#@ LogService sjlogservice
sjlogging.init(sjlogservice)

# Imports
#		Bio-Formats
from loci.plugins import BF
from loci.plugins.in import ImporterOptions
#		ImageJ
from ij.io import OpenDialog
#		ImageJ Plugins
from ij.plugin import ChannelSplitter
from ij.plugin.frame import SyncWindows
#		ImageJ and awt GUIs
from ij.gui import NonBlockingGenericDialog, GenericDialog
from java.awt import GridLayout, Button
from java.awt.event import ActionListener
from java.awt.event import KeyEvent, KeyAdapter
#		Python 2.x
import os, json
#		y3628 components
from y3628 import *

logMainMenu = sjlogging.SJLogger("punctaTracker:main")
logKeybinding = sjlogging.SJLogger("punctaTracker:keybinding")


# Global parameter
ROIsave_jf = 0 #this controls one-time activation of save and quit event for imageplus

#----------------------Key Binding Helpers--------------------------------
#   Keybinding dispatcher for a single ImagePlus
def response_dispatcher(imp, keyEvent):
	global ROIsave_jf
	logKeybinding.info("clicked keyCode " + str(keyEvent.getKeyCode()) + " on image " + str(imp))
	if str(keyEvent.getKeyCode()) == "32":
		#space key for contrast setting
		currLUTs = imp.getLuts()
		d = GenericDialog("White value setting")
		d.hideCancelButton()
		for i in xrange(len(currLUTs)):
			lut = currLUTs[i]
			d.addStringField("Ch#"+str(i+1)+" Black",str(lut.min))
			d.addStringField("Ch#"+str(i+1)+" White",str(lut.max))
		d.showDialog()
		newLUTs = currLUTs
		for i in xrange(len(currLUTs)):
			newMin = float(d.getNextString())
			newMax = float(d.getNextString())
			newLUTs[i].min = newMin
			newLUTs[i].max = newMax
		if len(currLUTs) == 1:
			#this is a normal imageplus
			imp.setLut(newLUTs[0])
		else:
			#this is a composite image
			imp.setLuts(newLUTs)
	if str(keyEvent.getKeyCode()) == "81" and ROIsave_jf == 0:
		#"q" is selected
		#Behavior: save ROI files into the temporary folder and then close all the images
		ROIsave_jf = 1
		RS = helpers.roiSaver(bListeners[1].time_point,bListeners[4].temp_folder_path)
		logKeybinding.info("updating ROIdata folder")
		RS.check()
		logKeybinding.info("saving ROI")
		RS.save()
		logKeybinding.info("saving measurement channel source image")
		RS.saveImage(imp)
		logKeybinding.info("closing up current measurement")
		RS.close()
		
class ListenToKey(KeyAdapter):
	def keyPressed(this, event):
		imp = event.getSource().getImage()
		response_dispatcher(imp, event)


#----------------------Main Dialog Listeners--------------------------------

#CZI Open
#	Listens mainDialog CZI Open button action
#	Opens CZI file into a single imagePlus stack
#	Starts image view windows: merged channels (original data)
class CZIOpen_listen(ActionListener):
	imp = None
	def actionPerformed(this, event):
		logMainMenu.info("CZI Open clicked")
		od = OpenDialog("Choose CZI File")
		file_path = od.getPath()
		importops = ImporterOptions()
		importops.setAutoscale(True)
		importops.setColorMode("Composite")
		importops.setLocation("Local machine")
		importops.setId(file_path)
		imps = BF.openImagePlus(importops)
		this.imp = imps[0]
		this.imp.show()

#Measure
#	Listens mainDialog Measure button action
class Measure_listen(ActionListener):
	measure_imp_title = "Measurement Channel Visualization"
	time_point = "ZT0"
	channelimp = None
	listener = None
	def actionPerformed(this, event):
		global ROIsave_jf
		logMainMenu.info("Measure clicked")
		ROIsave_jf = 0
		d = GenericDialog("Measurement Settings")
		d.hideCancelButton()
		chN = bListeners[0].imp.getDimensions()[2]
		strs = []
		for i in xrange(chN):
			strs.append(str(i+1))
		d.addRadioButtonGroup("Target Channel:",strs,1,chN,"2")
		d.addStringField("Timepoint:",this.time_point)
		d.showDialog()
		chSelection = int(d.getNextRadioButton())
		this.time_point = d.getNextString()
		logMainMenu.info("Selected channel " + str(chSelection))
		logMainMenu.info("Time point setting " + this.time_point)
		#Then we display a new window with only the selected channel
		this.channelimp = ChannelSplitter().split(bListeners[0].imp)
		this.channelimp = this.channelimp[chSelection - 1]
		this.channelimp.setTitle(this.measure_imp_title)
		this.channelimp.show()
		SyncWindows()
		#TODO: Synchronize contrast setting for the two windows
		#Then we install key listeners for all images for contrast setting
		this.listener = ListenToKey()
		helpers.virus_propagation(this.listener)
		logMainMenu.info("Key binding established")

#Analysis
#	Listens mainDialog Analysis button action
#	Shows what measurement data acquired. Provides GUI for analysis data export
class Analysis_listen(ActionListener):
	dResult = None
	def analysis_type(this):
		return ["Nucleus Periphery Dist", "Puncta CTCF", "Puncta Movement", "Spot in ROI"]
	def actionPerformed(this, event):
		logMainMenu.info("Analysis clicked")
		fhr = analysisHandlers.measurementHandler(bListeners[4].temp_folder_path)
		dataSummary = fhr.measurementDataSummary(bListeners[4].temp_folder_path)
		d = GenericDialog("Analysis File Summary")
		d.addMessage("The following time points and measurements will be analyzed:")
		for tp in dataSummary:
			d.addMessage(tp + "\t" + json.dumps(dataSummary[tp]))
		d.showDialog()
		d = GenericDialog("Measurement Type Selection")
		analy_type = this.analysis_type()
		d.addRadioButtonGroup("Measurement Type ",analy_type,1,len(analy_type),analy_type[0])
		d.showDialog()
		selected = d.getNextRadioButton()
		if selected == analy_type[3]:
			(spot_csv_path, meta_csv_path, params) = analysisDialogs.spotInRoiDialog()
			analysis.spotInRoiAnalysis(bListeners[4].temp_folder_path,spot_csv_path,meta_csv_path,params)
		if selected == analy_type[2]:
			unit_time = analysisDialogs.movementAnalysisDialog()
			analysis.movementAnalysis(bListeners[4].temp_folder_path,unit_time)
		if selected == analy_type[1]:
			analysis.roiIntAnalysis(bListeners[4].temp_folder_path)
		if selected == analy_type[0]:
			analysis.nucleusAnalysis(bListeners[4].temp_folder_path)

# Tools
#	Listens mainDialog Tools button action
#	All tools are defined in y3628.tools as ActionListener
class Tools_listen(ActionListener):
	bNames = ["ChEX"]
	bListeners = [tools.ChannelExtract_listen()]
	layout = None
	def __init__(this):
		this.layout = GridLayout(1,len(this.bNames))
	def actionPerformed(this, event):
		logMainMenu.info("Tools clicked")
		#IF YOU USE NONBLOCKING, THE PROGRAM WILL HANG.
		dialog = GenericDialog("Tools")
		buttons = []
		dialog.hideCancelButton()
		for i in xrange(len(this.bNames)):
			b = Button(this.bNames[i])
			b.addActionListener(this.bListeners[i])
			buttons.append(b)
		for b in buttons:
			dialog.add(b)
		dialog.setOKLabel("Quit")
		dialog.setLayout(this.layout)
		dialog.showDialog()

#About
#	Listens mainDialog About button action
class About_listen(ActionListener):
	#Limitation: temp folder path does not support single \
	temp_folder_path = "/Users/yeyuan/ROIdata"
	def actionPerformed(this, event):
		logMainMenu.info("About clicked")
		d = GenericDialog("About")
		d.hideCancelButton()
		d.addMessage("Version: R3.1 'Mod' \n Author: Ye Yuan (yeyu@umich.edu)")
		d.addStringField("Temp Folder Path",this.temp_folder_path)
		d.showDialog()
		this.temp_folder_path = d.getNextString()

#---------------------Main Program Startup---------------------------------
mainDialog = NonBlockingGenericDialog("Puncta Tracker R3.1")

bNames = ["CZI Open","Measure","Analysis","Tools","About"]
bListeners = [CZIOpen_listen(), Measure_listen(), Analysis_listen(), Tools_listen(), About_listen()]
mainLayout = GridLayout(1,len(bNames))
buttons = []
for i in xrange(len(bNames)):
	b = Button(bNames[i])
	b.addActionListener(bListeners[i])
	buttons.append(b)
for b in buttons:
	mainDialog.add(b)
mainDialog.setLayout(mainLayout)
mainDialog.hideCancelButton()
mainDialog.setOKLabel("Quit")
mainDialog.showDialog()
