# ------------------------------------------------------------------------ #
#      o-o      o                o                                         #
#     /         |                |                                         #
#    O     o  o O-o  o-o o-o     |  oo o--o o-o o-o                        #
#     \    |  | |  | |-' |   \   o | | |  |  /   /                         #
#      o-o o--O o-o  o-o o    o-o  o-o-o--O o-o o-o                        #
#             |                           |                                #
#          o--o                        o--o                                #
#                        o--o      o         o                             #
#                        |   |     |         |  o                          #
#                        O-Oo  o-o O-o  o-o -o-    o-o o-o                 #
#                        |  \  | | |  | | |  |  | |     \                  #
#                        o   o o-o o-o  o-o  o  |  o-o o-o                 #
#                                                                          #
#    Jemison High School - Huntsville Alabama                              #
# ------------------------------------------------------------------------ #
#  Makefile method of doing things should you prefer
#
# Configure shell
SHELL = bash -eu -o pipefail

# Variables
THIS_MAKEFILE	:= $(abspath $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST)))
WORKING_DIR		:= $(dir $(THIS_MAKEFILE))
PACKAGE_DIR     := $(WORKING_DIR)lib_6107
TEST_DIR        := $(WORKING_DIR)tests

include .make/setup.mk

# Variables

VENVDIR         := .venv
PYVERSION       ?= ${PYVERSION:-"3.14"}
PYTHON          := python${PYVERSION}

COVERAGE_OPTS	 = --with-xcoverage --with-xunit \
                   --cover-html --cover-html-dir=tmp/cover

# Lint tools
PYLINT_DISABLES  = -d similarities -d broad-except -d missing-class-docstring
PYLINT_OPTS		 = -j 4 --exit-zero --rcfile=${WORKING_DIR}.pylintrc $(PYLINT_DISABLES)
PYLINT_OUT		 = $(WORKING_DIR)pylint.out

LICENSE_OUT      = $(WORKING_DIR)license-check.out

.PHONY: venv test clean distclean

## Defaults
default: help		## Default operation is to print this help text

## Virtual Environment
venv: ${PACKAGE_DIR}/$(REQUIREMENTS) $(VENVDIR)/.built		    ## Application virtual environment

$(VENVDIR)/.built:
	$(Q) (if uv init --package; then \
              uname -s > ${VENVDIR}/.built; \
          fi))

######################################################################
## License and security

show-licenses: venv					## Show licenses of imported modules
	@ (cd ${PACKAGE_DIR} && uv run pip-licenses 2>&1 | tee ${LICENSE_OUT}))

bandit-test: venv					## Run security test on source
	$(Q) echo "Running python security check with bandit on module code"
	@ uv run bandit -n 3 -r $(PACKAGE_DIR) -o bandit.log

######################################################################
## Testing

test: venv		## Run tox-based unit tests
	$(Q) echo "Executing unit tests w/tox"
	@ uv tool install tox --with tox-uv && uvx --with tox-uv tox

######################################################################
## Linting

lint: venv     ## Run lint on PON Automation using pylint
	@ uv run tox pylint ${PYLINT_OPTS} ${PACKAGE_DIR} 2>&1 | tee ${PYLINT_OUT} && \
       echo; echo "See \"file://${PYLINT_OUT}\" for lint report")

########################################################
# Release related (Lint ran last since it probably will have errors until
# the code is refactored (which is not planned at this time)
## Release Procedures
release-check: distclean venv test bandit lint	## Clean distribution and run unit-test, security, and lint

######################################################################
## Utility
clean:		## Cleanup directory of build and test artifacts
	@ -rm -rf .tox *.coverage *.egg-info test/.pytest_cache ${PYLAMA_OUT} ${PYLINT_OUT} ${LICENSE_OUT}
	@ -rm -rf ${PACKAGE_DIR}/ctre_sim ${PACKAGE_DIR}/logs
	@ -find . -name '*.pyc' | xargs rm -f
	@ -find . -name '__pycache__' | xargs rm -rf
	@ -find . -name 'htmlcov' | xargs rm -rf
	@ -find . -name 'junit-report.xml' | xargs rm -rf
	@ -find . -name 'coverage.xml' | xargs rm -rf
	@ -find . -name '*.log' | xargs rm -rf
	@ -find . -name '*.wpilog' | xargs rm -rf
	@ -find . -name '._.DS_Store' | xargs rm -rf
	@ -find . -name 'ctre_sim' | xargs rm -rf

distclean: clean	## Cleanup all build, test, and virtual environment artifacts
	@ -rm -rf ${VENVDIR} ${TESTVENVDIR} ./vendordeps
	@ -find . -name 'simgui*.json' | xargs rm -rf
	@ -find . -name 'networktables.json' | xargs rm -rf

help: ## Print help for each Makefile target
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target> [<target> ...]${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} { \
		if (/^[a-zA-Z_-]+:.*?##.*$$/) {printf "    ${YELLOW}%-23s${GREEN}%s${RESET}\n", $$1, $$2} \
		else if (/^## .*$$/) {printf "  ${CYAN}%s${RESET}\n", substr($$1,4)} \
		}' $(MAKEFILE_LIST)

# end file
