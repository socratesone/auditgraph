# System Architecture

## Overview

The application uses a three-tier architecture with a React frontend, FastAPI backend, and PostgreSQL database.

## Components

### API Gateway
Routes incoming requests to appropriate microservices. Handles authentication via JWT tokens.

### Data Pipeline
Processes incoming events through a Kafka queue, transforms them, and stores results in the database.

### Monitoring
Uses Prometheus for metrics collection and Grafana for visualization.
