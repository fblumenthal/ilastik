from ilastik.workflow import Workflow

from ilastik.applets.dataSelection import DataSelectionApplet
from ilastik.applets.fillMissingSlices import FillMissingSlicesApplet
from ilastik.applets.featureSelection import FeatureSelectionApplet
from ilastik.applets.pixelClassification import PixelClassificationApplet, PixelClassificationBatchResultsApplet

from ilastik.applets.fillMissingSlices.opFillMissingSlices import OpFillMissingSlicesNoCache
from ilastik.applets.featureSelection.opFeatureSelection import OpFeatureSelectionNoCache
from ilastik.applets.pixelClassification.opPixelClassification import OpPredictionPipelineNoCache

from lazyflow.graph import Graph, OperatorWrapper

class SynapsePixelClassificationWorkflow(Workflow):
    """
    A special workflow for detecting synapses in TEM data with pixel classification.
    This is the first half of the synapse detection pipeline for the Bock11 dataset.
    """

    #FEATURE_IMPLEMENTATION = 'Original'
    FEATURE_IMPLEMENTATION = 'Interpolated'

    @property
    def applets(self):
        return self._applets

    @property
    def imageNameListSlot(self):
        return self.dataSelectionApplet.topLevelOperator.ImageName

    def __init__(self, appendBatchOperators=True, *args, **kwargs):
        # Create a graph to be shared by all operators
        graph = Graph()
        super( self.__class__, self ).__init__( graph=graph, *args, **kwargs )
        self._applets = []

        # Applets for training (interactive) workflow 
        self.dataSelectionApplet = DataSelectionApplet(self, "Input Data", "Input Data", supportIlastik05Import=True, batchDataGui=False)
        self.fillMissingSlicesApplet = FillMissingSlicesApplet(self, "Fill Missing Slices", "Fill Missing Slices")
        self.featureSelectionApplet = FeatureSelectionApplet(self,
                                                             "Feature Selection",
                                                             "FeatureSelections",
                                                             filter_implementation=self.FEATURE_IMPLEMENTATION)
        self.pcApplet = PixelClassificationApplet(self, "PixelClassification")

        # Expose for shell
        self._applets.append(self.dataSelectionApplet)
        self._applets.append(self.fillMissingSlicesApplet)
        self._applets.append(self.featureSelectionApplet)
        self._applets.append(self.pcApplet)

        if appendBatchOperators:
            # Create applets for batch workflow
            self.batchInputApplet = DataSelectionApplet(self, "Batch Prediction Input Selections", "BatchDataSelection", supportIlastik05Import=False, batchDataGui=True)
            self.batchResultsApplet = PixelClassificationBatchResultsApplet(self, "Batch Prediction Output Locations")
    
            # Expose in shell        
            self._applets.append(self.batchInputApplet)
            self._applets.append(self.batchResultsApplet)
    
            # Connect batch workflow (NOT lane-based)
            self._initBatchWorkflow()

    def connectLane(self, laneIndex):
        # Get a handle to each operator
        opData = self.dataSelectionApplet.topLevelOperator.getLane(laneIndex)
        opFillMissingSlices = self.fillMissingSlicesApplet.topLevelOperator.getLane(laneIndex)
        opTrainingFeatures = self.featureSelectionApplet.topLevelOperator.getLane(laneIndex)
        opClassify = self.pcApplet.topLevelOperator.getLane(laneIndex)

        # Input Image -> Fill Missing Slices
        opFillMissingSlices.Input.connect( opData.Image )
        
        # Preprocessed Input -> Feature Op
        #                and -> Classification Op (for display)
        opTrainingFeatures.InputImage.connect( opFillMissingSlices.Output )
        opClassify.InputImages.connect( opFillMissingSlices.Output )
        
        # Feature Images -> Classification Op (for training, prediction)
        opClassify.FeatureImages.connect( opTrainingFeatures.OutputImage )
        opClassify.CachedFeatureImages.connect( opTrainingFeatures.CachedOutputImage )
        
        # Training flags -> Classification Op (for GUI restrictions)
        opClassify.LabelsAllowedFlags.connect( opData.AllowLabels )
        

    def _initBatchWorkflow(self):
        """
        Connect the batch-mode top-level operators to the training workflow and to eachother.
        """
        # Access applet operators from the training workflow
        opTrainingFeatures = self.featureSelectionApplet.topLevelOperator
        opClassify = self.pcApplet.topLevelOperator
        
        # Access the batch operators
        opBatchInputs = self.batchInputApplet.topLevelOperator
        opBatchResults = self.batchResultsApplet.topLevelOperator
        
        ## Create additional batch workflow operators
        opBatchFillMissingSlices = OperatorWrapper( OpFillMissingSlicesNoCache, parent=self )
        opBatchFeatures = OperatorWrapper( OpFeatureSelectionNoCache,
                                           operator_kwargs={'filter_implementation' : self.FEATURE_IMPLEMENTATION},
                                           parent=self, promotedSlotNames=['InputImage'] )
        opBatchPredictionPipeline = OperatorWrapper( OpPredictionPipelineNoCache, parent=self )
        
        ## Connect Operators ## 
        
        # Provide dataset paths from data selection applet
        opBatchResults.DatasetPath.connect( opBatchInputs.ImageName )
        
        # Connect (clone) the feature operator inputs from 
        #  the interactive workflow's features operator (which gets them from the GUI)
        opBatchFeatures.Scales.connect( opTrainingFeatures.Scales )
        opBatchFeatures.FeatureIds.connect( opTrainingFeatures.FeatureIds )
        opBatchFeatures.SelectionMatrix.connect( opTrainingFeatures.SelectionMatrix )
        
        # Classifier and LabelsCount are provided by the interactive workflow
        opBatchPredictionPipeline.Classifier.connect( opClassify.Classifier )
        opBatchPredictionPipeline.MaxLabel.connect( opClassify.MaxLabelValue )
        opBatchPredictionPipeline.FreezePredictions.setValue( False )
        
        # Provide these for the gui
        opBatchResults.RawImage.connect( opBatchInputs.Image )
        opBatchResults.PmapColors.connect( opClassify.PmapColors )
        opBatchResults.LabelNames.connect( opClassify.LabelNames )
        
        # Connect Image pathway:
        # Input Image -> Fill Missing Slices -> Features Op -> Prediction Op -> Export
        opBatchFillMissingSlices.Input.connect( opBatchInputs.Image )
        opBatchFeatures.InputImage.connect( opBatchFillMissingSlices.Output )
        opBatchPredictionPipeline.FeatureImages.connect( opBatchFeatures.OutputImage )
        opBatchResults.ImageToExport.connect( opBatchPredictionPipeline.HeadlessPredictionProbabilities )

        self.opBatchPredictionPipeline = opBatchPredictionPipeline

    def getHeadlessOutputSlot(self, slotId):
        # "Regular" (i.e. with the images that the user selected as input data)
        if slotId == "Predictions":
            return self.pcApplet.topLevelOperator.HeadlessPredictionProbabilities
        elif slotId == "PredictionsUint8":
            return self.pcApplet.topLevelOperator.HeadlessUint8PredictionProbabilities
        # "Batch" (i.e. with the images that the user selected as batch inputs).
        elif slotId == "BatchPredictions":
            return self.opBatchPredictionPipeline.HeadlessPredictionProbabilities
        if slotId == "BatchPredictionsUint8":
            return self.opBatchPredictionPipeline.HeadlessUint8PredictionProbabilities
        
        raise Exception("Unknown headless output slot")



