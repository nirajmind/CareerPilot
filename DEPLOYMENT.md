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

---

## Step 1: Build and Push Docker Images

For each service (`api`, `agent`, `ui`), you need to build a Docker image and push it to your container registry.

1. **Log in to your Docker registry:**

```bash
    docker login
    ```

2.  **Build the images:**
    Replace `your-docker-username` with your actual username or the name of your registry.
    ```bash
    # From the project root directory
    docker build -t your-docker-username/careerpilot-api:1.0.0 -f Dockerfile.api .
    docker build -t your-docker-username/careerpilot-agent:1.0.0 -f Dockerfile.agent .
    docker build -t your-docker-username/careerpilot-ui:1.0.0 -f Dockerfile.ui .
    ```

3.  **Push the images to the registry:**
    ```bash
    docker push your-docker-username/careerpilot-api:1.0.0
    docker push your-docker-username/careerpilot-agent:1.0.0
    docker push your-docker-username/careerpilot-ui:1.0.0
    ```

---

## Step 2: Update Kubernetes Manifests

Before deploying, you must update the `image` paths in the Kubernetes deployment files to point to the images you just pushed.

-   `infra/k8s/api-deployment.yml`
-   `infra/k8s/agent-deployment.yml`
-   `infra/k8s/ui-deployment.yml`

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

2.  **Create the Gemini API Key Secret:**
    Replace `your-actual-api-key` with your real Gemini API key.
    ```bash
    kubectl create secret generic gemini-api-key-secret \
      --namespace=careerpilot \
      --from-literal=api-key='your-actual-api-key'
    ```

3.  **Deploy all other resources:**
    This command applies all the remaining manifests (`mongo`, `redis`, `api`, `agent`, `ui`).
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

2.  **Check the services:**
    ```bash
    kubectl get services -n careerpilot
    ```
    You should see the services for `mongo`, `redis`, `api`, and `ui`. Note the `NodePort` for the `ui` service.

3.  **Check the logs of a pod (for troubleshooting):**
    ```bash
    # Get the name of your API pod first
    kubectl get pods -n careerpilot

    # Then check its logs
    kubectl logs <name-of-api-pod> -n careerpilot
    ```

4.  **Access your application:**
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
