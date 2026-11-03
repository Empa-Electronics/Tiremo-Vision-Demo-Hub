# YOLOv8s on the AMD Versal VEK280 NPU with Vitis AI 6.1

A step-by-step example of the Vitis AI 6.1 flow: the COCO YOLOv8s (80 classes, 640 x 640) taken to the NPU of the
AMD Versal VEK280 as a **mixed-precision, full-NPU snapshot**, with the accuracy checked after each step.

- **The decode runs on the NPU too.** Exported as is, the end of YOLOv8 (reshape, softmax, box math) stays on the CPU.
  We rewrite the detection head's forward function in operations the NPU has. The weights stay the same.
- **INT8 core, BF16 head.** The backbone and the neck run in INT8, the head branches and the decode in BF16, which
  keeps the boxes and scores precise: 3.6% of the MACs.

| COCO val2017, 2,000 images | mAP50 | mAP50-95 |
|---|---|---|
| FP32 | 0.599 | 0.438 |
| Mixed precision, emulated NPU | 0.562 | 0.405 |

The snapshot has one NPU subgraph and no CPU subgraph. Target: NPU IP `VE2802_NPU_IP_O00_A304_M1`.

## The notebook

`quantize_compile_yolov8s.ipynb` goes through six steps, each writing its own folder:

| Step | Output |
|---|---|
| 1. Import the model: prediction and mAP | `result_export/` |
| 2. Inspect it: which parts run on the NPU? | `result_inspection/default/` |
| 3. Change the head so the decode runs on the NPU | `result_export/` |
| 4. Inspect the changed model | `result_inspection/npu_tail/` |
| 5. Quantize it (INT8 + BF16) and score it on the emulated NPU | `result_quantization/` |
| 6. Compile it: the snapshot for the board | `result_compilation/YOLOv8s_COCO.snapshot/` |

`utils.py` holds the notebook's helpers; `vitis_ai/` is the code that runs inside the Vitis AI container.

## Getting started

Follow [INSTALL.md](INSTALL.md): Vitis AI 6.1 and its container, the Python environment, the weights and COCO. Then
open the notebook with the project's `.venv` kernel and run all cells. `CALIB_SIZE` and `EVAL_SIZE` in the settings
cell set the number of images: fewer for a quick run.

The sample image shown at each step is `input.png` in this folder, with optional labels in `input.txt` (YOLO format).
Put your own there.

## How this project works with Vitis AI 6.1

- **The VAISW cache.** VAISW caches its quantization by model *structure*. Without `VAISW_QUANTIZATION_FORCE=true`,
  a retrained model of the same architecture gets the cached results of the previous one.
- **Reused outputs.** Each VAISW run reuses its output buffers: copy the results before the next image runs.
- **The Ultralytics tail stays on the CPU.** VAISW has no NPU `Reshape` or `Transpose` for it, so even `MIXED` leaves
  the decode there. `utils.npu_tail_forward` writes the same calculation per scale in NPU operations.
- **`BEFORE_LAST_CONV` loses small objects.** It leaves the first box convolutions in INT8, and on objects under 16
  pixels the rounding drops the IoU under 0.5. `VAISW_FE_MIXEDEXPLICITSELECTION` moves the border to them.
  `fe.mixedSelection=TAIL` does not compile for this model.
- **Non-contiguous input crashes VART's Python runner** on the board: pass `np.ascontiguousarray` arrays.

## Third-party

Ultralytics YOLOv8 (AGPL-3.0), the COCO dataset (CC BY 4.0) and AMD Vitis AI are used under their own licenses.
