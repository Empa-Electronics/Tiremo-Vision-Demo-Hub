<p align="center">
  <img src="assets/logo-empa.svg" alt="Empa" width="220">
  <br>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-tiremo-vision-dark.svg">
    <img src="assets/logo-tiremo-vision-light.svg" alt="Tiremo Vision" width="90">
  </picture>
</p>

<h1 align="center">One PCIe Card, Many Accelerators</h1>

<p align="center">
  <b>Zynq-7015 PCIe card</b><br>
  One card loads a new FPGA accelerator in about 3 seconds while the PC keeps running
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Zynq--7015%20PCIe-65b32e?style=flat-square">
  <img alt="Compute" src="https://img.shields.io/badge/compute-PL%20%2B%20Arm%20%2B%20host-65b32e?style=flat-square">
  <img alt="Workload" src="https://img.shields.io/badge/workload-runtime%20reconfiguration-65b32e?style=flat-square">
  <img alt="Model" src="https://img.shields.io/badge/model-HLS%20kernels-65b32e?style=flat-square">
</p>

<!-- TODO hero photo: the PC with the card, the stabilizer or tracker on the monitor and the switch screen. Save as assets/hero.jpg, then un-comment.
<p align="center">
  <img src="assets/hero.jpg" alt="" width="100%">
  <br>
  <sub></sub>
</p>
-->

## Summary

A Zynq-7015 PCIe card sits in an ordinary desktop PC and works as a fixed shell for FPGA accelerators. Each accelerator is one bitstream file built to the same rules, and the PC keeps as many of them as it needs. To switch, the PC sends the new bitstream over PCIe and the card reloads its programmable logic (PL) in about 3 seconds, with no reboot, no SD card change and no JTAG cable. A small loader on the card's Arm core checks every image and puts the last working design back if the new one does not answer. The demo switches live between a video stabilizer and a face tracker, both running in the PL, and a switch screen shows each step with its time.

## Highlights

- One card holds any number of accelerators, one bitstream each. Device IDs from 1350 up are free for new designs.
- A switch takes 3.2 to 3.3 s, and 6 of 6 live switches in both directions succeeded.
- A damaged or unconfirmed design is replaced by the last good one automatically, so a bad update never leaves a dead card.
- The PC talks to the card from user space through VFIO, with no kernel driver to build or sign.

## Specifications

| Category | Details |
|:--|:--|
| Use cases | multi-function PCIe accelerator cards, safe field updates of FPGA designs, video stabilization, visual tracking |
| Target markets | test and measurement, industrial PCs, data acquisition, machine vision |
| Platform | Deico PCIe card, Zynq-7015 (xc7z015clg485-1), 1 GB DDR3, SD card boot |
| Compute | programmable logic for the accelerators, Arm Cortex-A9 for the bare-metal loader, host x86 CPU for capture and display |
| Models and algorithms | stabilizer: FAST-9 corners, 256-bit BRIEF descriptors, RANSAC, Kalman smoothing and bilinear warp. Tracker: KCF with FFT, Gaussian kernel and 3 scales |
| Inputs | USB camera on the PC, bitstreams and frames over PCIe Gen1 x1 |
| Outputs | PC monitor with both demos and the switch screen, DMA at 220 MB/s to the card and 233 MB/s back |
| Software and tools | Vivado and Vitis HLS 2025.2, Ubuntu 24.04 with VFIO, Python 3 with numpy, OpenCV, GTK 3 and GStreamer |
| Data | none for the accelerators, OpenCV Zoo YuNet and SFace models for face detection on the PC |

## System

![System diagram: the host PC keeps a library of bitstreams and reaches the Zynq-7015 card over PCIe through VFIO. On the card, the XDMA endpoint and one accelerator at a time live in the PL, the Arm loader checks each image and reloads the PL through PCAP, and all of them share DDR3.](assets/system-diagram.svg)

1. The PC keeps each accelerator as one bitstream file, and the demo launcher picks the one to run.
2. To switch, the PC writes the new bitstream into the card's DDR over PCIe and leaves a LOAD command in a mailbox.
3. The loader on the Arm core checks the length and CRC-32, then reloads the PL through PCAP.
4. The new design's PCIe endpoint brings the link back. The PC rescans the bus and checks the device ID.
5. The PC sends CONFIRM, and the loader keeps the new design. Without it, the loader restores the previous design after 15 s.

## Performance

| Metric | Value | Conditions |
|:--|:--|:--|
| Switch time | 3.2 to 3.3 s | live demo, 6 of 6 switches, both directions |
| Bitstream upload | 17 ms | over PCIe Gen1 x1 |
| Recovery from a damaged bitstream | 5.2 s | 4 KB corrupted with a valid header |
| Stabilizer | 29.8 FPS | 1280×720, 16.5 ms FPGA time per frame |
| Host CPU load | about 6 % of one core | stabilizer running |
| Face tracker | about 1.6 ms per frame | on the FPGA, 30 FPS live |

## Development

The card runs a fixed shell: the rules every design follows so that it can be swapped in. They cover the AMD XDMA PCIe endpoint, the BAR sizes, the DDR address map, and the PS ports and clocks that the boot design enables. The accelerators are written in Vitis HLS and built in Vivado 2025.2. A bare-metal loader on the Arm core handles the mailbox, the CRC check, the PCAP reload and the confirm-or-revert logic. On the PC, a Python stack reaches the card through VFIO, uploads bitstreams, retrains the PCIe link and runs both demos.

A few problems were solved along the way:

- The PC sizes PCIe address windows only once, at boot. The first tracker switch failed because its BAR was larger than the boot design's. Every design now uses BAR0 at 1 MB and BAR1 at 64 KB, and that became the shell contract.
- After a rescan, the Linux serial driver claimed the card before VFIO could. The tools now rebind it to vfio-pci.
- A half-open VFIO group blocked every retry with "busy". The DMA layer now closes it on failure.
- The confirm-or-revert loader turned a broken bitstream into a 5 s detour instead of a lost card.

Next, a new boot image will be written to the SD card over PCIe, the switch will be brought under 2 s, and more accelerators will be added to the launcher.

## Setup

- Desktop PC with Ubuntu 24.04 and the card in a PCIe slot
- Deico Zynq-7015 PCIe card, which boots from its SD card before the PC starts
- USB camera on the PC, for the live input
- Monitor on the PC, for both demos and the switch screen

## Resources

- [Zynq-7000 SoC](https://www.amd.com/en/products/adaptive-socs-and-fpgas/soc/zynq-7000.html): the device family
- [DMA/Bridge Subsystem for PCI Express (PG195)](https://docs.amd.com/r/en-US/pg195-pcie-dma): the XDMA endpoint IP
- [Zynq-7000 SoC Technical Reference Manual (UG585)](https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM): PCAP and reconfiguration of the PL
- [VFIO](https://docs.kernel.org/driver-api/vfio.html): device access from user space in Linux
- [OpenCV Zoo](https://github.com/opencv/opencv_zoo): the YuNet and SFace face models

## Related demos

- [Air-to-All-Around Vision Tracking](../vek280-drone-vision-tracking/): an AI drone that flies by its camera alone
- [Air-to-Ground Surveillance](../alinx-z7a-air-to-ground-surveillance/): four drone cameras and one person detector on the NPU
- [ADAS Multi-Task Perception](../kv260-adas-multitask-perception/): five perception tasks in one network at 30 FPS

## Contact

Questions about this demo: [ai@empa.com](mailto:ai@empa.com)

<sub>Product names are trademarks of their respective owners. Last updated 2026-11.</sub>
