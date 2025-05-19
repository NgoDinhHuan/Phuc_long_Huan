PROJECT_NAME := emagiceye

ifndef PRODUCTION_ENVIRONMENT:
PRODUCTION_ENVIRONMENT := prod
endif

ifndef DOCKER_BIN:
DOCKER_BIN := docker
endif

ifndef DOCKER_COMPOSE_BIN:
DOCKER_COMPOSE_BIN := docker-compose
endif

GIT_SHA_FETCH:=$(shell git rev-parse HEAD | cut -c 1-8)
REGISTRY_HOST=docker.io
REGISTRY_NAME=rainscalesvn


CLOUD_APP := ${PROJECT_NAME}-cloud-app
DVR_APP := ${PROJECT_NAME}-dvr-app
DS_APP := ${PROJECT_NAME}-ds-app
EVIDENCE_APP := ${PROJECT_NAME}-evidence
LLAVA_APP := ${PROJECT_NAME}-llava
TARSIER_APP := ${PROJECT_NAME}-tarsier
THIRD-PARTY-SERVICES := ${PROJECT_NAME}-third-party-services

create-env-dvr:
	echo "export DVR_IMAGE=$(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DVR_APP):$(GIT_SHA_FETCH)" > build/.env.dvr
create-env-cloud:
	echo "export CLOUD_IMAGE=$(REGISTRY_HOST)/$(REGISTRY_NAME)/$(CLOUD_APP):$(GIT_SHA_FETCH)" > build/.env.cloud
	echo "export EVIDENCE_IMAGE=$(REGISTRY_HOST)/$(REGISTRY_NAME)/$(EVIDENCE_APP):$(GIT_SHA_FETCH)" >> build/.env.cloud

create-env-llava:
	echo "export LLAVA_IMAGE=$(REGISTRY_HOST)/$(REGISTRY_NAME)/$(LLAVA_APP):$(GIT_SHA_FETCH)" > build/.env.llava

create-env-tarsier:
	echo "export LLAVA_IMAGE=$(REGISTRY_HOST)/$(REGISTRY_NAME)/$(TARSIER_APP):$(GIT_SHA_FETCH)" > build/.env.tarsier

create-env-ds:
	echo "export DS_IMAGE=$(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DS_APP):$(GIT_SHA_FETCH)" > build/.env.ds

create-env-third-party:
	echo "export THIRD_PARTY_IMAGE=$(REGISTRY_HOST)/$(REGISTRY_NAME)/$(THIRD-PARTY-SERVICES):$(GIT_SHA_FETCH)" > build/.env.third-party

app-build-docker:
	$(DOCKER_BIN) build -t $(PROJECT_NAME)-veh01-app:$(DOCKER_TAG) -f build/Dockerfile.veh01.yml .

app-veh01-run:
	$(COMPOSE) run --name ${PROJECT_NAME}-veh01-local --rm -w / veh01

app-par02-run:
	$(DOCKER_COMPOSE_BIN) run --name ${PROJECT_NAME}-par02-local --rm -w / veh01

build-dvr-base:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DVR_APP):base -f build/dvr.base.Dockerfile .

push-dvr-base:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DVR_APP):base

build-dvr:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DVR_APP):$(GIT_SHA_FETCH) -f build/dvr.Dockerfile .

push-dvr:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DVR_APP):$(GIT_SHA_FETCH)

build-cloud-base:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(CLOUD_APP):base -f build/cloud.base.Dockerfile .

push-cloud-base:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(CLOUD_APP):base

build-cloud:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(CLOUD_APP):$(GIT_SHA_FETCH) -f build/cloud.Dockerfile .

push-cloud:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(CLOUD_APP):$(GIT_SHA_FETCH)

build-evd:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(EVIDENCE_APP):$(GIT_SHA_FETCH) -f build/evidence.Dockerfile .

push-evd:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(EVIDENCE_APP):$(GIT_SHA_FETCH)

build-llava:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(LLAVA_APP):$(GIT_SHA_FETCH) -f build/llava.Dockerfile .

push-llava:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(LLAVA_APP):$(GIT_SHA_FETCH)

build-tarsier:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(TARSIER_APP):$(GIT_SHA_FETCH) -f build/tarsier.Dockerfile .

push-tarsier:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(TARSIER_APP):$(GIT_SHA_FETCH)

build-ds-base:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DS_APP):base -f build/ds.base.Dockerfile .

push-ds-base:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DS_APP):base

build-ds:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DS_APP):$(GIT_SHA_FETCH) -f build/ds.Dockerfile .

push-ds:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(DS_APP):$(GIT_SHA_FETCH)



build-third-party-services:
	$(DOCKER_BIN) build -t $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(THIRD-PARTY-SERVICES):$(GIT_SHA_FETCH) -f build/mhe10.Dockerfile .

push-third-party-services:
	$(DOCKER_BIN) push $(REGISTRY_HOST)/$(REGISTRY_NAME)/$(THIRD-PARTY-SERVICES):$(GIT_SHA_FETCH)