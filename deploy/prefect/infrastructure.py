import os

import boto3
from prefect.filesystems import S3
from prefect_aws.ecs import ECSTask

# https://docs.prefect.io/concepts/deployments/#create-a-deployment


def build_and_save_ecs_task(repo_name: str):
    default_params = {}  # add your dict of default params here
    account_number = boto3.client("sts").get_caller_identity()["Account"]

    ecs = ECSTask(
        name=repo_name,
        image=f"{account_number}.dkr.ecr.ap-southeast-2.amazonaws.com/{repo_name}:latest",
        cpu=512,
        memory=256,
        **default_params,
    )
    ecs.save(name=repo_name, overwrite=True)


def build_and_save_s3_storage(repo_name: str, repo_flow_bucket: str) -> None:
    storage = S3(bucket_path=repo_flow_bucket)
    storage.save(name=repo_name, overwrite=True)


if __name__ == "__main__":
    REPOSITORY_NAME = os.getenv("REPOSITORY_NAME")
    REPO_FLOW_BUCKET = os.getenv("REPO_FLOW_BUCKET")

    if REPOSITORY_NAME is None:
        raise Exception("REPOSITORY_NAME is not set, please set it in your environment")

    if REPO_FLOW_BUCKET is None:
        raise Exception("REPO_FLOW_BUCKET is not set, please set it in your environment")

    print(f"💾 Saving ecs infrastructureas: ecs/{REPOSITORY_NAME}")
    build_and_save_ecs_task(REPOSITORY_NAME)
    print("➡️  Infrastructure deployed ✅")
    print(f"💾 Saving s3 storage as: s3/{REPOSITORY_NAME}")
    build_and_save_s3_storage(REPOSITORY_NAME, REPO_FLOW_BUCKET)
    print("➡️  Storage deployed ✅")
