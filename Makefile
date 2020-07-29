.PHONY: addlicense all check_binaries clean lint run unibg _unibg start_unibg_server stopserver shell test visualization demo _demo start_demo_server

SHELL          := /bin/bash
VENV           := $(PWD)/venv
VIRTUALENV     := python3 -m venv
ACTIVATE       := $(VENV)/bin/activate
PYTHON         := $(VENV)/bin/python
PIP            := $(PYTHON) -m pip
FLAKE8         := $(VENV)/bin/flake8
IPYTHON        := $(VENV)/bin/ipython
PYTEST         := $(VENV)/bin/pytest
PIDFILE        := $(VENV)/webserver.pid

PACKAGES       := mosaicrown
REQUIREMENTS   := requirements.txt
SHELL_PRIMER   := examples/scripts/shell.py

LICENSE_TYPE   := "apache"
LICENSE_HOLDER := "Unibg Seclab (https://seclab.unibg.it)"


define run_python
	@ echo -e "\n\n======================================"
	@ echo "$(PYTHON) $(1)"
	@ echo -e "======================================\n"
	@ PYTHONIOENCODING=UTF-8 $(PYTHON) $(1)
	@ echo -e "\n"
endef

all: run

# Make these targets quiet on pip.
lint shell test: QUIET = --quiet

$(VENV): $(ACTIVATE)

$(ACTIVATE): requirements.txt setup.py $(PACKAGES)
	test -d $(VENV) || $(VIRTUALENV) $(VENV)
	$(PIP) install $(QUIET) --upgrade pip
	$(PIP) install $(QUIET) -r $(REQUIREMENTS)
	touch $(ACTIVATE)

$(IPYTHON): $(VENV)
	$(PIP) install $(QUIET) ipython

$(FLAKE8): $(VENV)
	$(PIP) install $(QUIET) flake8

$(PYTEST): $(VENV)
	$(PIP) install $(QUIET) pytest

run: | _kill_server startserver _run stopserver

_kill_server:
	@ if test -f $(PIDFILE); then \
    	make -s stopserver; \
	fi

startserver: mosaicrown/namespaces $(VENV)
	@ echo "[*] Starting web server"
	@ echo "[i] Policy vocabulary now available"
	@ cd $< ; $(PYTHON) -m http.server >/dev/null & echo $$! > $(PIDFILE)


_run: $(VENV)
	$(call run_python,examples/scripts/actions.py)
	$(call run_python,examples/scripts/access.py)

stopserver:
	@ test -f $(PIDFILE) && \
		echo "[*] Stopping web server" && \
		kill -TERM `cat $(PIDFILE)` && \
		rm $(PIDFILE) || \
		echo "[*] No server running"

demo: | _kill_server start_demo_server _demo stopserver

start_demo_server: examples/demo/policy $(VENV)
	@ echo "[*] Starting web server"
	@ echo "[i] Policy vocabulary now available"
	@ cd $< ; $(PYTHON) -m http.server >/dev/null & echo $$! > $(PIDFILE)

_demo: $(VENV)
	$(call run_python,examples/demo/demo.py)

unibg: | _kill_server start_unibg_server _unibg stopserver

start_unibg_server: examples/unibg/policies $(VENV)
	@ echo "[*] Starting web server"
	@ cd $< ; $(PYTHON) -m http.server >/dev/null & echo $$! > $(PIDFILE)

_unibg: $(VENV)
	$(call run_python,examples/unibg/unibg.py)

test: $(VENV) $(PYTEST)
	$(PYTEST)

shell: | _kill_server startserver _shell stopserver

_shell: $(IPYTHON)
	@ echo -e "\n[*] Running the following script and defining variables ...\n"
	@ cat $(SHELL_PRIMER)
	@ echo -e "\n[*] Running and then activating a shell ...\n"
	$(IPYTHON) --no-banner -i $(SHELL_PRIMER)

visualization: $(VENV)
	$(PYTHON) -m mosaicrown.visualization

lint: $(FLAKE8)
	$(FLAKE8) $(PACKAGES)

addlicense:
	@ go get -u github.com/google/addlicense
	$(shell go env GOPATH)/bin/addlicense -c $(LICENSE_HOLDER) -l $(LICENSE_TYPE) .

clean:
	@ rm -rf $(VENV)
	@ rm -rf build/ dist/ *.egg-info/
	@ find . -path '*/__pycache__/*' -delete
	@ find . -type d -name '__pycache__' -delete
	@ find . -type f -name '*.pyo' -delete
	@ find . -type f -name '*.pyc' -delete

check_binaries:
	$(info If some of the following are empty you are missing some binaries)
	@ whereis go
#	hint: requires installing golang-go (ppa:longsleep/golang-backports)
	@ whereis graphviz
#	hint: requires installing graphviz
