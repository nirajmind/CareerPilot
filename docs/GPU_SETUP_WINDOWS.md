# GPU Setup Guide for Docker Desktop on Windows

This document provides a step-by-step guide for installing and configuring the NVIDIA Container Toolkit to enable GPU support for Docker Desktop on Windows using the WSL 2 backend.

## Prerequisites

1. **NVIDIA GPU:** You must have a compatible NVIDIA graphics card.
2. **WSL 2:** You need to have WSL 2 installed and set as your default. You can check this by running `wsl --status` in PowerShell.
3. **Docker Desktop:** Ensure Docker Desktop is installed and configured to use the WSL 2 based engine. You can verify this in **Docker Desktop > Settings > General**.

---

## Step 1: Install the NVIDIA Driver for WSL

The most important step is to install the correct NVIDIA driver that supports CUDA on WSL. Standard game-ready drivers may not be sufficient.

1. Go to the official NVIDIA CUDA on WSL download page: [https://developer.nvidia.com/cuda/wsl](https://developer.nvidia.com/cuda/wsl)
2. Download the driver for your specific GPU model.
3. Install the driver on your Windows machine and **reboot your computer** after the installation is complete. This is a critical step.

---

## Step 2: Update Your WSL Kernel

Ensure your WSL 2 Linux kernel is up to date. Open PowerShell as an administrator and run:

```powershell
wsl --update
```

---

## Step 3: Verify the Installation

Once you have rebooted and updated WSL, you can verify that Docker Desktop can access your GPU. Open PowerShell and run the following command:

```powershell
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
```

### Expected Output

If everything is configured correctly, you will see a detailed report of your GPU, including the driver version, CUDA version, and memory usage. It should look something like this:

```config
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 515.65.01    Driver Version: 515.65.01    CUDA Version: 11.7     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                               |                      |               MIG M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ...  On   | 00000000:01:00.0 Off |                  N/A |
| N/A   40C    P8    N/A /  N/A |      8MiB / 12288MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
...
```

If you see this output, your setup is complete. You can now run your `docker-compose.yml` file, and your services will have access to the GPU.
