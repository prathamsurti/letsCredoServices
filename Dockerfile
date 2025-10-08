# Use the official PostgreSQL image
FROM postgres:16

# Set environment variables
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=2410
ENV POSTGRES_DB=lets_credo_database

# Expose port
EXPOSE 5432
