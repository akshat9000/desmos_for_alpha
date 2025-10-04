# ====================================================
# Desmos-for-Alphas — Makefile
# ====================================================

# Python / venv settings
PYTHON := python
VENV := .venv
ACTIVATE := source $(VENV)/bin/activate

# Default FastAPI app path
APP := app.main:app
HOST := 127.0.0.1
PORT := 8000

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

# ====================================================
#  make develop  -> create virtualenv & install deps
#  make clean    -> remove caches, pyc, build artifacts
#  make launch   -> run uvicorn API
#  make tests    -> run pytest suite
# ====================================================

.PHONY: develop clean launch tests

develop:
	@echo "$(YELLOW)Creating virtual environment and installing dependencies...$(NC)"
	@if [ ! -d "$(VENV)" ]; then $(PYTHON) -m venv $(VENV); fi
	@. $(VENV)/bin/activate && pip install -U pip && pip install -e . -r requirements.txt
	@echo "$(GREEN)Development environment ready.$(NC)"

clean:
	@echo "$(YELLOW)Cleaning build, cache, and temp files...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf build dist *.egg-info .pytest_cache .coverage coverage.xml
	@echo "$(GREEN)Cleanup complete.$(NC)"

launch:
	@echo "$(YELLOW)Launching FastAPI (Uvicorn) server...$(NC)"
	@. $(VENV)/bin/activate && uvicorn $(APP) --reload --host $(HOST) --port $(PORT)

tests:
	@echo "$(YELLOW)Running pytest suite...$(NC)"
	@. $(VENV)/bin/activate && pytest -q
	@echo "$(GREEN)All tests completed.$(NC)"
