# Helpers for analysis modules

# Imports
#		ImageJ
from ij import IJ
from ij.plugin.frame import RoiManager
from ij.measure import ResultsTable
#		Python 2.x
from collections import OrderedDict
import os, json
if os.name == 'nt':
    import win32api, win32con

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
    def __init__(this, headers):
        this.table = ResultsTable()
        this.column_headers = ["Time Point", "Measurement#"]
        this.column_headers.extend(headers)

    def saveResult(this,results_headers, final_results, time_point, measurementN):
        for i in xrange(len(final_results)):
            #puncta
            this.table.incrementCounter()
            this.table.addValue(this.column_headers[0],time_point)
            this.table.addValue(this.column_headers[1], int(measurementN))
            for j in xrange(len(final_results[i])):
                this.table.addValue(this.column_headers[j+2],float(final_results[i][j]))
    def showResult(this):
        this.table.show("Results")
