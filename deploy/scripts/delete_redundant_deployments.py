#!/usr/bin/env python3

import os
from typing import Dict, List

import requests
import yaml

PREFECT_API_URL = os.getenv("PREFECT_API_URL")
PREFECT_API_KEY = os.getenv("PREFECT_API_KEY")
REPOSITORY_NAME = os.getenv("REPOSITORY_NAME")

if PREFECT_API_URL is None:
    raise Exception("PREFECT_API_URL is not set, please set it in your environment")

if PREFECT_API_KEY is None:
    raise Exception("PREFECT_API_KEY is not set, please set it in your environment")

if REPOSITORY_NAME is None:
    raise Exception("REPOSITORY_NAME is not set, please set it in your environment")


def delete_redundant_flows_and_deployments(local_deployments: List[Dict], cloud_deployments: List[Dict]) -> None:
    """
    Compares the deployments.yml file with the deployments in the prefect cloud workspace and deletes any flows
    that do not exist in the local deployments file, then deletes any deployments that do not exist in the local
    file.
    """

    local_flows = [deployment["flow_name"] for deployment in local_deployments]
    local_deployments = [f"{deployment['flow_name']}-{deployment['deployment_name']}" for deployment in local_deployments]

    deleted_flows = []
    deleted_deployments = []

    for cloud_deployment in cloud_deployments:
        cloud_flow_name = cloud_deployment["flow_name"]
        cloud_flow_id = cloud_deployment["flow_id"]
        cloud_deployment_name = cloud_deployment["deployment_name"]
        cloud_deployment_id = cloud_deployment["deployment_id"]
        flow_deployment_name = f"{cloud_flow_name}-{cloud_deployment_name}"

        if cloud_flow_name not in local_flows and cloud_flow_id not in deleted_flows:
            deleted_flows.append(delete_flow(flow_id=cloud_flow_id, flow_name=cloud_flow_name))
            print("🗑️  Successfully deleted flow", cloud_flow_name)
            continue

        if flow_deployment_name not in local_deployments:
            deleted_deployments.append(
                delete_deployment(deployment_id=cloud_deployment_id, flow_deployment_name=flow_deployment_name)
            )
            print(f"🗑️  Successfully deleted deployment {cloud_deployment_name} of flow {cloud_flow_name}")

    if not deleted_deployments and not deleted_flows:
        print("👍  No redundant flows or deployments found")


def get_cloud_account_deployments() -> List[Dict]:
    """
    Gets all the deployments from the prefect cloud workspace and returns them as a
    list of dicts with {"flow_name": xxxxx, "deployment_name":"some_name", "deployment_id": "some_id", "flow_id": "some_id"}

    https://docs.prefect.io/api-ref/rest-api/#/
    """
    deployments_metadata = request_prefect_api(path="/deployments/filter", method="POST").json()

    deployments = []
    for deployment in deployments_metadata:
        if REPOSITORY_NAME in deployment["tags"]:
            deployments.append(
                {
                    "flow_name": get_cloud_account_flow_name(deployment["flow_id"]),
                    "flow_id": deployment["flow_id"],
                    "deployment_name": deployment["name"],
                    "deployment_id": deployment["id"],
                }
            )

    return deployments


def get_local_file_deployments() -> List[Dict]:
    """
    Reads the deploy/prefect/deployments.yml and returns a list Dicts with the schema of:
    {"flow_name": xxxxx, "deployment_name":"some_name"}
    """
    with open("deploy/prefect/deployments.yml") as f:
        deployments_yml = yaml.safe_load(f)["flows"]

    deployments = []
    for flow in deployments_yml:
        for deployment in flow["deployments"]:
            deployments.append(
                {
                    "flow_name": flow["flow_name"].replace("_", "-"),  # the prefect api replaces _ with - in the flow name
                    "deployment_name": deployment["name"],
                }
            )
    return deployments


def delete_flow(flow_id: str, flow_name: str) -> str:
    response = request_prefect_api(f"/flows/{flow_id}", method="DELETE")

    if response.status_code != 204:
        raise Exception(f"Failed to delete flow {flow_name} => {flow_id}: {response.text}")

    return flow_id


def delete_deployment(deployment_id: str, flow_deployment_name: str) -> str:
    response = request_prefect_api(f"/deployments/{deployment_id}", method="DELETE")

    if response.status_code != 204:
        raise Exception(f"Failed to delete deployment: {flow_deployment_name} => {deployment_id}: {response.text}")

    return deployment_id


def request_prefect_api(path: str, method: str) -> requests.Response:
    url = f"{PREFECT_API_URL}{path}"
    headers = {"Authorization": f"Bearer {PREFECT_API_KEY}", "Content-Type": "application/json"}

    return requests.request(method, url, headers=headers)


def get_cloud_account_flow_name(flow_id: str) -> str:
    """Get a flow id from a deployment id
    https://docs.prefect.io/api-ref/rest-api/#/
    """
    response = request_prefect_api(path=f"/flows/{flow_id}", method="GET")
    return response.json()["name"]


if __name__ == "__main__":
    local_deployments = get_local_file_deployments()
    cloud_deployments = get_cloud_account_deployments()

    delete_redundant_flows_and_deployments(local_deployments=local_deployments, cloud_deployments=cloud_deployments)
