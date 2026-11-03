<#
.SYNOPSIS
    AgriKafka-Agent Local Kafka Infrastructure Management Script (Windows / PowerShell)
.DESCRIPTION
    Provides clean local lifecycle commands for starting, inspecting, testing, and stopping
    the single-broker KRaft Kafka development cluster without data loss.
#>

param (
    [Parameter(Position=0)]
    [ValidateSet("start", "status", "topics-init", "topics-list", "smoke-test", "persist-test", "stop", "down")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"

function Show-Header {
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host " AgriKafka-Agent — Kafka Infrastructure Manager (PowerShell)" -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
}

Show-Header

switch ($Action) {
    "start" {
        Write-Host "`n[STARTING] Launching Kafka KRaft container..." -ForegroundColor Yellow
        docker compose up -d kafka
        Write-Host "Waiting for Kafka broker to report healthy on port 9092..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        docker compose ps kafka
        Write-Host "`nBroker is starting. To provision topics, run: .\infra\kafka\manage.ps1 topics-init" -ForegroundColor Green
    }

    "status" {
        Write-Host "`n[STATUS] Inspecting Kafka container and health..." -ForegroundColor Yellow
        docker compose ps kafka
    }

    "topics-init" {
        Write-Host "`n[TOPICS] Declaratively provisioning AgriKafka core topics..." -ForegroundColor Yellow
        uv run python infra/kafka/init_topics.py --bootstrap-server 127.0.0.1:9092
    }

    "topics-list" {
        Write-Host "`n[INSPECT] Listing all topics, partitions, and replication..." -ForegroundColor Yellow
        uv run python infra/kafka/init_topics.py --bootstrap-server 127.0.0.1:9092 --inspect-only
    }

    "smoke-test" {
        Write-Host "`n[SMOKE TEST] Running end-to-end producer-consumer verification..." -ForegroundColor Yellow
        uv run python infra/kafka/smoke_test.py 127.0.0.1:9092
    }

    "persist-test" {
        Write-Host "`n[PERSISTENCE DRILL] Verifying volume persistence across container restart..." -ForegroundColor Yellow
        uv run python infra/kafka/verify_persistence.py 127.0.0.1:9092
    }

    "stop" {
        Write-Host "`n[STOPPING] Gracefully stopping Kafka container (Volume retained)..." -ForegroundColor Yellow
        docker compose stop kafka
        Write-Host "Kafka stopped. Data is preserved in volume 'agrikafka_dev_data'." -ForegroundColor Green
    }

    "down" {
        Write-Host "`n[DOWN] Stopping and removing container (Volume retained)..." -ForegroundColor Yellow
        docker compose down
        Write-Host "Container removed. Volume 'agrikafka_dev_data' was NOT deleted." -ForegroundColor Green
    }
}
