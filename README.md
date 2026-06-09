# CFM_User

<p align="center">
  <a href="https://www.fridgefinder.app/">
    <img src="https://raw.githubusercontent.com/CollectiveFocus/CFM_Frontend/dev/public/feedback/happyFridge.svg" height="128">
  </a>
    <h1 align="center">FridgeFinder User Service</h1>
</p>

<p align="center">
  <a aria-label="GitHub Repo stars" href="https://github.com/FridgeFinder/CFM_User/">
    <img alt="" src="https://img.shields.io/github/stars/FridgeFinder/CFM_User?style=flat-square&labelColor=F6F6F6">
  </a>
  <img aria-label="GitHub contributors" alt="GitHub contributors" src="https://img.shields.io/github/contributors/FridgeFinder/CFM_User?style=flat-square&labelColor=F6F6F6">
  <img aria-label="GitHub commit activity (dev)" alt="GitHub commit activity (dev)" src="https://img.shields.io/github/commit-activity/m/FridgeFinder/CFM_User/main?style=flat-square&labelColor=F6F6F6">
  <a aria-label="Join the community on Discord" href="https://discord.com/channels/955884900655972463/955886184159125534">
    <img alt="" src="https://img.shields.io/badge/Join%20the%20community-yellow.svg?style=flat-square&logo=Discord&labelColor=F6F6F6">
  </a>
</p>

## Overview

Manages user profiles for FridgeFinder

📖 **[View API Documentation](https://fridgefinder.github.io/CFM_User/)**

---

## Pre-Requisites

1. AWS CLI - [Install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
    * **You DO NOT have to create an AWS account to use AWS CLI for this project, skip these steps if you don't want to create an AWS account**
    * AWS CLI looks for credentials when using it, but doesn't validate. So will need to set some fake one. But the region name matters, use any valid region name. 
        ```sh
        $ aws configure
        $ AWS Access Key ID: [ANYTHING YOU WANT]
        $ AWS Secret Access Key: [ANYTHING YOUR HEART DESIRES]
        $ Default region nam: us-east-1
        $ Default output format [None]: (YOU CAN SKIP)
        ```
2. SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
    * **You DO NOT need to create an aws account to use SAM CLI for this project, skip these steps if you don't want to create an aws account**
    * Note: if you are getting the following error: `runtime is not supported` when running `sam build --use-container` make sure your SAM CLI version is up to date
3. Python 3 - [Install Python 3](https://www.python.org/downloads/)
4. Docker - [Install Docker](https://docs.docker.com/get-docker/)

---

## Setup Local Database Connection

**Guide that was used:** https://betterprogramming.pub/how-to-deploy-a-local-serverless-application-with-aws-sam-b7b314c3048c

Follow these steps to get Dynamodb running locally

1. **Start a local DynamoDB service**
    ```sh
    $ docker compose up
    # OR if you want to run it in the background:
    $ docker compose up -d
    ```

2. **Create tables**
    ```sh
    $ ./scripts/create_local_dynamodb_tables.py
    ```

---

## Build and Test Locally

### 1. Build the Application

```sh
cd user-service/
make build
```

### 2. Test Health Check Endpoint

```sh
cd user-service/
make invoke-hello
```

Expected response: `{"statusCode": 200, "body": "{\"message\": \"hello user service\"}"}`

### 3. Test User Service Functions with Events

**Create a new user:**
```sh
cd user-service/
make invoke-create-user
```

**Get user profile:**
```sh
cd user-service/
make invoke-get-user
```

**Get user profile: internal**
```sh
cd user-service/
make invoke-internal-get-user
```

**Update user profile:**
```sh
cd user-service/
make invoke-update-user
```

**Test user promotion (Neighbor → Volunteer):**
```sh
cd user-service/
make invoke-promote-user
```

**Test unauthorized access (should return 403):**
```sh
cd user-service/
make invoke-unauthorized
```

**Delete user profile:**
```sh
cd user-service/
make invoke-delete-user
```

**Note:** The `--docker-network cfm-network` flag ensures the Lambda can communicate with LocalStack DynamoDB running in Docker.

---

## Running Unit Tests

Unit tests live in `user-service/tests/unit/` and use `pytest`. They do **not** require Docker, LocalStack, or a running DynamoDB — all AWS calls are mocked.

### 1. Create and activate a virtual environment

```sh
cd user-service/
python3 -m venv .venv
source .venv/bin/activate
```

> To deactivate the virtual environment when you're done, run `deactivate`.

### 2. Install test dependencies

```sh
# From user-service/ with the virtual environment activated
pip install -r tests/requirements.txt
# Also install the layer packages used by the functions
pip install -r functions/user_service/requirements.txt
```

Make equivalent:
```sh
cd user-service/
make install
```

### 3. Run all unit tests

```sh
# From user-service/ with the virtual environment activated
pytest tests/unit/ -v
```

Make equivalent:
```sh
cd user-service/
make test
```

### 4. Run a specific test file

```sh
pytest tests/unit/test_models.py -v
pytest tests/unit/test_service.py -v
pytest tests/unit/test_repository.py -v
pytest tests/unit/test_user_service_handler.py -v
pytest tests/unit/test_internal_user_service.py -v
pytest tests/unit/test_username_check.py -v
pytest tests/unit/test_utils.py -v
```

### 5. Run with coverage

```sh
# Terminal report
pytest tests/unit/ --cov=functions --cov=layers --cov-report=term-missing

# HTML report (opens as htmlcov/index.html)
pytest tests/unit/ --cov=functions --cov=layers  --cov-report=html
```

Make equivalent:
```sh
cd user-service/
make test-cov
```

---

## Deploying to AWS

Deployments use `user-service/samconfig_local.toml`, which defines configuration for `dev`, `staging`, and `prod` environments.

> **Before deploying**, replace the placeholder values in `samconfig_local.toml`:
> - `YOUR_STAGING_FIREBASE_PROJECT_ID` — your Firebase project ID for dev/staging
> - `YOUR_PROD_FIREBASE_PROJECT_ID` — your Firebase project ID for production
> - `YOUR_HOSTED_ZONE_ID` — your Route 53 Hosted Zone ID

### 1. Build
```sh
cd user-service/
make build
```

### 2. Deploy

```sh
# Deploy to dev
sam deploy --config-env dev --config-file samconfig_local.toml

# Deploy to staging
sam deploy --config-env staging --config-file samconfig_local.toml

# Deploy to production
sam deploy --config-env prod --config-file samconfig_local.toml
```

Make equivalent:
```sh
cd user-service/
make deploy ENV=dev
make deploy ENV=staging
make deploy ENV=prod
```

Each command will show a changeset and prompt for confirmation before applying changes.

---
## Test User Service with local api

1. Edit the code to not check for authenticated user

```sh
sam local start-api --parameter-overrides ParameterKey=FirebaseProjectId,ParameterValue=fakeprojectid ParameterKey=DeploymentTarget,ParameterValue=local ParameterKey=Environment,ParameterValue=dev --docker-network cfm-network
```