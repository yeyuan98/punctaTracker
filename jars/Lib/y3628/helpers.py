# Static helpers

# Imports
#		y3628
import sjlogging
#		ImageJ
from ij import WindowManager
from ij.plugin.frame import RoiManager
from ij.io import FileSaver
#		Python 2.x
import os, json, math
if os.name == 'nt':
	import win32api, win32con

sjlog = sjlogging.SJLogger("punctaTracker:helpers")

#	Key binding propagation
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

#   File handler
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
		sjlog.info("Current folders after sorting: " + json.dumps(li))
		if len(li) == 0:
			return 1
		else:
			return int(li[len(li)-1]) + 1
	def checkExistenceAndCreate(this, path, dir_name):
		if not dir_name in os.listdir(path):
			os.mkdir(os.path.join(path,dir_name))
		sjlog.info("Checked folder name="+ dir_name + ", under path="+ path)

# ROI saver
class roiSaver:
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
		sjlog.info("total ROI count = " + str(RoiManager.getInstance().getCount()))
		path = os.path.join(this.temp_folder,this.time_point,str(this.measurementN),roiFileName)
		RoiManager.getInstance().runCommand("Save",path)
	def saveImage(this,imp):
		#saves the imageplus as is
		impFileName = "source.tif"
		path = os.path.join(this.temp_folder,this.time_point,str(this.measurementN),impFileName)
		fsr = FileSaver(imp)
		fsr.saveAsTiff(path)

# Misc functions

# L2-dist
def pointDist(p1,p2):
	return ((p1[0]-p2[0])**2+(p1[1]-p2[1])**2)**0.5

# Quantile (q in percentage)
def quantile(list_num, q):
	list_num = sorted(list_num)
	return list_num[int(max(math.floor(len(list_num)*q/100)-1,0))]
