#Puncta Tracker
#	Author: Ye Yuan (yeyu@umich.edu)
#Version info
#	R2.0 - fully rebuilt. based on bio-formats with real GUI and extendable analysis capability
#	R2.1 - ADDED FUNCTION: CHANNEL EXTRACT
#	R2.2 - ADDED FUNCTION: PERIPHERY DISTANCE ANALYSIS
#testing bio-formats
#	https://downloads.openmicroscopy.org/bio-formats/6.2.1/api/loci/plugins/BF.html
#to merge different channels, use merge channels WITH make composite selected. otherwise will get RGB and lose data.
from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from ij import ImagePlus, IJ
from ij.plugin import ChannelSplitter
from ij.plugin.frame import SyncWindows, RoiManager
from ij.gui import NonBlockingGenericDialog, GenericDialog
from java.awt import GridLayout, Button
from java.awt.event import ActionListener
from ij.io import OpenDialog, FileSaver, FileOpener, DirectoryChooser
from ij import WindowManager
from ij.measure import Measurements,ResultsTable

from collections import OrderedDict
import os, re
import locale, json
if os.name == 'nt':
	import win32api, win32con

from java.awt.event import KeyEvent, KeyAdapter

ROIsave_jf = 0 #this controls one-time activation of save and quit event for imageplus
#----------------------Main Dialog Listeners--------------------------------
#CZI Open
#	Listens mainDialog CZI Open button action
#	Opens CZI file into a single imagePlus stack
#	Starts image view windows: merged channels (original data)
class CZIOpen_listen(ActionListener):
	imp = None
	def actionPerformed(this, event):
		print "CZI Open clicked"
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
class Measure_listen(ActionListener):
	measure_imp_title = "Measurement Channel Visualization"
	time_point = "ZT0"
	channelimp = None
	listener = None
	def actionPerformed(this, event):
		global ROIsave_jf
		print "Measure clicked"
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
		print "Selected channel " + str(chSelection)
		print "Time point setting " + this.time_point
		#Then we display a new window with only the selected channel
		this.channelimp = ChannelSplitter().split(bListeners[0].imp)
		this.channelimp = this.channelimp[chSelection - 1]
		this.channelimp.setTitle(this.measure_imp_title)
		this.channelimp.show()
		SyncWindows()
		#TODO: Synchronize contrast setting for the two windows
		#Then we install key listeners for all images for contrast setting
		this.listener = ListenToKey()
		virus_propagation(this.listener)
		print "Key binding established"
#Analysis
#	Shows what measurement data acquired. Provides GUI for analysis data export
class Analysis_listen(ActionListener):
	dResult = None
	def generate_headers(this, mixed_mode):
		if mixed_mode == 6:
			#background subtraction
			final_columns = ["Area","Mean","Integrated","CTCF"]
		if mixed_mode == 8:
			#no background subtraction
			final_columns = ["Area","Mean","Integrated"]
		return final_columns
	def analysis_type(this):
		return ["Nucleus Periphery Dist", "Puncta CTCF","Puncta Movement"]
	def actionPerformed(this, event):
		print "Analysis clicked"
		fhr = fileHandler()
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
		if selected == analy_type[2]:
			d = GenericDialog("Puncta Movement Settings")
			d.addStringField("Unit time (sec)","10")
			d.showDialog()
			unit_time = float(d.getNextString())
			movementAnalysis(bListeners[4].temp_folder_path,unit_time)
		if selected == analy_type[1]:
			d = GenericDialog("Puncta CTCF - Analysis Mode Selection")
			d.addMessage("Select puncta measurement mode:")
			roiMeasMode = roiMeasurementModes().mode
			for subcategory in roiMeasMode:
				submodes = list(roiMeasMode[subcategory].keys())
				d.addRadioButtonGroup(subcategory,submodes,1,len(submodes),submodes[0])
			d.showDialog()
			modeSelected = 0
			for subcategory in roiMeasMode:
				modeSelected = modeSelected + roiMeasMode[subcategory][d.getNextRadioButton()]
			print "Selected Mixed mode=" + str(modeSelected)
			column_headers = this.generate_headers(modeSelected)
			this.dResult = displayResult(column_headers)
			for tp in dataSummary:
				print "Analyzing Time Point: " + tp
				roiMan = roiManagement(tp,bListeners[4].temp_folder_path)
				for measurementN in dataSummary[tp]:
					print "Processing: " + tp + "," + measurementN
					imp = fhr.readSingleMeasurement(tp,measurementN)
					roiMan.measure(imp,modeSelected,measurementN)
			this.dResult.showResult()
		if selected == analy_type[0]:
			nucleusAnalysis(bListeners[4].temp_folder_path)
