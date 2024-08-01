# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the necessary files into the container
COPY pyget-cli.py /app/
COPY pyget-cli.spec /app/

# Install the necessary dependencies
RUN apt-get update && apt-get install -y binutils
RUN pip install requests pyinstaller

# Create the executable
RUN pyinstaller pyget-cli.spec

# Set the entrypoint to bash to keep the container running
ENTRYPOINT ["bash"]
