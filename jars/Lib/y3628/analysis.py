# Analysis modules
#	TODO: Testing the movement analysis module
#	TODO: Further modularize

# Imports
#       y3628
import sjlogging
from analysisHandlers import *
from helpers import pointDist, quantile
#		ImageJ
from ij.measure import Measurements
#		ImageJ Plugins
from ij.plugin.frame import RoiManager
from collections import OrderedDict
#		Python 2.x
import csv

sjlog = sjlogging.SJLogger("punctaTracker:analysis")

#Puncta/ROI intensity (CTCF) analysis - original
#Refactored as part of R3.0
#Removed background subtraction mode selection
#Now it is enforced to perform background subtraction
class roiIntAnalysis:

	def measure_ROI(this,imp,roi):
		# Measure a single ROI
		imp.setSlice(int(roi.getName()[0:4]))
		imp.setRoi(roi, False)
		stat = imp.getStatistics()
		return [stat.area,stat.mean,stat.area*stat.mean]

	def __init__(this,resultPath):
		headers = ["Plane#", "Area", "Mean", "Integrated", "CTCF"]
		rm = RoiManager.getRoiManager()
		rm.reset()
		measHandler = measurementHandler(resultPath)
		resultSummary = measHandler.measurementDataSummary(resultPath)
		results = OrderedDict()
		dR = displayResult(headers)
		sjlog.info("Running roiIntAnalysis")
		for tp in resultSummary:
			results[tp] = OrderedDict()
			for measurementN in resultSummary[tp]:
				results[tp][measurementN] = []
				sjlog.info("Processing measurement N = " + str(measurementN))
				imp = measHandler.readSingleMeasurement(tp,measurementN)
				roiDict = measHandler.roiSorted()
				for planeN in roiDict:
					sjlog.info("Processing Z Plane = " + str(planeN))
					planeNresults = []
					for roi in roiDict[planeN]:
						# roiMeas: [plane#, A, M, I]
						roiMeas = [planeN]
						roiMeas.extend(this.measure_ROI(imp,roi))
						planeNresults.append(roiMeas)
					bgd = planeNresults[len(planeNresults) - 1][2]
					for i in xrange(len(planeNresults) - 1):
						planeNresults[i].append(
							planeNresults[i][3] - bgd*planeNresults[i][1])
					planeNresults.pop()
					results[tp][measurementN].extend(planeNresults)
				dR.saveResult(headers, results[tp][measurementN],tp,measurementN)
		dR.showResult()

#New for R2.2 Nucleus Dist Analysis Module
class nucleusAnalysis:
	
	def __init__(this,resultPath):
		headers = ["Distance", "Equivalent Diameter"]
		rm = RoiManager.getRoiManager()
		rm.reset()
		measHandler = measurementHandler(resultPath)
		resultSummary = measHandler.measurementDataSummary(resultPath)
		results = OrderedDict()
		dR = displayResult(headers)
		sjlog.info("Running nucleusAnalysis")
		for tp in resultSummary:
			sjlog.info("Processing time point = " + tp)
			results[tp] = OrderedDict()
			for measurementN in resultSummary[tp]:
				results[tp][measurementN] = []
				sjlog.info("Processing measurement N = " + str(measurementN))
				imp = measHandler.readSingleMeasurement(tp,measurementN)
				cal = imp.getCalibration()
				roiDict = measHandler.roiSorted()
				for planeN in roiDict:
					sjlog.info("Processing Z Plane = " + str(planeN))
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
						minimumDist = pointDist(cmass,points[0])
						for p in points:
							if pointDist(cmass,p) < minimumDist:
								minimumDist = pointDist(cmass,p)
						minDist.append(minimumDist)
					for md in minDist:
						results[tp][measurementN].append([md, equiD])
					#print "For planeN=" + str(planeN) + ", perimeter=" + str(equiD)
				dR.saveResult(headers,results[tp][measurementN],tp,measurementN)
		#print results
		dR.showResult()