#Tools
class ChannelExtract_listen(ActionListener):
	extractTitle = "Extracted channel image"
	def actionPerformed(this, event):
		print "Performing channel extract tool"
		IJ.showStatus("Select INPUT File Folder")
		dc_i = DirectoryChooser("Select INPUT File Folder")
		print dc_i.getDirectory()
		fH = fileHandler()
		file_list = fH.getFileList(dc_i.getDirectory())
		print file_list
		IJ.showStatus("Select OUTPUT File Folder")
		dc_o = DirectoryChooser("Select OUTPUT File Folder")
		chSet = 0
		for fn in file_list:
			IJ.showStatus("Extracting file: "+fn)
			file_path = os.path.join(dc_i.getDirectory(),fn)
			importops = ImporterOptions()
			importops.setAutoscale(True)
			importops.setColorMode("Composite")
			importops.setLocation("Local machine")
			importops.setId(file_path)
			imps = BF.openImagePlus(importops)
			imp = imps[0]
			if chSet == 0:
				#initialize channel setting first
				IJ.showStatus("Extract Target Channel Setting")
				nChannel = imp.getNChannels()
				d = GenericDialog("Select channel to extract")
				d.hideCancelButton()
				chN = imp.getDimensions()[2]
				strs = []
				for i in xrange(chN):
					strs.append(str(i+1))
				d.addRadioButtonGroup("Target Channel:",strs,1,chN,"2")
				d.showDialog()
				chSet = int(d.getNextRadioButton())
			channelimp = ChannelSplitter().split(imp)
			channelimp = channelimp[chSet - 1]
			channelimp.setTitle(this.extractTitle)
			save_path = os.path.join(dc_o.getDirectory(),fn)
			fsr = FileSaver(channelimp)
			fsr.saveAsTiff(save_path)
			
class Tools_listen(ActionListener):
	bNames = ["ChEX"]
	bListeners = [ChannelExtract_listen()]
	layout = None
	def __init__(this):
		this.layout = GridLayout(1,len(this.bNames))
	def actionPerformed(this, event):
		print "Tools clicked"
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
class About_listen(ActionListener):
	#Limitation: temp folder path does not support single \
	#temp_folder_path = "Default"
	temp_folder_path = "/Users/yeyuan/ROIdata"
	def actionPerformed(this, event):
		print "About clicked"
		d = GenericDialog("About")
		d.hideCancelButton()
		d.addMessage("Version: R2.3 'Wrapped Complexity' \n Author: Ye Yuan (yeyu@umich.edu)")
		d.addStringField("Temp Folder Path",this.temp_folder_path)
		d.showDialog()
		this.temp_folder_path = d.getNextString()
#---------------------Key binding dispatcher for single imageplus-----------------------------
def response_dispatcher(imp, keyEvent):
	global ROIsave_jf
	print "clicked keyCode " + str(keyEvent.getKeyCode()) + " on image " + str(imp)
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
		RM = roiManagement(bListeners[1].time_point,bListeners[4].temp_folder_path)
		print "updating ROIdata folder"
		RM.check()
		print "saving ROI"
		RM.save()
		print "saving measurement channel source image"
		RM.saveImage(imp)
		print "closing up current measurement"
		RM.close()
		
		
