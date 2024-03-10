#Tools
#   ActionListeners to put under mainDialog/Tools section

# Imports
#       y3628
import sjlogging
from helpers import fileHandler
#		Bio-Formats
from loci.plugins import BF
from loci.plugins.in import ImporterOptions
#		ImageJ
from ij import IJ
from ij.io import FileSaver, DirectoryChooser
#		ImageJ Plugins
from ij.plugin import ChannelSplitter
#		ImageJ and awt GUIs
from ij.gui import GenericDialog
from java.awt.event import ActionListener

sjlog = sjlogging.SJLogger("punctaTracker:tools")

class ChannelExtract_listen(ActionListener):
	extractTitle = "Extracted channel image"
	def actionPerformed(this, event):
		sjlog.info("Performing channel extract tool")
		IJ.showStatus("Select INPUT File Folder")
		dc_i = DirectoryChooser("Select INPUT File Folder")
		sjlog.info(dc_i.getDirectory())
		fH = fileHandler()
		file_list = fH.getFileList(dc_i.getDirectory())
		sjlog.info(file_list)
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
