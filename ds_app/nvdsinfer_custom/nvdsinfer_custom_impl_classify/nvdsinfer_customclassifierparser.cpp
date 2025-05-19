#include <cstring>
#include <iostream>
#include "nvdsinfer_custom_impl.h"
#include <cmath>
#include <algorithm>
/* This is a sample classifier output parsing function from softmax layers for
 * the vehicle type classifier model provided with the SDK. */
/* C-linkage to prevent name-mangling */

static std::vector < std::vector< std:: string > > labels_ppe02 { {
    "unknown", "not_safety_shoes", "safety_shoes"
    } };

// Function to calculate the softmax of a given vector (numerically stable)
std::vector<double> softmax(const std::vector<double>& x) {
    std::vector<double> softmaxOutputs(x.size());
    // Find the maximum value to subtract for numerical stability
    double maxVal = *std::max_element(x.begin(), x.end());
    // Compute the sum of the exponentials of the adjusted values
    double sumExp = 0.0;
    for (double val : x) {
        sumExp += std::exp(val - maxVal);
    }
    // Compute the softmax values
    for (size_t i = 0; i < x.size(); ++i) {
        softmaxOutputs[i] = std::exp(x[i] - maxVal) / sumExp;
    }
    return softmaxOutputs;
}
// Function to apply softmax to the output vector
std::vector<double> applySoftmax(const std::vector<double>& outputs) {
    return softmax(outputs);
}
// Function to find the index of the maximum element
int findMaxIndex(const std::vector<double>& vec) {
    auto maxElementIter = std::max_element(vec.begin(), vec.end());
    return std::distance(vec.begin(), maxElementIter);
}

extern "C"
bool NvDsInferClassiferParseCustomPPE02Sigmoid (std::vector<NvDsInferLayerInfo> const &outputLayersInfo,
        NvDsInferNetworkInfo  const &networkInfo,
        float classifierThreshold,
        std::vector<NvDsInferAttribute> &attrList,
        std::string &descString)
{
    /* Get the number of attributes supported by the classifier. */
    unsigned int numAttributes = outputLayersInfo.size();
    /* Iterate through all the output coverage layers of the classifier.
    */
    for (unsigned int l = 0; l < numAttributes; l++)
    {
        NvDsInferDimsCHW dims;
        getDimsCHWFromDims(dims, outputLayersInfo[l].inferDims);
        unsigned int numClasses = dims.c;
        float *outputCoverageBuffer = (float *)outputLayersInfo[l].buffer;
        std::vector<double> raw_outputs;
        for (unsigned int c = 0; c < numClasses; c++)
        {
            float probability = outputCoverageBuffer[c];
            raw_outputs.push_back(probability);
        }
        std::vector<double> probabilities = applySoftmax(raw_outputs);

        // Find index of maximum value
        int maxIndex = findMaxIndex(probabilities);
        // Dog Cat:
        float class_prob = probabilities[maxIndex];
        if (class_prob > classifierThreshold)
        {
            NvDsInferAttribute attr;
            attr.attributeIndex = l;
            attr.attributeValue = maxIndex;
            attr.attributeConfidence = class_prob;
            if (labels_ppe02.size() > attr.attributeIndex &&
                attr.attributeValue < labels_ppe02[attr.attributeIndex].size())
            attr.attributeLabel =
                strdup(labels_ppe02[attr.attributeIndex][attr.attributeValue].c_str());
            else
                attr.attributeLabel = nullptr;
            attrList.push_back(attr);
            if (attr.attributeLabel)
                descString.append(attr.attributeLabel).append(" ");
        }
    }
    return true;
}
/* Check that the custom function has been defined correctly */
CHECK_CUSTOM_CLASSIFIER_PARSE_FUNC_PROTOTYPE(NvDsInferClassiferParseCustomPPE02Sigmoid);