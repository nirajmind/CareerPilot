# Deployment Strategy & Implementation Guide

This document provides a step-by-step guide for deploying the CareerPilot application to a Kubernetes cluster.

## Deployment Strategy

The strategy is to deploy the application as a set of containerized microservices on Kubernetes. This approach ensures scalability, resilience, and a clear separation of concerns. We will use a `StatefulSet` for the database to ensure data persistence and `Deployments` for the stateless application services.

- **Namespace:** All resources will be deployed into a dedicated `careerpilot` namespace to keep the cluster organized.
- **Secrets Management:** API keys and other secrets will be managed using `kubectl` to create secrets directly in the cluster at runtime, ensuring they are not stored in version control.
- **External Access:** The application will be exposed to the internet via a `NodePort` service, with a Caddy server running on the host VM acting as a reverse proxy to handle HTTPS.

## Prerequisites

Before you begin, ensure you have the following:

1. **A running Kubernetes cluster.**
2. **`kubectl` installed and configured** to communicate with your cluster.
3. **Docker installed** on your local machine for building images.
4. **Access to a Docker registry** (like Docker Hub, GCR, or ACR) where you can push your images.
5. **Caddy installed and running** on your Kubernetes node (the VM).
6. **Your domain name (`careerpilot.duckdns.org`) pointing to your VM's public IP address.**
7. **Your Gemini API Key.**

The steps below will guide you through installing the necessary software (Kubernetes, Docker, etc.) on your VM.

---

## Step 0: Initial VM Setup

Run these commands on your new VM to install all the required software for hosting CareerPilot.

1. **Update Your System:**

```bash
    sudo apt update && sudo apt upgrade -y
```

1. **Install Docker:**
The application images are built with Docker.

```bash
    # Install prerequisites
    sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up the stable repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io

    # Add your user to the 'docker' group to run docker commands without sudo
    sudo usermod -aG docker ${USER}

    # You will need to log out and log back in for this change to take effect.
    echo "Please log out and log back in to apply Docker group permissions."
```

1. **Install Kubernetes (K3s):**

K3s is a lightweight, certified Kubernetes distribution perfect for a single-node setup. It includes `kubectl` and `containerd`.

```bash
    # Install k3s
    curl -sfL https://get.k3s.io | sh -

    # K3s automatically creates a kubeconfig file at /etc/rancher/k3s/k3s.yaml.
    # To allow kubectl to work without sudo, set the KUBECONFIG environment variable.
    # Add this line to your ~/.bashrc or ~/.zshrc and then source it.
    echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc
    source ~/.bashrc
    
    # Verify that kubectl can connect to the cluster
    kubectl get nodes
```

1. **Install Caddy:**

Caddy will act as our reverse proxy and handle HTTPS automatically.

```bash
    sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt update
    sudo apt install caddy
    ```
---

## Step 1: Build and Push Docker Images

For each service (`api`, `agent`, `ui`), you need to build a Docker image and push it to your container registry.

1. **Log in to your Docker registry:**

```bash
    docker login
```

1. **Build the images:**

Replace `your-docker-username` with your actual username or the name of your registry.

```bash
    # From the project root directory
    docker build -t your-docker-username/careerpilot-api:1.0.0 -f Dockerfile.api .
    docker build -t your-docker-username/careerpilot-agent:1.0.0 -f Dockerfile.agent .
    docker build -t your-docker-username/careerpilot-ui:1.0.0 -f Dockerfile.ui .
```

1. **Push the images to the registry:**

```bash
    docker push your-docker-username/careerpilot-api:1.0.0
    docker push your-docker-username/careerpilot-agent:1.0.0
    docker push your-docker-username/careerpilot-ui:1.0.0
```

---

## Step 2: Update Kubernetes Manifests

Before deploying, you must update the `image` paths in the Kubernetes deployment files to point to the images you just pushed.

- `infra/k8s/api-deployment.yml`
- `infra/k8s/agent-deployment.yml`
- `infra/k8s/ui-deployment.yml`

**Example:** In `api-deployment.yml`, change this line:

```yaml
image: your-docker-repo/careerpilot-api:latest
```

to:

```yaml
image: your-docker-username/careerpilot-api:1.0.0
```

Repeat this for all three deployment files.

---

## Step 3: Deploy to Kubernetes

Apply the Kubernetes manifests in the correct order. These commands should be run from your VM or any machine where `kubectl` is configured to access your cluster.

1. **Apply the Namespace:**

```bash
    kubectl apply -f infra/k8s/namespace.yml
```

1. **Create the Gemini API Key Secret:**

Replace `your-actual-api-key` with your real Gemini API key.

```bash
    kubectl create secret generic gemini-api-key-secret \
      --namespace=careerpilot \
      --from-literal=api-key='your-actual-api-key'
```

1. **Deploy all other resources:**

This command applies all the remaining manifests (`mongo`, `redis`, `api`,`agent`, `ui`).

```bash
    kubectl apply -f infra/k8s/
```

---

## Step 4: Configure Caddy

On your VM, add the following block to your `Caddyfile` and reload Caddy's configuration.

```caddy
careerpilot.duckdns.org {
    # Caddy will automatically handle HTTPS
    reverse_proxy localhost:30001
}
```

This configuration will proxy requests from your domain to the `NodePort` of your Streamlit UI service.

---

## Step 5: Verify the Deployment

After applying the manifests, you can check the status of your deployment.

1. **Check the pods:**

```bash
    kubectl get pods -n careerpilot
```

You should see pods for `mongo`, `redis`, `api`, `agent`, and `ui` with a status of `Running`.

1. **Check the services:**

```bash
    kubectl get services -n careerpilot
```

You should see the services for `mongo`, `redis`, `api`, and `ui`. Note the `NodePort` for the `ui` service.

1. **Check the logs of a pod (for troubleshooting):**

```bash
    # Get the name of your API pod first
    kubectl get pods -n careerpilot

    # Then check its logs
    kubectl logs <name-of-api-pod> -n careerpilot
```

1. **Access your application:**
    Once all pods are running, you should be able to access your application at `https://careerpilot.duckdns.org`.

---

## Rollback Strategy

If a deployment fails, the quickest way to roll back is to apply the manifests from a previous, stable commit in your Git history.

For a specific deployment, you can use `kubectl rollout undo`:

```bash
    # Check the history of a deployment
    kubectl rollout history deployment/api -n careerpilot

    # Roll back to the previous version
    kubectl rollout undo deployment/api -n careerpilot
```
