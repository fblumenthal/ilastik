from ilastik.shell.gui.startShellGui import startShellGui
from synapseBlockwiseWorkflow import SynapseBlockwiseWorkflow

def debug_with_new(shell):
    """
    (Function for debug and testing.)
    """
    #projFilePath = "/magnetic/synapse_debug_data/object_prediction.ilp"
    projFilePath = "/magnetic/stuart_object_predictions.ilp"

    # New project
    shell.createAndLoadNewProject(projFilePath)
    workflow = shell.projectManager.workflow

    # Add a file
    from ilastik.applets.dataSelection.opDataSelection import DatasetInfo

    rawInfo = DatasetInfo()
    #rawInfo.filePath = '/magnetic/synapse_debug_data/block256.h5/cube'
    #rawInfo.filePath = '/magnetic/synapse_small_4d.h5/volume/data'
    rawInfo.filePath = '/magnetic/validation_slices_20_40_3200_4000_1200_2000.h5/volume/data'
    opRawDataSelection = workflow.rawDataSelectionApplet.topLevelOperator
    opRawDataSelection.Dataset.resize(1)
    opRawDataSelection.Dataset[0].setValue(rawInfo)

    predictionInfo = DatasetInfo()
    #predictionInfo.filePath = '/magnetic/synapse_debug_data/block256_spots_predictions.h5/cube'
    #predictionInfo.filePath = '/magnetic/synapse_small_4d_synapse_predictions.h5/volume/data'
    predictionInfo.filePath = '/magnetic/validation_slices_20_40_3200_4000_1200_2000_pred.h5/volume/data'
    opPredDataSelection = workflow.predictionSelectionApplet.topLevelOperator
    opPredDataSelection.Dataset.resize(1)
    opPredDataSelection.Dataset[0].setValue(predictionInfo)

    # Select the feature drawer
    shell.setSelectedAppletDrawer(2)

def debug_with_existing(shell):
    """
    (Function for debug and testing.)
    """
    # Open an existing project
    #projFilePath = "/magnetic/objectLabels_good.ilp"
    #projFilePath = "/magnetic/object_prediction.ilp"
    projFilePath = "/magnetic/stuart_object_predictions.ilp"
    
    shell.openProjectFile(projFilePath)

    # Select a default drawer
    shell.setSelectedAppletDrawer(2)
    
    
if __name__ == '__main__':
    startShellGui( SynapseBlockwiseWorkflow )
    #startShellGui( SynapseBlockwiseWorkflow, debug_with_new )
    #startShellGui( SynapseBlockwiseWorkflow, debug_with_existing )

