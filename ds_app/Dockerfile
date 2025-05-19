FROM nvcr.io/nvidia/deepstream:6.4-samples-multiarch

ENV NVIDIA_DRIVER_CAPABILITIES $NVIDIA_DRIVER_CAPABILITIES,video
ENV LOGLEVEL="INFO"
ENV GST_DEBUG=2
ENV GST_DEBUG_FILE=/app/GST_DEBUG.log

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
    libgirepository1.0-dev \
    libavformat-dev \
    libswscale-dev 

RUN python3 -m pip install --upgrade pip
COPY requirements.txt .
RUN pip3 install -r requirements.txt

## For Pyds
RUN apt-get -y install \
    libcairo2-dev \
    pkg-config python3-dev \
    libgirepository1.0-dev

# Install pyds
WORKDIR /pyds
COPY *.whl .
RUN pip3 install ./pyds-1.1.10-py3-none-linux_x86_64.whl

# Install nvdsinfer custom: PAR
WORKDIR /nvdsinfer_custom_impl_par
COPY nvdsinfer_custom/nvdsinfer_custom_impl_par .
RUN make clean && make -j4

# Install nvdsinfer custom: YOLO
WORKDIR /nvdsinfer_custom_impl_Yolo
COPY nvdsinfer_custom/nvdsinfer_custom_impl_Yolo .
RUN make clean && make -j4

# Build DSL
COPY ./dsl /dsl
WORKDIR /dsl
RUN cp /usr/local/cuda-12.1/targets/x86_64-linux/lib/stubs/libcuda.so /usr/local/lib/
RUN make clean && make -j4 && make install

# WORKDIR /app
# COPY . .
# WORKDIR /app