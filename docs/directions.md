# Downloading and Converting

## 1. Download fastqc file

This involves using `downloadcmd` which is part of the `nda-tools` package. You will need the package id for the fastqc data package created earlier. See the `nda-tools` documentation for more information about using `downloadcmd`.

Once the package is downloaded, locate the `abcd_fastqc01.txt` file and make note of its path, as it will be needed for the next step.


## 2. Run swarm.sh

Before you run this script, make sure to check the inputs and modify them to fit your conversion needs. You will need the `abcd_fastqc01.txt` path here, as well as paths to both a .csv file containing all of the sessions you want to download and a version of the `MATLAB Compiler Runtime Environment (MCR)`.

See `README.md` for tips on how to properly the script. The result will be a `.swarm` file for you to run to execute the download and conversion of the data. Additionally, the terminal command for running the new swarm file is printed in the output for your convenience.


## 3. Run swarm job

We recommend you use the command outputted from 'swarm.sh' to run your swarm. The '.swarm' file created contains a header with specifications that are optimal for the job.