class ListenToKey(KeyAdapter):
	def keyPressed(this, event):
		imp = event.getSource().getImage()
		response_dispatcher(imp, event)

#--------------------Helper functions----------------------
#	KEY BINDING
def virus_propagation(listener):
	for imp in map(WindowManager.getImage, WindowManager.getIDList()):
		win = imp.getWindow()
		if win is None:
			continue
		canvas = win.getCanvas()
		kls = canvas.getKeyListeners()
		map(canvas.removeKeyListener, kls)
		canvas.addKeyListener(listener)
		map(canvas.addKeyListener, kls)
#	FILE HANDLING
class fileHandler:
	imgExt = ".tif"
	def folder_is_hidden(this, p):
		if os.name== 'nt':
			attribute = win32api.GetFileAttributes(p)
			return attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM)
		else:
			return p.startswith('.') #linux-osx
	def getFileList(this, folder_path):
		li = [f for f in os.listdir(folder_path) if not this.folder_is_hidden(f)]
		return li
	def getCurrMeasurementN(this, temp_folder,time_point):
		li = [f for f in os.listdir(os.path.join(temp_folder,time_point)) if not this.folder_is_hidden(f)]
		for i in xrange(0,len(li)):
			li[i] = int(li[i])
		li.sort()
		for i in xrange(0,len(li)):
			li[i] = str(li[i])
		print "Current folders after sorting: " + json.dumps(li)
		if len(li) == 0:
			return 1
		else:
			return int(li[len(li)-1]) + 1
	def measurementDataSummary(this, temp_folder):
		#first we summarize time_points, based on mtime
		time_points = [f for f in os.listdir(temp_folder) if not this.folder_is_hidden(f)]
		mtime = lambda f: os.stat(os.path.join(temp_folder, f)).st_mtime
		time_points = list(sorted(time_points, key=mtime))
		#then we construct the data summary ordereddict {tp0:[folder names], tp1:[folder names],...}
		#still, based on mtime
		summary = OrderedDict()
		for tp in time_points:
			folders = [f for f in os.listdir(os.path.join(temp_folder,tp)) if not this.folder_is_hidden(f)]
			mtime = lambda f: os.stat(os.path.join(temp_folder, tp, f)).st_mtime
			folders = list(sorted(folders, key=mtime))
			summary[tp] = folders
		return summary
	def singleMeasurementList(this,time_point,measurementN):
		measurement_folder_path = os.path.join(bListeners[4].temp_folder_path, time_point, str(measurementN))
		files = [f for f in os.listdir(measurement_folder_path) if not this.folder_is_hidden(f)]
		if len(files) != 2:
			raise NameError("Wrong file count for measurement folder " + measurement_folder_path)
		#files = [img_filename, ROIset_filename]
		if files[0].find(this.imgExt) == -1:
			files[0], files[1] = files[1], files[0]
		return files
	def readSingleMeasurement(this,time_point,measurementN):
		#read and load ROIset and also the tif file saved in measurement folder, returns the opened tif imageplus
		#list the files
		print "Reading measurement..."
		measurement_folder_path = os.path.join(bListeners[4].temp_folder_path, time_point, str(measurementN))
		print "Path = " + measurement_folder_path
		files = this.singleMeasurementList(time_point,measurementN)
		print files
		imp = IJ.openImage(os.path.join(measurement_folder_path, files[0]))
		rm = roiManagement(time_point, bListeners[4].temp_folder_path)
		rm.load(measurementN)
		return imp
		
	def checkExistenceAndCreate(this, path, dir_name):
		if not dir_name in os.listdir(path):
			os.mkdir(os.path.join(path,dir_name))
		print "Checked folder name="+ dir_name + ", under path="+ path
