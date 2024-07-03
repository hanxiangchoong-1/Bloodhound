# Use the official Python 3.9 image from the Docker Hub
FROM python:3.12.4-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app

# Install curl for the initialize_es.sh script
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Ensure the initialize_es.sh script is executable
RUN chmod +x /app/initialize_es.sh

# Expose the port the app runs on
EXPOSE 8000

# Run the initialize_es.sh script and then start the FastAPI app
ENTRYPOINT ["/bin/bash", "-c", "/app/initialize_es.sh && python /app/main.py"]