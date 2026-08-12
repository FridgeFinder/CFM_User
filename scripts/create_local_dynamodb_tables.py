#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

ENDPOINT_URL = "http://localhost:4566"

scripts_dir = os.path.dirname(__file__)
schema_dir = os.path.join(scripts_dir, "../local_schema")

for file in sorted(os.listdir(schema_dir)):
    file_path = os.path.abspath(os.path.join(schema_dir, file))
    if file.endswith(".json"):
        p = subprocess.run(
            [
                "aws",
                "dynamodb",
                "create-table",
                "--cli-input-json",
                Path(file_path).as_uri(),
                "--endpoint-url",
                ENDPOINT_URL,
            ],
            capture_output=True,
            text=True,
            env=dict(os.environ, AWS_PAGER=""),
        )
        if p.returncode:
            if "ResourceInUseException" in p.stderr:
                print(f"Table from {file} already exists, skipping")
                continue
            print(f"Could not create DynamoDB table from {file}")
            if p.stderr:
                print(p.stderr.strip())
            exit(p.returncode)

        print(f"Created table from {file}")

