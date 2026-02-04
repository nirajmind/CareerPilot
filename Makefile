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

# ===== PIPELINE =====

pipeline: ui api deploy cleanup status
	@echo "$(GREEN)[PIPELINE] Completed successfully.$(NC)"

# ===== BUILD UI =====

ui:
	@echo "$(BLUE)[UI] Building Docker image $(UI_IMAGE)...$(NC)"
	docker build -t $(UI_IMAGE) -f Dockerfile.ui . || { echo "$(RED)[UI] Build failed.$(NC)"; exit 1; }

	@echo "$(BLUE)[UI] Saving image to tar...$(NC)"
	docker save -o $(UI_TAR) $(UI_IMAGE)

	@echo "$(BLUE)[UI] Importing into containerd...$(NC)"
	$(CTR) images import $(UI_TAR) || { echo "$(RED)[UI] Import failed.$(NC)"; exit 1; }

	@echo "$(GREEN)[UI] Done.$(NC)"

# ===== BUILD API =====

api:
	@echo "$(BLUE)[API] Building Docker image $(API_IMAGE)...$(NC)"
	docker build -t $(API_IMAGE) -f Dockerfile.api.cpu . || { echo "$(RED)[API] Build failed.$(NC)"; exit 1; }

	@echo "$(BLUE)[API] Saving image to tar...$(NC)"
	docker save -o $(API_TAR) $(API_IMAGE)

	@echo "$(BLUE)[API] Importing into containerd...$(NC)"
	$(CTR) images import $(API_TAR) || { echo "$(RED)[API] Import failed.$(NC)"; exit 1; }

	@echo "$(GREEN)[API] Done.$(NC)"

# ===== DEPLOY =====

deploy:
	@echo "$(YELLOW)[K8S] Updating deployment YAMLs with tag $(TAG)...$(NC)"

	cp infra/k8s/ui-deployment.yml.template infra/k8s/ui-deployment.yml
	cp infra/k8s/api-deployment.yml.template infra/k8s/api-deployment.yml

	sed -i "s/__TAG__/$(TAG)/g" infra/k8s/ui-deployment.yml
	sed -i "s/__TAG__/$(TAG)/g" infra/k8s/api-deployment.yml

	@echo "$(YELLOW)[K8S] Applying deployments...$(NC)"
	kubectl apply -f infra/k8s/api-deployment.yml || { echo "$(RED)[K8S] Apply failed.$(NC)"; exit 1; }
	kubectl apply -f infra/k8s/ui-deployment.yml || { echo "$(RED)[K8S] Apply failed.$(NC)"; exit 1; }

	@echo "$(YELLOW)[K8S] Restarting deployments...$(NC)"
	kubectl rollout restart deployment ui $(KNS)
	kubectl rollout restart deployment api $(KNS)

	@echo "$(GREEN)[K8S] Deployments restarted.$(NC)"

# ===== CLEANUP =====

cleanup:
	@echo "$(RED)[CLEAN] Removing old Docker images (keeping latest)...$(NC)"
	@docker images 'careerpilot-ui' --format "{{.Repository}}:{{.Tag}}" | grep -v $(TAG) | xargs -r docker rmi
	@docker images 'careerpilot-api' --format "{{.Repository}}:{{.Tag}}" | grep -v $(TAG) | xargs -r docker rmi

	@echo "$(RED)[CLEAN] Removing old containerd images (keeping latest)...$(NC)"
	@$(CTR) images ls | grep careerpilot-ui | sort -k2 | head -n -1 | awk '{print $$1}' | xargs -r $(CTR) images rm
	@$(CTR) images ls | grep careerpilot-api | sort -k2 | head -n -1 | awk '{print $$1}' | xargs -r $(CTR) images rm

	@echo "$(RED)[CLEAN] Removing tarballs...$(NC)"
	rm -f *.tar

	@echo "$(GREEN)[CLEAN] Cleanup complete.$(NC)"

# ===== STATUS =====

status:
	@echo "$(BLUE)[STATUS] Pods:$(NC)"
	kubectl get pods $(KNS) -o wide

	@echo "$(BLUE)[STATUS] Deployments:$(NC)"
	kubectl get deployments $(KNS)

	@echo "$(BLUE)[STATUS] Images in containerd:$(NC)"
	$(CTR) images ls | grep careerpilot || echo "$(RED)No images found.$(NC)"

# ===== OTHER TARGETS =====

logs:
	@echo "$(YELLOW)[LOGS] Tailing logs for UI & API...$(NC)"
	kubectl logs -l app=ui $(KNS) -f &
	kubectl logs -l app=api $(KNS) -f

clean-k8s:
	@echo "$(RED)[CLEAN] Removing old pods & ReplicaSets...$(NC)"
	kubectl delete pod --all $(KNS) --force --grace-period=0
	kubectl delete rs --all $(KNS)
	@echo "$(GREEN)[CLEAN] K8s cleanup complete.$(NC)"

port-forward:
	@echo "$(YELLOW)[PORT] Forwarding UI to localhost:8080...$(NC)"
	kubectl port-forward deployment/ui 8080:80 $(KNS)

.PHONY: pipeline ui api deploy cleanup status logs clean-k8s port-forward