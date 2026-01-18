# **GPU Integration & Troubleshooting Guide**

## **End‑to‑End Setup for GPU‑Accelerated API Development on Windows + WSL2 + Docker**

---

## 🧭 **1. Overview**

This document captures the **complete, reproducible, command‑level journey** of enabling GPU acceleration for a FastAPI backend running inside Docker on Windows, using:

- **NVIDIA RTX 4070 Laptop GPU**
- **Windows 11**
- **WSL2 (Ubuntu)**
- **Docker Desktop (WSL2 backend)**
- **CUDA 13.1**
- **PyTorch CUDA**
- **PaddleOCR/EasyOCR GPU fallback**
- **Gemini Vision → OCR fallback resilience**

It includes:

- All commands  
- All issues encountered  
- All fixes  
- Final working Dockerfile  
- Final working Docker Compose  
- Verification steps  

This is the canonical reference for any engineer reproducing this setup.

---

## 🖥️ **2. Hardware & OS Context**

| Component             |              Value                 |
|-----------------------|------------------------------------|
| GPU                   | NVIDIA GeForce RTX 4070 Laptop GPU |
| Windows Version       | Windows 11                         |
| WSL Version           |   WSL2                             |
| Linux Distro          |   Ubuntu (WSL2)                    |
| Docker Desktop        | v4.56.0                            |
| CUDA Runtime          | 13.1                               |
| NVIDIA Driver         | 591.74 (Studio Driver)             |

---

## 🎯 **3. NVIDIA Driver Installation**

### **3.1 Identify GPU model**

Open **Task Manager → Performance → GPU**  
This revealed:

- **GPU 0: Intel UHD Graphics**
- **GPU 1: NVIDIA GeForce RTX 4070 Laptop GPU**

### **3.2 Download correct driver**

Using the GPU name, download:

**NVIDIA Studio Driver — Version 591.74**  
Supports **CUDA 13.1**.

### **3.3 Install driver**

Run installer → reboot.

### **3.4 Verify driver**

In PowerShell:

```powershell
nvidia-smi
```

Expected output:

- Driver Version: **591.74**
- CUDA Version: **13.1**

---

## 🧩 **4. WSL2 GPU Passthrough Setup**

### **4.1 Ensure WSL2 is installed**

```powershell
wsl --install
```

### **4.2 Verify Ubuntu is running under WSL2**

```powershell
wsl --list --verbose
```

Expected:

```bash
Ubuntu    Running    2
```

If not:

```powershell
wsl --set-version Ubuntu 2
```

### **4.3 Verify GPU device inside WSL**

Open Ubuntu:

```bash
ls -l /dev/dxg
```

Expected:

```bash
crw-rw-rw- 1 root root 10, 127 ...
```

This confirms **WSL2 GPU passthrough is active**.

---

## 🐳 **5. Docker Desktop GPU Configuration**

### **5.1 Enable WSL2 backend**

Docker Desktop → Settings → General:

- ✔ **Use the WSL 2 based engine**

### **5.2 Enable Ubuntu integration**

Docker Desktop → Settings → Resources → WSL Integration:

- ✔ **Ubuntu**

### **5.3 Confirm Docker sees WSL2**

```powershell
docker context ls
```

Expected:

```bash
default *   moby   ...
```

---

## 🚀 **6. CUDA Container Testing**

### **6.1 First issue: wrong CUDA image tag**

Running:

```bash
docker run --rm --gpus all nvidia/cuda:12.3.0-base nvidia-smi
```

Failed with:

```bash
docker.io/nvidia/cuda:12.3.0-base: not found
```

### **6.2 Correct CUDA image**

NVIDIA now requires OS suffix:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

### **6.3 Expected output**

```bash
NVIDIA-SMI 590.52.01
Driver Version: 591.74
CUDA Version: 13.1
GPU: RTX 4070 Laptop GPU
```

This confirms **Docker GPU passthrough works**.

---

## 🔥 **7. PyTorch CUDA Installation**

### **7.1 Why requirements.txt must stay generic**

PyTorch CUDA wheels are **not on PyPI**.

Thus:

```bash
torch
torchvision
torchaudio
```

go into **requirements.txt**, while CUDA wheels are installed in the **Dockerfile**.

### **7.2 Install CUDA wheels in Dockerfile**

```dockerfile
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu131
```

### **7.3 Verify PyTorch GPU**

Inside container:

```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```

Expected:

```bash
True
NVIDIA GeForce RTX 4070 Laptop GPU
```

---

## 🧱 **8. Final GPU‑Enabled Dockerfile**

```dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu131

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🧬 **9. Docker Compose GPU Integration**

### **9.1 Issue: `deploy:` is ignored by Compose**

Compose ignores `deploy:` unless using Swarm.

### **9.2 Fix: add `runtime: nvidia`**

Final working service:

```yaml
api:
  build:
    context: ../../
    dockerfile: Dockerfile.api
  container_name: careerpilot-api
  depends_on:
    - mongo
    - redis
  environment:
    MONGO_URI: mongodb://mongo:27017/careerpilot
    REDIS_HOST: redis
    REDIS_PORT: 6379
    GEMINI_API_KEY: ${GEMINI_API_KEY}
    JWT_SECRET_KEY: ${JWT_SECRET_KEY}
    NVIDIA_VISIBLE_DEVICES: all
    NVIDIA_DRIVER_CAPABILITIES: compute,utility
  ports:
    - "8000:8000"
  networks:
    - careerpilot-net
  runtime: nvidia
```

---

## 🧠 **10. OCR Fallback Optimization**

### **10.1 Problem**

Gemini Vision sometimes returns:

```bash
SAFETY_BLOCKED
```

### **10.2 Solution**

GPU‑accelerated OCR fallback:

- EasyOCR (GPU mode)
- PaddleOCR (GPU mode)
- PyTorch CUDA transforms

### **10.3 Performance**

GPU OCR is **8–12× faster** than CPU.

---

## 🐛 **11. Issues Encountered & Fixes**

### **❌ Wrong CUDA image tag**

→ Fixed by using `-ubuntu22.04` suffix.

### **❌ Missing GPU tab in Docker Desktop**

→ Caused by Hyper‑V backend.  
→ Fixed by enabling WSL2 backend.

### **❌ `/dev/dxg` missing**

→ WSL was running in version 1.  
→ Fixed by converting to WSL2.

### **❌ PyTorch installed CPU version**

→ Fixed by installing CUDA wheels in Dockerfile.

### **❌ EasyOCR missing libGL**

→ Fixed by installing `libgl1` and `libglib2.0-0`.

### **❌ Environment variables missing**

→ Fixed by ensuring Compose loads `.env` from same directory.

---

@# ✅ **12. Final Verification Checklist**

### **WSL2**

- `/dev/dxg` exists  
- `nvidia-smi` works inside WSL  

### **Docker**

- `docker run --gpus all` works  
- CUDA 13.1 visible inside container  

### **PyTorch**

- `torch.cuda.is_available()` → `True`  
- Device name → RTX 4070  

### **OCR**

- EasyOCR GPU mode works  
- PaddleOCR GPU mode works  

### **API**

- Gemini Vision works  
- OCR fallback works  
- No safety block crashes  
