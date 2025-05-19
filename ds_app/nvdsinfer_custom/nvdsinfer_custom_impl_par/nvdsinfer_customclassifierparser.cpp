/*
 * Copyright (c) 2018-2019, NVIDIA CORPORATION. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */

#include <cstring>
#include <iostream>
#include "nvdsinfer_custom_impl.h"
#include <cmath>

/* This is a sample classifier output parsing function from softmax layers for
 * the vehicle type classifier model provided with the SDK. */

/* C-linkage to prevent name-mangling */
extern "C"
bool NvDsInferClassiferParseCustomSigmoid (std::vector<NvDsInferLayerInfo> const &outputLayersInfo,
        NvDsInferNetworkInfo  const &networkInfo,
        float classifierThreshold,
        std::vector<NvDsInferAttribute> &attrList,
        std::string &descString);

static std::vector < std::vector< std:: string > > labels { {
    "gender_male", "gender_female", "gender_other", "age_less_than_15", "age_16_30", "age_30_35", "age_46_60", "age_more_than_60", 
    "head_hair_loss", "head_long_hair", "head_black_hair", "head_color_hair", "head_hat", "head_glasses", "head_sun_glasses", 
    "head_facemask", "head_cover", "head_other", "shirt_somi", "shirt_tshirt", "shirt_sweater", "shirt_hoodie", "shirt_short_coat", 
    "shirt_long_coat", "shirt_vest", "shirt_skirt", "shirt_ppe", "shirt_rain_coat", "shirt_none", "shirt_long", "shirt_other", 
    "tayao_long", "tayao_short", "tayao_tanktop", "shirtcolor_black", "shirtcolor_white", "shirtcolor_gray", "shirtcolor_red", 
    "shirtcolor_green", "shirtcolor_blue", "shirtcolor_yellow", "shirtcolor_brown", "shirtcolor_purple", "shirtcolor_pink", 
    "shirtcolor_orange", "shirtcolor_mix", "shirtcolor_other", "pant_jean", "pant_quanthung", "pant_leging", "pant_vest", 
    "pant_vay_xoe", "pant_vay_suon", "pant_vay_bo", "pant_other", "pantlength_angle", "pantlength_knee", "pantlength_upper_knee", 
    "pantcolor_black", "pantcolor_white", "pantcolor_gray", "pantcolor_red", "pantcolor_green", "pantcolor_blue", "pantcolor_yellow", 
    "pantcolor_brown", "pantcolor_purple", "pantcolor_pink", "pantcolor_orange", "pantcolor_mix", "pantcolor_other", "shoes_slipper", 
    "shoes_sport_shoes", "shoes_boot", "shoes_giay_au", "shoes_caogot", "shoes_bupbe", "shoes_other", "status_stand", "status_sit", 
    "status_lie", "status_sleep", "status_walk_run", "status_other", "using_phone", "action_hand_taking", 
    "action_deo_vat_tren_canh_tay", "action_deo_vat_tren_vai", "action_be_tre_em", "action_cong_tre_em", "action_bung_be", 
    "action_push", "action_other", "attach_phone", "thing_tui_vi_cam_tay", "thing_tui_vi_xach_tay", "thing_tui_deo_cheo", 
    "thing_backback", "thing_box", "thing_weapond", "thing_clothes", "thing_other"
    } };

// Function to calculate the sigmoid of a given value x
double sigmoid(double x) {
    return 1 / (1 + std::exp(-x));
}

// Function to apply the sigmoid to each element in the output vector
std::vector<double> applySigmoid(const std::vector<double>& outputs) {
    std::vector<double> sigmoidOutputs;
    sigmoidOutputs.reserve(outputs.size());
    for (double output : outputs) {
        sigmoidOutputs.push_back(sigmoid(output));
    }
    return sigmoidOutputs;
}

extern "C"
bool NvDsInferClassiferParseCustomSigmoid (std::vector<NvDsInferLayerInfo> const &outputLayersInfo,
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
        std::vector<double> probabilities = applySigmoid(raw_outputs);
        
        // Using Phone:
        int c = 84;
        float use_phone_prob = probabilities[c];

        if (use_phone_prob > classifierThreshold)
        {
            NvDsInferAttribute attr;

            attr.attributeIndex = l;
            attr.attributeValue = c;
            attr.attributeConfidence = use_phone_prob;

            if (labels.size() > attr.attributeIndex &&
                attr.attributeValue < labels[attr.attributeIndex].size())
            attr.attributeLabel =
                strdup(labels[attr.attributeIndex][attr.attributeValue].c_str());
            else
                attr.attributeLabel = nullptr;
            attrList.push_back(attr);
            if (attr.attributeLabel)
                descString.append(attr.attributeLabel).append(" ");
        }

        // Attach Phone:
        c = 93;
        float attach_phone_prob = probabilities[c];

        if (attach_phone_prob > classifierThreshold)
        {
            NvDsInferAttribute attr;

            attr.attributeIndex = l;
            attr.attributeValue = c;
            attr.attributeConfidence = attach_phone_prob;

            if (labels.size() > attr.attributeIndex &&
                attr.attributeValue < labels[attr.attributeIndex].size())
            attr.attributeLabel =
                strdup(labels[attr.attributeIndex][attr.attributeValue].c_str());
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
CHECK_CUSTOM_CLASSIFIER_PARSE_FUNC_PROTOTYPE(NvDsInferClassiferParseCustomSigmoid);

