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
PACKAGE_NAME    := lib_6107
THIS_MAKEFILE	:= $(abspath $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST)))
WORKING_DIR		:= $(dir $(THIS_MAKEFILE))
PACKAGE_DIR     := $(WORKING_DIR)src/${PACKAGE_NAME}
TEST_DIR        := $(WORKING_DIR)tests

include .make/setup.mk
include .make/pypi-token.mk		# If not found, create your own but never push to github

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

.PHONY: venv test clean distclean release-check release publish release-build

## Defaults
default: help		## Default operation is to print this help text

## Virtual Environment
$(VENVDIR)/.built:
	$(Q) uv venv
	$(Q) uname -s > ${VENVDIR}/.built

venv: $(VENVDIR)/.built		    ## Application virtual environment

######################################################################
## License and security

show-licenses: 				## Show licenses of imported modules
	@ (cd ${PACKAGE_DIR} && \
       UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv add --dev pip-licenses && \
       UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv run pip-licenses 2>&1 | tee ${LICENSE_OUT}))

bandit-test: 				## Run security test on source
	$(Q) echo "Running python security check with bandit on module code"
	$(Q) UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv add --dev bandit
	@ UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv run bandit -n 3 -r $(PACKAGE_DIR) -o bandit.log

######################################################################
## Testing

test:                		## Run tox-based unit tests
	$(Q) echo "Executing unit tests w/tox"
	$(Q) UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv add --dev tox-uv
	$(Q) UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv add --dev pytest
	@ UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv tool install tox --with tox-uv && \
	  UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uvx --with tox-uv tox

######################################################################
## Linting

lint:      ## Run lint on PON Automation using pylint
	$(Q) UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv add --dev pylint
	$(Q) UV_PROJECT_ENVIRONMENT=${VENVDIR}-dev uv run pylint ${PYLINT_OPTS} ${PACKAGE_DIR} 2>&1 | tee ${PYLINT_OUT} && \
       echo; echo "See \"file://${PYLINT_OUT}\" for lint report"

########################################################
# Release related (Lint ran last since it probably will have errors until
# the code is refactored (which is not planned at this time)
#
# TODO: Use github actions to perform all of our release procedures in the future
#
## Release Procedures
release-check: distclean venv test bandit lint	## Clean distribution and run unit-test, security, and lint

release-build: distclean      ## Run 'uv build' to create distribution (dist/) folder with uploadable tarballs
	uv build --no-sources

publish-dry-run:    ## Dry-run test of releasing tarball to pipy
	$(Q) echo "Publishing dryrun verification to test-site"
	uv publish --dry-run --token ${UV_PUBLISH_TOKEN} --publish-url https://test/pypi.org/legacy/
	$(Q) echo "Publishing dryrun to pypi"
	uv publish --dry-run --token ${UV_PUBLISH_TOKEN}
	$(Q) echo "${GREEN}SUCCESS${RESET}: Dry run of publishing package"

publish:    ## Push release tarball to pipy
	$(Q) echo "Dry run of publishing to pypi"
	uv publish --dry-run --token ${UV_PUBLISH_TOKEN}
	$(Q) echo ""
	$(Q) echo "${GREEN}----------------------------------------------------------${RESET}"
	$(Q) echo ""
	$(Q) echo "Publishing to pypi"
	uv publish --token ${UV_PUBLISH_TOKEN}
	$(Q) echo ""
	$(Q) echo "${GREEN}----------------------------------------------------------${RESET}"
	$(Q) echo ""
	$(Q) echo "${GREEN}SUCCESS${RESET}: Publishing package, verifying published package"
	uv run --with ${PACKAGE_NAME} --no-project -- python -c "import ${PACKAGE_NAME}"
	$(Q) echo ""
	$(Q) echo "${GREEN}----------------------------------------------------------${RESET}"
	$(Q) echo ""
	$(Q) echo "${GREEN}SUCCESS${RESET}: Publish package can be imported"
	$(Q) echo ""

release: release-check release publish   ## Full build and publishing steps to pypi
	@ echo "The release was successfully pushed."
	@ echo "Please verify that appropriate tags and/or branches have been created for this specific release."

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
	@ -rm -rf ${VENVDIR} ${VENVDIR}-dev
	@ -rm -rf dist
	@ -find src -name '*.egg-info' | xargs rm -rf

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
