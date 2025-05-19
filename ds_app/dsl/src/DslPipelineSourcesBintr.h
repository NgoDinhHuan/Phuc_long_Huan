
/*
The MIT License

Copyright (c) 2019-2021, Prominence AI, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in-
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/

#ifndef _DSL_PIPELINE_SOURCES_BINTR_H
#define _DSL_PIPELINE_SOURCES_BINTR_H

#include "Dsl.h"
#include "DslApi.h"
#include "DslSourceBintr.h"

namespace DSL
{
    #define DSL_PIPELINE_SOURCES_PTR std::shared_ptr<PipelineSourcesBintr>
    #define DSL_PIPELINE_SOURCES_NEW(name, uniquePipelineId) \
        std::shared_ptr<PipelineSourcesBintr> \
           (new PipelineSourcesBintr(name, uniquePipelineId))

    class PipelineSourcesBintr : public Bintr
    {
    public: 
    
        PipelineSourcesBintr(const char* name, uint uniquePipelineId);

        ~PipelineSourcesBintr();
        
        /**
         * @brief adds a child SourceBintr to this PipelineSourcesBintr
         * @param pChildSource shared pointer to SourceBintr to add
         * @return true if the SourceBintr was added correctly, false otherwise
         */
        bool AddChild(DSL_SOURCE_PTR pChildSource);
        
        /**
         * @brief removes a child SourceBintr from this PipelineSourcesBintr
         * @param pChildElement a shared pointer to SourceBintr to remove
         * @return true if the SourceBintr was removed correctly, false otherwise
         */
        bool RemoveChild(DSL_SOURCE_PTR pChildSource);

        /**
         * @brief overrides the base method and checks in m_pChildSources only.
         */
        bool IsChild(DSL_SOURCE_PTR pChildSource);

        /**
         * @brief overrides the base Noder method to only return the number of 
         * child SourceBintrs and not the total number of children... 
         * i.e. exclude the nuber of child Elementrs from the count
         * @return the number of Child SourceBintrs held by this PipelineSourcesBintr
         */
        uint GetNumChildren()
        {
            LOG_FUNC();
            
            return m_pChildSources.size();
        }

        /**
         * @brief interates through the list of child source bintrs setting 
         * their Sensor Id's and linking to the Streammux
         */
        bool LinkAll();
        
        /**
         * @brief interates through the list of child source bintrs unlinking
         * them from the Streammux and reseting their Sensor Id's
         */
        void UnlinkAll();

        void EosAll();

        /**
         * @brief Gets the current Streammuxer "play-type-is-live" setting
         * @return true if play-type is live, false otherwise
         */
        bool StreammuxPlayTypeIsLiveGet();

        /**
         * @brief Sets the current Streammuxer play type based on the first source added
         * @param isLive set to true if all sources are to be Live, and therefore live only.
         * @return true if live-source is succesfully set, false otherwise
         */
        bool StreammuxPlayTypeIsLiveSet(bool isLive);

        /**
         * @brief Gets the current config-file in use by the Pipeline's Streammuxer.
         * Default = NULL. Streammuxer will use all default vaules.
         * @return Current config file in use.
         */
        const char* GetStreammuxConfigFile();
        
        /**
         * @brief Sets the config-file for the Pipeline's Streammuxer to use.
         * Default = NULL. Streammuxer will use all default vaules.
         * @param[in] configFile absolute or relative pathspec to new Config file.
         * @return True if the config-file property could be set, false otherwise,
         */
        bool SetStreammuxConfigFile(const char* configFile);

        /**
         * @brief Gets the current batch settings for the SourcesBintr's Stream Muxer.
         * @return Current batchSize, default == the number of source.
         */
        uint GetStreammuxBatchSize();

        /**
         * @brief Sets the current batch size for the SourcesBintr's Stream Muxer.
         * @param[in] batchSize new batchSize to set, default == the number of sources.
         * @return true if batch-size is succesfully set, false otherwise.
         */
        bool SetStreammuxBatchSize(uint batchSize);

        /**
         * @brief Gets the current setting for the PipelineSourcesBintr's Streammuxer
         * num-surfaces-per-frame seting
         * @return current setting for the number of surfaces [1..4].
         */
        uint GetStreammuxNumSurfacesPerFrame();

        /**
         * @brief Sets the current setting for the PipelineSourcesBintr's 
         * Streammuxer num-surfaces-per-frame seting.
         * @param[in] num new value for the number of surfaces [1..4].
         * @return true if dimensions are succesfully set, false otherwise.
         */
        bool SetStreammuxNumSurfacesPerFrame(uint num);
        
        /**
         * @brief Gets the current setting for the PipelineSourcesBintr's 
         * Streammuxer sync-inputs enabled property.
         * @preturn true if enabled, false otherwise.
         */
        boolean GetStreammuxSyncInputsEnabled();
        
        /**
         * @brief Sets the PipelineSourcesBintr's Streammuxer sync-inputs 
         * enabled property.
         * @param enabled set to true to enable sync-inputs, false otherwise.
         * @return true if sync-inputs enabled was succesfully set, false otherwise.
         */
        bool SetStreammuxSyncInputsEnabled(boolean enabled);
        
        /**
         * @brief Gets the current setting for the PipelineSourcesBintr's 
         * Streammuxer attach-sys-ts enabled property.
         * @preturn true if attach-sys-ts is enabled, false otherwise.
         */
        boolean GetStreammuxAttachSysTsEnabled();
        
        /**
         * @brief Sets the PipelineSourcesBintr's Streammuxer attach-sys-ts 
         * enabled property.
         * @param enabled set to true to enable attach-sys-ts, false otherwise.
         * @return true if attach-sys-ts enabled was succesfully set, false otherwise.
         */
        bool SetStreammuxAttachSysTsEnabled(boolean enabled);
        
        /**
         * @brief Gets the current setting for the PipelineSourcesBintr's 
         * Streammuxer max-latency property.
         * @preturn The maximum upstream latency in nanoseconds. 
         * When sync-inputs=1, buffers coming in after max-latency shall be dropped.
         */
        uint GetStreammuxMaxLatency();
        
        /**
         * @brief Sets the PipelineSourcesBintr's Streammuxer max-latency property.
         * @param[in] maxLatency the maximum upstream latency in nanoseconds. 
         * When sync-inputs=1, buffers coming in after max-latency shall be dropped.
         * @return true if max-latency was succesfully set, false otherwise.
         */
        bool SetStreammuxMaxLatency(uint maxLatency);
        
        /**
         * @brief Calls on all child Sources to disable their EOS consumers.
         */
        void DisableEosConsumers();

        /** 
         * @brief Returns the state of the USE_NEW_NVSTREAMMUX env var.
         * @return true if USE_NEW_NVSTREAMMUX=yes, false otherwise.
         */
        bool UseNewStreammux(){return m_useNewStreammux;};

        //----------------------------------------------------------------------------
        // OLD NVSTREAMMUX SERVICES - Start
        
        /**
         * @brief Gets the current batch settings for the SourcesBintr's Stream Muxer.
         * @param[out] batchSize current batchSize, default == the number of source.
         * @param[out] batchTimeout current batch timeout. Default = -1, disabled.
         */
        void GetStreammuxBatchProperties(uint* batchSize, int* batchTimeout);

        /**
         * @brief Sets the current batch settings for the SourcesBintr's Stream Muxer.
         * @param[in] batchSize new batchSize to set, default == the number of sources.
         * @param[in] batchTimeout timeout value to set in ms. Set to -1 to disable.
         * @return true if batch-properties are succesfully set, false otherwise.
         */
        bool SetStreammuxBatchProperties(uint batchSize, int batchTimeout);

        /**
         * @brief Gets the current Streammuxer NVIDIA buffer memory type.
         * @return one of the DSL_NVBUF_MEM_TYPE constant values.
         */
        uint GetStreammuxNvbufMemType();

        /**
         * @brief Sets the Streammuxer's NVIDIA buffer memory type.
         * @param[in] type one of the DSL_NVBUF_MEM_TYPE constant values.
         * @return true if nvbuf-memory-type is succesfully set, false otherwise
         */
        bool SetStreammuxNvbufMemType(uint type);

        /**
         * @brief Sets the GPU for the Pipeline's Streammuxer.
         * @return true if successfully set, false otherwise.
         */
        bool SetGpuId(uint gpuId);
        
        /**
         * @brief Gets the current dimensions for the SourcesBintr's Stream Muxer.
         * @param[out] width width in pixels for the current setting.
         * @param[out] height height in pixels for the curren setting.
         */
        void GetStreammuxDimensions(uint* width, uint* height);

        /**
         * @brief Set the dimensions for the SourcesBintr's Streammuxer.
         * @param width width in pixels to set the streamMux Output.
         * @param height height in pixels to set the Streammux output.
         * @return true if dimensions are succesfully set, false otherwise.
         */
        bool SetStreammuxDimensions(uint width, uint height);
        
        /**
         * @brief Gets the current setting for the PipelineSourcesBintr's 
         * Streammuxer padding enabled property.
         * @preturn true if enabled, false otherwise.
         */
        boolean GetStreammuxPaddingEnabled();

        /**
         * @brief Sets the PipelineSourcesBintr's Streammuxer padding 
         * enabled property.
         * @param enabled set to true to enable padding, false otherwise.
         * @return true if padding enabled was succesfully set, false otherwise.
         */
        bool SetStreammuxPaddingEnabled(boolean enabled);


    private:
    
        /**
         * @brief boolean flag to indicate if USE_NEW_NVSTREAMMUX=yes
         */
        bool m_useNewStreammux;
        
        /**
         * @brief adds a child Elementr to this PipelineSourcesBintr
         * @param pChildElement a shared pointer to the Elementr to add
         * @return a shared pointer to the Elementr if added correctly, 
         * nullptr otherwise
         */
        bool AddChild(DSL_BASE_PTR pChildElement);
        
        /**
         * @brief removes a child Elementr from this PipelineSourcesBintr
         * @param pChildElement a shared pointer to the Elementr to remove
         */
        bool RemoveChild(DSL_BASE_PTR pChildElement);
        
        /**
         * @brief unique id for the Parent Pipeline, used to offset all source
         * Id's (if greater than 0)
         */
        uint m_uniquePipelineId; 
        
        /**
         * @brief true if Client explicity set by client, false by default.
         */
        bool m_batchSizeSetByClient;
         
        /**
         * @brief Pad Probe Event Handler to handle all dowstream nvstreammux
         * custome events [GST_NVEVENT_PAD_ADDED, GST_NVEVENT_PAD_DELETED,
         * GST_NVEVENT_STREAM_EOS, GST_NVEVENT_STREAM_SEGMENT]
         */
        DSL_PPEH_STREAM_EVENT_PTR m_pEventHandler;
        
        /**
         * @brief Pad Probe Event Handler to consume all dowstream EOS events
         * Will be created if and when a RTSP source is added to this 
         * PipelineSourcesBintr.
         */
        DSL_PPEH_EOS_CONSUMER_PTR m_pEosConsumer;
        
        /**
         * @brief Pad Probe Handler to add the source-id offset (based on unique 
         * pipeline-id) for this PipelineSourcesBintr
         */
        DSL_PPH_SOURCE_ID_OFFSETTER_PTR m_pSourceIdOffsetter;


        DSL_ELEMENT_PTR m_pStreammux;
        
        /**
         * @brief container of all child sources mapped by their unique names
         */
        std::map<std::string, DSL_SOURCE_PTR> m_pChildSources;
        
        /**
         * @brief container of all child sources mapped by their unique stream-id
         */
        std::map<uint, DSL_SOURCE_PTR> m_pChildSourcesIndexed;

        /**
         * @brief Each source is assigned a unique pad/stream id used to define the
         * streammuxer sink pad when linking. The vector is used on add/remove 
         * to find the next available pad id.
         */
        std::vector<bool> m_usedRequestPadIds;
        
        /**
         * @brief true if all sources are live, false if all sources are non-live
         */
        bool m_areSourcesLive;
        
        /**
         * @brief Absolute or relative path to the Streammuxer config file.
         */
        std::string m_streammuxConfigFile;

        /**
         * @brief Number of surfaces-per-frame stream-muxer setting
         */
        int m_numSurfacesPerFrame;

        /**
         * @brief Compute Scaling HW to use. Applicable only for Jetson.
         * 0 (Default): Default, GPU for Tesla, VIC for Jetson
         * 1 (GPU): GPU
         * 2 (VIC): VIC
         */
        uint m_computeHw;
        
        /**
         * @brief Attach system timestamp as ntp timestamp, otherwise ntp 
         * timestamp calculated from RTCP sender reports.
         */
        boolean m_attachSysTs;
        
        /**
         * @brief if true, sychronizes input frames using PTS.
         */
        boolean m_syncInputs;
        
        /**
         * @brief The maximum upstream latency in nanoseconds. 
         * When sync-inputs=1, buffers coming in after max-latency shall be dropped.
         */
        uint m_maxLatency;
        
        /**
         * @brief Duration of input frames in milliseconds for use in NTP timestamp 
         * correction based on frame rate. If set to 0 (default), frame duration is 
         * inferred automatically from PTS values seen at RTP jitter buffer. When 
         * there is change in frame duration between the RTP jitter buffer and the 
         * nvstreammux, this property can be used to indicate the correct frame rate 
         * to the nvstreammux, for e.g. when there is an audiobuffersplit GstElement 
         * before nvstreammux in the pipeline. If set to -1, disables frame rate 
         * based NTP timestamp correction. 
         */
        int64_t m_frameDuration;
        
        /**
         * @brief property to control EOS propagation downstream from nvstreammux
         * when all the sink pads are at EOS. (Experimental)
         */
        boolean m_dropPipelineEos;

        // ---------------------------------------------------------------------------
        // OLD STREAMMUX PROPERTIES
        
        /**
         * @brief Stream-muxer batch timeout used when waiting for all sources
         * to produce a frame when batching together
         */
        gint m_batchTimeout;
        
        /**
         * @brief Stream-muxer batched frame output width in pixels
         */
        gint m_streamMuxWidth;

        /**
         * @brief Stream-muxer batched frame output height in pixels
         */
        gint m_streamMuxHeight;

        /**
         * @brief true if frame padding is enabled, false otherwise
         */
        boolean m_isPaddingEnabled;

        /**
         * @brief Number of buffers in output buffer pool
         */
        uint m_bufferPoolSize;
        
    };

    
}

#endif // _DSL_PIPELINE_SOURCES_BINTR_H
