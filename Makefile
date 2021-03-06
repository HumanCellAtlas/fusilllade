SHELL:=/bin/bash
tests:=$(wildcard tests/test_*.py)

before-test: package

lint:
	flake8 app.py fusillade

test: before-test lint $(tests)
	coverage combine
	rm -f .coverage.*

$(tests): %.py : lint
	coverage run -p --source=fusillade $*.py -v

unittest: before-test
	python -m unittest discover -p test_*api.py -t . -v

integration_test:
	source environment && $(MAKE) FUS_TEST_MODE=integration unittest
	
init_docs:
	cd docs; sphinx-quickstart

docs:
	pandoc --from markdown --to rst Readme.md > README.rst
	$(MAKE) -C docs html

install: docs
	-rm -rf dist
	python setup.py bdist_wheel
	pip install --upgrade dist/*.whl

set_oauth2_config:
	source environment && cat ./deployments/$(FUS_DEPLOYMENT_STAGE)/oauth2_config.json | ./scripts/set_secret.py --secret-name oauth2_config

set_test_service_accounts:
	source environment && cat ./deployments/$(FUS_DEPLOYMENT_STAGE)/test_service_accounts.json | ./scripts/set_secret.py --secret-name test_service_accounts

_check_directory_schema:
	./scripts/upgrade_schema.py

check_directory_schema:
	source environment && $(MAKE) _check_directory_schema

upgrade_directory_schema:
	source environment && ./scripts/upgrade_schema.py --upgrade-published --upgrade-directory

plan-infra:
	source environment && $(MAKE) -C infra plan-all

deploy-infra:
	source environment && $(MAKE) -C infra apply-all

package:
	source environment && $(MAKE) _package

_package:
	git clean -df chalicelib vendor
	shopt -s nullglob; for wheel in vendor.in/*/*.whl; do unzip -q -o -d vendor $$wheel; done
	cat fusillade-api.yml | envsubst '$$API_DOMAIN_NAME' | envsubst '$$FUS_VERSION' > chalicelib/fusillade-api.yml
	cat fusillade-internal-api.yml | envsubst '$$API_DOMAIN_NAME' | envsubst '$$FUS_VERSION' > chalicelib/fusillade-internal-api.yml
	cat service_config.json | jq .version=\"$(shell git describe --tags --abbrev=0)\" > ./chalicelib/service_config.json
	cp -R ./fusillade ./policies chalicelib

_setup_directory:
	./scripts/make_directory.py

setup_directory:
	source environment && $(MAKE) _setup_directory

_deploy: _setup_directory _check_directory_schema _package
	./build_chalice_config.sh
	chalice deploy --no-autogen-policy --stage $(FUS_DEPLOYMENT_STAGE) --api-gateway-stage $(FUS_DEPLOYMENT_STAGE)

deploy:
	source environment && $(MAKE) _deploy


refresh_all_requirements:
	@echo -n '' >| requirements.txt
	@echo -n '' >| requirements-dev.txt
	@if [ $$(uname -s) == "Darwin" ]; then sleep 1; fi  # this is require because Darwin HFS+ only has second-resolution for timestamps.
	@touch requirements.txt.in requirements-dev.txt.in
	@$(MAKE) requirements.txt requirements-dev.txt

requirements.txt requirements-dev.txt : %.txt : %.txt.in
	[ ! -e .requirements-env ] || exit 1
	virtualenv -p $(shell which python3) .$<-env
	.$<-env/bin/pip install -r $@
	.$<-env/bin/pip install -r $<
	echo "# You should not edit this file directly.  Instead, you should edit $<." >| $@
	.$<-env/bin/pip freeze >> $@
	rm -rf .$<-env
	scripts/find_missing_wheels.py requirements.txt # Disable if causing circular dependency issues

requirements-dev.txt : requirements.txt.in

.PHONY: test release docs

include common.mk