#Result Table
class displayResult:
	column_headers = None
	table = None
	def __init__(this,cH):
		this.column_headers = cH
		this.table = ResultsTable()
	def saveResult(this,final_results, time_point, measurementN):
		for planeN in final_results:
			#cell
			for i in xrange(len(final_results[planeN])):
				#puncta
				this.table.incrementCounter()
				this.table.addValue("Time Point",time_point)
				this.table.addValue("Measurement#", int(measurementN))
				this.table.addValue("Slice#",int(planeN))
				for j in xrange(len(final_results[planeN][i])):
					this.table.addValue(this.column_headers[j],float(final_results[planeN][i][j]))
	def showResult(this):
		this.table.show("Results")
#	ROI MANAGER
class roiMeasurementModes:
	mode = {"order":{"SINGLE_PLANE" : 1, "AS_IS" : 2}, "background":{"SUBTRACTION" : 5, "NOTSET" : 7}}
class roiManagement:
	time_point = "ZT0"
	temp_folder = None
	def __init__(this,tp,tf):
		this.time_point = tp
		this.temp_folder = tf
	def close(this):
		RoiManager.getInstance().reset()
		RoiManager.getInstance().close()
		iid = WindowManager.getIDList()
		for i in iid:
			im = WindowManager.getImage(i)
			win = im.getWindow()
			if win is None:
				continue
			canvas = win.getCanvas()
			kls = canvas.getKeyListeners()
			map(canvas.removeKeyListener, kls)
			im.changes = False
			im.close()
		WindowManager.getWindow("Synchronize Windows").close()
	def check(this):
		#check for time_point folder and stack measurement folder
		fH = fileHandler()
		fH.checkExistenceAndCreate(this.temp_folder,this.time_point)
		this.measurementN = fH.getCurrMeasurementN(this.temp_folder,this.time_point)
		fH.checkExistenceAndCreate(os.path.join(this.temp_folder,this.time_point), str(this.measurementN))
	def save(this):
		#saves all ROIs using Roimanager.
		roiFileName = "roiSet.zip"
		print "total ROI count = " + str(RoiManager.getInstance().getCount())
		path = os.path.join(this.temp_folder,this.time_point,str(this.measurementN),roiFileName)
		RoiManager.getInstance().runCommand("Save",path)
	def saveImage(this,imp):
		#saves the imageplus as is
		impFileName = "source.tif"
		path = os.path.join(this.temp_folder,this.time_point,str(this.measurementN),impFileName)
		fsr = FileSaver(imp)
		fsr.saveAsTiff(path)
	def load(this,measurementN):
		#reset ROImanager and load the ROIset specified
		print "Loading ROI..."
		RoiManager.getRoiManager()
		RoiManager.getInstance().reset()
		fhr = fileHandler()
		roifile = fhr.singleMeasurementList(this.time_point,measurementN)
		print roifile
		roifile = os.path.join(this.temp_folder,this.time_point,measurementN,roifile[1])
		RoiManager.getInstance().runCommand("Open",roifile)
	def measure_ROI(this,imp,roi):
		#helper for measure. set roi and do measurement in imp.
		#------------HERE, WE SPECIFY THE WANTED STATISTICS------------
		imp.setSlice(int(roi.getName()[0:4]))
		imp.setRoi(roi, False)
		stat = imp.getStatistics()
		return [stat.area,stat.mean,stat.area*stat.mean]
	def displayResult(this,column_headers,final_results):
		#displays a ResultTable
		table = ResultsTable()
		for planeN in final_results:
			#cell
			for i in xrange(len(final_results[planeN])):
				#puncta
				table.incrementCounter()
				table.addValue("Slice#",int(planeN))
				for j in xrange(len(final_results[planeN][i])):
					table.addValue(column_headers[j],float(final_results[planeN][i][j]))
		table.show("Results")
	def measure(this,imp,mode,measurementN):
		#carry out the specified measurement using the current ROIs in ROI Manager. Mode specified in roiMeasurementModes
		modeFound = 0
		if mode == 6 or mode == 8:
			#single_plane sorting
			modeFound = 1
			sortedROI = OrderedDict()
			rois = RoiManager.getInstance().getRoisAsArray()
			#sort the ROIs based on plane number
			for roi in rois:
				planeN = roi.getName()[0:4]
				if planeN in sortedROI:
					sortedROI[planeN].append(roi)
				else:
					sortedROI[planeN] = [roi]
			#then for each do ROI measurement
			results = OrderedDict()
			for planeN in sortedROI:
				results[planeN] = []
			for planeN in sortedROI:
				for roi in sortedROI[planeN]:
					results[planeN].append(this.measure_ROI(imp,roi))
			#then decide on background subtraction or not
			if mode == 6:
				#background subtraction
				final_result = OrderedDict()
				for planeN in results:
					planeResult = results[planeN]
					final_result[planeN] = []
					Bgd = planeResult[len(planeResult) - 1][1] #mean gray value of the last selection in this plane
					for i in xrange(len(planeResult) - 1):
						final_result[planeN].append([planeResult[i][0],planeResult[i][1],planeResult[i][2],planeResult[i][2] - Bgd*planeResult[i][0]]) #area mean area*mean CTCF
			if mode == 8:
				#no background subtraction
				final_result = results
		if modeFound == 0:
			print "NO MEASUREMENT MODE SELECTED!"
		else:
			#then we save the measurement data
			print "ROIMangement saved result for time_point "+this.time_point+", measurementN "+str(measurementN)
			bListeners[2].dResult.saveResult(final_result,this.time_point,measurementN)

