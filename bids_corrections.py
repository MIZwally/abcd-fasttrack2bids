#! /usr/bin/env python3

# The purpose of this script is to correct BIDS data in the outputs

# Importing the required libraries
import argparse
import logging
import os
import shutil

from bids import BIDSLayout
from dependencies.sefm_eval_and_json_editor import insert_edit_json
from dependencies.sefm_eval_and_json_editor import read_bids_layout
from dependencies.sefm_eval_and_json_editor import sefm_select
from dependencies.sefm_eval_and_json_editor import seperate_concatenated_fm
from logging import debug, info, warning, error, critical
from pathlib import Path
from utilities import readable, writable, available

# get the path to here
HERE = Path(__file__).parent.resolve()
dwi_tables = HERE / 'dependencies' / 'ABCD_Release_2.0_Diffusion_Tables'

# Set up logging
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# create help strings for the log level option
log_levels_str = "\n    ".join(LOG_LEVELS)


def cli():
    parser = argparse.ArgumentParser(description='Correct BIDS data')

    # very necessary arguments
    parser.add_argument('-b', '--bids', type=writable, required=True,
                        help='Path to the BIDS input directory')
    parser.add_argument('-t', '--temporary', type=available, required=True,
                        help='Path to the temporary directory for intermediary files')

    # optional arguments
    parser.add_argument('-l', '--log-level', metavar='LEVEL',
                        choices=LOG_LEVELS, default='INFO',
                        help="Set the minimum logging level. Defaults to INFO.\n"
                            "Options, in most to least verbose order, are:\n"
                            f"    {log_levels_str}")
    parser.add_argument('--dwiCorrectOldGE', action='store_true', required=False,
                        help='Correct any present "old" GE DV25 through DV28 '
                            'DWI BVAL and BVEC files.')

    parser.add_argument('--fmapSeparate', action='store_true', required=False,
                        help='Separate all concatenated field maps using the '
                            'DCAN-Labs/abcd-dicom2bids seperate_concatenated_fm function. '
                            'WARNING: Requires FSL as a dependency.')

    parser.add_argument('--dwifmapIntendedFor', action='store_true', required=False,
                        help='Assign IntendedFor fields to diffusion fmaps using the '
                            'DCAN-Labs/abcd-dicom2bids eta^2 technique.')

    parser.add_argument('--funcfmapIntendedFor', nargs=1, default=None, required=False,
                        metavar='MRE_DIR',
                        help='Assign IntendedFor fields to functional fmaps using the '
                            'DCAN-Labs/abcd-dicom2bids eta^2 technique. '
                            'This argument also triggers the --fmapSeparate option. '
                            'WARNING: Requires FSL and MATLAB Runtime Environment 9.1 as dependencies.')

    parser.add_argument('--anatDwellTime', action='store_true', required=False,
                        help='Inject the DwellTime field into the '
                            'anat JSON sidecar metadata files, '
                            'as recommended by the DCAN-Labs/abcd-dicom2bids repo.')

    parser.add_argument('--dwiTotalReadoutTime', action='store_true', required=False,
                        help='Inject the TotalReadoutTime field into the '
                            'dwi and dwi fmap JSON sidecar metadata files, '
                            'as recommended by the DCAN-Labs/abcd-dicom2bids repo.')

    parser.add_argument('--dwiEffectiveEchoSpacing', action='store_true', required=False,
                        help='Inject the EffectiveEchoSpacing field into the '
                            'dwi and dwi fmap JSON sidecar metadata files, '
                            'as recommended by the DCAN-Labs/abcd-dicom2bids repo.')

    parser.add_argument('--funcfmapEffectiveEchoSpacing', action='store_true', required=False,
                        help='Inject the EffectiveEchoSpacing field into the '
                            'func fmap JSON sidecar metadata files, '
                            'as recommended by the DCAN-Labs/abcd-dicom2bids repo.')

    parser.add_argument('--funcEffectiveEchoSpacing', action='store_true', required=False,
                        help='Inject the EffectiveEchoSpacing field into the '
                            'func JSON sidecar metadata files, '
                            'as recommended by the DCAN-Labs/abcd-dicom2bids repo.')

    parser.add_argument('--dwifmapPhaseEncodingDirection', action='store_true', required=False,
                        help='Inject the PhaseEncodingDirection field into the '
                            'dwi fmap JSON sidecar metadata files, '
                            'as recommended by the DCAN-Labs/abcd-dicom2bids repo.')

    parser.add_argument('--funcPhaseEncoding', action='store_true', required=False,
                        help='Make sure both the PhaseEncodingDirection and '
                            'PhaseEncodingAxis fields are present in the '
                            'func JSON sidecar metadata files, '
                            'as recommended by DCAN-Labs/abcd-dicom2bids.')

    parser.add_argument('--DCAN', nargs=1, default=None, required=False,
                        metavar='MRE_DIR',
                        help='Run all of the DCAN-Labs/abcd-dicom2bids recommendations. '
                            'WARNING: Requires FSL and MATLAB Runtime Environment 9.1 as dependencies.')

    return parser.parse_args()


