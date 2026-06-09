.PHONY: build deploy install invoke-hello invoke-create-user invoke-get-user invoke-internal-get-user invoke-update-user invoke-promote-user invoke-delete-user invoke-unauthorized test test-cov clean

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
ENV ?= dev
DEPLOYMENT_TARGET ?= local
FIREBASE_PROJECT_ID ?= your-firebase-project-id
USER_FUNCTION ?= UserServiceFunction
INTERNAL_FUNCTION ?= InternalUserServiceFunction
HELLO_FUNCTION ?= HelloWorldFunction
DOCKER_NETWORK ?= cfm-network

# -----------------------------------------------------------------------------
# SAM
# -----------------------------------------------------------------------------

## Build the SAM application
build:
	sam build --use-container

## Deploy using samconfig_local.toml (ENV=dev|staging|prod)
deploy:
	sam deploy --config-env $(ENV) --config-file samconfig_local.toml

# -----------------------------------------------------------------------------
# Local invokes
# -----------------------------------------------------------------------------

## Invoke health check function
invoke-hello:
	sam local invoke $(HELLO_FUNCTION) --event events/event.json

## Invoke POST /v1/users
invoke-create-user:
	sam local invoke $(USER_FUNCTION) \
		--event events/create-user.json \
		--parameter-overrides \
			ParameterKey=DeploymentTarget,ParameterValue=$(DEPLOYMENT_TARGET) \
			ParameterKey=Environment,ParameterValue=$(ENV) \
			ParameterKey=FirebaseProjectId,ParameterValue=$(FIREBASE_PROJECT_ID) \
		--docker-network $(DOCKER_NETWORK)

## Invoke GET /v1/users/{userId}
invoke-get-user:
	sam local invoke $(USER_FUNCTION) \
		--event events/get-user.json \
		--parameter-overrides \
			ParameterKey=DeploymentTarget,ParameterValue=$(DEPLOYMENT_TARGET) \
			ParameterKey=Environment,ParameterValue=$(ENV) \
			ParameterKey=FirebaseProjectId,ParameterValue=$(FIREBASE_PROJECT_ID) \
		--docker-network $(DOCKER_NETWORK)

## Invoke internal GET /internal/v1/users/{userId}
invoke-internal-get-user:
	sam local invoke $(INTERNAL_FUNCTION) \
		--event events/internal-get-user.json \
		--parameter-overrides \
			ParameterKey=DeploymentTarget,ParameterValue=$(DEPLOYMENT_TARGET) \
			ParameterKey=Environment,ParameterValue=$(ENV) \
			ParameterKey=FirebaseProjectId,ParameterValue=$(FIREBASE_PROJECT_ID) \
		--docker-network $(DOCKER_NETWORK)

## Invoke PATCH /v1/users/{userId}
invoke-update-user:
	sam local invoke $(USER_FUNCTION) \
		--event events/update-user.json \
		--parameter-overrides \
			ParameterKey=DeploymentTarget,ParameterValue=$(DEPLOYMENT_TARGET) \
			ParameterKey=Environment,ParameterValue=$(ENV) \
			ParameterKey=FirebaseProjectId,ParameterValue=$(FIREBASE_PROJECT_ID) \
		--docker-network $(DOCKER_NETWORK)

## Invoke PATCH user promotion scenario
invoke-promote-user:
	sam local invoke $(USER_FUNCTION) \
		--event events/update-user-promote-steward.json \
		--parameter-overrides \
			ParameterKey=DeploymentTarget,ParameterValue=$(DEPLOYMENT_TARGET) \
			ParameterKey=Environment,ParameterValue=$(ENV) \
			ParameterKey=FirebaseProjectId,ParameterValue=$(FIREBASE_PROJECT_ID) \
		--docker-network $(DOCKER_NETWORK)

## Invoke DELETE /v1/users/{userId}
invoke-delete-user:
	sam local invoke $(USER_FUNCTION) \
		--event events/delete-user.json \
		--parameter-overrides \
			ParameterKey=DeploymentTarget,ParameterValue=$(DEPLOYMENT_TARGET) \
			ParameterKey=Environment,ParameterValue=$(ENV) \
			ParameterKey=FirebaseProjectId,ParameterValue=$(FIREBASE_PROJECT_ID) \
		--docker-network $(DOCKER_NETWORK)

## Invoke unauthorized access scenario (expected 403)
invoke-unauthorized:
	sam local invoke $(USER_FUNCTION) \
		--event events/unauthorized-access.json \
		--parameter-overrides \
			ParameterKey=DeploymentTarget,ParameterValue=$(DEPLOYMENT_TARGET) \
			ParameterKey=Environment,ParameterValue=$(ENV) \
			ParameterKey=FirebaseProjectId,ParameterValue=$(FIREBASE_PROJECT_ID) \
		--docker-network $(DOCKER_NETWORK)

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------

## Install test dependencies and function runtime dependencies
install:
	pip install -r tests/requirements.txt
	pip install -r functions/user_service/requirements.txt

## Run all unit tests
test:
	pytest tests/unit/ -v

## Run unit tests with coverage
test-cov:
	pytest tests/unit/ -v \
		--cov=functions --cov=layers \
		--cov-report=term-missing \
		--cov-report=html

# -----------------------------------------------------------------------------
# Housekeeping
# -----------------------------------------------------------------------------

## Remove build and test artifacts
clean:
	rm -rf .aws-sam htmlcov .pytest_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