#New for R2.2 Nucleus Dist Analysis Module
class nucleusAnalysis:
	class measurementHandler:
		imgExt = [".tif", ".czi"]
		temp_folder = None
		def __init__(this, temp_folder_path):
			this.temp_folder = temp_folder_path
		def folder_is_hidden(this, p):
			if os.name== 'nt':
				attribute = win32api.GetFileAttributes(p)
				return attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM)
			else:
				return p.startswith('.') #linux-osx
		def getFileList(this, folder_path):
			li = [f for f in os.listdir(folder_path) if not this.folder_is_hidden(f)]
			return li
		def checkExistenceAndCreate(this, path, dir_name):
			if not dir_name in os.listdir(path):
				os.mkdir(os.path.join(path,dir_name))
			print "Checked folder name="+ dir_name + ", under path="+ path
		def getCurrMeasurementN(this, temp_folder,time_point):
			li = [f for f in os.listdir(os.path.join(temp_folder,time_point)) if not this.folder_is_hidden(f)]
			for i in xrange(0,len(li)):
				li[i] = int(li[i])
			li.sort()
			for i in xrange(0,len(li)):
				li[i] = str(li[i])
			print "Current folders after sorting: " + json.dumps(li)
			if len(li) == 0:
				return 1
			else:
				return int(li[len(li)-1]) + 1
		def measurementDataSummary(this, temp_folder):
			#first we summarize time_points, based on mtime
			time_points = [f for f in os.listdir(temp_folder) if not this.folder_is_hidden(f)]
			mtime = lambda f: os.stat(os.path.join(temp_folder, f)).st_mtime
			time_points = list(sorted(time_points, key=mtime))
			#then we construct the data summary ordereddict {tp0:[folder names], tp1:[folder names],...}
			#still, based on mtime
			summary = OrderedDict()
			for tp in time_points:
				folders = [f for f in os.listdir(os.path.join(temp_folder,tp)) if not this.folder_is_hidden(f)]
				mtime = lambda f: os.stat(os.path.join(temp_folder, tp, f)).st_mtime
				folders = list(sorted(folders, key=mtime))
				summary[tp] = folders
			return summary
		def singleMeasurementList(this,time_point,measurementN):
			measurement_folder_path = os.path.join(this.temp_folder, time_point, str(measurementN))
			files = [f for f in os.listdir(measurement_folder_path) if not this.folder_is_hidden(f)]
			print files
			if len(files) != 2:
				raise NameError("Wrong file count for measurement folder " + measurement_folder_path)
			#files = [img_filename, ROIset_filename]
			for ext in this.imgExt:
				if files[0].find(ext) != -1:
					files[0], files[1] = files[1], files[0]
					break
			return files
		def readSingleMeasurement(this,time_point,measurementN):
			#read and load ROIset and also the tif file saved in measurement folder, returns the opened tif imageplus
			#list the files
			print "Reading measurement..."
			measurement_folder_path = os.path.join(this.temp_folder, time_point, str(measurementN))
			print "Path = " + measurement_folder_path
			files = this.singleMeasurementList(time_point,measurementN)
			print files
			for i in xrange(len(files)):
				files[i] = os.path.join(this.temp_folder, time_point, str(measurementN), files[i])
			imp = IJ.openImage(os.path.join(measurement_folder_path, files[1]))
			rm = RoiManager.getInstance()
			rm.reset()
			rm.runCommand("Open",files[0])
			print "Roi Count = " + str(len(rm.getRoisAsArray()))
			return imp
		def roiSorted(this):
			rm = RoiManager.getInstance()
			rois = rm.getRoisAsArray()
			roiDict = OrderedDict()
			for roi in rois:
				stackN = roi.getName()[0:4]
				if stackN not in roiDict:
					roiDict[stackN] = []
				roiDict[stackN].append(roi)
			return roiDict
	
	#Result Table
	class displayResult:
		column_headers = None
		table = None
		def __init__(this):
			this.table = ResultsTable()
		def saveResult(this,results_headers, final_results, time_point, measurementN):
			results_headers.insert(0,"Time Point")
			results_headers.insert(1,"Measurement#")
			print results_headers
			for i in xrange(len(final_results)):
				#puncta
				this.table.incrementCounter()
				this.table.addValue("Time Point",time_point)
				this.table.addValue("Measurement#", int(measurementN))
				for j in xrange(len(final_results[i])):
					this.table.addValue(results_headers[j+2],float(final_results[i][j]))
		def showResult(this):
			this.table.show("Results")
	
	def pointDist(this,p1,p2):
		return ((p1[0]-p2[0])**2+(p1[1]-p2[1])**2)**0.5	
	def __init__(this,resultPath):
		rm = RoiManager.getRoiManager()
		rm.reset()
		measHandler = nucleusAnalysis.measurementHandler(resultPath)
		resultSummary = measHandler.measurementDataSummary(resultPath)
		results = OrderedDict()
		dR = nucleusAnalysis.displayResult()
		for tp in resultSummary:
			print "Processing time point = " + tp
			results[tp] = OrderedDict()
			for measurementN in resultSummary[tp]:
				results[tp][measurementN] = []
				print "        Processing measurement N = " + str(measurementN)
				imp = measHandler.readSingleMeasurement(tp,measurementN)
				cal = imp.getCalibration()
				roiDict = measHandler.roiSorted()
				for planeN in roiDict:
					print "                Processing Z Plane = " + str(planeN)
					polygon = roiDict[planeN][0].getInterpolatedPolygon()
					imp.setSlice(int(planeN))
					imp.setRoi(roiDict[planeN][0], False)
					stat = imp.getStatistics(Measurements.AREA)
					area = stat.area
					equiD = (4*area/3.141593)**0.5
					#print polygon.npoints
					#print polygon.xpoints
					#print polygon.ypoints
					px = polygon.xpoints
					py = polygon.ypoints
					points = []
					for i in xrange(polygon.npoints):
						points.append([cal.getX(px[i]),cal.getY(py[i])])
					
					puncta = roiDict[planeN]
					puncta = puncta[1:len(puncta)]
					
					#print len(puncta)
					
					minDist = []
					
					for roi in puncta:
						imp.setSlice(int(planeN))
						imp.setRoi(roi, False)
						stat = imp.getStatistics(Measurements.CENTER_OF_MASS)
						cmass = [stat.xCenterOfMass, stat.yCenterOfMass]
						#print cmass
						#print stat.mean
						minimumDist = this.pointDist(cmass,points[0])
						for p in points:
							if this.pointDist(cmass,p) < minimumDist:
								minimumDist = this.pointDist(cmass,p)
						minDist.append(minimumDist)
					for md in minDist:
						results[tp][measurementN].append([md, equiD])
					#print "For planeN=" + str(planeN) + ", perimeter=" + str(equiD)
				headers = ["Distance", "Equivalent Diameter"]
				dR.saveResult(headers,results[tp][measurementN],tp,measurementN)
		#print results
		dR.showResult()