def fsl_check():
    # Set FSLDIR environment variable
    if 'FSLDIR' not in os.environ and 'FSL_DIR' not in os.environ:
        raise Exception("Neither FSLDIR nor FSL_DIR environment variables are set. Unable to use as-is.")
    elif 'FSLDIR' not in os.environ:
        os.environ['FSLDIR'] = os.environ['FSL_DIR']
    elif 'FSL_DIR' not in os.environ:
        os.environ['FSL_DIR'] = os.environ['FSLDIR']

    # for this function's usage of FSLDIR
    fsl_dir = os.environ['FSLDIR'] + '/bin'

    return fsl_dir

def correct_old_GE_DV25_DV28(layout, subsess, args):
    for subject, sessions in subsess:

        # Check if there are any old GE DV25 through DV28 DWI BVAL and BVEC files
        dwi_niftis = layout.get(subject=subject, session=sessions, datatype='dwi', extension='.nii.gz')

        if dwi_niftis:
            for dwi_nifti in [os.path.join(x.dirname, x.filename) for x in dwi_niftis]:
                dwi_bval = dwi_nifti.replace('.nii.gz', '.bval')
                dwi_bvec = dwi_nifti.replace('.nii.gz', '.bvec')
                dwi_metadata = layout.get_metadata(dwi_nifti)

                if 'GE' in dwi_metadata['Manufacturer']:
                    for version in ['DV25', 'DV26', 'DV27', 'DV28', 'RX26', 'RX27', 'RX28']:
                        if version in dwi_metadata['SoftwareVersions']:
                            # correct the bval and bvec files
                            info(f'Overwriting the bval and bvec files for GE {version}: {dwi_nifti}')
                            if version == 'DV25':
                                shutil.copyfile(dwi_tables.joinpath('GE_bvals_DV25.txt'), dwi_bval)
                                shutil.copyfile(dwi_tables.joinpath('GE_bvecs_DV25.txt'), dwi_bvec)
                            else:
                                shutil.copyfile(dwi_tables.joinpath('GE_bvals_DV26.txt'), dwi_bval)
                                shutil.copyfile(dwi_tables.joinpath('GE_bvecs_DV26.txt'), dwi_bvec)

    return BIDSLayout(args.bids)


# Most of the following functions are based on the sefm_eval_and_json_editor.py main function

def separate_fmaps(layout, subsess, args):
    fsl_dir = fsl_check()

    for subject, sessions in subsess:

        # Check if there are any concatenated field maps
        fmaps = layout.get(subject=subject, session=sessions, datatype='fmap', extension='.nii.gz', acquisition='func', direction='both')

        if fmaps:
            info(f"Func fieldmaps for {subject}, {sessions} are concatenated. Running seperate_concatenated_fm.")
            seperate_concatenated_fm(layout, subject, sessions, fsl_dir)

            for fmap_nifti in [os.path.join(x.dirname, x.filename) for x in fmaps]:
                fmap_json = fmap_nifti.replace('.nii.gz', '.json')

                # remove the old concatenated field maps
                os.remove(fmap_nifti)
                os.remove(fmap_json)

            # recreate layout with the additional fmaps
            layout = BIDSLayout(args.bids)

    return layout


def assign_funcfmapIntendedFor(layout, subsess, args):
    fsl_dir = fsl_check()
    if args.DCAN != None:
        MRE_DIR = args.DCAN[0]
    elif args.funcfmapIntendedFor != None:
        MRE_DIR = args.funcfmapIntendedFor[0]
    else:
        raise Exception("No MRE_DIR provided for func fmap IntendedFor assignment.")

    debug(MRE_DIR)

    for subject, sessions in subsess:

        # Check if there are func fieldmaps and return a list of each SEFM pos/neg pair
        fmaps = layout.get(subject=subject, session=sessions, datatype='fmap', extension='.nii.gz', acquisition='func')

        if fmaps:
            info(f"Running SEFM select for {subject}, {sessions}")
            # base_temp_dir = fmaps[0].dirname
            base_temp_dir = args.temporary
            best_pos, best_neg = sefm_select(layout, subject, sessions, base_temp_dir, fsl_dir, MRE_DIR, debug=False)

    return BIDSLayout(args.bids)


