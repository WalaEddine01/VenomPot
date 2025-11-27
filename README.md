# VenomPot

A minimal starter repository for a future honeypot project.

## Setup

1. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

2. Create the data directory:
   ```bash
   mkdir -p data
   ```

3. Build and run the stack:
   ```bash
   cd compose
   docker compose up --build
   ```