#New for R2.3 Movement analysis module
class movementAnalysis:
	class measurementHandler:
		imgExt = [".tif", ".czi"]
		temp_folder = None
		def __init__(this, temp_folder_path):
			this.temp_folder = temp_folder_path
		def folder_is_hidden(this, p):
			if os.name== 'nt':
				attribute = win32api.GetFileAttributes(p)
				return attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM)
			else:
				return p.startswith('.') #linux-osx
		def getFileList(this, folder_path):
			li = [f for f in os.listdir(folder_path) if not this.folder_is_hidden(f)]
			return li
		def checkExistenceAndCreate(this, path, dir_name):
			if not dir_name in os.listdir(path):
				os.mkdir(os.path.join(path,dir_name))
			print "Checked folder name="+ dir_name + ", under path="+ path
		def getCurrMeasurementN(this, temp_folder,time_point):
			li = [f for f in os.listdir(os.path.join(temp_folder,time_point)) if not this.folder_is_hidden(f)]
			for i in xrange(0,len(li)):
				li[i] = int(li[i])
			li.sort()
			for i in xrange(0,len(li)):
				li[i] = str(li[i])
			print "Current folders after sorting: " + json.dumps(li)
			if len(li) == 0:
				return 1
			else:
				return int(li[len(li)-1]) + 1
		def measurementDataSummary(this, temp_folder):
			#first we summarize time_points, based on mtime
			time_points = [f for f in os.listdir(temp_folder) if not this.folder_is_hidden(f)]
			mtime = lambda f: os.stat(os.path.join(temp_folder, f)).st_mtime
			time_points = list(sorted(time_points, key=mtime))
			#then we construct the data summary ordereddict {tp0:[folder names], tp1:[folder names],...}
			#still, based on mtime
			summary = OrderedDict()
			for tp in time_points:
				folders = [f for f in os.listdir(os.path.join(temp_folder,tp)) if not this.folder_is_hidden(f)]
				mtime = lambda f: os.stat(os.path.join(temp_folder, tp, f)).st_mtime
				folders = list(sorted(folders, key=mtime))
				summary[tp] = folders
			return summary
		def singleMeasurementList(this,time_point,measurementN):
			measurement_folder_path = os.path.join(this.temp_folder, time_point, str(measurementN))
			files = [f for f in os.listdir(measurement_folder_path) if not this.folder_is_hidden(f)]
			print files
			if len(files) != 2:
				raise NameError("Wrong file count for measurement folder " + measurement_folder_path)
			#files = [img_filename, ROIset_filename]
			for ext in this.imgExt:
				if files[0].find(ext) != -1:
					files[0], files[1] = files[1], files[0]
					break
			return files
		def readSingleMeasurement(this,time_point,measurementN):
			#read and load ROIset and also the tif file saved in measurement folder, returns the opened tif imageplus
			#list the files
			print "Reading measurement..."
			measurement_folder_path = os.path.join(this.temp_folder, time_point, str(measurementN))
			print "Path = " + measurement_folder_path
			files = this.singleMeasurementList(time_point,measurementN)
			print files
			for i in xrange(len(files)):
				files[i] = os.path.join(this.temp_folder, time_point, str(measurementN), files[i])
			imp = IJ.openImage(os.path.join(measurement_folder_path, files[1]))
			rm = RoiManager.getInstance()
			rm.reset()
			rm.runCommand("Open",files[0])
			print "Roi Count = " + str(len(rm.getRoisAsArray()))
			return imp
		def roiSorted(this):
			rm = RoiManager.getInstance()
			rois = rm.getRoisAsArray()
			roiDict = OrderedDict()
			for roi in rois:
				stackN = roi.getName()[0:4]
				if stackN not in roiDict:
					roiDict[stackN] = []
				roiDict[stackN].append(roi)
			return roiDict
	
	#Result Table
	class displayResult:
		column_headers = None
		table = None
		def __init__(this):
			this.table = ResultsTable()
		def saveResult(this,results_headers, final_results, time_point, measurementN):
			results_headers.insert(0,"Time Point")
			results_headers.insert(1,"Measurement#")
			print results_headers
			for i in xrange(len(final_results)):
				#puncta
				this.table.incrementCounter()
				this.table.addValue("Time Point",time_point)
				this.table.addValue("Measurement#", int(measurementN))
				for j in xrange(len(final_results[i])):
					this.table.addValue(results_headers[j+2],float(final_results[i][j]))
		def showResult(this):
			this.table.show("Results")
	
	def pointDist(this,p1,p2):
		return ((p1[0]-p2[0])**2+(p1[1]-p2[1])**2)**0.5	

	def __init__(this,resultPath,timeSet):
		rm = RoiManager.getRoiManager()
		rm.reset()
		measHandler = movementAnalysis.measurementHandler(resultPath)
		resultSummary = measHandler.measurementDataSummary(resultPath)
		results = OrderedDict()
		dR = movementAnalysis.displayResult()
		for tp in resultSummary:
			print "Processing time point = " + tp
			results[tp] = OrderedDict()
			for measurementN in resultSummary[tp]:
				results[tp][measurementN] = []
				print "        Processing measurement N = " + str(measurementN)
				imp = measHandler.readSingleMeasurement(tp,measurementN)
				cal = imp.getCalibration()
				fps = 1/cal.frameInterval
				roiDict = measHandler.roiSorted()
				for planeN in roiDict:
					print "                Processing Time plane = " + str(planeN)
					imp.setSlice(int(planeN))
					
					if len(roiDict[planeN]) != 1:
						raise NameError("Only one ROI for each plane accepted for single puncta movement tracking!")
					
					puncta = roiDict[planeN][0]
					
					imp.setRoi(puncta, False)
					stat = imp.getStatistics(Measurements.CENTER_OF_MASS)
					cmass = [stat.xCenterOfMass, stat.yCenterOfMass]
					cmass0 = cmass
					if len(results[tp][measurementN]) !=0:
						cmass.append(this.pointDist(results[tp][measurementN][0],cmass0))
						cmass.append(this.pointDist(results[tp][measurementN][len(results[tp][measurementN]) - 1],cmass0)*fps*timeSet)
					else:
						cmass.append(-1)
						cmass.append(-1)
					results[tp][measurementN].append(cmass)
					#print "For planeN=" + str(planeN) + ", perimeter=" + str(equiD)
				headers = ["Centroid X", "Centroid Y","Displacement T=0","Displacement per " + str(timeSet) + "sec"]
				dR.saveResult(headers,results[tp][measurementN],tp,measurementN)
		#print results
		dR.showResult()


#---------------------Main Program Startup---------------------------------
mainDialog = NonBlockingGenericDialog("Puncta Tracker V2.3")

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