def assign_dwifmapIntendedFor(layout, subsess, args):
    for subject, sessions in subsess:

        # grap the DWI NIfTIs and the AP dwi fmap JSON
        dwi_niftis = layout.get(subject=subject, session=sessions, datatype='dwi', suffix='dwi', extension='.nii.gz')
        APs = layout.get(subject=subject, session=sessions, datatype='fmap', acquisition='dwi', direction='AP', extension='.json')

        if dwi_niftis and APs:
            dwi_relpath = []
            for dwi_nifti in [os.path.join(x.dirname, x.filename) for x in dwi_niftis]:
                dwi_relpath += [os.path.relpath(dwi_nifti, str(args.bids))]

            # pick the first AP fmap to assign to all dwi scans
            sorted_APs = sorted([os.path.join(AP.dirname, AP.filename) for AP in APs])
            debug(sorted_APs)
            AP_json = sorted_APs[0]
            insert_edit_json(AP_json, 'IntendedFor', dwi_relpath)

    return BIDSLayout(args.bids)


def inject_anatDwellTime(layout, subsess, args):
    for subject, sessions in subsess:

        anat = layout.get(subject=subject, session=sessions, datatype='anat', extension='.nii.gz')

        if anat:
            for TX in [os.path.join(x.dirname, x.filename) for x in anat]:
                TX_json = TX.replace('.nii.gz', '.json') 
                TX_metadata = layout.get_metadata(TX)

                if 'GE' in TX_metadata['Manufacturer']:
                    insert_edit_json(TX_json, 'DwellTime', 0.000536)
                if 'Philips' in TX_metadata['Manufacturer']:
                    insert_edit_json(TX_json, 'DwellTime', 0.00062771)
                if 'Siemens' in TX_metadata['Manufacturer']:
                    insert_edit_json(TX_json, 'DwellTime', 0.000510012)

    return BIDSLayout(args.bids)


def inject_dwiTotalReadoutTime(layout, subsess, args):
    for subject, sessions in subsess:

        dwi = layout.get(subject=subject, session=sessions, datatype='dwi', suffix='dwi', extension='.nii.gz')
        fmap = layout.get(subject=subject, session=sessions, datatype='fmap', extension='.nii.gz', acquisition='dwi')

        scans = []
        if fmap:
            scans += [os.path.join(x.dirname, x.filename) for x in fmap]
        if dwi:
            scans += [os.path.join(x.dirname, x.filename) for x in dwi]

        for scan in scans:
            scan_json = scan.replace('.nii.gz', '.json')
            scan_metadata = layout.get_metadata(scan)

            if 'GE' in scan_metadata['Manufacturer']:
                if 'DV25' in scan_metadata['SoftwareVersions']:
                    insert_edit_json(scan_json, 'TotalReadoutTime', 0.104528)
                if 'DV26' in scan_metadata['SoftwareVersions']:
                    insert_edit_json(scan_json, 'TotalReadoutTime', 0.106752)
            if 'Philips' in scan_metadata['Manufacturer']:
                insert_edit_json(scan_json, 'TotalReadoutTime', 0.08976)
            if 'Siemens' in scan_metadata['Manufacturer']:
                insert_edit_json(scan_json, 'TotalReadoutTime', 0.0959097)

    return BIDSLayout(args.bids)


def inject_dwiEffectiveEchoSpacing(layout, subsess, args):
    for subject, sessions in subsess:

        dwi = layout.get(subject=subject, session=sessions, datatype='dwi', suffix='dwi', extension='.nii.gz')
        fmap = layout.get(subject=subject, session=sessions, datatype='fmap', extension='.nii.gz', acquisition='dwi')

        scans = []
        if fmap:
            scans += [os.path.join(x.dirname, x.filename) for x in fmap]
        if dwi:
            scans += [os.path.join(x.dirname, x.filename) for x in dwi]

        for scan in scans:
            scan_json = scan.replace('.nii.gz', '.json')
            scan_metadata = layout.get_metadata(scan)

            if 'GE' in scan_metadata['Manufacturer']:
                if 'DV25' in scan_metadata['SoftwareVersions']:
                    insert_edit_json(scan_json, 'EffectiveEchoSpacing', 0.000752)
                if 'DV26' in scan_metadata['SoftwareVersions']:
                    insert_edit_json(scan_json, 'EffectiveEchoSpacing', 0.000768)
            if 'Philips' in scan_metadata['Manufacturer']:
                insert_edit_json(scan_json, 'EffectiveEchoSpacing', 0.00062771)
            if 'Siemens' in scan_metadata['Manufacturer']:
                insert_edit_json(scan_json, 'EffectiveEchoSpacing', 0.000689998)

    return BIDSLayout(args.bids)


