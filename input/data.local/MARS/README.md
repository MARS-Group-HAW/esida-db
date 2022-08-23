# How to run the simulation

If you are on the macOS platform you can run the `./run.sh`, otherwise follow these steps:

1. Extract the applicable box for your architecture
2. Merge (!) the `./resources/` folder into the `./<box>/<box>/resources/` folder
3. Run the simulation with the binary inside your box folder


# Analyze the simulation

The provided Jupyter Notebook `OutputVisualization` has some basic visualizations for analyzing the input and the simulation. If you have not the required Python packages installed on your system usage of the provided Docker image is recommended. Start the dockerized Jupyter hub with `./docker-jupyter-hub.sh`.
