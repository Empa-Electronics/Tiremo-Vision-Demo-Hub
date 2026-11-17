<p align="center">
  <img src="Additionals/logo-empa.svg" alt="Empa" width="220">
  <br>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="Additionals/logo-tiremo-vision-dark.svg">
    <img src="Additionals/logo-tiremo-vision-light.svg" alt="Tiremo Vision" width="90">
  </picture>
</p>

<h1 align="center">Edge AI Demos Hub</h1>

<p align="center">
  Working AI applications on AMD embedded platforms, with their documentation and source code
</p>

<p align="center">
  English · <a href="README.tr.md">Türkçe</a>
</p>

## Welcome

This repository collects our edge AI work on AMD embedded platforms, such as Versal and Zynq UltraScale+ adaptive SoCs and Kria system-on-modules. Each entry below has its own page that explains what the application does, how the system is built and how it performs. Where the source code is shared, it sits in the same folder.

The pages are written for two kinds of readers. If you want a quick picture, the summary and highlights at the top of each page are enough. If you build similar systems, the system diagram, performance figures and development notes go into the details.

## Demos

| Demo | Platform | Description |
|:--|:--|:--|
| [Air-to-All-Around Vision Tracking](Applications/vek280-drone-vision-tracking/) | Versal AI Edge VEK280 | An AI drone flies by its camera alone, with object detection on the AI Engine NPU |
| [Air-to-Ground Surveillance](Applications/alinx-z7a-air-to-ground-surveillance/) | Zynq UltraScale+ (ALINX Z7-A) | Four drone cameras and one person detector, running entirely on the NPU |
| [ADAS Multi-Task Perception](Applications/kv260-adas-multitask-perception/) | Kria KV260 | Five driving perception tasks from one network at 30 FPS |
| [One PCIe Card, Many Accelerators](Applications/deico-z7015-pcie-accelerator-switching/) | Zynq-7015 PCIe card | Loads a new FPGA accelerator over PCIe in about 3 s, while the PC keeps running |
| [YOLOv8s on the Versal NPU with Vitis AI 6.1](Applications/AI-Flow-on-Versal-VEK280-with-Vitis-AI/) | Versal AI Edge VEK280 | Step-by-step notebook that quantizes and compiles YOLOv8s for the NPU, with source code |
| [Semantic Segmentation with DeepLabV3](Applications/Building_AI_Solutions_with_Vitis_AI/Semantic_Segmentation_DeepLabV3_KV260/) | Kria KV260 | Live camera segmentation with DeepLabV3 MobileNetV3 on the DPU, with compiled models and scripts |

## Edge AI

Edge AI runs a trained model directly on the device that collects the data, such as a camera, a sensor board or a vehicle computer. The data doesn't travel to a cloud server and back, so the result is available right where it is needed.

This brings a few practical benefits:

- Low and predictable latency, because there is no network round trip
- Less bandwidth, because only results leave the device, not raw video or sensor data
- Better privacy, because the data stays on the device
- Lower power and cost for always-on applications

The challenge is that edge devices have limited power and memory. Models have to be made smaller and faster, usually by quantizing them to 8-bit integers, and they need hardware built for neural network inference.

## AMD Vitis

[AMD Vitis](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vitis.html) is the software platform for building applications on AMD adaptive SoCs and FPGAs. It covers embedded software for the Arm processors, hardware acceleration in the programmable logic and programming of the AI Engines on Versal devices.

[Vitis AI](https://www.amd.com/en/developer/resources/vitis-ai.html) is the part of this platform for AI inference. It takes a model trained in a framework such as PyTorch, quantizes it to INT8 (with BF16 where accuracy needs it), compiles it for the target accelerator and runs it on the device. That accelerator is the DPU on Zynq UltraScale+ and Kria devices, and the AI Engine based NPU on Versal AI Edge devices. The Versal, Zynq UltraScale+ and Kria demos in this repository were built with Vitis and Vitis AI.

## Contact

Questions about the demos or the source code: [ai@empa.com](mailto:ai@empa.com)

<sub>Product names are trademarks of their respective owners. Each application's source code and third-party models are used under their own licenses.</sub>
