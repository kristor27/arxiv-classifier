# WikiPulse — every command you need. `make help` lists them.
NS := wikipulse

help:  ## list commands
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

# --- 1. local development: Python + Vite on your machine, Postgres + Redis in Docker
dev-infra:  ## start Postgres (:5433) and Redis (:6379)
	docker compose up -d postgres redis
dev-ingestor:  ## run the ingestor locally
	uv run python -m wikipulse.ingestor
dev-worker:  ## run a worker locally
	uv run python -m wikipulse.worker
dev-api:  ## run the API locally with auto-reload (:8000)
	uv run uvicorn wikipulse.api:app --reload --port 8000
dev-web:  ## run the dashboard with hot reload (:5173)
	cd web && npm install && npm run dev
test:  ## run the self-checks
	uv run python -m wikipulse.wiki

# --- 2. Docker Compose: the whole stack in containers
up:  ## build and start everything → http://localhost:8080
	docker compose up -d --build
logs:  ## follow worker logs
	docker compose logs -f worker
down:  ## stop everything (keeps the database volume)
	docker compose down

# --- 3. Kubernetes (OrbStack / k3s / any cluster)
k8s-build:  ## build the two images
	docker build -t wikipulse:latest . && docker build -t wikipulse-web:latest web
k8s-secrets:  ## create the API-key Secret from .env
	kubectl create namespace $(NS) --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(NS) create secret generic wikipulse-keys --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
k8s-deploy: k8s-build k8s-secrets  ## build + deploy everything
	kubectl apply -k deploy/k8s
	kubectl -n $(NS) rollout restart deploy/ingestor deploy/worker deploy/api deploy/web
	kubectl -n $(NS) rollout status deploy --timeout=180s
k8s-status:  ## show pods, services, cronjobs
	kubectl -n $(NS) get pods,svc,cronjob,ingress,pvc
k8s-open:  ## open the dashboard through a port-forward → http://localhost:8081
	kubectl -n $(NS) port-forward svc/web 8081:80
k8s-scale:  ## scale the workers, e.g. make k8s-scale N=5
	kubectl -n $(NS) scale deploy/worker --replicas=$(N)
k8s-logs:  ## follow logs of every worker pod
	kubectl -n $(NS) logs -f -l app=worker --prefix --max-log-requests=10
k8s-stop:  ## stop all billing: scale ingestor + workers to 0 (dashboard and data stay up)
	kubectl -n $(NS) scale deploy/ingestor deploy/worker --replicas=0
k8s-start:  ## start judging again
	kubectl -n $(NS) scale deploy/ingestor --replicas=1
	kubectl -n $(NS) scale deploy/worker --replicas=2
k8s-delete:  ## remove everything, including the database disk
	kubectl delete namespace $(NS)

.PHONY: help dev-infra dev-ingestor dev-worker dev-api dev-web test up logs down k8s-build k8s-secrets k8s-deploy k8s-status k8s-open k8s-scale k8s-logs k8s-stop k8s-start k8s-delete
