#!/usr/bin/env bash
# Innovation Sprint 2026 — GPU instance control.
#
# A g6e.xlarge costs roughly $1.86/hour against a $100 team budget.
# Leaving it running overnight is most of a day's budget for nothing.
# Stopping preserves the disk and everything installed on it.
#
# Usage:  ./instance.sh status | start | stop | connect | cost | uptime | dcv

set -euo pipefail

# Set these for your own environment, or export them before running.
# Deliberately not hard-coded: this file is published, and instance/security
# group identifiers are reconnaissance material even though they are not secrets.
INSTANCE_ID="${CRASHLAB_INSTANCE_ID:?set CRASHLAB_INSTANCE_ID (e.g. i-0abc123...)}"
REGION="${CRASHLAB_REGION:-us-east-1}"
PROFILE="${AWS_PROFILE:-hackathon}"
HOURLY_USD="${CRASHLAB_HOURLY_USD:-1.86}"   # g6e.xlarge on-demand, us-east-1
DCV_SG="${CRASHLAB_DCV_SG:-}"               # security group to open DCV on
DCV_PORT="${CRASHLAB_DCV_PORT:-8443}"

aws_() { aws "$@" --region "$REGION" --profile "$PROFILE"; }

require_login() {
  if ! aws_ sts get-caller-identity >/dev/null 2>&1; then
    echo "Not logged in. Run:  aws sso login --sso-session presidio-hack" >&2
    exit 1
  fi
}

state() {
  aws_ ec2 describe-instances --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' --output text
}

case "${1:-status}" in

  status)
    require_login
    aws_ ec2 describe-instances --instance-ids "$INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].{State:State.Name,Type:InstanceType,PublicIP:PublicIpAddress,Launched:LaunchTime}' \
      --output table
    echo "SSM agent registration:"
    aws_ ssm describe-instance-information \
      --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
      --query 'InstanceInformationList[0].{Ping:PingStatus,Platform:PlatformName,Agent:AgentVersion}' \
      --output table 2>/dev/null || echo "  (not registered — ask the tech team)"
    ;;

  start)
    require_login
    aws_ ec2 start-instances --instance-ids "$INSTANCE_ID" \
      --query 'StartingInstances[0].CurrentState.Name' --output text
    echo "Starting. Billing has resumed. Waiting for running state..."
    aws_ ec2 wait instance-running --instance-ids "$INSTANCE_ID"
    echo "Running. Public IP:"
    aws_ ec2 describe-instances --instance-ids "$INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
    echo "NOTE: the public IP changes on every stop/start unless an Elastic IP is attached."
    ;;

  stop)
    require_login
    aws_ ec2 stop-instances --instance-ids "$INSTANCE_ID" \
      --query 'StoppingInstances[0].CurrentState.Name' --output text
    echo "Stopping. Compute billing ends once stopped; the disk is preserved."
    ;;

  connect)
    require_login
    if [[ "$(state)" != "running" ]]; then
      echo "Instance is not running. Start it first:  ./instance.sh start" >&2
      exit 1
    fi
    exec aws_ ssm start-session --target "$INSTANCE_ID"
    ;;

  uptime)
    require_login
    launched=$(aws_ ec2 describe-instances --instance-ids "$INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].LaunchTime' --output text)
    echo "Launched:       $launched"
    echo "Current state:  $(state)"
    echo
    echo "Compute cost accrues only while running, at ~\$${HOURLY_USD}/hour."
    echo "Check real spend with:  ./instance.sh cost"
    ;;

  cost)
    require_login
    echo "Month-to-date spend by service (unblended):"
    start_of_month="$(date +%Y-%m-01)"
    tomorrow="$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d tomorrow +%Y-%m-%d)"
    aws ce get-cost-and-usage \
      --time-period "Start=${start_of_month},End=${tomorrow}" \
      --granularity MONTHLY --metrics UnblendedCost \
      --group-by Type=DIMENSION,Key=SERVICE \
      --region us-east-1 --profile "$PROFILE" \
      --query 'ResultsByTime[0].Groups[].[Keys[0],Metrics.UnblendedCost.Amount]' \
      --output table
    echo
    echo "Team budget is \$100. Cost Explorer data can lag several hours."
    ;;

  dcv|dcv-clean)
    if [[ -z "$DCV_SG" ]]; then
      echo "set CRASHLAB_DCV_SG to the security group id first" >&2
      exit 1
    fi
    # This connection alternates between a couple of public addresses, so the
    # rule is ADDITIVE: authorise wherever we are now and leave previously
    # authorised addresses alone. Revoking the "stale" one just guarantees the
    # rule is wrong again after the next flip. Each entry is still a single /32.
    # Use `dcv-clean` to prune back to only the current address.
    require_login
    ip="$(curl -fsS https://checkip.amazonaws.com | tr -d '[:space:]')"
    if [[ -z "$ip" ]]; then
      echo "could not determine your public IP" >&2
      exit 1
    fi
    echo "your public IP: $ip"

    existing=$(aws_ ec2 describe-security-groups --group-ids "$DCV_SG" \
      --query "SecurityGroups[0].IpPermissions[?FromPort==\`$DCV_PORT\`].IpRanges[].CidrIp" \
      --output text)

    if [[ "$1" == "dcv-clean" ]]; then
      for cidr in $existing; do
        if [[ "$cidr" != "$ip/32" ]]; then
          echo "revoking $cidr"
          aws_ ec2 revoke-security-group-ingress --group-id "$DCV_SG" \
            --ip-permissions "IpProtocol=tcp,FromPort=$DCV_PORT,ToPort=$DCV_PORT,IpRanges=[{CidrIp=$cidr}]" \
            >/dev/null
        fi
      done
      existing="$ip/32"
    else
      [[ -n "$existing" ]] && echo "already authorised: $existing"
    fi

    if [[ " $existing " != *" $ip/32 "* ]]; then
      aws_ ec2 authorize-security-group-ingress --group-id "$DCV_SG" \
        --ip-permissions "IpProtocol=tcp,FromPort=$DCV_PORT,ToPort=$DCV_PORT,IpRanges=[{CidrIp=$ip/32,Description=\"Amazon DCV\"}]" \
        >/dev/null
      echo "authorised $ip/32 on port $DCV_PORT"
    else
      echo "already authorised"
    fi

    public_ip=$(aws_ ec2 describe-instances --instance-ids "$INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    echo
    echo "open:  https://${public_ip}:${DCV_PORT}"
    echo "log in as 'ubuntu'. If the login is rejected, the account has no"
    echo "password yet — set one with 'passwd ubuntu' via ./instance.sh connect."
    ;;

  *)
    echo "Usage: $0 {status|start|stop|connect|cost|uptime|dcv}" >&2
    exit 1
    ;;
esac