def inject_funcfmapEffectiveEchoSpacing(layout, subsess, args):
    for subject, sessions in subsess:

        fmap = layout.get(subject=subject, session=sessions, datatype='fmap', extension='.nii.gz', acquisition='func')

        if fmap:
            for fm in [os.path.join(x.dirname, x.filename) for x in fmap]:
                fm_json = fm.replace('.nii.gz', '.json')
                fm_metadata = layout.get_metadata(fm)

                if 'GE' in fm_metadata['Manufacturer']:
                    insert_edit_json(fm_json, 'EffectiveEchoSpacing', 0.000536)
                if 'Philips' in fm_metadata['Manufacturer']:
                    insert_edit_json(fm_json, 'EffectiveEchoSpacing', 0.00062771)
                if 'Siemens' in fm_metadata['Manufacturer']:
                    insert_edit_json(fm_json, 'EffectiveEchoSpacing', 0.000510012)
    
    return BIDSLayout(args.bids)


def inject_funcEffectiveEchoSpacing(layout, subsess, args):
    for subject, sessions in subsess:

        func = layout.get(subject=subject, session=sessions, datatype='func', extension='.nii.gz')

        if func:
            for task in [os.path.join(x.dirname, x.filename) for x in func]:
                task_json = task.replace('.nii.gz', '.json')
                task_metadata = layout.get_metadata(task)

                if 'GE' in task_metadata['Manufacturer']:
                    if 'DV26' in task_metadata['SoftwareVersions']:
                        insert_edit_json(task_json, 'EffectiveEchoSpacing', 0.000556)
                if 'Philips' in task_metadata['Manufacturer']:
                    insert_edit_json(task_json, 'EffectiveEchoSpacing', 0.00062771)
                if 'Siemens' in task_metadata['Manufacturer']:
                    insert_edit_json(task_json, 'EffectiveEchoSpacing', 0.000510012)
    
    return BIDSLayout(args.bids)


def inject_dwifmapPhaseEncodingDirection(layout, subsess, args):
    for subject, sessions in subsess:

        AP = layout.get(subject=subject, session=sessions, datatype='fmap', acquisition='dwi', direction='AP', extension='.nii.gz')
        PA = layout.get(subject=subject, session=sessions, datatype='fmap', acquisition='dwi', direction='PA', extension='.nii.gz')

        if AP:
            for fm in [os.path.join(x.dirname, x.filename) for x in AP]:
                fm_json = fm.replace('.nii.gz', '.json')
                insert_edit_json(fm_json, 'PhaseEncodingDirection', 'j-')
        if PA:
            for fm in [os.path.join(x.dirname, x.filename) for x in PA]:
                fm_json = fm.replace('.nii.gz', '.json')
                insert_edit_json(fm_json, 'PhaseEncodingDirection', 'j')

        # # this can't be right, can it?
        # # https://github.com/DCAN-Labs/abcd-dicom2bids/blame/main/src/sefm_eval_and_json_editor.py#L264
        # dwi = layout.get(subject=subject, session=sessions, datatype='dwi', suffix='dwi', extension='.nii.gz')

        # if dwi:
        #     for dwi_nifti in [os.path.join(x.dirname, x.filename) for x in dwi]:
        #         dwi_json = dwi_nifti.replace('.nii.gz', '.json')
        #         dwi_metadata = layout.get_metadata(dwi_nifti)

        #         if 'Philips' in dwi_metadata['Manufacturer']:
        #             insert_edit_json(dwi_json, 'PhaseEncodingDirection', 'j')

    return BIDSLayout(args.bids)


def add_PhaseEncodingAxisAndDirection(layout, subsess, args):
    for subject, sessions in subsess:

        # PE direction vs axis
        func = layout.get(subject=subject, session=sessions, datatype='func', extension='.nii.gz')

        if func:
            for task in [os.path.join(x.dirname, x.filename) for x in func]:
                task_json = task.replace('.nii.gz', '.json')
                task_metadata = layout.get_metadata(task)

                # add whichever field is missing based on the other
                if "PhaseEncodingAxis" in task_metadata:
                    insert_edit_json(task_json, 'PhaseEncodingDirection', task_metadata['PhaseEncodingAxis'])
                elif "PhaseEncodingDirection" in task_metadata:
                    insert_edit_json(task_json, 'PhaseEncodingAxis', task_metadata['PhaseEncodingDirection'].strip('-'))

    return BIDSLayout(args.bids)


