# the things that don't have output files or run every time
.PHONY: help all install test dev coverage clean \
		pre-commit update-pre-commit


all: dev coverage ## builds everything

install: .venv/.installed ## installs the venv and the project packages

dev: .venv/.installed-dev pre-commit ## prepare local repo and venv for dev

test: .venv/.installed-dev  ## run the project's tests
	scripts/test.sh

coverage: .venv/.installed-dev scripts/coverage.sh  ## build the html coverage report
	scripts/coverage.sh

clean:  ## delete caches and the venv
	scripts/clean.sh

pre-commit: .git/hooks/pre-commit ## install pre-commit into the git repo

update-pre-commit: scripts/update-pre-commit.sh ## autoupdate pre-commit
	scripts/update-pre-commit.sh



# Caching doesn't work if we depend on PHONY targets

.venv/.installed: pyproject.toml .venv/bin/activate scripts/install.sh
	scripts/install.sh

.venv/.installed-dev: pyproject.toml .venv/bin/activate scripts/install-dev.sh
	scripts/install-dev.sh

.venv/bin/activate:
	scripts/venv.sh

.git/hooks/pre-commit: scripts/install-pre-commit.sh
	scripts/install-pre-commit.sh


help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