#New for R2.3 Movement analysis module
class movementAnalysis:

	def __init__(this,resultPath,timeSet):
		headers = ["Centroid X", "Centroid Y","Displacement T=0","Displacement per " + str(timeSet) + "sec"]
		rm = RoiManager.getRoiManager()
		rm.reset()
		measHandler = measurementHandler(resultPath)
		resultSummary = measHandler.measurementDataSummary(resultPath)
		results = OrderedDict()
		dR = displayResult(headers)
		sjlog.info("Running movementAnalysis")
		for tp in resultSummary:
			sjlog.info("Processing time point = " + tp)
			results[tp] = OrderedDict()
			for measurementN in resultSummary[tp]:
				results[tp][measurementN] = []
				sjlog.info("Processing measurement N = " + str(measurementN))
				imp = measHandler.readSingleMeasurement(tp,measurementN)
				cal = imp.getCalibration()
				fps = 1/cal.frameInterval
				roiDict = measHandler.roiSorted()
				for planeN in roiDict:
					sjlog.info("Processing Time plane = " + str(planeN))
					imp.setSlice(int(planeN))
					
					if len(roiDict[planeN]) != 1:
						raise NameError("Only one ROI for each plane accepted for single puncta movement tracking!")
					
					puncta = roiDict[planeN][0]
					
					imp.setRoi(puncta, False)
					stat = imp.getStatistics(Measurements.CENTER_OF_MASS)
					cmass = [stat.xCenterOfMass, stat.yCenterOfMass]
					cmass0 = cmass
					if len(results[tp][measurementN]) !=0:
						cmass.append(pointDist(results[tp][measurementN][0],cmass0))
						cmass.append(pointDist(results[tp][measurementN][len(results[tp][measurementN]) - 1],cmass0)*fps*timeSet)
					else:
						cmass.append(-1)
						cmass.append(-1)
					results[tp][measurementN].append(cmass)
					#print "For planeN=" + str(planeN) + ", perimeter=" + str(equiD)
				dR.saveResult(headers,results[tp][measurementN],tp,measurementN)
		#print results
		dR.showResult()

