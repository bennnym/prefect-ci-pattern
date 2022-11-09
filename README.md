# prefect-ci-pattern

This is a very basic CI pattern that I have used to very much fit my use case.

It may not be very helpful to others, but I thought it could have some useful tidbits.

The general pattern for Prefect Deployment in my CI I am using is as follows:

1. Create Base Docker Image with all repo dependancies ( not included in repo )
2. Push Image to AWS ECR ( not included in repo )
3. [Deploy Prefect Infrastructure and Storage Block](deploy/prefect/infrastructure.py)
4. [Deploy Prefect "deployments"](deploy/scripts/build_apply_prefect.sh)
5. [Clean up cloud deployments](deploy/scripts/delete_redundant_deployments.py) to make sure they match what is in the deployments.yml file locally ( eg. when you remove a deployment from your local code ).

Dependancies are yq, prefect==2.X, prefect-aws-==0.1.7, boto3