def main():
    # Parse the command line
    args = cli()

    # Set up logging
    if args.log_level == 'DEBUG':
        logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
    elif args.log_level == 'INFO':
        logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    elif args.log_level == 'WARNING':
        logging.basicConfig(format=LOG_FORMAT, level=logging.WARNING)
    elif args.log_level == 'ERROR':
        logging.basicConfig(format=LOG_FORMAT, level=logging.ERROR)
    elif args.log_level == 'CRITICAL':
        logging.basicConfig(format=LOG_FORMAT, level=logging.CRITICAL)
    else:
        raise ValueError(f"Invalid log level: {args.log_level}")

    # Load the bids layout
    layout = BIDSLayout(args.bids)
    subsess = read_bids_layout(layout, subject_list=layout.get_subjects(), collect_on_subject=False)
    debug(subsess)

    # check if the DCAN argument was provided
    if args.DCAN != None:
        info("Running all DCAN-Labs/abcd-dicom2bids recommendations")

    # check if the old GE DV25 through DV28 argument was provided
    if args.dwiCorrectOldGE or args.DCAN != None:
        info("Correcting old GE DV25 through DV28 DWI BVAL and BVEC files")
        layout = correct_old_GE_DV25_DV28(layout, subsess, args)

    # check if the acq-dwi fmap IntendedFor argument was provided
    if args.dwifmapIntendedFor or args.DCAN != None:
        info("Assigning dwi fmap IntendedFor field")
        layout = assign_dwifmapIntendedFor(layout, subsess, args)

    # check if the acq-func fmap IntendedFor argument was provided
    # if so, also run the fmapSeparate option
    if args.funcfmapIntendedFor != None or args.DCAN != None:
        info("Separating concatenated field maps")
        layout = separate_fmaps(layout, subsess, args)

        info("Assigning func fmap IntendedFor fields")
        layout = assign_funcfmapIntendedFor(layout, subsess, args)
    # if not and the fmapSeparate option was passed without the funcfmapIntendedFor
    elif args.funcfmapIntendedFor == None and args.fmapSeparate:
        info("Separating concatenated field maps")
        layout = separate_fmaps(layout, subsess, args)

    # check if the anat DwellTime argument was provided
    if args.anatDwellTime or args.DCAN != None:
        info("Injecting anat DwellTime fields")
        layout = inject_anatDwellTime(layout, subsess, args)

    # check if the dwi fmap TotalReadoutTime argument was provided
    if args.dwiTotalReadoutTime or args.DCAN != None:
        info("Injecting dwi and dwi fmap TotalReadoutTime fields")
        layout = inject_dwiTotalReadoutTime(layout, subsess, args)

    # check if the dwi fmap EffectiveEchoSpacing argument was provided
    if args.dwiEffectiveEchoSpacing or args.DCAN != None:
        info("Injecting dwi and dwi fmap EffectiveEchoSpacing fields")
        layout = inject_dwiEffectiveEchoSpacing(layout, subsess, args)

    # check if the func fmap EffectiveEchoSpacing argument was provided
    if args.funcfmapEffectiveEchoSpacing or args.DCAN != None:
        info("Injecting func fmap EffectiveEchoSpacing fields")
        layout = inject_funcfmapEffectiveEchoSpacing(layout, subsess, args)

    # check if the func EffectiveEchoSpacing argument was provided
    if args.funcEffectiveEchoSpacing or args.DCAN != None:
        info("Injecting func EffectiveEchoSpacing fields")
        layout = inject_funcEffectiveEchoSpacing(layout, subsess, args)

    # check if the dwi fmap PhaseEncodingDirection argument was provided
    if args.dwifmapPhaseEncodingDirection or args.DCAN != None:
        info("Injecting dwi fmap PhaseEncodingDirection fields")
        layout = inject_dwifmapPhaseEncodingDirection(layout, subsess, args)

    # check if the PhaseEncoding argument was provided
    if args.funcPhaseEncoding or args.DCAN != None:
        info("Adding PhaseEncodingAxis and Direction fields")
        layout = add_PhaseEncodingAxisAndDirection(layout, subsess, args)


if __name__ == '__main__':
    main()
