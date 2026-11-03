# Installation

Ubuntu with Docker, about 100 GB of free disk space, and [uv](https://docs.astral.sh/uv/). No GPU is needed.

The notebook expects this layout; set `WORKSPACE` in its settings cell to your folder:

```
<WORKSPACE>/src/
├── Vitis-AI-6.1/                      # step 1
├── coco/                              # step 4
└── pt_detection_yolov8s_AMDDay2026/   # this repository
```

## 1. Vitis AI 6.1

```bash
cd <WORKSPACE>/src
git clone --recurse-submodules <Vitis AI 6.1 repository> Vitis-AI-6.1
cd Vitis-AI-6.1
```

`--recurse-submodules` matters: without it, parts of the repository are missing.

## 2. The Vitis AI container image

```bash
./docker/run.bash --acceptLicense --noGpu -- true      # builds the image (about 60 GB, first time only)
docker tag vaisw_from_hub:$(id -u) vai-npu-sw:6.1      # the name the notebook uses
```

`--noGpu`: VAISW's GPU emulation crashes on YOLOv8s, and calibration does not need a GPU. The notebook starts its
own container from this image (`CONTAINER` in the settings cell) and mounts `WORKSPACE` at the same path.

## 3. The NPU IP

```bash
./docker/run.bash --acceptLicense --noGpu -- bash -c "source npu_ip/settings.sh LIST"
```

lists the NPU IPs, and `source npu_ip/settings.sh <IP>` downloads one. It must match the NPU of the board's
bitstream; this project uses `VE2802_NPU_IP_O00_A304_M1` (`TARGET_NPU_IP` in the settings cell).

## 4. COCO val2017

```bash
cd <WORKSPACE>/src && mkdir -p coco && cd coco
curl -L -O http://images.cocodataset.org/zips/val2017.zip
curl -L -O https://github.com/ultralytics/assets/releases/download/v0.0.0/coco2017labels.zip
mkdir -p images && unzip -q val2017.zip -d images
unzip -q coco2017labels.zip "coco/labels/val2017/*" && mv coco/labels . && rm -r coco *.zip
```

## 5. This project

```bash
cd <WORKSPACE>/src/pt_detection_yolov8s_AMDDay2026
uv sync                                                # Python 3.11, PyTorch, Ultralytics, ONNX Runtime
mkdir -p weights && curl -L -o weights/yolov8s.pt \
  https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt
uv run python -c "
import yaml; from ultralytics import YOLO
names = YOLO('weights/yolov8s.pt').names
yaml.safe_dump({'path': '$(realpath ../coco)', 'val': 'images/val2017', 'nc': 80, 'names': names},
               open('../coco/data.yaml', 'w'), sort_keys=False)"
```

Open `quantize_compile_yolov8s.ipynb` with the `.venv` kernel and run all cells.

## On the board

Copy `result_compilation/YOLOv8s_COCO.snapshot/` to the VEK280. There, `source /etc/vai.sh` sets up Vitis AI, and
`vart_ml_runner.py --snapshot <folder>` makes a first test run. The application loads the snapshot with VART ML
(`VART.Runner`), writes the 640 x 640 image into the NPU input, runs it, reads the output `[1, 84, 8400]`
(cx, cy, w, h in input pixels and 80 class scores per anchor point) and runs NMS.

To build your own SD card image instead of using a ready one, see the Vitis AI 6.1 README and AMD UG1703.
