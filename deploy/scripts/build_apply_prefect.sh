#!/usr/bin/env bash

set -e

die () { echo "$1" >&2; exit 1; }
[[ -n "$ENVIRONMENT" ]] || { die "ENVIRONMENT env variable must be bound."; }
[[ -n "$REPOSITORY_NAME" ]] || { die "REPOSITORY_NAME env variable must be bound."; }
[[ -n "$PREFECT_API_KEY" ]] || { die "PREFECT_API_KEY env variable must be bound."; }
[[ -n "$PREFECT_API_URL" ]] || { die "PREFECT_API_URL env variable must be bound."; }

hash yq 2>/dev/null || { die "Missing dependency: yq"; }

deploymentsPath="deploy/prefect/deployments.yml"
flowsToDeploy=$(yq  '.flows | length' "$deploymentsPath")

repoFlowBucket="prefect-$REPOSITORY_NAME-$ENVIRONMENT"
echo "Deploying Infrastructure and Storage"
REPOSITORY_NAME=$REPOSITORY_NAME REPO_FLOW_BUCKET=$repoFlowBucket python ./deploy/prefect/infrastructure.py 2>&1


echo "Deploying $flowsToDeploy flows"  

for ((flowIndex=0; flowIndex < flowsToDeploy; flowIndex++)); do

    flow=$(yq  ".flows[$flowIndex]" "$deploymentsPath")
    flowName=$(echo "$flow" | yq '.flow_name' )
    
    deploymentsForFlow=$(yq  ".flows[$flowIndex].deployments | length" "$deploymentsPath")
    echo "Found $deploymentsForFlow deplopyments for flow $flowName"

    for ((deploymentIndex=0; deploymentIndex < deploymentsForFlow; deploymentIndex++)); do
        deployment=$(yq ".flows[$flowIndex].deployments[$deploymentIndex]" "$deploymentsPath")

        deploymentName=$(echo "$deployment" | yq '.name')
        flowPath=$(echo "$flow" | yq '.flow_path')
        cpu=$(echo "$deployment" | yq '.infra_overrides.cpu // 256')
        memory=$(echo "$deployment" | yq '.infra_overrides.memory // 512')
        parameters=$(echo "$deployment" | yq '.parameters // {}')
        schedule=$(echo "$deployment" | yq '.schedule // {}')
        outputDeployment="$flowName"-"$deploymentName".yaml

        echo "Building deployment $deploymentName for flow $flowName"

        prefect deployment build "$flowPath":"$flowName" \
            --name "$deploymentName" \
            --work-queue "$ENVIRONMENT" \
            --tag "$REPOSITORY_NAME" \
            --storage-block s3/"$REPOSITORY_NAME" \
            --infra-block ecs-task/"$REPOSITORY_NAME" \
            --path "$flowName" \
            --override cpu="$cpu" \
            --override memory="$memory" \
            --output "$outputDeployment" \
            --skip-upload

        echo "Adding deployment parameters to YAML"
        yq -i ".parameters = $parameters" "$outputDeployment"

        if [ "$ENVIRONMENT" == "prod" ] && [ "$schedule" != "{}" ]; then
            echo "Activating schedule for prod flow $flowName"
            yq -i ".schedule = $schedule" "$outputDeployment"
        elif [ "$ENVIRONMENT" == "prod" ] && [ "$schedule" == "{}" ]; then
            # if a flow is already registered, it appears as though the schedule is pre populated, so we need to remove it
            yq 'del(.schedule)' "$outputDeployment" > "$outputDeployment".tmp && mv "$outputDeployment".tmp "$outputDeployment"
        else
            echo "No schedule added for staging flow: $flowName, deployment: $deploymentName"
        fi


        prefect deployment apply "$outputDeployment" --upload
    done
done


PREFECT_API_URL=$PREFECT_API_URL PREFECT_API_KEY=$PREFECT_API_KEY REPOSITORY_NAME=$REPOSITORY_NAME python ./deploy/prefect/delete_redundany_deployments.py 2>&1
