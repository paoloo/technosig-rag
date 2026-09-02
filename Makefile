REMOTE ?= atadev
REMOTE_DIR ?= /mnt/raid1/paolo_tests/tecnosig/code-multimodal

.PHONY: deploy test status process mcp-smoke server-deploy server-status server-logs server-down

deploy:
	rsync -az --delete --exclude=.git --exclude=.venv --exclude=.env --exclude=HANDOFF.md --exclude=data --exclude=__pycache__ --exclude=.pytest_cache --exclude='*.pyc' ./ $(REMOTE):$(REMOTE_DIR)/

test:
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && .venv/bin/python -m pytest tests/unit -q'

status:
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && .venv/bin/python pipeline.py status'

process:
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && .venv/bin/python pipeline.py process'

mcp-smoke:
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && .venv/bin/python scripts/mcp_smoke.py'

server-deploy: deploy
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && docker compose build'
	ssh $(REMOTE) 'docker run --rm --user 0:0 -v /mnt/raid1/paolo_tests/tecnosig/visual:/visual tecnosig-rag-multimodal-mcp:local sh -c "mkdir -p /visual/pages /visual/metadata /visual/embeddings_cache /visual/lancedb && chown -R 1001:1001 /visual"'
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && docker compose up -d'

server-status:
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && docker compose ps'

server-logs:
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && docker compose logs --tail=200 tecnosig-multimodal-mcp'

server-down:
	ssh $(REMOTE) 'cd $(REMOTE_DIR) && docker compose down'
