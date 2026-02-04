# ===== COLORS =====
GREEN=\033[0;32m
BLUE=\033[0;34m
YELLOW=\033[1;33m
RED=\033[0;31m
NC=\033[0m

# ===== CONFIG =====
CTR = sudo ctr --address /run/k3s/containerd/containerd.sock -n k8s.io
KNS = -n careerpilot

TAG := $(shell date +%Y%m%d-%H%M%S)
UI_IMAGE = careerpilot-ui:$(TAG)
API_IMAGE = careerpilot-api:$(TAG)

UI_TAR = ui.tar
API_TAR = api.tar

# ===== TARGETS =====

all: ui api deploy

ui:
        @echo "$(BLUE)[UI] Building Docker image...$(NC)"
        docker build -t $(UI_IMAGE) -f Dockerfile.ui .
        @echo "$(BLUE)[UI] Saving image to tar...$(NC)"
        docker save -o $(UI_TAR) $(UI_IMAGE)
        @echo "$(BLUE)[UI] Importing into containerd...$(NC)"
        $(CTR) images import $(UI_TAR)
        @echo "$(GREEN)[UI] Done.$(NC)"

api:
        @echo "$(BLUE)[API] Building Docker image...$(NC)"
        docker build -t $(API_IMAGE) -f Dockerfile.api.cpu .
        @echo "$(BLUE)[API] Saving image to tar...$(NC)"
        docker save -o $(API_TAR) $(API_IMAGE)
        @echo "$(BLUE)[API] Importing into containerd...$(NC)"
        $(CTR) images import $(API_TAR)
        @echo "$(GREEN)[API] Done.$(NC)"

deploy:
        @echo "$(YELLOW)[K8S] Restarting deployments...$(NC)"
		sed -i "s/__TAG__/$(TAG)/g" infra/ui-deployment.yml
		sed -i "s/__TAG__/$(TAG)/g" infra/api-deployment.yml
        kubectl rollout restart deployment ui $(KNS)
        kubectl rollout restart deployment api $(KNS)
        @echo "$(GREEN)[K8S] Deployments restarted.$(NC)"

clean:
        @echo "$(RED)[CLEAN] Pruning Docker...$(NC)"
        docker system prune -af
        @echo "$(RED)[CLEAN] Pruning containerd...$(NC)"
        $(CTR) images prune
        @echo "$(GREEN)[CLEAN] Cleanup complete.$(NC)"

clean-k8s:
        @echo "$(RED)[CLEAN] Removing old pods & ReplicaSets...$(NC)"
        kubectl delete pod --all $(KNS) --force --grace-period=0
        kubectl delete rs --all $(KNS)
        @echo "$(GREEN)[CLEAN] K8s cleanup complete.$(NC)"

logs:
        @echo "$(YELLOW)[LOGS] Tailing logs for UI & API...$(NC)"
        kubectl logs -l app=ui $(KNS) -f &
        kubectl logs -l app=api $(KNS) -f

status:
        @echo "$(BLUE)[STATUS] Pods in careerpilot namespace:$(NC)"
        kubectl get pods $(KNS) -o wide
        @echo "$(BLUE)[STATUS] Deployments:$(NC)"
        kubectl get deployments $(KNS)

port-forward:
        @echo "$(YELLOW)[PORT] Forwarding UI to localhost:8080...$(NC)"
        kubectl port-forward deployment/ui 8080:80 $(KNS)

release:
        @if [ -z "$(v)" ]; then \
                echo "$(RED)Error: specify version with v=1.2.3$(NC)"; exit 1; \
        fi
        @echo "$(BLUE)[RELEASE] Building version $(v)...$(NC)"
        docker build -t careerpilot-ui:$(v) -f Dockerfile.ui .
        docker build -t careerpilot-api:$(v) -f Dockerfile.api .
        docker save -o ui.tar careerpilot-ui:$(v)
        docker save -o api.tar careerpilot-api:$(v)
        $(CTR) images import ui.tar
        $(CTR) images import api.tar
        @echo "$(GREEN)[RELEASE] Version $(v) imported into k3s.$(NC)"

.PHONY: all ui api deploy clean clean-k8s logs status port-forward release