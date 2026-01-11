Here are the commands to run the project:

# 1. Make sure Docker services are running (Postgres + Redis)

make up

# 2. Activate the virtual environment

source .venv/bin/activate

# 3. Start the dev server

make dev
The server will start at http://localhost:8000.

To verify it's working, in another terminal:

# Health check

curl http://localhost:8000/api/v1/public/health

# Readiness check (verifies DB + Redis connections)

curl http://localhost:8000/api/v1/public/health/ready

# View API docs in browser

open http://localhost:8000/docs
If you get port conflicts (local Postgres running):

brew services stop postgresql@17 # or your version
Quick one-liner to start everything:

make up && source .venv/bin/activate && make dev

make up # Start Docker (Postgres + Redis)
make dev # Start API server
make test # Run tests
make lint # Run linter
make migrate msg="description" # Generate & apply migrations

GO through the CLAUDE.md file to understand the project and continue development.
