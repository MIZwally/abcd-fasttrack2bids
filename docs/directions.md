# Downloading and Converting

## Requirements for running `swarm.sh`

- `abcd-fastqc01.txt`
- a `.csv` file containing all session ids to be converted
- access to the `MATLAB Compiler Runtime Environment (MCR)`

## 2. Run swarm.sh

Before you run this script, make sure to check the inputs and modify them to fit your conversion needs. You will need the `abcd_fastqc01.txt` path here, as well as paths to both a .csv file containing all of the sessions you want to download and a version of the `MATLAB Compiler Runtime Environment (MCR)`.

See `README.md` for tips on how to properly the script. The result will be a `.swarm` file for you to run to execute the download and conversion of the data. Additionally, the terminal command for running the new swarm file is printed in the output for your convenience.


## 3. Run swarm job

We recommend you use the command outputted from 'swarm.sh' to run your swarm. The '.swarm' file created contains a header with specifications that are optimal for the job.
