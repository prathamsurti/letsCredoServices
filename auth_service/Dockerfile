FROM python:3.10-slim

WORKDIR /app

# Install uv, a fast Python package installer
RUN pip install uv

# Create a virtual environment in /opt/venv
RUN python -m venv /opt/venv

# Add the virtual environment's bin directory to the PATH
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt .

# Install dependencies into the virtual environment using uv
RUN uv pip install --no-cache -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8001

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]