#New for R3.1 Percentage in ROI analysis
#	Example: how many RNA-FISH spots are within manually annotated nucleus / whole cell
class spotInRoiAnalysis:

	def addMetaDataEntries(this, metaCsvPath):
		# Loading metadata csv
		#	1. Adding extra columns to read for the spot CSV file
		#		~ appending to this.dataEntries
		#		~ adding this.params: meta_i -> real_spot_csv_column_name_i
		#	2. Adding an dict for mapping: (tp, meas) -> (meta_1, ...)
		with open(metaCsvPath, 'rb') as cf:
			rd = csv.reader(cf)
			# Header row, which should contain ("tp", "meas", ...)
			metaHeaders = rd.next()
			(metaIdx_tp, metaIdx_meas) = (metaHeaders.index("tp"), metaHeaders.index("meas"))
			# The ... spotCsv columns will be what we want to read in
			metaHeaders.remove("tp")
			metaHeaders.remove("meas")
			# Add the ... columns to params and dataEntries
			for metaIdx in xrange(len(metaHeaders)):
				newEntryForMeta = "meta_" + str(metaIdx)
				this.dataEntries.append(newEntryForMeta)
				this.params[newEntryForMeta] = metaHeaders[metaIdx]
			# Adding the mapping dict this.metaMap
			this.metaMap = {}
			for row in rd:
				(tp, meas) = (row[metaIdx_tp], row[metaIdx_meas])
				for idx in sorted([metaIdx_tp, metaIdx_meas], reverse=True):
					# Pop >1 elements need to remove by reverse index order
					del row[idx]
				this.metaMap[(tp, meas)] = tuple(row)
		sjlog.info("Metadata mapping = "+str(this.metaMap))
	
	
	def computeColumnIndices(this):
		mapped = lambda s : this.headers.index(this.params[s])
		indices = {}
		for entry in this.dataEntries:
			indices[entry] = mapped(entry)
		this.indices = indices
	
	# Data manipulation
	def initializeData(this):
		# Data stored in this.data, dict of list
		this.data = {}
		for entry in this.dataEntries:
			this.data[entry] = []
	def addDataRow(this, row):
		# Pick the relevant entries to append to lists
		for entry in this.dataEntries:
			this.data[entry].append(row[this.indices[entry]])
	def convertDataTypes(this):
		# Convert into suitable types
		# 	tp, meas: string
		#	x, y, z, score: float
		this.data["x"] = [float(t) for t in this.data["x"]]
		this.data["y"] = [float(t) for t in this.data["y"]]
		this.data["z"] = [float(t) for t in this.data["z"]]
		this.data["score"] = [float(t) for t in this.data["score"]]
	
	# Data computation

	def getDataSubset(this, indices, data2subset):
		# Subset loaded data based on a bunch of indices
		#	Takes data from data2subset
		data_subset = {}
		for entry in this.dataEntries:
			data_subset[entry] = [data2subset[entry][i] for i in indices]
		return data_subset

	def prepDataByMeasTp(this, tp, meas):
		# Subset loaded data based on timepoint and measurement#
		#	Should be called before `getDataByProximalZ`
		
		#	Which meta combination is the given (tp, meas)
		metaValues = this.metaMap[(tp, meas)]
		sjlog.info("Metadata for this measurement = "+str(metaValues))
		#	Subset data to get those fully match the meta
		#		Start with meta_0
		meta_0 = this.data["meta_0"]
		currMeta = metaValues[0]
		indices = [idx for idx in xrange(len(meta_0)) if meta_0[idx] == currMeta]
		#		Check all remaining meta
		for j in xrange(1, len(metaValues)):
			meta_j = this.data["meta_"+str(j)]
			currMeta = metaValues[j]
			indices = [idx for idx in indices if meta_j[idx] == currMeta]
		sjlog.info("Number of spots for this measurement = "+str(len(indices)))
		this.prepedData = this.getDataSubset(indices, this.data)

	def getDataByProximalZ(this, z):
		dist_z = [abs(t - z) for t in this.prepedData["z"]]
		score = this.prepedData["score"]
		z_max = this.params["z_slice_max"]
		score_min = quantile(score, this.params["min_score"])
		proximal_indices = [idx for idx in xrange(len(dist_z)) if dist_z[idx] <= z_max and score[idx] >= score_min]
		sjlog.info("Number of spots in Z proximity & sufficient score = "+str(len(proximal_indices)))
		sjlog.info("Minimum score is "+str(score_min))
		return this.getDataSubset(proximal_indices, this.prepedData)
	
	def __init__(this,resultPath,spotCsvPath,metaCsvPath,params):

		this.params = params
		this.dataEntries = ["x", "y", "z", "score"]

		sjlog.info("Running spotInRoiAnalysis")
		# Adding data entries for metadata columns
		this.addMetaDataEntries(metaCsvPath)
		
		# Loading spot csv data
		with open(spotCsvPath, 'rb') as cf:
			rd = csv.reader(cf)
			# Header row, use params for mapping
			this.headers = rd.next()
			# Get indices for the relevant rows
			this.computeColumnIndices()
			# Read in all points
			this.initializeData()
			for row in rd:
				this.addDataRow(row)
			# Convert data into suitable types
			this.convertDataTypes()
		sjlog.info("Total number of spots after init = "+str(len(this.data["x"])))

		headers = ["Plane#", "Equivalent Diameter", "Spot Count"]
		rm = RoiManager.getRoiManager()
		rm.reset()
		measHandler = measurementHandler(resultPath)
		resultSummary = measHandler.measurementDataSummary(resultPath)
		results = OrderedDict()
		dR = displayResult(headers)
		for tp in resultSummary:
			sjlog.info("Processing time point = " + tp)
			results[tp] = OrderedDict()
			for measurementN in resultSummary[tp]:
				# Subset data - only relevant (tp, meas)
				sjlog.info("Processing measurement N = " + str(measurementN))
				this.prepDataByMeasTp(tp, measurementN)
				results[tp][measurementN] = []
				imp = measHandler.readSingleMeasurement(tp,measurementN)
				roiDict = measHandler.roiSorted()
				for planeN in roiDict:
					sjlog.info("Processing Z Plane = " + str(planeN))
					# Subset spot data - only proximal Z
					#	Also filters by score
					spot_data = this.getDataByProximalZ(float(planeN))
					spot_num = len(spot_data["z"])
					for idx in xrange(len(roiDict[planeN])):
						# Can have multiple ROIs per plane
						polygon = roiDict[planeN][idx].getInterpolatedPolygon()
						px = polygon.xpoints
						py = polygon.ypoints
						imp.setSlice(int(planeN))
						imp.setRoi(roiDict[planeN][idx], False)
						# Get equi. diameter
						stat = imp.getStatistics(Measurements.AREA)
						area = stat.area
						equiD = (4*area/3.141593)**0.5
						# Contains by (x, y)
						spot_contains = [polygon.contains(spot_data["x"][i], spot_data["y"][i]) for i in xrange(spot_num)]
						sjlog.info("Number of fully contained spots in ROI = "+str(sum(spot_contains)))
						# Which are "close enough" according to XY maximum distance param
						maxXYdistPixels = this.params["xy_max"]
						for j in xrange(len(spot_contains)):
							# Only do computation for spots not contained
							if not spot_contains[j]:
								dists = [pointDist((spot_data["x"][j], spot_data["y"][j]), (px[k],py[k])) for k in xrange(len(px))]
								if min(dists) <= maxXYdistPixels:
									spot_contains[j] = True
						spot_num_contains = sum(spot_contains)
						sjlog.info("Number of contained spots (w/ XY padding) in ROI = "+str(spot_num_contains))
						sjlog.info(
							"Position of all contained spots = "+
							str([(spot_data["x"][idx], spot_data["y"][idx]) for idx in xrange(len(spot_contains)) if spot_contains[idx]]))
						# Append results
						results[tp][measurementN].append([planeN, equiD, spot_num_contains])
					
				dR.saveResult(headers,results[tp][measurementN],tp,measurementN)
		#print results
		dR.showResult()