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
sam build --use-container
```

### 2. Test Health Check Endpoint

```sh
sam local invoke HelloWorldFunction --event events/event.json
```
Expected response: `{"statusCode": 200, "body": "{\"message\": \"hello world\"}"}`

### 3. Start Local API

```sh
sam local start-api
curl http://localhost:3000/hello
```
Expected response: `{"message": "hello world"}`

### 4. Test User Service Functions with Events

**Create a new user:**
```sh
sam local invoke UserServiceFunction \
  --event events/create-user.json \
  --parameter-overrides \
    ParameterKey=DeploymentTarget,ParameterValue=local \
    ParameterKey=Stage,ParameterValue=dev \
    ParameterKey=FirebaseProjectId,ParameterValue=your-firebase-project-id \
  --docker-network cfm-network
```

**Get user profile:**
```sh
sam local invoke UserServiceFunction \
  --event events/get-user.json \
  --parameter-overrides \
    ParameterKey=DeploymentTarget,ParameterValue=local \
    ParameterKey=Stage,ParameterValue=dev \
    ParameterKey=FirebaseProjectId,ParameterValue=your-firebase-project-id \
  --docker-network cfm-network
```

**Update user profile:**
```sh
sam local invoke UserServiceFunction \
  --event events/update-user.json \
  --parameter-overrides \
    ParameterKey=DeploymentTarget,ParameterValue=local \
    ParameterKey=Stage,ParameterValue=dev \
    ParameterKey=FirebaseProjectId,ParameterValue=your-firebase-project-id \
  --docker-network cfm-network
```

**Test user promotion (Neighbor → Volunteer):**
```sh
sam local invoke UserServiceFunction \
  --event events/update-user-promote-steward.json \
  --parameter-overrides \
    ParameterKey=DeploymentTarget,ParameterValue=local \
    ParameterKey=Stage,ParameterValue=dev \
    ParameterKey=FirebaseProjectId,ParameterValue=your-firebase-project-id \
  --docker-network cfm-network
```

**Test unauthorized access (should return 403):**
```sh
sam local invoke UserServiceFunction \
  --event events/unauthorized-access.json \
  --parameter-overrides \
    ParameterKey=DeploymentTarget,ParameterValue=local \
    ParameterKey=Stage,ParameterValue=dev \
    ParameterKey=FirebaseProjectId,ParameterValue=your-firebase-project-id \
  --docker-network cfm-network
```

**Note:** The `--docker-network cfm-network` flag ensures the Lambda can communicate with LocalStack DynamoDB running in Docker.

---
## Test User Service with local api

1. Edit the code to not check for authenticated user

```sh
sam local start-api --parameter-overrides ParameterKey=FirebaseProjectId,ParameterValue=fakeprojectid ParameterKey=DeploymentTarget,ParameterValue=local ParameterKey=Environment,ParameterValue=dev --docker-network cfm-network
```