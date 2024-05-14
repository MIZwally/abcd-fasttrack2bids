# ABCD NDA Fast Track to BIDS conversion tools

## To Do

### `fasttrack2s3.py`

- [ ] Make "special" inclusions and exclusions, like "Replaced" or ftq_complete==1, easier to do.
- [ ] Add a flag to optionally output one `abcd_fastqc01.txt` file per BIDS subject+session pairing instead of just one big file.
- [ ] Add flag to grab `--only-new` given a DSST ABCD fast-track `scans.tsv` file.
- [ ] Add additonal option to save out logs to a specific file.
- [ ] Add levels of log messages of warning/caution for the user to know what's going on with datatypes specifically.

### `run.py`

- [ ] Make the Pydra `run.py` script take as input either a single `abcd_fastqc01.txt` file, or a directory of them (to prepare for swarm submission).
- [ ] Add what's necessary to `run.py` to download to, work on, copy back from a temporary directory, and then delete the temporary directory contents responsibly.
- [ ] Add a flag to `run.py` to optionally run bids-validator on the output BIDS directory.

### Others

- [ ] Improve this `README.md` with a walkthrough of preparing the two NDA packages necessary for using this.

## Operating Procedure

Each numbered part of this list is one tool, which can be used independently. I will build a common usage pipeline out of it.

1. `fasttrack2s3.py`: Filter down the `abcd_fastqc01.txt` file based on user selection of data types, participants, and sessions, then output an `s3_links.txt`.
1. NDA Tools' `downloadcmd` on all the links in `s3_links.txt`, output to a single directory. Or maybe just use `downloadcmd` as-is?
1. ABCD DICOM TGZ unpack.
1. Dcm2Bids (v3) across all available unpacked DICOMs.
1. Grab unpacked event timing files and put them in the BIDS `sourcedata` directory.
1. (stretch goal) Ingest BIDS sidecar metadata from the DAIRC present in the unpacked TGZs
1. (optional) Automated sidecar JSON corrections for "EffectiveEchoSpacing".
1. (optional) Use bids-validator to log the validity of output data.

## Improvement Ideas

- Perhaps add arguments to a top-level wrapper, `fasttrack2bids.py`, to allow for controlling the overall workflow with some sane defaults and running options.

## Acknowledgements

Thanks to [`DCAN-Labs/abcd-dicom2bids`](https://github.com/DCAN-Labs/abcd-dicom2bids) for inspiration of the dcm2bids version 3 configuration JSON and general order of operations for the NDA's fast track conversion to BIDS.
