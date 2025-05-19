FROM nvcr.io/nvidia/deepstream:7.0-triton-multiarch

ENV NVIDIA_DRIVER_CAPABILITIES $NVIDIA_DRIVER_CAPABILITIES,video
ENV LOGLEVEL="INFO"
ENV GST_DEBUG=2
ENV GST_DEBUG_FILE=/app/GST_DEBUG.log
ENV CUDA_VER=12

RUN apt update -y && apt-get -y install \
    libgstrtspserver-1.0-dev \
    gstreamer1.0-rtsp \
    libapr1 \
    libapr1-dev \
    libaprutil1 \
    libaprutil1-dev \
    libgeos-dev \
    libcurl4-openssl-dev python3-pip \
    graphviz \
    libcairo2-dev pkg-config python3-dev \
    libgirepository1.0-dev

RUN apt-get -y install \
    libavformat-dev \
    libswscale-dev  

RUN cp /usr/local/cuda-${CUDA_VER}/targets/x86_64-linux/lib/stubs/libcuda.so /usr/local/lib/

# RUN apt -y install libapr*
RUN python3 -m pip install --upgrade pip
COPY build/ds.requirements requirements.txt
RUN pip3 install -r requirements.txt

## For Pyds
RUN apt-get -y install \
    libcairo2-dev \
    pkg-config python3-dev \
    libgirepository1.0-dev

# Install pyds
WORKDIR /pyds
COPY ds_app/pyds-1.1.10-py3-none-linux_x86_64.whl .
RUN pip3 install ./pyds-1.1.10-py3-none-linux_x86_64.whl

# Custom infer: Yolo
WORKDIR /nvdsinfer_custom_impl_Yolo
COPY ds_app/nvdsinfer_custom/nvdsinfer_custom_impl_Yolo .
RUN make clean && make -j4

WORKDIR /nvdsinfer_custom_impl_Yolo_triton
COPY ds_app/nvdsinfer_custom/nvdsinfer_custom_impl_Yolo_triton .
RUN make clean && make -j4

# Custom infer: PAR
WORKDIR /nvdsinfer_custom_impl_par
COPY ds_app/nvdsinfer_custom/nvdsinfer_custom_impl_par .
RUN make clean && make -j4

# Custom infer: Classify
WORKDIR /nvdsinfer_custom_impl_classify
COPY ds_app/nvdsinfer_custom/nvdsinfer_custom_impl_classify .
RUN make clean && make -j4

# Build dsl
WORKDIR /dsl
COPY ./ds_app/dsl .
RUN make clean && make -j4 && make install

RUN apt update && apt install wget -y && rm -rf /var/lib/apt/lists/*

RUN pip3 install cuda-python

COPY ./ds_app /ds_app

# Download tracker
# RUN wget http://192.168.1.92:9000/cloud-ai-models/tracker/mars-small128.uff -O /ds_app/configs/trackers/mars-small128.uff 

# RUN mkdir -p /ds_app/models/infer/onnx
# RUN mkdir -p /ds_app/models/tracker
# RUN wget http://192.168.1.92:9000/cloud-ai-models/tracker/mars-small128.uff -O /ds_app/models/tracker/mars-small128.uff 
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/cm02_2007_640.onnx  -O /ds_app/models/infer/onnx/cm02_2007_640.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/par_2609_dynamic_shape.onnx -O /ds_app/models/infer/onnx/par_2609_dynamic_shape.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/yolov8l_forklift.onnx -O /ds_app/models/infer/onnx/yolov8l_forklift.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/yolov8n.onnx -O /ds_app/models/infer/onnx/yolov8n.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/alcoholxface2_best.onnx -O /ds_app/models/infer/onnx/alcoholxface2_best.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/alcoholxperson_best_14072024.onnx -O /ds_app/models/infer/onnx/alcoholxperson_best_14072024.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/product_fall.onnx -O /ds_app/models/infer/onnx/product_fall.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/yolov8m_PPE02.onnx -O /ds_app/models/infer/onnx/yolov8m_PPE02.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/yolov8m_warehouse05052024_v3.onnx -O /ds_app/models/infer/onnx/yolov8m_warehouse05052024_v3.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/VEH03.onnx -O /ds_app/models/infer/onnx/VEH03.onnx
# RUN wget http://192.168.1.92:9000/cloud-ai-models/infer/onnx/21Label7_best.onnx -O /ds_app/models/infer/onnx/21Label7_best.onnx

WORKDIR /ds_app

