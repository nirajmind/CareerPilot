# **📦 Reusable Deployment Template (Markdown)**  

A clean, future‑proof template you can reuse for any self‑hosted app deployed on k3s + Caddy + FreeDNS.

---

## **Reusable Deployment Template: k3s + Caddy + FreeDNS + HTTPS (HTTP‑01)**

### **1. Prerequisites**

- Ubuntu server (or any Linux host)
- Public IP address
- Ports **80** and **443** open
- k3s installed
- Caddy installed as a systemd service
- FreeDNS [account](https://freedns.afraid.org)

---

## **2. Build and Load Local Images into k3s**

### **Build Docker images**

```bash
docker build -t myapp:latest .
docker save myapp:latest -o myapp.tar
```

### **Load into containerd (k3s)**

```bash
sudo k3s ctr images import myapp.tar
```

### **Verify**

```bash
sudo k3s ctr images ls | grep myapp
```

---

## **3. Deploy to k3s**

### **Deployment YAML**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 3000
```

### **Service YAML**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  type: NodePort
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 3000
    nodePort: 30001
```

Apply:

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

---

## **4. Configure FreeDNS**

1. Log in to [FreeDNS](https://freedns.afraid.org)  
2. Create a new **A record** pointing to your server’s public IP  
   - `myapp.chickenkiller.com` → `YOUR_PUBLIC_IP`  
3. Wait 1–2 minutes for propagation

---

## **5. Configure Caddy (HTTP‑01)**

### **Caddyfile**

```caddyfile
myapp.chickenkiller.com {
    reverse_proxy 127.0.0.1:30001
}
```

Reload:

```bash
sudo systemctl restart caddy
```

---

## **6. Validate HTTPS**

### **Check logs**

```bash
sudo journalctl -u caddy -f
```

Look for:

- “authorization finalized”
- “certificate obtained successfully”

### **Test**

```bash
curl -I https://myapp.chickenkiller.com
```

Expected:

```bash
HTTP/2 200
server: Caddy
```

---

## **7. Troubleshooting Checklist**

### **Ports**

```bash
sudo ss -tulpn | grep :80
sudo ss -tulpn | grep :443
```

### **DNS**

```bash
dig myapp.chickenkiller.com +short
```

### **k3s**

```bash
kubectl get pods
kubectl logs <pod>
```

---

## **8. Final Architecture**

```bash
Internet → Caddy → k3s NodePort → App Pod
```
